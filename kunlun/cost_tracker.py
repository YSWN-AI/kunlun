"""
昆仑创作引擎 — LLM 成本追踪与预算控制器

基于 awesome-llm-token-optimization 的成本管理最佳实践。
提供精确到每次调用的 Token 用量、费用计算、预算预警。

核心能力：
  1. 实时 Token 计数 — 输入/输出 Token 精确追踪
  2. 模型级计费 — 按实际 API 定价计算（支持 10+ 模型）
  3. 预算控制 — 多级预算（日/月/项目），逼近上限自动降级
  4. 成本分析 — 按 Agent/章节/模型维度的费用分布
  5. 告警通知 — 预算告警/异常用量检测/成本异常飙升
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger


class BudgetTier(Enum):
    """预算等级 — 不同等级对应不同模型策略"""

    UNLIMITED = "unlimited"  # 预算充足，可用最贵模型
    NORMAL = "normal"  # 正常预算
    CONSERVATIVE = "conservative"  # 预算紧张，优先便宜模型
    CRITICAL = "critical"  # 预算告急，仅用最便宜模型
    EXCEEDED = "exceeded"  # 预算已超，停止调用


# ═══════════════════════════════════════════════════════════════
# 模型定价表（2026年参考价，$/1M tokens）
# ═══════════════════════════════════════════════════════════════

MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI 系列
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Anthropic 系列
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    # DeepSeek 系列
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # 开源/其他
    "qwen-plus": {"input": 0.80, "output": 2.00},
    "qwen-turbo": {"input": 0.30, "output": 0.60},
    "glm-4": {"input": 0.10, "output": 0.10},
    # 默认（未知模型）
    "default": {"input": 1.00, "output": 4.00},
}

# 模型成本等级
MODEL_COST_TIER: dict[str, int] = {
    "gpt-4o": 100,
    "gpt-4-turbo": 100,
    "claude-sonnet-4-20250514": 100,
    "deepseek-reasoner": 60,
    "o3-mini": 60,
    "deepseek-chat": 30,
    "qwen-plus": 30,
    "glm-4": 20,
    "gpt-4o-mini": 15,
    "claude-3-5-haiku": 15,
    "qwen-turbo": 15,
}


@dataclass
class CallRecord:
    """单次 LLM 调用记录"""

    timestamp: float
    model: str
    provider: str  # openai/deepseek/anthropic
    agent: str  # 调用方（architect/writer/auditor）
    action: str  # 调用目的（generate/audit/polish）
    book_id: str
    chapter: int
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    cached: bool = False  # 是否命中缓存
    compressed: bool = False  # 是否使用了压缩


@dataclass
class BudgetStatus:
    """预算状态"""

    tier: BudgetTier
    daily_used: float  # 今日已用 ($)
    daily_limit: float  # 今日预算 ($)
    monthly_used: float  # 本月已用 ($)
    monthly_limit: float  # 本月预算 ($)
    project_used: float  # 本书已用 ($)
    project_limit: float  # 本书预算 ($)
    total_calls: int
    cached_calls: int
    compressed_calls: int


@dataclass
class CostReport:
    """费用报告"""

    period: str  # daily/monthly/project
    total_cost: float  # 总费用
    total_tokens: int  # 总 Token
    by_model: dict[str, float]  # 按模型
    by_agent: dict[str, float]  # 按 Agent
    by_action: dict[str, float]  # 按操作类型
    savings_from_cache: float  # 缓存节省
    savings_from_compression: float  # 压缩节省
    trend: list[float] = field(default_factory=list)  # 费用趋势


class CostTracker:
    """LLM 成本追踪器

    使用方式：
      tracker = CostTracker()

      # 记录调用
      tracker.record(
          model="deepseek-chat", provider="deepseek",
          agent="writer", action="generate",
          book_id="mybook", chapter=5,
          input_tokens=2000, output_tokens=500,
          latency_ms=1200,
      )

      # 检查预算
      if tracker.is_budget_available():
          # 正常调用
          pass
      else:
          # 降级到更便宜的模型
          fallback_model = tracker.suggest_fallback()
    """

    # 预算阈值
    BUDGET_WARNING_RATIO: ClassVar[float] = 0.70  # 70% → 保守模式
    BUDGET_CRITICAL_RATIO: ClassVar[float] = 0.90  # 90% → 告急模式

    def __init__(
        self,
        daily_limit: float = 2.0,  # 每日预算 ($)
        monthly_limit: float = 50.0,  # 每月预算 ($)
        project_limit: float = 10.0,  # 每本书预算 ($)
        data_dir: str = "data",
    ) -> None:
        self._daily_limit = daily_limit
        self._monthly_limit = monthly_limit
        self._project_limit = project_limit
        self._data_dir = Path(data_dir) / "cost_tracker"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # 调用记录 — 单一可信数据源
        self._records: list[CallRecord] = []
        # 按项目快速索引（指向 _records 中相同对象的引用，不复制）
        self._project_calls: dict[str, list[CallRecord]] = defaultdict(list)

        # 从磁盘恢复
        self._load()

    # ── 记录 API ────────────────────────────────

    def record(
        self,
        model: str,
        provider: str,
        agent: str,
        action: str,
        book_id: str,
        chapter: int,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float = 0.0,
        cached: bool = False,
        compressed: bool = False,
    ) -> CallRecord:
        """记录一次 LLM 调用"""
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        record = CallRecord(
            timestamp=time.time(),
            model=model,
            provider=provider,
            agent=agent,
            action=action,
            book_id=book_id,
            chapter=chapter,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            cached=cached,
            compressed=compressed,
        )

        self._records.append(record)
        self._project_calls[book_id].append(record)

        # 检查预算
        status = self.get_budget_status(book_id)
        if status.tier in (BudgetTier.CRITICAL, BudgetTier.EXCEEDED):
            logger.warning(
                f"[CostTracker] 预算告警: {status.tier.value} "
                f"(日 {status.daily_used:.2f}/{status.daily_limit:.2f})"
            )

        return record

    def is_budget_available(self, book_id: str = "") -> bool:
        """检查预算是否可用"""
        status = self.get_budget_status(book_id)
        return status.tier != BudgetTier.EXCEEDED

    def get_budget_tier(self, book_id: str = "") -> BudgetTier:
        """获取当前预算等级"""
        return self.get_budget_status(book_id).tier

    def get_budget_status(self, book_id: str = "") -> BudgetStatus:
        """获取当前预算状态"""
        now = time.time()
        day_start = now - (now % 86400)  # 当天0点
        month_start = now - 30 * 86400   # 30天滚动窗口

        # 从单一数据源按时间窗口筛选，避免数据不一致
        daily_used = sum(r.cost_usd for r in self._records if r.timestamp >= day_start)
        monthly_used = sum(r.cost_usd for r in self._records if r.timestamp >= month_start)
        project_used = (
            sum(r.cost_usd for r in self._project_calls.get(book_id, [])) if book_id else 0.0
        )

        # 确定预算等级
        daily_ratio = daily_used / max(self._daily_limit, 0.01)
        monthly_ratio = monthly_used / max(self._monthly_limit, 0.01)

        if daily_ratio >= 1.0 or monthly_ratio >= 1.0:
            tier = BudgetTier.EXCEEDED
        elif daily_ratio >= self.BUDGET_CRITICAL_RATIO:
            tier = BudgetTier.CRITICAL
        elif daily_ratio >= self.BUDGET_WARNING_RATIO:
            tier = BudgetTier.CONSERVATIVE
        else:
            tier = BudgetTier.NORMAL

        cached = sum(1 for r in self._records if r.cached)
        compressed = sum(1 for r in self._records if r.compressed)

        return BudgetStatus(
            tier=tier,
            daily_used=daily_used,
            daily_limit=self._daily_limit,
            monthly_used=monthly_used,
            monthly_limit=self._monthly_limit,
            project_used=project_used,
            project_limit=self._project_limit,
            total_calls=len(self._records),
            cached_calls=cached,
            compressed_calls=compressed,
        )

    def suggest_fallback(self, current_model: str = "") -> str:
        """当预算紧张时，推荐更便宜的模型"""
        # 获取当前模型的成本等级
        current_tier = MODEL_COST_TIER.get(current_model, 50)

        # 预算不足时降级策略
        fallbacks = [
            ("deepseek-chat", 30),  # 性价比之王
            ("qwen-turbo", 15),  # 极便宜
            ("gpt-4o-mini", 15),  # 标准便宜选项
            ("glm-4", 20),  # 中文便宜
        ]

        for model, cost_tier in fallbacks:
            if cost_tier < current_tier:
                logger.info(f"[CostTracker] 预算降级: {current_model} → {model}")
                return model

        return "deepseek-chat"  # 最终fallback

    # ── 报告 API ────────────────────────────────

    def generate_report(self, period: str = "daily", book_id: str = "") -> CostReport:
        """生成费用报告

        Args:
            period: daily/monthly/project
            book_id: 指定书籍（project模式必填）
        """
        now = time.time()
        if period == "daily":
            cutoff = now - 86400
            records = [r for r in self._records if r.timestamp >= cutoff]
        elif period == "monthly":
            cutoff = now - 30 * 86400
            records = [r for r in self._records if r.timestamp >= cutoff]
        else:
            records = self._project_calls.get(book_id, [])

        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.input_tokens + r.output_tokens for r in records)

        by_model: dict[str, float] = defaultdict(float)
        by_agent: dict[str, float] = defaultdict(float)
        by_action: dict[str, float] = defaultdict(float)
        cache_savings = 0.0
        compression_savings = 0.0

        for r in records:
            by_model[r.model] += r.cost_usd
            by_agent[r.agent] += r.cost_usd
            by_action[r.action] += r.cost_usd
            if r.cached:
                cache_savings += r.cost_usd
            if r.compressed:
                compression_savings += r.cost_usd * 0.4  # 预估节省40%

        return CostReport(
            period=period,
            total_cost=round(total_cost, 4),
            total_tokens=total_tokens,
            by_model=dict(by_model),
            by_agent=dict(by_agent),
            by_action=dict(by_action),
            savings_from_cache=round(cache_savings, 4),
            savings_from_compression=round(compression_savings, 4),
        )

    def get_summary(self) -> dict[str, Any]:
        """获取摘要（供API返回）"""
        status = self.get_budget_status()
        daily_report = self.generate_report("daily")

        return {
            "budget": {
                "tier": status.tier.value,
                "daily_used": round(status.daily_used, 4),
                "daily_limit": status.daily_limit,
                "daily_ratio": round(status.daily_used / max(status.daily_limit, 0.01), 3),
                "monthly_used": round(status.monthly_used, 4),
                "monthly_limit": status.monthly_limit,
            },
            "usage": {
                "total_calls": status.total_calls,
                "cached_calls": status.cached_calls,
                "cached_ratio": round(status.cached_calls / max(status.total_calls, 1), 3),
                "compressed_calls": status.compressed_calls,
            },
            "daily_cost": {
                "total": daily_report.total_cost,
                "by_model": daily_report.by_model,
                "by_agent": daily_report.by_agent,
                "savings_from_cache": daily_report.savings_from_cache,
                "savings_from_compression": daily_report.savings_from_compression,
            },
        }

    # ── 内部方法 ────────────────────────────────

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算单次调用费用"""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        return (
            pricing["input"] * input_tokens / 1_000_000
            + pricing["output"] * output_tokens / 1_000_000
        )

    def _load(self) -> None:
        """从磁盘恢复调用记录"""
        path = self._data_dir / "records.jsonl"
        if not path.exists():
            return
        try:
            count = 0
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        record = CallRecord(**data)
                        self._records.append(record)
                        self._project_calls[record.book_id].append(record)
                        count += 1
                    except (TypeError, ValueError, KeyError) as e:
                        logger.debug(f"[CostTracker] 跳过无效记录: {e}")
            logger.info(f"[CostTracker] 从磁盘恢复: {count} 条记录")
        except OSError as e:
            logger.warning(f"[CostTracker] 磁盘加载失败: {e}")

    def save(self) -> None:
        """持久化调用记录到磁盘"""
        try:
            path = self._data_dir / "records.jsonl"
            # 只保存最近10000条
            recent = self._records[-10000:]
            with path.open("w", encoding="utf-8") as f:
                for r in recent:
                    f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.debug(f"[CostTracker] 持久化失败: {e}")

    def set_budget(
        self,
        daily: float | None = None,
        monthly: float | None = None,
        project: float | None = None,
    ) -> None:
        """动态调整预算"""
        if daily is not None:
            self._daily_limit = daily
        if monthly is not None:
            self._monthly_limit = monthly
        if project is not None:
            self._project_limit = project
        logger.info(
            f"[CostTracker] 预算已更新: 日={self._daily_limit}, "
            f"月={self._monthly_limit}, 项目={self._project_limit}"
        )

    def clear_old_records(self, days: int = 90) -> int:
        """清除过期记录"""
        cutoff = time.time() - days * 86400
        before = len(self._records)
        self._records = [r for r in self._records if r.timestamp >= cutoff]
        # 同步清理 project 索引
        for book_id in list(self._project_calls.keys()):
            self._project_calls[book_id] = [
                r for r in self._project_calls[book_id] if r.timestamp >= cutoff
            ]
            if not self._project_calls[book_id]:
                del self._project_calls[book_id]
        removed = before - len(self._records)
        if removed > 0:
            logger.info(f"[CostTracker] 清除 {removed} 条过期记录")
        return removed


# 全局单例
cost_tracker = CostTracker()

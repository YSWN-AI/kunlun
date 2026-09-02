"""
Token用量追踪 + 预算控制 — 按作品/Agent统计费用 + 前置配额管理

对应 inkos 的成本管控功能
"""

from __future__ import annotations

import contextlib
import json
import time
from dataclasses import dataclass

from loguru import logger

from kunlun.config import settings

# 模型价格 (每1M token的美元价格，2026年参考)
MODEL_PRICES = {
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
}

# 预算等级（每章最大tokens，适用于 DeepSeek-chat）
BUDGET_TIERS = {
    "economy": 30000,  # 经济档：单模型+核心推演
    "standard": 80000,  # 标准档：3模型并行+标准推演
    "premium": 150000,  # 高级档：5模型+全推演
    "unlimited": 999999,  # 无限制
}

# 各Agent的预算分配比例（占每章总预算的百分比）
AGENT_BUDGET_RATIO = {
    "architect": 0.08,  # 蓝图 8%
    "writer": 0.25,  # 写作 25%
    "sociologist": 0.35,  # 推演 35% (核心成本)
    "auditor": 0.0,  # 审计 0% (纯规则)
    "reviser": 0.20,  # 修订 20%
    "icu": 0.07,  # ICU 7%
    "reflector": 0.05,  # 反思 5%
}


@dataclass
class UsageRecord:
    timestamp: float
    book_id: str
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    operation: str = ""


class BudgetExceeded(Exception):
    """预算超限异常"""

    pass


class TokenTracker:
    """Token用量追踪器 + 预算控制器

    成本控制分层：
    1. 每章预算（tier-based）— init_chapter_budget / check_budget / spend
    2. 每日Token预算（.env: LLM_DAILY_TOKEN_BUDGET）— 全局日配额
    3. 每小时调用频率（.env: LLM_MAX_CALLS_PER_HOUR）— 滑动窗口限流
    """

    def __init__(self):
        self.tracker_dir = settings.DATA_DIR / "usage"
        self.tracker_dir.mkdir(parents=True, exist_ok=True)
        # 每章预算控制（运行期状态）
        self._chapter_budgets: dict[str, dict] = {}
        # 每日Token预算（运行期状态）
        self._daily_tokens: int = 0
        self._daily_reset_day: int = -1  # 记录上次重置的日期（0=周一）
        # 每小时调用次数（滑动窗口）
        self._hourly_calls: list[float] = []  # 调用时间戳列表

    def init_chapter_budget(self, pipeline_id: str, tier: str = "standard"):
        """初始化单章预算"""
        budget = BUDGET_TIERS.get(tier, BUDGET_TIERS["standard"])
        self._chapter_budgets[pipeline_id] = {
            "budget": budget,
            "spent": 0,
            "tier": tier,
            "over_budget_count": 0,
            "agents": {},
        }
        logger.info(f"[Budget] {pipeline_id} 预算初始化: tier={tier}, budget={budget}")

    def check_budget(self, pipeline_id: str, agent: str, estimated_tokens: int = 0) -> bool:
        """检查当前Agent是否还有预算。True=充足，False=建议降级"""
        info = self._chapter_budgets.get(pipeline_id)
        if not info:
            return True
        if info["spent"] >= info["budget"]:
            info["over_budget_count"] += 1
            return False
        if estimated_tokens > 0 and (info["spent"] + estimated_tokens) > info["budget"]:
            return False
        agent_budget = info["budget"] * AGENT_BUDGET_RATIO.get(agent, 0.1)
        agent_spent = info["agents"].get(agent, 0)
        return not (agent_spent >= agent_budget and info["spent"] > info["budget"] * 0.7)

    def spend(
        self,
        pipeline_id: str,
        agent: str,
        tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        """记录Token消耗。支持 tokens 整数或 prompt_tokens+completion_tokens 关键字参数"""
        total = tokens + prompt_tokens + completion_tokens
        info = self._chapter_budgets.get(pipeline_id)
        if info:
            info["spent"] += total
            info["agents"][agent] = info["agents"].get(agent, 0) + total

        # 接入 .env 日预算追踪
        if settings.llm_daily_token_budget > 0 and total > 0:
            self._track_daily_tokens(total)
        # 接入 .env 小时频率追踪
        if settings.llm_max_calls_per_hour > 0:
            self._record_call()

    def get_budget_status(self, pipeline_id: str) -> dict:
        """获取预算状态"""
        info = self._chapter_budgets.get(pipeline_id)
        if not info:
            return {"active": False}
        return {
            "active": True,
            "tier": info["tier"],
            "budget": info["budget"],
            "spent": info["spent"],
            "remaining": max(0, info["budget"] - info["spent"]),
            "usage_pct": round(info["spent"] / max(info["budget"], 1) * 100, 1),
            "agents": dict(info["agents"]),
        }

    def close_budget(self, pipeline_id: str):
        """关闭预算"""
        self._chapter_budgets.pop(pipeline_id, None)

    def suggest_tier(self, mode: str, chapter_type: str, is_first_chapter: bool) -> str:
        """根据配置自动推荐预算等级（同时受 .env 日预算和小时频率限制）"""
        # 先检查日预算是否已耗尽
        if settings.llm_daily_token_budget > 0 and not self._check_daily_budget():
            logger.warning("日Token预算已耗尽，降级到economy")
            return "economy"
        # 再检查小时频率
        if settings.llm_max_calls_per_hour > 0 and not self._check_hourly_rate():
            logger.warning("小时调用频率超限，降级到economy")
            return "economy"

        if is_first_chapter or chapter_type == "climax" or mode == "gacha_ultimate_5":
            return "premium"
        if mode in ("gacha_parallel_3", "gacha_cascade"):
            return "standard"
        return "economy"

    def _check_daily_budget(self) -> bool:
        """检查日Token预算是否还有剩余"""
        import datetime

        today = datetime.date.today().toordinal()
        if self._daily_reset_day != today:
            self._daily_tokens = 0
            self._daily_reset_day = today
            logger.info(f"[Budget] 日Token预算重置: {settings.llm_daily_token_budget}")
        return self._daily_tokens < settings.llm_daily_token_budget

    def _check_hourly_rate(self) -> bool:
        """检查小时调用频率是否超限（滑动窗口）"""
        now = time.time()
        one_hour_ago = now - 3600
        # 清理过期记录
        self._hourly_calls = [t for t in self._hourly_calls if t > one_hour_ago]
        return len(self._hourly_calls) < settings.llm_max_calls_per_hour

    def _record_call(self):
        """记录一次LLM调用（用于小时频率统计）"""
        self._hourly_calls.append(time.time())
        # 定期清理（每100次调用清理一次）
        if len(self._hourly_calls) > 100:
            now = time.time()
            self._hourly_calls = [t for t in self._hourly_calls if t > now - 3600]

    def _track_daily_tokens(self, tokens: int):
        """跟踪日Token消耗"""
        import datetime

        today = datetime.date.today().toordinal()
        if self._daily_reset_day != today:
            self._daily_tokens = 0
            self._daily_reset_day = today
        self._daily_tokens += tokens

    def record(
        self,
        book_id: str,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str = "",
    ):
        """记录一次API调用"""
        price = MODEL_PRICES.get(
            model, MODEL_PRICES.get("deepseek-chat", {"input": 0.14, "output": 0.28})
        )
        cost = (input_tokens / 1_000_000) * price["input"] + (output_tokens / 1_000_000) * price[
            "output"
        ]

        record = UsageRecord(
            time.time(), book_id, agent, model, input_tokens, output_tokens, cost, operation
        )

        # 追加到日志
        log_path = self.tracker_dir / f"{book_id}_usage.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")

        # 更新汇总
        self._update_summary(book_id, record)

    def _update_summary(self, book_id: str, record: UsageRecord):
        summary_path = self.tracker_dir / f"{book_id}_summary.json"
        summary = {}
        if summary_path.exists():
            with contextlib.suppress(Exception):
                summary = json.loads(summary_path.read_text())

        # 按agent汇总
        if record.agent not in summary:
            summary[record.agent] = {"total_tokens": 0, "total_cost": 0, "calls": 0}
        summary[record.agent]["total_tokens"] += record.input_tokens + record.output_tokens
        summary[record.agent]["total_cost"] += record.cost_usd
        summary[record.agent]["calls"] += 1

        # 全局汇总
        if "_total" not in summary:
            summary["_total"] = {"total_tokens": 0, "total_cost": 0, "calls": 0}
        summary["_total"]["total_tokens"] += record.input_tokens + record.output_tokens
        summary["_total"]["total_cost"] += record.cost_usd
        summary["_total"]["calls"] += 1

        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    def get_summary(self, book_id: str) -> dict:
        """获取费用汇总"""
        path = self.tracker_dir / f"{book_id}_summary.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                logger.debug(f"用量摘要加载失败: {book_id}")
        return {}

    def get_total_cost(self, book_id: str) -> float:
        summary = self.get_summary(book_id)
        return summary.get("_total", {}).get("total_cost", 0)

    def get_daily_budget_status(self) -> dict:
        """获取日预算状态"""
        import datetime

        today = datetime.date.today().toordinal()
        if self._daily_reset_day != today:
            self._daily_tokens = 0
            self._daily_reset_day = today
        budget = settings.llm_daily_token_budget
        return {
            "enabled": budget > 0,
            "budget": budget,
            "used": self._daily_tokens,
            "remaining": max(0, budget - self._daily_tokens),
            "usage_pct": round(self._daily_tokens / max(budget, 1) * 100, 1),
        }

    def get_hourly_rate_status(self) -> dict:
        """获取小时频率状态"""
        now = time.time()
        one_hour_ago = now - 3600
        self._hourly_calls = [t for t in self._hourly_calls if t > one_hour_ago]
        limit = settings.llm_max_calls_per_hour
        return {
            "enabled": limit > 0,
            "limit": limit,
            "used": len(self._hourly_calls),
            "remaining": max(0, limit - len(self._hourly_calls)),
        }


# 全局单例
token_tracker = TokenTracker()

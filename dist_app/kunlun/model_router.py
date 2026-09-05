"""
昆仑创作引擎 — 模型分层路由器

基于 NovelForger 3-tier 策略扩展，实现智能模型路由：

三层架构:
  ┌─────────────────────────────────────────────────┐
  │ Tier 1: Classification（廉价）                 │
  │   - 任务: 分类、判断、简单决策                   │
  │   - 模型: deepseek-chat (低temp)                │
  │   - 成本: 最低                                  │
  ├─────────────────────────────────────────────────┤
  │ Tier 2: Creation（标准）                        │
  │   - 任务: 内容创作、生成、改写                   │
  │   - 模型: deepseek-chat (标准temp)              │
  │   - 成本: 中等                                  │
  ├─────────────────────────────────────────────────┤
  │ Tier 3: Evaluation（昂贵）                      │
  │   - 任务: 质量评估、深度分析、高级推理            │
  │   - 模型: deepseek-reasoner / gpt-4o           │
  │   - 成本: 最高                                  │
  └─────────────────────────────────────────────────┘

智能路由策略:
  1. 按任务类型自动选择层级
  2. 级联模式：廉价模型达标则跳过昂贵模型
  3. 章节类型感知：高潮章节自动升级到高级模型
  4. 预算控制：根据Token预算动态调整模型选择
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.common.cache import TTLPropertyCache
from kunlun.config import settings
from kunlun.gacha.circuit_breaker import CircuitState


class ModelTier(Enum):
    """模型层级"""

    CLASSIFICATION = "classification"  # 分类/判断
    CREATION = "creation"  # 创作/生成
    EVALUATION = "evaluation"  # 评估/推理
    POLISH = "polish"  # 润色/优化
    QUICK = "quick"  # 快速生成
    PREMIUM = "premium"  # 高级生成


class ProviderType(Enum):
    """Provider类型"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPAT = "openai_compat"


@dataclass
class AgentModelConfig:
    """Agent模型配置"""

    agent: str
    model: str
    provider: str = "openai_compat"
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.8
    max_tokens: int = 4096
    tier: ModelTier = ModelTier.CREATION
    extra_params: dict = field(default_factory=dict)


@dataclass
class TierConfig:
    """层级配置"""

    tier: ModelTier
    model: str
    temperature: float
    max_tokens: int
    cost_level: str  # "cheap", "standard", "expensive"
    capabilities: list[str]


# 默认层级配置（基于 NovelForger 3-tier 策略）
DEFAULT_TIER_CONFIGS: dict[ModelTier, TierConfig] = {
    ModelTier.CLASSIFICATION: TierConfig(
        tier=ModelTier.CLASSIFICATION,
        model="deepseek-chat",
        temperature=0.0,
        max_tokens=512,
        cost_level="cheap",
        capabilities=["classification", "judgment", "simple_decision"],
    ),
    ModelTier.CREATION: TierConfig(
        tier=ModelTier.CREATION,
        model="deepseek-chat",
        temperature=0.8,
        max_tokens=4096,
        cost_level="standard",
        capabilities=["narrative", "emotion", "structure", "worldbuilding"],
    ),
    ModelTier.EVALUATION: TierConfig(
        tier=ModelTier.EVALUATION,
        model="deepseek-reasoner",
        temperature=0.3,
        max_tokens=2048,
        cost_level="standard",
        capabilities=["analysis", "quality_assessment", "reasoning"],
    ),
    ModelTier.POLISH: TierConfig(
        tier=ModelTier.POLISH,
        model="deepseek-chat",
        temperature=0.4,
        max_tokens=2048,
        cost_level="standard",
        capabilities=["style", "polishing", "refinement"],
    ),
    ModelTier.QUICK: TierConfig(
        tier=ModelTier.QUICK,
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=1024,
        cost_level="cheap",
        capabilities=["rapid", "draft", "outline"],
    ),
    ModelTier.PREMIUM: TierConfig(
        tier=ModelTier.PREMIUM,
        model="deepseek-reasoner",
        temperature=0.7,
        max_tokens=8192,
        cost_level="expensive",
        capabilities=["premium", "critical", "complex_reasoning"],
    ),
}


# Agent到层级的默认映射
AGENT_TIER_MAP: dict[str, ModelTier] = {
    "architect": ModelTier.CREATION,  # 蓝图生成
    "writer": ModelTier.CREATION,  # 内容创作
    "auditor": ModelTier.EVALUATION,  # 审计评估
    "reviser": ModelTier.POLISH,  # 修订润色
    "stylist": ModelTier.POLISH,  # 风格优化
    "planner": ModelTier.CREATION,  # 大纲规划
    "radar": ModelTier.CLASSIFICATION,  # 模式检测
    "sociologist": ModelTier.CREATION,  # 社会推演
    "market": ModelTier.EVALUATION,  # 市场分析
    "editor": ModelTier.EVALUATION,  # 主编决策
    "learner": ModelTier.CLASSIFICATION,  # 偏好学习
}


# 章节类型到级联阈值的映射
CASCADE_THRESHOLD_BY_TYPE: dict[str, float] = {
    "climax": 0.70,  # 高潮章节：高质量要求
    "battle": 0.65,  # 战斗章节：较高质量要求
    "normal": 0.55,  # 普通章节：标准质量要求
    "transition": 0.45,  # 过渡章节：较低质量要求
    "exposition": 0.50,  # 说明章节：中等质量要求
}


class FallbackStrategy(Enum):
    """回退策略"""

    FIXED_ORDER = "fixed_order"  # 固定顺序回退
    COST_ASC = "cost_asc"  # 按成本升序回退
    CAPABILITY_MATCH = "capability_match"  # 按能力匹配回退
    RANDOM_LOAD_BALANCE = "random_load_balance"  # 随机负载均衡


@dataclass
class FallbackModel:
    """回退模型配置"""

    model: str
    provider: str = "openai_compat"
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    context_window: int = 65536  # token
    priority: int = 0  # 越低越优先
    cost_per_1k: float = 0.001  # 每1K tokens成本（美元）


# 智能回退链：主模型 -> 备选模型（按优先级排序）
# 参考 LiteLLM 的多路由策略，按主模型名索引
FALLBACK_CHAIN: dict[str, list[FallbackModel]] = {
    # Tier 3 (Evaluation) 回退链
    "deepseek-reasoner": [
        FallbackModel("deepseek-reasoner", priority=0, cost_per_1k=0.00055, context_window=65536),
        FallbackModel("deepseek-chat", priority=1, cost_per_1k=0.00027, context_window=65536),
        FallbackModel(
            "gpt-4o-mini", provider="openai", priority=2, cost_per_1k=0.0006, context_window=128000
        ),
    ],
    # Tier 1/2/4 (Classification/Creation/Polish) 通用回退链
    "deepseek-chat": [
        FallbackModel("deepseek-chat", priority=0, cost_per_1k=0.00027, context_window=65536),
        FallbackModel("qwen-plus", priority=1, cost_per_1k=0.0004, context_window=131072),
        FallbackModel("deepseek-reasoner", priority=2, cost_per_1k=0.00055, context_window=65536),
        FallbackModel(
            "gpt-4o-mini", provider="openai", priority=3, cost_per_1k=0.0006, context_window=128000
        ),
    ],
    # qwen 系列回退链
    "qwen-plus": [
        FallbackModel("qwen-plus", priority=0, cost_per_1k=0.0004, context_window=131072),
        FallbackModel("deepseek-chat", priority=1, cost_per_1k=0.00027, context_window=65536),
        FallbackModel(
            "gpt-4o-mini", provider="openai", priority=2, cost_per_1k=0.0006, context_window=128000
        ),
    ],
    # gpt-4o 系列回退链
    "gpt-4o": [
        FallbackModel(
            "gpt-4o", provider="openai", priority=0, cost_per_1k=0.005, context_window=128000
        ),
        FallbackModel("deepseek-reasoner", priority=1, cost_per_1k=0.00055, context_window=65536),
        FallbackModel("deepseek-chat", priority=2, cost_per_1k=0.00027, context_window=65536),
    ],
    "gpt-4o-mini": [
        FallbackModel(
            "gpt-4o-mini", provider="openai", priority=0, cost_per_1k=0.0006, context_window=128000
        ),
        FallbackModel("deepseek-chat", priority=1, cost_per_1k=0.00027, context_window=65536),
        FallbackModel("qwen-plus", priority=2, cost_per_1k=0.0004, context_window=131072),
    ],
}

# 默认通用回退链（未显式配置的模型）
DEFAULT_FALLBACK_CHAIN: list[FallbackModel] = [
    FallbackModel("deepseek-chat", priority=0, cost_per_1k=0.00027),
    FallbackModel("qwen-plus", priority=1, cost_per_1k=0.0004),
    FallbackModel("gpt-4o-mini", provider="openai", priority=2, cost_per_1k=0.0006),
]

# 限流冷却时间（秒）
RATE_LIMIT_COOLDOWN_SECONDS = 30
# 连续失败冷却递增系数
COOLDOWN_BACKOFF_MULTIPLIER = 2.0
# 最大冷却时间（秒）
MAX_COOLDOWN_SECONDS = 300


# ─── 熔断保护配置（借鉴PlotPilot Autopilot守护进程）───
# 熔断器状态机: CLOSED → OPEN → HALF_OPEN → CLOSED


@dataclass
class CircuitBreaker:
    """模型级熔断器"""

    model: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0  # HALF_OPEN状态下的成功计数
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    open_since: float = 0.0  # 熔断打开时间
    half_open_since: float = 0.0  # 半开状态起始时间

    # 熔断阈值配置
    FAILURE_THRESHOLD: int = 5  # 连续失败5次触发熔断
    SUCCESS_TO_CLOSE: int = 3  # 半开状态下连续成功3次关闭熔断
    OPEN_TIMEOUT: float = 60.0  # 熔断后60秒尝试半开
    HALF_OPEN_PROBE_INTERVAL: float = 10.0  # 半开状态下每10秒发送一个探测请求


class ModelRouter:
    """
    多模型分层路由器

    核心功能:
    1. 基于任务类型自动选择模型层级
    2. 支持级联模式（廉价→标准→昂贵）
    3. 章节类型感知的阈值调整
    4. Token预算控制
    5. 配置持久化
    6. 智能回退链（LiteLLM风格）
    7. 限流冷却机制
    8. 上下文窗口感知路由
    """

    def __init__(self):
        self._configs: dict[str, AgentModelConfig] = {}
        self._config_path = settings.DATA_DIR / "model_routing.json"
        self._cooldown_map: dict[str, tuple[float, int]] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._cache = TTLPropertyCache()
        self._init_defaults()
        self._load()

    def _init_defaults(self):
        """初始化默认配置"""
        for agent, tier in AGENT_TIER_MAP.items():
            tier_config = DEFAULT_TIER_CONFIGS[tier]
            self._configs[agent] = AgentModelConfig(
                agent=agent,
                model=tier_config.model,
                temperature=tier_config.temperature,
                max_tokens=tier_config.max_tokens,
                tier=tier,
            )
        # 添加默认配置
        self._configs["default"] = AgentModelConfig(
            agent="default",
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=2048,
            tier=ModelTier.CREATION,
        )

    def get(self, agent: str) -> AgentModelConfig:
        """获取Agent的模型配置"""
        if agent in self._configs:
            return self._configs[agent]
        if "default" in self._configs:
            return self._configs["default"]
        return AgentModelConfig(agent, "deepseek-chat")

    def get_tier(self, agent: str) -> ModelTier:
        """获取Agent所属层级"""
        return self.get(agent).tier

    def suggest_for_task(self, task_type: str, custom_model: str | None = None) -> AgentModelConfig:
        """
        根据任务类型推荐模型配置

        Args:
            task_type: 任务类型
            custom_model: 自定义模型名（覆盖默认）

        Returns:
            AgentModelConfig
        """
        tier = self._resolve_tier(task_type)
        tier_config = DEFAULT_TIER_CONFIGS[tier]

        return AgentModelConfig(
            agent=f"task_{task_type}",
            model=custom_model or tier_config.model,
            temperature=tier_config.temperature,
            max_tokens=tier_config.max_tokens,
            tier=tier,
        )

    def _resolve_tier(self, task_type: str) -> ModelTier:
        """将任务类型解析为模型层级"""
        task_type = task_type.lower()

        if task_type in ["classification", "classify", "judge", "detect"]:
            return ModelTier.CLASSIFICATION
        if task_type in ["creation", "create", "write", "generate", "draft"]:
            return ModelTier.CREATION
        if task_type in ["evaluation", "evaluate", "audit", "analyze", "review"]:
            return ModelTier.EVALUATION
        if task_type in ["polish", "refine", "style", "edit"]:
            return ModelTier.POLISH
        if task_type in ["quick", "fast", "simple"]:
            return ModelTier.QUICK
        if task_type in ["premium", "advanced", "critical"]:
            return ModelTier.PREMIUM

        return ModelTier.CREATION

    def should_upgrade_to_premium(self, chapter_type: str, quality_score: float) -> bool:
        """
        判断是否需要升级到高级模型

        Args:
            chapter_type: 章节类型
            quality_score: 当前质量分数

        Returns:
            True表示需要升级到高级模型
        """
        threshold = CASCADE_THRESHOLD_BY_TYPE.get(chapter_type, 0.55)
        return quality_score < threshold

    def get_cascade_threshold(self, chapter_type: str) -> float:
        """获取级联模式的质量阈值"""
        return CASCADE_THRESHOLD_BY_TYPE.get(chapter_type, 0.55)

    def set(
        self,
        agent: str,
        model: str,
        provider: str = "openai_compat",
        base_url: str = "",
        api_key: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        tier: str | None = None,
        **extra,
    ):
        """设置Agent的模型配置"""
        tier_enum = ModelTier(tier) if tier else AGENT_TIER_MAP.get(agent, ModelTier.CREATION)

        cfg = AgentModelConfig(
            agent=agent,
            model=model,
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature or 0.8,
            max_tokens=max_tokens or 4096,
            tier=tier_enum,
            extra_params=extra,
        )
        self._configs[agent] = cfg
        self._save()
        self._cache.invalidate("list_all")
        self._cache.invalidate("tier_stats")
        logger.info(f"[ModelRouter] {agent} → {model} ({provider}, tier={tier_enum.value})")

    def set_tier(self, agent: str, tier: ModelTier):
        """设置Agent的层级"""
        if agent in self._configs:
            self._configs[agent].tier = tier
            tier_config = DEFAULT_TIER_CONFIGS[tier]
            self._configs[agent].model = tier_config.model
            self._configs[agent].temperature = tier_config.temperature
            self._configs[agent].max_tokens = tier_config.max_tokens
            self._save()
            self._cache.invalidate("list_all")
            self._cache.invalidate("tier_stats")
            logger.info(f"[ModelRouter] {agent} tier updated to {tier.value}")

    def list_all(self) -> dict[str, dict[str, Any]]:
        """列出所有配置（TTL缓存10秒）"""
        return self._cache.get("list_all", 10, self._do_list_all)

    def _do_list_all(self) -> dict[str, dict[str, Any]]:
        return {
            agent: {
                "model": cfg.model,
                "provider": cfg.provider,
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "tier": cfg.tier.value,
            }
            for agent, cfg in self._configs.items()
        }

    def get_tier_stats(self) -> dict[str, int]:
        """获取各层级的Agent数量统计（TTL缓存10秒）"""
        return self._cache.get("tier_stats", 10, self._do_get_tier_stats)

    def _do_get_tier_stats(self) -> dict[str, int]:
        stats = {tier.value: 0 for tier in ModelTier}
        for cfg in self._configs.values():
            stats[cfg.tier.value] += 1
        return stats

    def _save(self):
        """保存配置到文件"""
        try:
            data = {}
            for agent, cfg in self._configs.items():
                data[agent] = {
                    "agent": cfg.agent,
                    "model": cfg.model,
                    "provider": cfg.provider,
                    "base_url": cfg.base_url,
                    # 安全：不保存API密钥到明文JSON文件，运行时从环境变量加载
                    "api_key": "",
                    "temperature": cfg.temperature,
                    "max_tokens": cfg.max_tokens,
                    "tier": cfg.tier.value,
                    "extra_params": cfg.extra_params,
                }
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"[ModelRouter] 保存失败: {e}")

    def _load(self):
        """从文件加载配置"""
        try:
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                for agent, d in data.items():
                    tier = ModelTier(d.get("tier", "creation"))
                    loaded_key = d.get("api_key", "")
                    # 若文件中无API密钥，保留已从环境变量加载的密钥
                    existing_key = ""
                    if agent in self._configs:
                        existing_key = self._configs[agent].api_key
                    self._configs[agent] = AgentModelConfig(
                        agent=d["agent"],
                        model=d["model"],
                        provider=d.get("provider", "openai_compat"),
                        base_url=d.get("base_url", ""),
                        api_key=loaded_key or existing_key,
                        temperature=d.get("temperature", 0.8),
                        max_tokens=d.get("max_tokens", 4096),
                        tier=tier,
                        extra_params=d.get("extra_params", {}),
                    )
        except Exception as e:
            logger.warning(f"[ModelRouter] 加载失败，使用默认配置: {e}")

    # ─── 智能回退链 ─────────────────────────────

    def is_cooling_down(self, model: str) -> bool:
        """检查模型是否处于限流冷却期"""
        if model in self._cooldown_map:
            until, _ = self._cooldown_map[model]
            if time.time() < until:
                remaining = until - time.time()
                logger.debug(f"[ModelRouter] {model} 冷却中 (剩余 {remaining:.1f}s)")
                return True
            # 冷却期已过，清理记录
            del self._cooldown_map[model]
        return False

    def report_rate_limit(self, model: str) -> None:
        """上报限流/错误，触发冷却"""
        now = time.time()
        _, consecutive = self._cooldown_map.get(model, (0, 0))
        consecutive += 1
        # 指数退避：30s * 2^(consecutive-1)，最大300s
        cooldown = min(
            RATE_LIMIT_COOLDOWN_SECONDS * (COOLDOWN_BACKOFF_MULTIPLIER ** (consecutive - 1)),
            MAX_COOLDOWN_SECONDS,
        )
        self._cooldown_map[model] = (now + cooldown, consecutive)
        logger.warning(
            f"[ModelRouter] {model} 触发冷却 {cooldown:.0f}s (连续失败 {consecutive} 次)"
        )

    def report_success(self, model: str) -> None:
        """上报成功，解除冷却"""
        if model in self._cooldown_map:
            del self._cooldown_map[model]
            logger.debug(f"[ModelRouter] {model} 冷却已解除")

    def _get_fallback_chain(self, primary_model: str) -> list[FallbackModel]:
        """获取模型的回退链"""
        # 尝试精确匹配
        for key, chain in FALLBACK_CHAIN.items():
            if key == primary_model:
                return chain
        # 尝试模糊匹配（如 "deepseek-chat" 匹配 "deepseek" 前缀）
        for key, chain in FALLBACK_CHAIN.items():
            if primary_model.startswith(key) or key.startswith(primary_model):
                return chain
        return DEFAULT_FALLBACK_CHAIN

    def _sort_fallback_chain(
        self,
        chain: list[FallbackModel],
        strategy: FallbackStrategy,
        estimated_tokens: int = 0,
    ) -> list[FallbackModel]:
        """根据策略排序回退链"""
        if strategy == FallbackStrategy.FIXED_ORDER:
            return sorted(chain, key=lambda x: x.priority)
        if strategy == FallbackStrategy.COST_ASC:
            return sorted(chain, key=lambda x: (x.cost_per_1k, x.priority))
        if strategy == FallbackStrategy.CAPABILITY_MATCH:
            # 按上下文窗口能否容纳排序
            def _score(fm: FallbackModel) -> tuple:
                fits = 0 if fm.context_window >= estimated_tokens else 1
                return (fits, fm.priority)

            return sorted(chain, key=_score)
        if strategy == FallbackStrategy.RANDOM_LOAD_BALANCE:
            import random

            shuffled = list(chain)
            random.shuffle(shuffled)
            return shuffled
        return chain

    def _filter_chain_by_cooldown(self, chain: list[FallbackModel]) -> list[FallbackModel]:
        """过滤掉处于冷却期的模型"""
        return [m for m in chain if not self.is_cooling_down(m.model)]

    def _filter_chain_by_context(
        self,
        chain: list[FallbackModel],
        estimated_tokens: int,
    ) -> list[FallbackModel]:
        """过滤掉上下文窗口不足的模型"""
        return [m for m in chain if m.context_window >= estimated_tokens]

    @staticmethod
    def _classify_call_error(error_msg: str) -> str:
        """分类调用错误类型，返回 'rate_limit' | 'context_overflow' | 'general'"""
        msg_lower = error_msg.lower()
        if any(kw in msg_lower for kw in ("rate limit", "429", "too many requests", "quota")):
            return "rate_limit"
        if any(
            kw in msg_lower
            for kw in (
                "context length",
                "maximum context",
                "token limit",
                "reduce the length",
                "input length",
            )
        ):
            return "context_overflow"
        return "general"

    def _handle_context_overflow(
        self,
        fm: FallbackModel,
        chain: list[FallbackModel],
        tried_count: int,
        estimated_tokens: int,
    ) -> dict[str, Any] | None:
        """处理上下文溢出错误。返回错误响应 dict 或 None（继续尝试）。"""
        remaining = chain[tried_count:]
        larger = [
            m
            for m in remaining
            if m.context_window > fm.context_window and not self.is_cooling_down(m.model)
        ]
        if not larger:
            max_window = max(m.context_window for m in chain)
            return {
                "success": False,
                "error": (
                    f"上下文溢出: 需要 >{estimated_tokens} tokens, 可用模型最大窗口 {max_window}"
                ),
                "models_tried": [m.model for m in chain[:tried_count]],
            }
        return None  # 有更大窗口的模型，继续尝试

    async def call_with_fallback(
        self,
        call_func: Callable[..., Awaitable[Any]],
        primary_model: str,
        estimated_tokens: int = 4096,
        strategy: FallbackStrategy = FallbackStrategy.FIXED_ORDER,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """
        带智能回退的模型调用

        Args:
            call_func: 异步调用函数，签名 (model_name: str, **kwargs) -> Any
            primary_model: 主模型名称
            estimated_tokens: 预估的输入token数（用于上下文窗口检查）
            strategy: 回退策略
            *args, **kwargs: 传递给 call_func 的额外参数

        Returns:
            {"success": True, "result": ..., "model_used": "..."}
            或 {"success": False, "error": "...", "models_tried": [...]}
        """
        chain = self._get_fallback_chain(primary_model)
        chain = self._sort_fallback_chain(chain, strategy, estimated_tokens)
        chain = self._filter_chain_by_context(chain, estimated_tokens)
        chain = self._filter_chain_by_cooldown(chain)

        if not chain:
            return {
                "success": False,
                "error": "所有模型均不可用（全部处于冷却期或上下文窗口不足）",
                "models_tried": [],
            }

        models_tried: list[str] = []
        last_error = None

        for fm in chain:
            # 将模型名注入 kwargs
            kwargs["model"] = fm.model
            kwargs["provider"] = fm.provider
            if fm.base_url:
                kwargs["base_url"] = fm.base_url

            try:
                logger.info(
                    f"[ModelRouter] 尝试 {fm.model} (priority={fm.priority}, "
                    f"cost=${fm.cost_per_1k}/1k)"
                )

                result = await call_func(*args, **kwargs)

                # 成功，清除冷却并返回
                self.report_success(fm.model)
                return {
                    "success": True,
                    "result": result,
                    "model_used": fm.model,
                    "models_tried": [*models_tried, fm.model],
                    "fallback_used": fm.model != primary_model,
                }

            except Exception as e:
                last_error = str(e)
                models_tried.append(fm.model)
                logger.warning(f"[ModelRouter] {fm.model} 调用失败: {e}")

                error_type = self._classify_call_error(str(e))

                if error_type == "rate_limit":
                    self.report_rate_limit(fm.model)
                    remaining_available = any(
                        not self.is_cooling_down(m.model) for m in chain[len(models_tried) :]
                    )
                    if not remaining_available:
                        break

                elif error_type == "context_overflow":
                    logger.error(f"[ModelRouter] {fm.model} 上下文溢出 (窗口={fm.context_window})")
                    overflow_result = self._handle_context_overflow(
                        fm,
                        chain,
                        len(models_tried),
                        estimated_tokens,
                    )
                    if overflow_result is not None:
                        return overflow_result

                else:
                    self.report_rate_limit(fm.model)

        return {
            "success": False,
            "error": f"所有模型调用失败. 最后错误: {last_error}",
            "models_tried": models_tried,
        }

    def suggest_model_for_context(
        self, estimated_tokens: int, tier: ModelTier = ModelTier.CREATION
    ) -> str:
        """
        根据预估上下文大小推荐合适的模型

        Args:
            estimated_tokens: 预估输入token数
            tier: 目标层级

        Returns:
            推荐的模型名
        """
        tier_config = DEFAULT_TIER_CONFIGS.get(tier)
        if not tier_config:
            return "deepseek-chat"

        primary = tier_config.model
        chain = self._get_fallback_chain(primary)

        # 选第一个上下文窗口足够且不在冷却期的模型
        for fm in sorted(chain, key=lambda x: x.priority):
            if fm.context_window >= estimated_tokens and not self.is_cooling_down(fm.model):
                return fm.model

        # 如果所有模型都不可用，返回窗口最大的那个
        best = max(chain, key=lambda x: x.context_window)
        return best.model

    def get_cooldown_status(self) -> dict[str, dict[str, Any]]:
        """
        查询所有模型的冷却状态

        Returns:
            {model_name: {"cooling_down": bool, "remaining_seconds": float,
                          "consecutive_failures": int}}
        """
        now = time.time()
        status = {}
        for model, (until, consecutive) in self._cooldown_map.items():
            remaining = until - now
            if remaining > 0:
                status[model] = {
                    "cooling_down": True,
                    "remaining_seconds": round(remaining, 1),
                    "consecutive_failures": consecutive,
                }
        return status

    def reset_cooldown(self, model: str | None = None) -> None:
        """重置冷却状态"""
        if model:
            self._cooldown_map.pop(model, None)
            logger.info(f"[ModelRouter] {model} 冷却已手动重置")
        else:
            self._cooldown_map.clear()
            logger.info("[ModelRouter] 所有冷却已重置")

    # ─── 熔断器管理（借鉴PlotPilot Autopilot）───

    def _get_circuit_breaker(self, model: str) -> CircuitBreaker:
        """获取或创建模型的熔断器"""
        if model not in self._circuit_breakers:
            self._circuit_breakers[model] = CircuitBreaker(model=model)
        return self._circuit_breakers[model]

    def is_circuit_open(self, model: str) -> bool:
        """检查模型是否处于熔断状态"""
        cb = self._get_circuit_breaker(model)
        now = time.time()

        if cb.state == CircuitState.CLOSED:
            return False

        if cb.state == CircuitState.OPEN:
            # 检查是否到了尝试恢复的时间
            if now - cb.open_since >= cb.OPEN_TIMEOUT:
                cb.state = CircuitState.HALF_OPEN
                cb.half_open_since = now
                cb.success_count = 0
                logger.info(f"[CircuitBreaker] {model} 熔断超时，进入半开状态（探测恢复）")
                return False  # 允许一个探测请求通过
            return True  # 仍在熔断中，拒绝请求

        if cb.state == CircuitState.HALF_OPEN:
            # 半开状态下，每HALF_OPEN_PROBE_INTERVAL秒允许一个探测请求
            if now - cb.half_open_since >= cb.HALF_OPEN_PROBE_INTERVAL:
                cb.half_open_since = now
                return False  # 允许探测请求
            return True  # 距离上次探测太近，拒绝

        return False

    def report_circuit_failure(self, model: str) -> None:
        """上报失败，更新熔断器状态"""
        cb = self._get_circuit_breaker(model)
        now = time.time()
        cb.last_failure_time = now

        if cb.state == CircuitState.CLOSED:
            cb.failure_count += 1
            if cb.failure_count >= cb.FAILURE_THRESHOLD:
                cb.state = CircuitState.OPEN
                cb.open_since = now
                logger.warning(
                    f"[CircuitBreaker] {model} 熔断器打开！"
                    f"（连续失败{cb.failure_count}次，将在{cb.OPEN_TIMEOUT}s后尝试恢复）"
                )

        elif cb.state == CircuitState.HALF_OPEN:
            # 半开状态下的探测请求失败 → 重新熔断
            cb.state = CircuitState.OPEN
            cb.open_since = now
            cb.failure_count += 1
            logger.warning(
                f"[CircuitBreaker] {model} 探测失败，重新熔断（累计失败{cb.failure_count}次）"
            )

    def report_circuit_success(self, model: str) -> None:
        """上报成功，更新熔断器状态"""
        cb = self._get_circuit_breaker(model)
        now = time.time()
        cb.last_success_time = now
        cb.failure_count = 0  # 重置失败计数

        if cb.state == CircuitState.HALF_OPEN:
            cb.success_count += 1
            if cb.success_count >= cb.SUCCESS_TO_CLOSE:
                cb.state = CircuitState.CLOSED
                cb.failure_count = 0
                logger.info(
                    f"[CircuitBreaker] {model} 连续成功{cb.success_count}次，熔断器关闭（恢复正常）"
                )

    def get_circuit_status(self) -> dict[str, dict[str, Any]]:
        """获取所有模型的熔断器状态"""
        now = time.time()
        status = {}
        for model, cb in self._circuit_breakers.items():
            if cb.state != CircuitState.CLOSED:
                status[model] = {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "open_duration": round(now - cb.open_since, 1) if cb.open_since > 0 else 0,
                    "half_open_success": cb.success_count,
                }
        return status

    def force_close_circuit(self, model: str | None = None) -> None:
        """强制关闭熔断器（手动恢复）"""
        if model:
            cb = self._get_circuit_breaker(model)
            cb.state = CircuitState.CLOSED
            cb.failure_count = 0
            cb.success_count = 0
            logger.info(f"[CircuitBreaker] {model} 熔断器已手动关闭")
        else:
            for cb in self._circuit_breakers.values():
                cb.state = CircuitState.CLOSED
                cb.failure_count = 0
                cb.success_count = 0
            logger.info("[CircuitBreaker] 所有熔断器已手动关闭")

    # ─── 增强的带熔断保护的回退调用 ───

    async def _try_downgrade_chain(
        self,
        call_func: Callable[..., Awaitable[Any]],
        primary_model: str,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """主模型熔断时，从回退链中选第一个可用模型执行调用"""
        chain = self._get_fallback_chain(primary_model)
        chain = self._filter_chain_by_cooldown(chain)
        downgraded = next(
            (
                fm
                for fm in chain
                if fm.model != primary_model and not self.is_circuit_open(fm.model)
            ),
            None,
        )
        if not downgraded:
            return {
                "success": False,
                "error": f"主模型 {primary_model} 已熔断，且无可用降级模型",
                "models_tried": [],
                "circuit_breaker_triggered": True,
            }
        logger.info(f"[CircuitBreaker] 自动降级: {primary_model} → {downgraded.model}")
        kwargs["model"] = downgraded.model
        kwargs["provider"] = downgraded.provider
        try:
            result = await call_func(*args, **kwargs)
            self.report_circuit_success(downgraded.model)
            return {
                "success": True,
                "result": result,
                "model_used": downgraded.model,
                "models_tried": [downgraded.model],
                "circuit_breaker_triggered": True,
                "original_model": primary_model,
            }
        except Exception as e:
            self.report_circuit_failure(downgraded.model)
            return {
                "success": False,
                "error": f"主模型熔断且降级模型也失败: {e}",
                "models_tried": [downgraded.model],
                "circuit_breaker_triggered": True,
            }

    def _update_circuit_from_result(self, result: dict[str, Any], primary_model: str) -> None:
        """根据调用结果更新熔断器状态"""
        if result.get("success"):
            self.report_circuit_success(result.get("model_used", primary_model))
        else:
            for model in result.get("models_tried", []):
                self.report_circuit_failure(model)

    async def call_with_circuit_breaker(
        self,
        call_func: Callable[..., Awaitable[Any]],
        primary_model: str,
        estimated_tokens: int = 4096,
        strategy: FallbackStrategy = FallbackStrategy.FIXED_ORDER,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """
        带熔断保护的智能回退调用

        熔断流程: CLOSED(正常) → 5次失败 → OPEN(60s)
                 → HALF_OPEN(10s探测) → 3次成功 → CLOSED

        在 call_with_fallback 基础上增加:
        1. CircuitBreaker 检查
        2. 自动降级到回退链
        3. 半开状态恢复探测
        """
        if self.is_circuit_open(primary_model):
            logger.warning(f"[CircuitBreaker] {primary_model} 已熔断，尝试自动降级")
            return await self._try_downgrade_chain(call_func, primary_model, *args, **kwargs)

        result = await self.call_with_fallback(
            call_func, primary_model, estimated_tokens, strategy, *args, **kwargs
        )
        self._update_circuit_from_result(result, primary_model)
        return result


# ─── 模型信息与统一调用接口 ──────────────────────


@dataclass
class LLMModelInfo:
    """轻量级模型信息（用于 _LLM_MODELS 字典）"""

    name: str
    provider: str
    max_len: int = 4096
    cost_million_in: float = 0.0
    cost_million_out: float = 0.0
    speed_tps: float = 0.0
    quality: int = 50
    strengths: list = field(default_factory=list)


_LLM_MODELS: dict[str, LLMModelInfo] = {
    "deepseek-chat": LLMModelInfo(
        "deepseek-chat",
        "deepseek",
        max_len=65536,
        cost_million_in=0.27,
        cost_million_out=1.10,
        speed_tps=30,
        quality=85,
        strengths=["通用", "中文写作", "高性价比"],
    ),
    # Ollama 本地模型（需搭配 ollama pull 拉取）
    "qwen2.5:7b": LLMModelInfo(
        "qwen2.5:7b",
        "ollama",
        max_len=32768,
        cost_million_in=0,
        cost_million_out=0,
        speed_tps=40,
        quality=78,
        strengths=["中文写作", "长文本", "本地免费"],
    ),
    "qwen2.5:14b": LLMModelInfo(
        "qwen2.5:14b",
        "ollama",
        max_len=32768,
        cost_million_in=0,
        cost_million_out=0,
        speed_tps=35,
        quality=75,
        strengths=["中文写作", "长文本", "性价比选"],
    ),
    "llama3.1:8b": LLMModelInfo(
        "llama3.1:8b",
        "ollama",
        max_len=8192,
        cost_million_in=0,
        cost_million_out=0,
        speed_tps=50,
        quality=65,
        strengths=["通用", "快速原型", "本地免费"],
    ),
    "deepseek-r1:8b": LLMModelInfo(
        "deepseek-r1:8b",
        "ollama",
        max_len=8192,
        cost_million_in=0,
        cost_million_out=0,
        speed_tps=30,
        quality=70,
        strengths=["推理", "逻辑", "本地免费"],
    ),
    "deepseek-reasoner": LLMModelInfo(
        "deepseek-reasoner",
        "deepseek",
        max_len=65536,
        cost_million_in=0.55,
        cost_million_out=2.19,
        speed_tps=20,
        quality=90,
        strengths=["推理", "分析", "复杂任务"],
    ),
}


def get_ollama_client(base_url: str | None = None):
    """获取 Ollama 兼容客户端（Ollama 提供 OpenAI 兼容 API）"""
    import openai

    ollama_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    return openai.OpenAI(base_url=ollama_url, api_key="ollama")


def _get_deepseek_client():
    """获取 DeepSeek 客户端（OpenAI 兼容 API）"""
    import openai

    return openai.OpenAI(
        base_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
    )


def call_llm(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **kwargs,
) -> str:
    """统一 LLM 调用接口，根据 provider 自动选择客户端。

    Args:
        model: 模型名称（对应 _LLM_MODELS 中的 key）
        messages: 消息列表 [{"role": "user", "content": "..."}]
        temperature: 温度参数
        max_tokens: 最大输出 token 数
        **kwargs: 其他参数传递给 API

    Returns:
        LLM 响应文本
    """
    import openai

    model_info = _LLM_MODELS.get(model)
    if not model_info:
        raise ValueError(f"未知模型: {model}，可用模型: {list(_LLM_MODELS.keys())}")

    provider = model_info.provider

    if provider == "ollama":
        client = get_ollama_client()
    elif provider == "deepseek":
        client = _get_deepseek_client()
    else:
        client = openai.OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
        )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    return response.choices[0].message.content


# 全局单例
model_router = ModelRouter()

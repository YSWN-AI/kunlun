"""
昆仑创作引擎 — 多模型智能路由 (Multi-Model Router)

灵感来源: OpenRouter + webnovel-writer 多模型路由 + Novel-OS 13+LLM供应商
对标: 不同 Agent/任务使用不同模型的最优配置

核心设计:
  - 按任务类型自动选择最优模型 (不是所有任务都用最贵模型)
  - 支持模型降级链 (主模型不可用时自动切换)
  - 成本感知 (预算内优先用便宜模型)
  - 与 gacha 引擎集成

任务类型 → 推荐模型映射:
  - 正文生成 (creative): deepseek-chat / claude-sonnet
  - 审计检查 (analytical): gpt-4o-mini / deepseek-chat
  - 大纲规划 (planning): claude-sonnet / deepseek-chat
  - 风格润色 (styling): claude-sonnet / gpt-4o
  - 简单修复 (simple_fix): gpt-4o-mini / deepseek-chat
  - 对话 (chat): deepseek-chat (便宜)
  - 角色推演 (roleplay): claude-sonnet (长上下文)
  - 世界观构建 (worldbuilding): claude-sonnet / gpt-4o

设计原则:
  - 成本优先: 简单任务不浪费昂贵模型
  - 质量优先: 核心创作任务使用最佳模型
  - 可配置: 用户可自定义路由规则
  - 自动降级: 模型不可用时自动切换
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from kunlun.config import settings

# ─── 任务类型 ────────────────────────────────────────


class TaskType(Enum):
    """Agent 任务类型"""

    CREATIVE_WRITING = "creative_writing"  # 正文生成 (Writer)
    ANALYTICAL = "analytical"  # 审计分析 (Auditor)
    PLANNING = "planning"  # 大纲规划 (Architect/Planner)
    STYLING = "styling"  # 风格润色 (Stylist)
    SIMPLE_FIX = "simple_fix"  # 简单修复 (Reviser)
    CHAT = "chat"  # 对话交互 (EditorInChief)
    ROLEPLAY = "roleplay"  # 角色推演 (Sociologist)
    WORLDBUILDING = "worldbuilding"  # 世界观构建
    SUMMARIZATION = "summarization"  # 摘要总结
    EXTRACTION = "extraction"  # 信息提取 (Observer)
    LEARNING = "learning"  # 偏好学习 (LearnAgent)
    MARKET = "market"  # 市场分析 (Market)


# ─── 模型定义 ────────────────────────────────────────


@dataclass
class ModelInfo:
    """模型信息"""

    provider: str
    model: str
    display_name: str
    base_url: str
    api_key_env: str
    context_window: int  # 最大上下文
    max_output_tokens: int  # 最大输出
    cost_per_1k_input: float  # 每千token输入成本 ($)
    cost_per_1k_output: float  # 每千token输出成本 ($)
    strengths: list[TaskType]  # 擅长任务
    priority: int = 50  # 默认优先级 (1-100, 越低越优先)
    enabled: bool = True


# ─── 默认模型库 ──────────────────────────────────────

DEFAULT_MODEL_LIBRARY: list[ModelInfo] = [
    ModelInfo(
        provider="deepseek",
        model="deepseek-chat",
        display_name="DeepSeek V3",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        context_window=65536,
        max_output_tokens=8192,
        cost_per_1k_input=0.00027,
        cost_per_1k_output=0.0011,
        strengths=[
            TaskType.CREATIVE_WRITING,
            TaskType.ANALYTICAL,
            TaskType.SIMPLE_FIX,
            TaskType.CHAT,
            TaskType.SUMMARIZATION,
            TaskType.EXTRACTION,
        ],
        priority=10,  # 性价比最高
    ),
    ModelInfo(
        provider="deepseek",
        model="deepseek-reasoner",
        display_name="DeepSeek R1",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        context_window=65536,
        max_output_tokens=8192,
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.00219,
        strengths=[TaskType.PLANNING, TaskType.WORLDBUILDING],
        priority=20,
    ),
    ModelInfo(
        provider="openai",
        model="gpt-4o-mini",
        display_name="GPT-4o Mini",
        base_url="",
        api_key_env="OPENAI_API_KEY",
        context_window=128000,
        max_output_tokens=16384,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        strengths=[TaskType.ANALYTICAL, TaskType.SIMPLE_FIX, TaskType.EXTRACTION],
        priority=15,
    ),
    ModelInfo(
        provider="openai",
        model="gpt-4o",
        display_name="GPT-4o",
        base_url="",
        api_key_env="OPENAI_API_KEY",
        context_window=128000,
        max_output_tokens=16384,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        strengths=[TaskType.CREATIVE_WRITING, TaskType.STYLING, TaskType.WORLDBUILDING],
        priority=30,
    ),
    ModelInfo(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        base_url="",
        api_key_env="ANTHROPIC_API_KEY",
        context_window=200000,
        max_output_tokens=8192,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        strengths=[
            TaskType.CREATIVE_WRITING,
            TaskType.STYLING,
            TaskType.PLANNING,
            TaskType.ROLEPLAY,
            TaskType.WORLDBUILDING,
        ],
        priority=25,
    ),
    ModelInfo(
        provider="anthropic",
        model="claude-haiku-3-5-20241022",
        display_name="Claude Haiku 3.5",
        base_url="",
        api_key_env="ANTHROPIC_API_KEY",
        context_window=200000,
        max_output_tokens=4096,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.005,
        strengths=[TaskType.SIMPLE_FIX, TaskType.ANALYTICAL, TaskType.EXTRACTION],
        priority=12,
    ),
]


# ─── 路由规则 ────────────────────────────────────────


@dataclass
class RoutingRule:
    """单条路由规则"""

    task_type: TaskType
    preferred_models: list[tuple[str, str]]  # [(provider, model), ...] 优先级递减
    fallback_models: list[tuple[str, str]]  # 降级模型列表
    min_context_needed: int = 4096
    max_budget_per_call: float = 0.05  # 单次调用最大成本 ($)
    prefer_cheapest: bool = False  # 同优先级选最便宜的


# ─── 默认路由表 ──────────────────────────────────────

DEFAULT_ROUTING_TABLE: dict[TaskType, RoutingRule] = {
    TaskType.CREATIVE_WRITING: RoutingRule(
        task_type=TaskType.CREATIVE_WRITING,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        fallback_models=[
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-haiku-3-5-20241022"),
        ],
        min_context_needed=8192,
        max_budget_per_call=0.02,
    ),
    TaskType.ANALYTICAL: RoutingRule(
        task_type=TaskType.ANALYTICAL,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
            ("openai", "gpt-4o-mini"),
        ],
        fallback_models=[
            ("anthropic", "claude-haiku-3-5-20241022"),
        ],
        prefer_cheapest=True,  # 审计不浪费钱
    ),
    TaskType.PLANNING: RoutingRule(
        task_type=TaskType.PLANNING,
        preferred_models=[
            ("deepseek", "deepseek-reasoner"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        fallback_models=[
            ("deepseek", "deepseek-chat"),
        ],
        min_context_needed=16384,
        max_budget_per_call=0.03,
    ),
    TaskType.STYLING: RoutingRule(
        task_type=TaskType.STYLING,
        preferred_models=[
            ("anthropic", "claude-sonnet-4-20250514"),
            ("openai", "gpt-4o"),
        ],
        fallback_models=[
            ("deepseek", "deepseek-chat"),
        ],
        max_budget_per_call=0.03,
    ),
    TaskType.SIMPLE_FIX: RoutingRule(
        task_type=TaskType.SIMPLE_FIX,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
            ("openai", "gpt-4o-mini"),
        ],
        fallback_models=[
            ("anthropic", "claude-haiku-3-5-20241022"),
        ],
        prefer_cheapest=True,
    ),
    TaskType.CHAT: RoutingRule(
        task_type=TaskType.CHAT,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
        ],
        fallback_models=[
            ("openai", "gpt-4o-mini"),
        ],
        prefer_cheapest=True,
    ),
    TaskType.ROLEPLAY: RoutingRule(
        task_type=TaskType.ROLEPLAY,
        preferred_models=[
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        fallback_models=[
            ("deepseek", "deepseek-chat"),
        ],
        min_context_needed=16384,
        max_budget_per_call=0.03,
    ),
    TaskType.WORLDBUILDING: RoutingRule(
        task_type=TaskType.WORLDBUILDING,
        preferred_models=[
            ("deepseek", "deepseek-reasoner"),
            ("anthropic", "claude-sonnet-4-20250514"),
        ],
        fallback_models=[
            ("openai", "gpt-4o"),
        ],
        min_context_needed=16384,
        max_budget_per_call=0.04,
    ),
    TaskType.SUMMARIZATION: RoutingRule(
        task_type=TaskType.SUMMARIZATION,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
            ("openai", "gpt-4o-mini"),
        ],
        fallback_models=[],
        prefer_cheapest=True,
    ),
    TaskType.EXTRACTION: RoutingRule(
        task_type=TaskType.EXTRACTION,
        preferred_models=[
            ("openai", "gpt-4o-mini"),
            ("deepseek", "deepseek-chat"),
        ],
        fallback_models=[],
        prefer_cheapest=True,
    ),
    TaskType.LEARNING: RoutingRule(
        task_type=TaskType.LEARNING,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
        ],
        fallback_models=[],
        prefer_cheapest=True,
    ),
    TaskType.MARKET: RoutingRule(
        task_type=TaskType.MARKET,
        preferred_models=[
            ("deepseek", "deepseek-chat"),
        ],
        fallback_models=[],
    ),
}


# ─── 路由引擎 ────────────────────────────────────────


class ModelRouter:
    """多模型智能路由器

    用法:
        router = ModelRouter()
        model = router.route(TaskType.CREATIVE_WRITING)
        # → ModelInfo(provider="deepseek", model="deepseek-chat", ...)

        # 带预算约束
        model = router.route(TaskType.STYLING, budget=0.01)
        # → 可能降级到更便宜的模型

        # 手动指定
        model = router.route(TaskType.CREATIVE_WRITING,
                             force_model=("anthropic", "claude-sonnet-4-20250514"))
    """

    def __init__(self):
        self.model_library: dict[str, ModelInfo] = {}  # "provider:model" → ModelInfo
        self.routing_table: dict[TaskType, RoutingRule] = dict(DEFAULT_ROUTING_TABLE)
        self._model_stats: dict[str, dict] = defaultdict(dict)  # 使用统计
        self._model_available: dict[str, bool] = {}  # 可用性缓存

        self._init_library()

    def _init_library(self) -> None:
        """初始化模型库"""
        for mi in DEFAULT_MODEL_LIBRARY:
            key = f"{mi.provider}:{mi.model}"
            # 检查 API Key 是否存在
            api_key = getattr(settings, mi.api_key_env.lower(), "")
            if api_key:
                mi.enabled = True
            else:
                logger.debug(f"模型 {mi.display_name} 未配置 API Key，禁用")
                mi.enabled = False
            self.model_library[key] = mi

        # 加载用户自定义模型配置
        self._load_custom_models()

    def _load_custom_models(self) -> None:
        """加载用户自定义模型配置"""
        custom_path = settings.DATA_DIR / "model_routing.yaml"
        if not custom_path.exists():
            return
        try:
            import yaml

            with custom_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return

            # 加载自定义模型
            for model_data in data.get("models", []):
                mi = ModelInfo(
                    provider=model_data["provider"],
                    model=model_data["model"],
                    display_name=model_data.get("display_name", model_data["model"]),
                    base_url=model_data.get("base_url", ""),
                    api_key_env=model_data.get("api_key_env", ""),
                    context_window=model_data.get("context_window", 4096),
                    max_output_tokens=model_data.get("max_output_tokens", 4096),
                    cost_per_1k_input=model_data.get("cost_per_1k_input", 0.001),
                    cost_per_1k_output=model_data.get("cost_per_1k_output", 0.001),
                    strengths=[TaskType(t) for t in model_data.get("strengths", [])],
                    priority=model_data.get("priority", 50),
                )
                key = f"{mi.provider}:{mi.model}"
                self.model_library[key] = mi
                logger.info(f"加载自定义模型: {mi.display_name}")

            # 加载自定义路由规则
            for task_name, rule_data in data.get("routing", {}).items():
                try:
                    task_type = TaskType(task_name)
                    self.routing_table[task_type] = RoutingRule(
                        task_type=task_type,
                        preferred_models=[tuple(m) for m in rule_data.get("preferred", [])],
                        fallback_models=[tuple(m) for m in rule_data.get("fallback", [])],
                        min_context_needed=rule_data.get("min_context", 4096),
                        max_budget_per_call=rule_data.get("max_budget", 0.05),
                        prefer_cheapest=rule_data.get("prefer_cheapest", False),
                    )
                except ValueError:
                    logger.warning(f"未知任务类型: {task_name}")

        except Exception as e:
            logger.warning(f"加载自定义模型配置失败: {e}")

    # ── 路由核心 ──────────────────────────────────────

    def route(
        self,
        task_type: TaskType,
        budget: float = 0.0,
        force_model: tuple[str, str] | None = None,
        min_context: int = 0,
    ) -> ModelInfo | None:
        """为任务选择最优模型

        Args:
            task_type: 任务类型
            budget: 单次调用预算 ($, 0=不限制)
            force_model: 强制指定模型 (provider, model)
            min_context: 最低上下文要求

        Returns:
            最佳模型信息，无可选模型返回 None
        """
        # 强制指定模式
        if force_model:
            key = f"{force_model[0]}:{force_model[1]}"
            model = self.model_library.get(key)
            if model and model.enabled:
                return model
            logger.warning(f"强制指定模型不可用: {key}")

        # 获取路由规则
        rule = self.routing_table.get(task_type)
        if not rule:
            logger.warning(f"无路由规则: {task_type}")
            return self._fallback_any()

        effective_budget = budget or rule.max_budget_per_call
        effective_context = max(min_context, rule.min_context_needed)

        # 在偏好列表中查找最佳模型
        candidates = self._get_available_models(
            rule.preferred_models,
            effective_budget,
            effective_context,
        )

        if not candidates:
            # 尝试降级模型
            candidates = self._get_available_models(
                rule.fallback_models,
                effective_budget,
                effective_context,
            )

        if not candidates:
            # 最后尝试任何可用模型
            return self._fallback_any()

        # 选择最优模型
        if rule.prefer_cheapest:
            # 成本优先: 选最便宜的
            candidates.sort(key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)
        else:
            # 质量优先: 选优先级最高的
            candidates.sort(key=lambda m: (m.priority, m.cost_per_1k_input + m.cost_per_1k_output))

        selected = candidates[0]
        logger.debug(
            f"路由 {task_type.value} → {selected.display_name} "
            f"(预算=${effective_budget:.4f}, "
            f"成本=${selected.cost_per_1k_input + selected.cost_per_1k_output:.6f}/1k)"
        )
        return selected

    def _get_available_models(
        self,
        model_ids: list[tuple[str, str]],
        budget: float,
        min_context: int,
    ) -> list[ModelInfo]:
        """获取可用且满足条件的模型列表"""
        result: list[ModelInfo] = []
        for provider, model in model_ids:
            key = f"{provider}:{model}"
            mi = self.model_library.get(key)
            if not mi or not mi.enabled:
                continue
            # 预算检查
            call_cost = (mi.cost_per_1k_input + mi.cost_per_1k_output) * (min_context / 1000)
            if budget > 0 and call_cost > budget:
                continue
            # 上下文检查
            if mi.context_window < min_context:
                continue
            result.append(mi)
        return result

    def _fallback_any(self) -> ModelInfo | None:
        """返回任意可用模型"""
        available = [m for m in self.model_library.values() if m.enabled]
        if not available:
            logger.error("无可用模型！请检查 API Key 配置")
            return None
        available.sort(key=lambda m: m.priority)
        return available[0]

    # ── 模型信息 ──────────────────────────────────────

    def get_model(self, provider: str, model: str) -> ModelInfo | None:
        """获取模型信息"""
        key = f"{provider}:{model}"
        return self.model_library.get(key)

    def list_available_models(self) -> list[ModelInfo]:
        """列出所有可用模型"""
        return [m for m in self.model_library.values() if m.enabled]

    def list_all_models(self) -> list[ModelInfo]:
        """列出所有模型（含禁用）"""
        return list(self.model_library.values())

    # ── 成本估算 ──────────────────────────────────────

    def estimate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int = 0,
    ) -> float:
        """估算调用成本"""
        mi = self.get_model(provider, model)
        if not mi:
            return 0.0
        return mi.cost_per_1k_input * (input_tokens / 1000) + mi.cost_per_1k_output * (
            output_tokens / 1000
        )

    def compare_costs(
        self, task_type: TaskType, input_tokens: int = 2000, output_tokens: int = 1000
    ) -> dict:
        """比较不同模型对同一任务的成本"""
        rule = self.routing_table.get(task_type)
        if not rule:
            return {}

        all_model_ids = rule.preferred_models + rule.fallback_models
        result: dict[str, dict] = {}
        for provider, model in all_model_ids:
            cost = self.estimate_cost(provider, model, input_tokens, output_tokens)
            key = f"{provider}/{model}"
            result[key] = {
                "input_cost": self.estimate_cost(provider, model, input_tokens, 0),
                "output_cost": self.estimate_cost(provider, model, 0, output_tokens),
                "total_cost": cost,
            }
        return result

    # ── 路由表管理 ────────────────────────────────────

    def get_routing_rule(self, task_type: TaskType) -> RoutingRule | None:
        """获取任务路由规则"""
        return self.routing_table.get(task_type)

    def set_routing_rule(self, task_type: TaskType, rule: RoutingRule) -> None:
        """设置任务路由规则"""
        self.routing_table[task_type] = rule

    def get_routing_summary(self) -> dict:
        """获取路由摘要"""
        summary: dict[str, dict] = {}
        for task_type, rule in self.routing_table.items():
            primary = self._get_available_models(rule.preferred_models, 0, 0)
            summary[task_type.value] = {
                "preferred": [f"{p}/{m}" for p, m in rule.preferred_models],
                "available": [m.display_name for m in primary],
                "prefer_cheapest": rule.prefer_cheapest,
                "max_budget": rule.max_budget_per_call,
            }
        return summary


# ─── 工厂函数 ────────────────────────────────────────

_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """获取模型路由器单例"""
    global _router  # noqa: PLW0603
    if _router is None:
        _router = ModelRouter()
    return _router


def route_for_agent(agent_name: str) -> ModelInfo | None:
    """根据 Agent 名称路由模型

    便捷函数: 将 Agent 名称映射到任务类型
    """
    agent_task_map = {
        "writer": TaskType.CREATIVE_WRITING,
        "architect": TaskType.PLANNING,
        "auditor": TaskType.ANALYTICAL,
        "stylist": TaskType.STYLING,
        "reviser": TaskType.SIMPLE_FIX,
        "sociologist": TaskType.ROLEPLAY,
        "planner": TaskType.PLANNING,
        "observer": TaskType.EXTRACTION,
        "reflector": TaskType.EXTRACTION,
        "learner": TaskType.LEARNING,
        "market": TaskType.MARKET,
        "editor": TaskType.CHAT,
    }
    task_type = agent_task_map.get(agent_name.lower())
    if not task_type:
        logger.warning(f"未知 Agent: {agent_name}, 使用默认路由")
        task_type = TaskType.CHAT

    return get_model_router().route(task_type)

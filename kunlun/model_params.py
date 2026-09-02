"""
昆仑创作引擎 — 模型参数管理器

每个 Agent 可独立设置模型参数（temperature/top_p/max_tokens等），
每个参数都有推荐范围和说明。

设计原则:
  - 安全范围: 所有参数有推荐值、最小值、最大值
  - per-Agent: 不同 Agent 可用不同参数
  - per-Book: 不同作品可覆盖全局参数
  - 脚注注入: 在 Prompt 末尾自动附加参数说明
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger


@dataclass
class ParamDef:
    """参数定义"""

    key: str
    label: str
    description: str
    default: float
    min_val: float
    max_val: float
    step: float = 0.05
    agent_defaults: dict[str, float] = field(default_factory=dict)


# 全局参数定义（含推荐范围）
PARAM_DEFS: list[ParamDef] = [
    ParamDef(
        key="temperature",
        label="温度",
        description="控制输出的随机性。越低越确定(适合审计/修订)，越高越有创意(适合写作/推演)",
        default=0.7,
        min_val=0.0,
        max_val=2.0,
        step=0.05,
        agent_defaults={
            "architect": 0.8,  # 蓝图需要一定创意
            "writer": 0.85,  # 写作需要创意
            "auditor": 0.1,  # 审计要确定性
            "sociologist": 0.7,  # 推演需要平衡
            "style_engineer": 0.3,  # 润色要稳定
            "reviser": 0.3,  # 修订要精准
            "icu": 0.1,  # ICU要严格
        },
    ),
    ParamDef(
        key="top_p",
        label="Top-P (核采样)",
        description="控制采样的核大小。配合temperature使用，建议保持默认",
        default=0.9,
        min_val=0.0,
        max_val=1.0,
        step=0.05,
        agent_defaults={
            "writer": 0.95,
            "auditor": 0.5,
        },
    ),
    ParamDef(
        key="max_tokens",
        label="最大输出Token",
        description="每次LLM调用的最大输出长度。长篇写作需要较大的值",
        default=4096,
        min_val=512,
        max_val=16384,
        step=512,
        agent_defaults={
            "writer": 8192,
            "sociologist": 4096,
            "architect": 2048,
        },
    ),
    ParamDef(
        key="frequency_penalty",
        label="频率惩罚",
        description="减少重复内容的惩罚系数。越高越不重复",
        default=0.0,
        min_val=-2.0,
        max_val=2.0,
        step=0.1,
        agent_defaults={
            "writer": 0.3,
        },
    ),
    ParamDef(
        key="presence_penalty",
        label="存在惩罚",
        description="鼓励谈论新话题的惩罚系数。越高越倾向于引入新内容",
        default=0.0,
        min_val=-2.0,
        max_val=2.0,
        step=0.1,
    ),
]

# Agent 列表
AGENTS = [
    "architect",
    "writer",
    "auditor",
    "sociologist",
    "style_engineer",
    "reviser",
    "icu",
    "publisher",
]


class ModelParamManager:
    """
    模型参数管理器

    使用方式:
        mpm = ModelParamManager()
        temp = mpm.get("writer", "temperature", book_id="my_book")
        mpm.set("writer", "temperature", 0.9, book_id="my_book")
    """

    def __init__(self):
        # {book_id: {agent: {param: value}}}
        self._overrides: dict[str, dict[str, dict[str, float]]] = {}

    def get(self, agent: str, param: str, book_id: str = "default") -> float:
        """获取参数值（优先用户覆盖 → Agent默认 → 全局默认）"""
        # 1. 用户覆盖
        if (
            book_id in self._overrides
            and agent in self._overrides[book_id]
            and param in self._overrides[book_id][agent]
        ):
            return self._overrides[book_id][agent][param]
        # 2. Agent默认
        for pd in PARAM_DEFS:
            if pd.key == param and agent in pd.agent_defaults:
                return pd.agent_defaults[agent]
        # 3. 全局默认
        for pd in PARAM_DEFS:
            if pd.key == param:
                return pd.default
        return 0.7  # 终极保底

    def set(self, agent: str, param: str, value: float, book_id: str = "default") -> str:
        """设置参数值（含范围校验）。返回警告消息（如果有）"""
        # 查找参数定义
        param_def = None
        for pd in PARAM_DEFS:
            if pd.key == param:
                param_def = pd
                break
        if not param_def:
            raise ValueError(f"未知参数: {param}")

        # 范围校验
        if value < param_def.min_val or value > param_def.max_val:
            raise ValueError(
                f"{param} 值 {value} 超出推荐范围 [{param_def.min_val}, {param_def.max_val}]"
            )

        # 存储
        if book_id not in self._overrides:
            self._overrides[book_id] = {}
        if agent not in self._overrides[book_id]:
            self._overrides[book_id][agent] = {}
        self._overrides[book_id][agent][param] = value

        # 检查是否超出"安全"范围（推荐范围的一半区间外给出温和提示）
        warning = ""
        mid = (param_def.min_val + param_def.max_val) / 2
        half_range = (param_def.max_val - param_def.min_val) / 4
        if abs(value - mid) > half_range:
            warning = f"提示: {param}={value} 接近边界，建议 {param_def.default}"
        logger.info(f"[ModelParam] {book_id}/{agent}.{param} = {value}")
        return warning

    def get_all(self, agent: str, book_id: str = "default") -> dict:
        """获取Agent的所有参数"""
        result = {}
        for pd in PARAM_DEFS:
            result[pd.key] = self.get(agent, pd.key, book_id)
        return result

    def get_all_agents(self, book_id: str = "default") -> dict:
        """获取所有Agent的所有参数"""
        return {agent: self.get_all(agent, book_id) for agent in AGENTS}

    def reset(self, agent: str | None = None, book_id: str = "default"):
        """重置参数为用户覆盖"""
        if book_id in self._overrides:
            if agent:
                self._overrides[book_id].pop(agent, None)
            else:
                self._overrides[book_id].clear()

    def build_footnote(self, agent: str, book_id: str = "default") -> str:
        """
        构建参数脚注，注入到Prompt末尾。

        让用户知道当前使用的参数值及其推荐范围。
        """
        lines = ["", "---", "📐 当前模型参数:", ""]
        for pd in PARAM_DEFS:
            val = self.get(agent, pd.key, book_id)
            default = pd.agent_defaults.get(agent, pd.default)
            flag = " ⬅️ 默认" if abs(val - default) < 0.01 else " ✏️ 已自定义"
            lines.append(
                f"- `{pd.key}` = **{val}** (推荐: {pd.min_val}~{pd.max_val}, 默认: {default}){flag}"
            )
            lines.append(f"  · {pd.description}")
        return "\n".join(lines)


# 全局单例
model_param_manager = ModelParamManager()

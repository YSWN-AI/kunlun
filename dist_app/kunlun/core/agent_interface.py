"""
Agent 接口抽象层
定义所有 Agent 必须实现的协议，以及管线步骤的声明式接口。

基于 500 开源项目调研结论：
- 一切皆 Runnable（LangChain 风格）
- 声明式 Pipeline（Haystack 风格）
- 三层拦截（NestJS 风格）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

# ── 管线步骤结果 ────────────────────────────────────────


class StepStatus(StrEnum):
    """步骤执行状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"  # 降级执行（非关键步骤失败后继续）


@dataclass
class StepResult:
    """统一的管线步骤返回结果"""

    step_name: str
    status: StepStatus = StepStatus.PENDING
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (StepStatus.SUCCESS, StepStatus.SKIPPED, StepStatus.DEGRADED)

    @property
    def is_degraded(self) -> bool:
        return self.status == StepStatus.DEGRADED


# ── Agent 接口 ──────────────────────────────────────────


class PipelineContext(Protocol):
    """管线上下文协议（供各步骤共享状态）"""

    book_id: str
    chapter_number: int
    mode: str
    budget_tier: str


class AgentCapability(StrEnum):
    """Agent 能力枚举"""

    PIPELINE_ORCHESTRATION = "pipeline_orchestration"
    CHAPTER_GENERATION = "chapter_generation"
    AUDIT = "audit"
    BLUEPRINT = "blueprint"
    WRITING = "writing"
    REVISION = "revision"
    POLISH = "polish"
    KG_UPDATE = "kg_update"
    PUBLISH = "publish"
    SOCIETY_DEDUCTION = "society_deduction"
    CONFLICT_TRACKING = "conflict_tracking"
    VIBE_TRACKING = "vibe_tracking"
    STYLE_ENGINEERING = "style_engineering"
    QUALITY_CHECK = "quality_check"
    LEARNING = "learning"


class AgentProtocol(ABC):
    """Agent 抽象基类 — 所有 Agent 必须实现"""

    agent_name: str
    capabilities: list[str] = []

    @abstractmethod
    async def execute(self, task: dict) -> dict:
        """执行 Agent 任务"""
        ...

    async def validate_input(self, _task: dict) -> bool:
        """验证输入（可覆盖）"""
        return True

    async def pre_execute(self, task: dict) -> dict:
        """执行前钩子（可覆盖）"""
        return task

    async def post_execute(self, result: dict) -> dict:
        """执行后钩子（可覆盖）"""
        return result


# ── 声明式管线步骤 ────────────────────────────────────────


@dataclass
class PipelineStepDef:
    """声明式管线步骤定义"""

    name: str
    handler: str  # Agent 方法名或函数引用名
    required: bool = True  # 失败是否阻断管线
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: float = 120.0  # 超时秒数
    degrade_on_failure: bool = False  # 失败时是否降级而非中断
    skip_conditions: list[str] = field(default_factory=list)  # 跳过条件（上下文属性名）


# ── 错误处理三层拦截 ──────────────────────────────────────


class ErrorSeverity(StrEnum):
    """错误严重程度"""

    RETRYABLE = "retryable"  # 可重试
    DEGRADABLE = "degradable"  # 可降级
    FATAL = "fatal"  # 致命（中断管线）


@dataclass
class ErrorDecision:
    """错误处理决策"""

    severity: ErrorSeverity
    action: str  # retry / degrade / abort
    message: str
    retry_after_ms: int = 0


class ErrorClassifier:
    """错误分类器 — 将原始异常映射为结构化决策"""

    # 可重试的错误类型
    RETRYABLE_ERRORS = (
        "TimeoutError",
        "ConnectionError",
        "RateLimitError",
        "GachaRateLimitError",
    )

    # 可降级的错误类型
    DEGRADABLE_ERRORS = (
        "ValueError",
        "ImportError",
        "KGConnectionError",
        "KGEntityNotFoundError",
    )

    # 致命错误类型
    FATAL_ERRORS = (
        "ConfigError",
        "ConfigValidationError",
        "AuditGateError",
        "PipelineTimeoutError",
    )

    @classmethod
    def classify(cls, error: Exception, step_name: str = "") -> ErrorDecision:
        """分类异常并返回处理决策"""
        error_type = type(error).__name__

        if error_type in cls.RETRYABLE_ERRORS:
            return ErrorDecision(
                severity=ErrorSeverity.RETRYABLE,
                action="retry",
                message=f"[{step_name}] {error_type}: {error}",
                retry_after_ms=1000,
            )

        if error_type in cls.DEGRADABLE_ERRORS:
            return ErrorDecision(
                severity=ErrorSeverity.DEGRADABLE,
                action="degrade",
                message=f"[{step_name}] {error_type}: {error}（降级继续）",
            )

        if error_type in cls.FATAL_ERRORS:
            return ErrorDecision(
                severity=ErrorSeverity.FATAL,
                action="abort",
                message=f"[{step_name}] {error_type}: {error}（致命，中断管线）",
            )

        # 未知错误默认为致命
        return ErrorDecision(
            severity=ErrorSeverity.FATAL,
            action="abort",
            message=f"[{step_name}] 未知错误 {error_type}: {error}",
        )


# ── 管线结果 ────────────────────────────────────────────


@dataclass
class PipelineResult:
    """统一的管线执行结果"""

    success: bool
    book_id: str = ""
    chapter_number: int = 0
    steps: list[StepResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    error_summary: str = ""
    degraded_steps: list[str] = field(default_factory=list)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def failed_steps(self) -> list[str]:
        return [s.step_name for s in self.steps if s.status == StepStatus.FAILED]

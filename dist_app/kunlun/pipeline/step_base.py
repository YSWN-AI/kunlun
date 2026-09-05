"""
管线步骤抽象基类

将所有 _step_* 方法的共同模式提取为 BaseStep:
    - 检查点跳过（断点续跑）
    - 计时 & 进度上报
    - 三层错误处理（重试/降级/致命）
    - 统一 StepResult 返回

迁移路径：
    未来将 Makefile._step_* 方法逐个替换为独立的 BaseStep 子类，
    注册到 PipelineStepDef → StepRegistry → NovelPipeline 调用链。

用法示例：
    class BlueprintStep(BaseStep):
        step_name = "blueprint"
        def __init__(self, architect):
            super().__init__(PipelineStepDef(
                name="blueprint", handler="architect.generate",
                required=True, retry_count=1, timeout=120,
            ))
            self.architect = architect

        async def _execute_impl(self, ctx: _PipelineContext) -> dict:
            return await self.architect.generate(ctx)
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from kunlun.core.agent_interface import (
    ErrorClassifier,
    ErrorDecision,
    ErrorSeverity,
    PipelineStepDef,
    StepResult,
    StepStatus,
)

# ── 步骤执行摘要 ────────────────────────────────────────


@dataclass
class StepSummary:
    """步骤执行后的完整摘要，供 Pipeline 聚合使用"""

    result: StepResult
    decision: ErrorDecision | None = None  # 仅在异常时有值
    attempt: int = 1
    total_attempts: int = 1


# ── 上下文协议（最小接口）────────────────────────────────


class StepContext:  # pyright: ignore[reportUnusedClass]
    """步骤上下文的最小接口，基类只关心这两个属性"""

    book_id: str
    chapter: int
    completed_steps: set[str] = field(default_factory=set)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # 子类可以扩展更多属性（如 _PipelineContext 的 blueprint/draft 等）
        super().__init_subclass__(**kwargs)


# ── BaseStep 抽象基类 ──────────────────────────────────


class BaseStep(ABC):
    """
    管线步骤抽象基类

    封装所有步骤的共同模式：
    1. 检查点跳过   — 断点续跑
    2. 计时         — 性能指标
    3. 进度上报     — 可观测性
    4. 业务执行     — 子类实现 _execute_impl()
    5. 错误处理     — ErrorClassifier 三层决策
    6. 结果聚合     — 统一 StepResult

    子类必须：
    - 设置 class-level `step_name`
    - 实现 `_execute_impl(ctx) -> dict`
    """

    # 子类必须覆盖的类属性
    step_name: str = ""  # 步骤名（与 PipelineStep 枚举值对应）

    # 默认配置（子类可在 __init__ 中覆盖）
    required: bool = True
    retry_count: int = 1
    retry_delay: float = 2.0
    timeout: float = 120.0
    degrade_on_failure: bool = False
    skip_conditions: list = []

    def __init__(self, step_def: PipelineStepDef | None = None):
        """
        Args:
            step_def: 声明式步骤定义。若提供，覆盖类级默认值。
        """
        if step_def is not None:
            self.step_name = step_def.name
            self.required = step_def.required
            self.retry_count = step_def.retry_count
            self.retry_delay = step_def.retry_delay
            self.timeout = step_def.timeout
            self.degrade_on_failure = step_def.degrade_on_failure
            self.skip_conditions = step_def.skip_conditions

        if not self.step_name:
            raise ValueError(f"{self.__class__.__name__} 必须设置 step_name")

    # ── 子类必须实现 ──────────────────────────────────

    @abstractmethod
    async def _execute_impl(self, ctx: Any) -> dict:
        """
        步骤的实际业务逻辑。

        Args:
            ctx: 管线上下文（通常为 _PipelineContext 或类似对象）

        Returns:
            业务结果 dict，将被合并到 StepResult.data 中
        """
        ...

    # ── 公共接口 ──────────────────────────────────────

    async def execute(self, ctx: Any) -> StepResult:
        """
        执行步骤（含检查点跳过、重试、错误处理）。

        Pipeline 入口: pipeline.run() → step.execute(ctx)

        Returns:
            StepResult，status 为 SUCCESS / SKIPPED / DEGRADED / FAILED
        """
        # ① 检查跳过条件
        if self._should_skip(ctx):
            return StepResult(
                step_name=self.step_name,
                status=StepStatus.SKIPPED,
                data={"reason": "skip_condition_met"},
            )

        # ② 检查点跳过（断点续跑）
        if self._is_checkpoint_done(ctx):
            logger.debug(f"[{self.step_name}] 从检查点恢复，跳过")
            return StepResult(
                step_name=self.step_name,
                status=StepStatus.SKIPPED,
                data={"reason": "checkpoint_restored"},
            )

        # ③ 带重试的执行
        return await self._execute_with_retry(ctx)

    async def run(self, ctx: Any) -> StepSummary:
        """
        带完整摘要的执行（供 pipeline 引擎使用）。

        与 execute() 的区别：返回 StepSummary 而非 StepResult，
        包含 ErrorDecision 等额外元数据。
        """
        result = await self.execute(ctx)
        return StepSummary(result=result)

    # ── 内部方法 ──────────────────────────────────────

    def _should_skip(self, ctx: Any) -> bool:
        """检查是否满足跳过条件"""
        for cond in self.skip_conditions:
            if hasattr(ctx, cond) and getattr(ctx, cond):
                logger.debug(f"[{self.step_name}] 跳过条件 '{cond}' 满足")
                return True
        return False

    def _is_checkpoint_done(self, ctx: Any) -> bool:
        """检查是否已从检查点恢复（已完成）"""
        if hasattr(ctx, "completed_steps") and isinstance(ctx.completed_steps, set):
            return self.step_name in ctx.completed_steps
        return False

    async def _on_step_start(self, _ctx: Any) -> None:
        """步骤开始钩子（可覆盖，用于进度上报等）"""
        return

    async def _on_step_done(self, _ctx: Any, _result: StepResult) -> None:
        """步骤完成钩子（可覆盖，用于检查点保存等）"""
        return

    async def _on_step_error(self, _ctx: Any, _decision: ErrorDecision) -> None:
        """步骤出错钩子（可覆盖）"""
        return

    async def _execute_with_retry(self, ctx: Any) -> StepResult:
        """带重试逻辑的执行包装器"""
        total_attempts = 1 + self.retry_count
        last_error: Exception | None = None

        for attempt in range(1, total_attempts + 1):
            try:
                t_start = time.perf_counter()
                await self._on_step_start(ctx)

                # 带超时的执行
                data = await asyncio.wait_for(
                    self._execute_impl(ctx),
                    timeout=self.timeout,
                )

                duration_ms = (time.perf_counter() - t_start) * 1000
                result = StepResult(
                    step_name=self.step_name,
                    status=StepStatus.SUCCESS,
                    data=data,
                    duration_ms=round(duration_ms, 1),
                )
                await self._on_step_done(ctx, result)
                return result

            except TimeoutError as e:
                last_error = e
                decision = ErrorDecision(
                    severity=ErrorSeverity.RETRYABLE,
                    action="retry" if attempt <= self.retry_count else "degrade",
                    message=f"[{self.step_name}] 超时 ({self.timeout}s)",
                    retry_after_ms=int(self.retry_delay * 1000),
                )
                logger.warning(f"[{self.step_name}] {decision.message}，第{attempt}次")

            except Exception as e:
                last_error = e
                decision = ErrorClassifier.classify(e, self.step_name)

                # 重试或降级
                if decision.severity == ErrorSeverity.RETRYABLE and attempt <= self.retry_count:
                    logger.warning(
                        f"[{self.step_name}] {decision.message}，"
                        f"第{attempt}/{total_attempts}次，{decision.retry_after_ms}ms后重试"
                    )
                    await asyncio.sleep(decision.retry_after_ms / 1000)
                    continue
                if decision.severity == ErrorSeverity.DEGRADABLE and self.degrade_on_failure:
                    logger.warning(f"[{self.step_name}] 降级: {decision.message}")
                    await self._on_step_error(ctx, decision)
                    return StepResult(
                        step_name=self.step_name,
                        status=StepStatus.DEGRADED,
                        errors=[str(e)],
                        duration_ms=0,
                    )
                # 致命或不支持降级/重试耗尽
                logger.error(f"[{self.step_name}] {decision.message}")
                await self._on_step_error(ctx, decision)
                return StepResult(
                    step_name=self.step_name,
                    status=StepStatus.FAILED,
                    errors=[str(e)],
                    duration_ms=0,
                )

        # 重试耗尽
        decision = ErrorDecision(
            severity=ErrorSeverity.FATAL,
            action="abort",
            message=f"[{self.step_name}] {total_attempts}次尝试后仍失败",
        )
        logger.error(f"[{self.step_name}] {decision.message}")
        await self._on_step_error(ctx, decision)
        return StepResult(
            step_name=self.step_name,
            status=StepStatus.FAILED,
            errors=[str(last_error) if last_error else "重试耗尽"],
            duration_ms=0,
        )


# ── 步骤注册表（工厂模式）──────────────────────────────


class StepRegistry:
    """
    管线步骤注册表 — 工厂模式

    注册步骤类后，Pipeline 可按名称创建步骤实例。

    用法:
        registry = StepRegistry()
        registry.register("blueprint", BlueprintStep)
        step = registry.create("blueprint", architect=my_architect)
    """

    def __init__(self):
        self._steps: dict[str, type[BaseStep]] = {}

    def register(self, name: str, step_cls: type[BaseStep]) -> None:
        """注册步骤类"""
        if name in self._steps:
            logger.warning(f"[StepRegistry] 覆盖已注册步骤: {name}")
        self._steps[name] = step_cls

    def register_many(self, steps: dict[str, type[BaseStep]]) -> None:
        """批量注册"""
        for name, cls in steps.items():
            self.register(name, cls)

    def create(self, name: str, **kwargs: Any) -> BaseStep:
        """
        创建步骤实例。

        Args:
            name: 步骤名（注册时的 key）
            **kwargs: 传递给步骤构造函数的参数

        Returns:
            BaseStep 实例

        Raises:
            KeyError: 步骤未注册
        """
        if name not in self._steps:
            available = ", ".join(sorted(self._steps.keys()))
            raise KeyError(f"步骤 '{name}' 未注册。可用步骤: [{available}]")
        return self._steps[name](**kwargs)

    def list_steps(self) -> list[str]:
        """列出所有已注册步骤"""
        return sorted(self._steps.keys())

    def is_registered(self, name: str) -> bool:
        """检查步骤是否已注册"""
        return name in self._steps


# ── 全局单例注册表 ─────────────────────────────────────

default_registry = StepRegistry()

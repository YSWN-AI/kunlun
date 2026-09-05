"""
昆仑创作引擎 — 统一自定义异常类

from __future__ import annotations
按模块分层定义，支持精确的错误捕获和日志记录。
所有异常继承自 KunlunError，便于全局异常处理器统一捕获。
"""


class KunlunError(Exception):
    """昆仑引擎基础异常，所有自定义异常的基类。

    全局异常处理器 (main.py) 通过捕获 KunlunError 实现：
    - 已知业务异常 → 返回友好提示
    - 未知异常 (非 KunlunError) → 记录完整 traceback
    """

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ─── Writer Agent 异常 ───────────────────────


class WriterError(KunlunError):
    """Writer Agent 通用异常"""

    pass


class WriterBudgetError(WriterError):
    """Writer 上下文预算模块不可用或配置异常"""

    pass


class WriterRevisionError(WriterError):
    """Writer 修订提示词构建异常"""

    pass


class WriterGenerationError(WriterError):
    """Writer 正文生成异常"""

    pass


# ─── Pipeline 异常 ───────────────────────


class PipelineError(KunlunError):
    """Pipeline 通用异常"""

    pass


class PipelineStepError(PipelineError):
    """Pipeline 单步执行失败"""

    pass


class PipelineTimeoutError(PipelineError):
    """Pipeline 超时"""

    pass


# ─── Gacha Engine 异常 ───────────────────────


class GachaError(KunlunError):
    """Gacha Engine 通用异常"""

    pass


class GachaModelError(GachaError):
    """Gacha 模型不可用或配置错误"""

    pass


class GachaKeyExhaustedError(GachaError):
    """所有 API Key 均已熔断冷却"""

    pass


class GachaRateLimitError(GachaError):
    """Gacha 触发 API 限流"""

    pass


# ─── 知识图谱 (KG) 异常 ───────────────────────


class KGError(KunlunError):
    """知识图谱通用异常"""

    pass


class KGConnectionError(KGError):
    """KG 数据库连接异常"""

    pass


class KGEntityNotFoundError(KGError):
    """KG 实体不存在"""

    pass


# ─── 导出异常 ───────────────────────


class ExportError(KunlunError):
    """导出引擎通用异常"""

    pass


class ExportFormatError(ExportError):
    """不支持的导出格式"""

    pass


class ExportDependencyError(ExportError):
    """导出所需依赖未安装"""

    pass


# ─── 审计异常 ───────────────────────


class AuditError(KunlunError):
    """审计系统通用异常"""

    pass


class AuditGateError(AuditError):
    """审计门禁执行异常"""

    pass


# ─── 配置异常 ───────────────────────


class ConfigError(KunlunError):
    """配置异常"""

    pass


class ConfigValidationError(ConfigError):
    """配置校验失败"""

    pass

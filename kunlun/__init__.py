"""
昆仑创作引擎
MIT License - 开源 AI 辅助网文创作引擎

核心模块：
  - humanize/    去AI痕迹引擎
  - agents/      多Agent协作体系
  - gacha/       多模型抽卡引擎
  - audit/       33维审计门禁
  - kg/          知识图谱
  - structure/   故事结构分析器（Dramatica + Save the Cat + Hero's Journey）
  - proofread/   文本审校引擎（pycorrector + Vale 风格）
  - worlds/      世界观构建引擎（StoryCraftr RAG + 交互式图集）
  - character/   角色设定引擎（弧线/关系图/OOC检测）
  - plot/        情节推演引擎（因果链/伏笔/冲突/节奏）
  - coherence/   长文本连贯性引擎（SCORE + 摘要链 + 物品追踪）
  - marginal_efficiency/ 边际收益优化引擎
  - pipeline/    全管线创作编排
"""

from __future__ import annotations

import importlib

__version__ = "0.4.0"

from kunlun.config import settings
from kunlun.exceptions import (
    AuditError,
    AuditGateError,
    ConfigError,
    ConfigValidationError,
    ExportDependencyError,
    ExportError,
    ExportFormatError,
    GachaError,
    GachaKeyExhaustedError,
    GachaModelError,
    GachaRateLimitError,
    KGConnectionError,
    KGEntityNotFoundError,
    KGError,
    KunlunError,
    PipelineError,
    PipelineStepError,
    PipelineTimeoutError,
    WriterBudgetError,
    WriterError,
    WriterGenerationError,
    WriterRevisionError,
)

_LAZY_IMPORTS: dict[str, str] = {
    "gacha_engine": "kunlun.gacha.engine",
    "kg_client": "kunlun.kg.client",
    "model_router": "kunlun.model_router",
    "skill_loader": "kunlun.skills.loader",
    "icu_system": "kunlun.audit.icu",
    "token_tracker": "kunlun.token_tracker",
    "alerter": "kunlun.common.alerter",
    "output_contract": "kunlun.audit.output_contract",
    "snapshot_manager": "kunlun.kg.snapshot",
    "embedder": "kunlun.kg.embedder",
    "param_variator": "kunlun.gacha.param_variator",
    "text_refiner": "kunlun.style.refiner",
    "quality_dashboard": "kunlun.quality",
    "pipeline_intervention": "kunlun.pipeline",
    "get_orchestrator": "kunlun.vibe_writer.orchestrator",
    "fanqie_optimizer": "kunlun.audit.fanqie_gates",
    "get_conflict_manager": "kunlun.conflict",
    "get_vibe_engine": "kunlun.style.vibe",
    "gacha": "kunlun.gacha",
    "kg": "kunlun.kg",
    "audit": "kunlun.audit",
    "pipeline": "kunlun.pipeline",
    "agents": "kunlun.agents",
    # Phase 3 模块
    "monetize_engine": "kunlun.monetize",
    "marketplace_engine": "kunlun.marketplace",
    "plugin_store_engine": "kunlun.plugin_store",
    "finetune_engine": "kunlun.finetune",
    "analytics_engine": "kunlun.analytics",
}

_imported: dict[str, object] = {}


def __getattr__(name: str):
    if name in _imported:
        return _imported[name]

    module_path = _LAZY_IMPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'kunlun' has no attribute '{name}'")

    try:
        mod = importlib.import_module(module_path)
        attr = getattr(mod, name)
        _imported[name] = attr
        return attr
    except ImportError as e:
        raise AttributeError(
            f"module 'kunlun' has no attribute '{name}' (import failed: {e})"
        ) from e


__all__ = [
    "AuditError",
    "AuditGateError",
    "ConfigError",
    "ConfigValidationError",
    "ExportDependencyError",
    "ExportError",
    "ExportFormatError",
    "GachaError",
    "GachaKeyExhaustedError",
    "GachaModelError",
    "GachaRateLimitError",
    "KGConnectionError",
    "KGEntityNotFoundError",
    "KGError",
    "KunlunError",
    "PipelineError",
    "PipelineStepError",
    "PipelineTimeoutError",
    "WriterBudgetError",
    "WriterError",
    "WriterGenerationError",
    "WriterRevisionError",
    "__version__",
    "alerter",
    "analytics_engine",
    "embedder",
    "fanqie_optimizer",
    "finetune_engine",
    "gacha_engine",
    "get_conflict_manager",
    "get_orchestrator",
    "get_vibe_engine",
    "icu_system",
    "kg_client",
    "marketplace_engine",
    "model_router",
    "monetize_engine",
    "output_contract",
    "param_variator",
    "pipeline_intervention",
    "plugin_store_engine",
    "quality_dashboard",
    "settings",
    "skill_loader",
    "snapshot_manager",
    "text_refiner",
    "token_tracker",
]

"""
昆仑创作引擎 — 专业生成器工具箱

纯模板+规则生成，不调用 LLM，离线可用、零成本。
包含8种生成器：书名、简介、大纲、细纲、黄金开篇、金手指、名字、人设。
"""

from kunlun.toolbox.models import (
    GENERATOR_LABELS,
    GENERATOR_TYPES,
    ChapterOutlineGenerateRequest,
    ChapterOutlineResult,
    CharacterGenerateRequest,
    CharacterProfile,
    CharacterResult,
    CheatGenerateRequest,
    CheatResult,
    CheatScheme,
    GeneratorInfo,
    GenericGenerateRequest,
    HistoryRecord,
    NameGenerateRequest,
    NameResult,
    OpeningGenerateRequest,
    OpeningResult,
    OpeningScheme,
    OutlineGenerateRequest,
    OutlineResult,
    SaveRequest,
    SynopsisGenerateRequest,
    SynopsisResult,
    TitleGenerateRequest,
    TitleResult,
    VolumeOutline,
)
from kunlun.toolbox.service import generate, get_history, list_generators, save_result

__all__ = [
    "GENERATOR_LABELS",
    "GENERATOR_TYPES",
    "ChapterOutlineGenerateRequest",
    "ChapterOutlineResult",
    "CharacterGenerateRequest",
    "CharacterProfile",
    "CharacterResult",
    "CheatGenerateRequest",
    "CheatResult",
    "CheatScheme",
    "GeneratorInfo",
    "GenericGenerateRequest",
    "HistoryRecord",
    "NameGenerateRequest",
    "NameResult",
    "OpeningGenerateRequest",
    "OpeningResult",
    "OpeningScheme",
    "OutlineGenerateRequest",
    "OutlineResult",
    "SaveRequest",
    "SynopsisGenerateRequest",
    "SynopsisResult",
    "TitleGenerateRequest",
    "TitleResult",
    "VolumeOutline",
    "generate",
    "get_history",
    "list_generators",
    "save_result",
]

__version__ = "0.1.0"

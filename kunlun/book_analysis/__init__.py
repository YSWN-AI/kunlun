"""
昆仑创作引擎 — AI拆书案例库

内置12个覆盖不同题材和平台的爆款作品拆解案例，
提供案例检索、多案例对比分析、共性方法论提炼等功能。
纯数据+规则实现，不调用LLM。
"""

from kunlun.book_analysis.models import (
    BookAnalysisCase,
    CharacterArc,
    CompareRequest,
    CustomCaseCreateRequest,
    CustomCaseUpdateRequest,
    MethodologyRequest,
    NarrativeRhythm,
    NarrativeRhythmPhase,
    PleasurePoint,
    PlotStructure,
    StyleFingerprint,
)
from kunlun.book_analysis.service import (
    compare_cases,
    create_custom_case,
    delete_custom_case,
    extract_methodology,
    get_all_cases,
    get_case,
    get_categories,
    search_cases,
    update_custom_case,
)

__all__ = [
    "BookAnalysisCase",
    "CharacterArc",
    "CompareRequest",
    "CustomCaseCreateRequest",
    "CustomCaseUpdateRequest",
    "MethodologyRequest",
    "NarrativeRhythm",
    "NarrativeRhythmPhase",
    "PleasurePoint",
    "PlotStructure",
    "StyleFingerprint",
    "compare_cases",
    "create_custom_case",
    "delete_custom_case",
    "extract_methodology",
    "get_all_cases",
    "get_case",
    "get_categories",
    "search_cases",
    "update_custom_case",
]

__version__ = "0.1.0"

"""
昆仑创作引擎 — story structure analyzer (故事结构分析器)

深度融合 Dramatica 理论 + Save the Cat 15节拍 + Hero's Journey 12阶段。
纯规则+简单NLP（jieba分词），零LLM成本；可选LLM增强模式。

核心组件:
  - StoryStructureAnalyzer: 主分析器入口
  - BeatLibrary: 节拍库（3种理论体系）
  - TensionCurve: 张力曲线分析
  - PlotPointDetector: 情节点检测器
"""

from kunlun.structure.analyzer import (
    BeatInfo,
    BeatLibrary,
    DramaticaPoint,
    HeroJourneyStage,
    PlotPointDetector,
    SaveTheCatBeat,
    StoryStructureAnalyzer,
    TensionCurve,
    TensionReport,
    plot_detector,
    structure_analyzer,
    tension_curve,
)

__all__ = [
    "BeatInfo",
    "BeatLibrary",
    "DramaticaPoint",
    "HeroJourneyStage",
    "PlotPointDetector",
    "SaveTheCatBeat",
    "StoryStructureAnalyzer",
    "TensionCurve",
    "TensionReport",
    "plot_detector",
    "structure_analyzer",
    "tension_curve",
]

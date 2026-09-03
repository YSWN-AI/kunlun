"""
Style 风格润色模块
Phase 6 实现: 消AI味 + 语感优化 + 文风指纹

组件:
  - StyleEngineer: 规则化去AI味后处理
  - StyleAnalyzer: 提取统计风格指纹
  - StyleInjector: 将指纹注入到 Writer prompt
  - StyleLibrary: 风格库管理（多指纹存储/对比/持久化）
  - StyleDriftDetector: 风格漂移检测（章节一致性监控）
"""

from .fingerprint import (
    StyleAnalyzer,
    StyleFingerprint,
    StyleInjector,
    style_analyzer,
    style_injector,
)
from .library import StyleLibrary, style_library
from .drift_detector import DriftReport, StyleDriftDetector, drift_detector

# StyleEngineer 延迟导入：避免循环依赖
# (engineer 继承 BaseAgent -> agents.__init__ -> editor -> style.engineer)
def __getattr__(name: str):
    if name == "StyleEngineer":
        from .engineer import StyleEngineer

        return StyleEngineer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "StyleAnalyzer",
    "StyleDriftDetector",
    "StyleEngineer",
    "StyleFingerprint",
    "StyleInjector",
    "StyleLibrary",
    "DriftReport",
    "drift_detector",
    "style_analyzer",
    "style_injector",
    "style_library",
]

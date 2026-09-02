"""
Style 风格润色模块
Phase 6 实现: 消AI味 + 语感优化 + 文风指纹

组件:
  - StyleEngineer: 规则化去AI味后处理
  - StyleAnalyzer: 提取统计风格指纹
  - StyleInjector: 将指纹注入到 Writer prompt
"""

from .engineer import StyleEngineer
from .fingerprint import (
    StyleAnalyzer,
    StyleFingerprint,
    StyleInjector,
    style_analyzer,
    style_injector,
)

__all__ = [
    "StyleAnalyzer",
    "StyleEngineer",
    "StyleFingerprint",
    "StyleInjector",
    "style_analyzer",
    "style_injector",
]

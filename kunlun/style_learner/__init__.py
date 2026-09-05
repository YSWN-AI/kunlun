"""
昆仑创作引擎 — 风格学习与人类风格模仿模块

提供中文男频网文的风格指纹提取、风格相似度计算、风格引导生成和作者风格库。
同时提供爆款仿写四维度分析器（StyleLearner），覆盖设定/情节/正文风格/结构。

Usage:
    from kunlun.style_learner import (
        extract_style_fingerprint, calculate_style_similarity,
        get_preset_style, list_preset_styles, build_style_prompt,
        StyleFingerprintExtractor, StyleSimilarityCalculator,
        StyleGuidedGenerator, StyleLibrary, StyleFingerprint,
        StyleLearner,
    )

    # 提取风格指纹
    fp = extract_style_fingerprint(text, "作者名")
    print(fp.summary())

    # 爆款仿写四维度分析
    learner = StyleLearner()
    report = learner.analyze_book("书名", text, book_id="mybook")
"""

from kunlun.style_learner.engine import (
    MALE_AUTHOR_STYLES,
    DimensionFeature,
    StyleDimension,
    StyleFingerprint,
    StyleFingerprintExtractor,
    StyleGuidedGenerator,
    StyleLearner,
    StyleLibrary,
    StyleSimilarityCalculator,
    StyleSimilarityResult,
    build_style_prompt,
    calculate_style_similarity,
    extract_style_fingerprint,
    get_preset_style,
    list_preset_styles,
)

__all__ = [
    "MALE_AUTHOR_STYLES",
    "DimensionFeature",
    "StyleDimension",
    "StyleFingerprint",
    "StyleFingerprintExtractor",
    "StyleGuidedGenerator",
    "StyleLearner",
    "StyleLibrary",
    "StyleSimilarityCalculator",
    "StyleSimilarityResult",
    "build_style_prompt",
    "calculate_style_similarity",
    "extract_style_fingerprint",
    "get_preset_style",
    "list_preset_styles",
]

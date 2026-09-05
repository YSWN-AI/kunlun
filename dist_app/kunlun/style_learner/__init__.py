"""
昆仑创作引擎 — 风格学习与人类风格模仿模块

提供中文男频网文的风格指纹提取、风格相似度计算、风格引导生成和作者风格库。

Usage:
    from kunlun.style_learner import (
        extract_style_fingerprint, calculate_style_similarity,
        get_preset_style, list_preset_styles, build_style_prompt,
        StyleFingerprintExtractor, StyleSimilarityCalculator,
        StyleGuidedGenerator, StyleLibrary, StyleFingerprint,
    )

    # 提取风格指纹
    fp = extract_style_fingerprint(text, "作者名")
    print(fp.summary())

    # 计算风格相似度
    sim = calculate_style_similarity(text1, text2)
    print(sim.summary())

    # 使用预设风格
    styles = list_preset_styles()
    prompt = build_style_prompt("辰东", scene_type="battle")

    # 风格一致性检查
    generator = StyleGuidedGenerator()
    result = generator.check_style_consistency(chapters, "作者名")
"""

from kunlun.style_learner.engine import (
    MALE_AUTHOR_STYLES,
    DimensionFeature,
    StyleDimension,
    StyleFingerprint,
    StyleFingerprintExtractor,
    StyleGuidedGenerator,
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
    "StyleLibrary",
    "StyleSimilarityCalculator",
    "StyleSimilarityResult",
    "build_style_prompt",
    "calculate_style_similarity",
    "extract_style_fingerprint",
    "get_preset_style",
    "list_preset_styles",
]

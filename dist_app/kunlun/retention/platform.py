"""
昆仑创作引擎 — 平台适配评分器
"""

from __future__ import annotations

from typing import Any

from .types import ChapterFeatures


class PlatformAdapter:
    """平台适配评分器

    不同平台有不同的追读力偏好:
      - 番茄小说: 黄金三章 + 快节奏 + 高爽点密度
      - 起点: 慢热 + 深度 + 长线伏笔
      - 七猫: 快节奏 + 轻松 + 笑点密集
      - 飞卢: 极快节奏 + 强冲突 + 脑洞
      - 晋江: 感情线 + 细腻 + 氛围
    """

    PLATFORM_WEIGHTS: dict[str, dict[str, Any]] = {
        "fanqie": {  # 番茄小说
            "hook": 0.35,
            "pleasure": 0.35,
            "payoff": 0.15,
            "debt": 0.15,
            "min_words": 1500,
            "max_words": 3000,
            "prefer_dialogue_ratio": (0.3, 0.5),
            "prefer_pleasure_density": 3.0,  # 每千字
        },
        "qidian": {  # 起点
            "hook": 0.25,
            "pleasure": 0.25,
            "payoff": 0.25,
            "debt": 0.25,
            "min_words": 2000,
            "max_words": 5000,
            "prefer_dialogue_ratio": (0.2, 0.4),
            "prefer_pleasure_density": 2.0,
        },
        "qimao": {  # 七猫
            "hook": 0.30,
            "pleasure": 0.35,
            "payoff": 0.15,
            "debt": 0.20,
            "min_words": 1500,
            "max_words": 3000,
            "prefer_dialogue_ratio": (0.3, 0.6),
            "prefer_pleasure_density": 3.5,
        },
        "feilu": {  # 飞卢
            "hook": 0.35,
            "pleasure": 0.35,
            "payoff": 0.10,
            "debt": 0.20,
            "min_words": 1000,
            "max_words": 2500,
            "prefer_dialogue_ratio": (0.2, 0.5),
            "prefer_pleasure_density": 4.0,
        },
        "jjwxc": {  # 晋江
            "hook": 0.20,
            "pleasure": 0.20,
            "payoff": 0.30,
            "debt": 0.30,
            "min_words": 2500,
            "max_words": 6000,
            "prefer_dialogue_ratio": (0.3, 0.5),
            "prefer_pleasure_density": 1.5,
        },
    }

    @classmethod
    def score_for_platform(
        cls,
        platform: str,
        hook_score: float,
        pleasure_score: float,
        payoff_score: float,
        debt_score: float,
        features: ChapterFeatures | None = None,
    ) -> tuple[float, list[str]]:
        """计算特定平台追读力评分"""
        if platform not in cls.PLATFORM_WEIGHTS:
            return 0.0, [f"未知平台: {platform}"]

        w = cls.PLATFORM_WEIGHTS[platform]
        base_score = (
            hook_score * w["hook"]
            + pleasure_score * w["pleasure"]
            + payoff_score * w["payoff"]
            + debt_score * w["debt"]
        )

        suggestions: list[str] = []

        # 字数适配
        if features:
            if features.word_count < w["min_words"]:
                base_score -= 0.05
                suggestions.append(f"字数不足 {platform} 最低要求 ({w['min_words']})")
            if features.word_count > w["max_words"]:
                suggestions.append(f"字数超过 {platform} 最佳上限 ({w['max_words']})")

            # 对话比例适配
            d_min, d_max = w["prefer_dialogue_ratio"]
            if features.dialogue_ratio < d_min:
                suggestions.append(
                    f"对话比例偏低 (当前{features.dialogue_ratio:.0%}, 建议≥{d_min:.0%})"
                )
            if features.dialogue_ratio > d_max:
                suggestions.append(
                    f"对话比例偏高 (当前{features.dialogue_ratio:.0%}, 建议≤{d_max:.0%})"
                )

        return round(min(base_score, 1.0), 2), suggestions

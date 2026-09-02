"""
昆仑创作引擎 — 爽点评分器
"""

from __future__ import annotations

import itertools
import re
from typing import Any

from .types import PleasureCategory, PleasurePoint


class PleasureScorer:
    """爽点评分器 — 基于规则和统计

    评估维度:
      1. 爽点密度 — 每千字爽点数量
      2. 爽点间隔 — 爽点之间的段落间距
      3. 爽点多样性 — 不同类别爽点的分布
      4. 爽点强度 — 爽点的平均强度
      5. 类型疲劳 — 同类型爽点连续出现次数
    """

    # 爽点关键词库
    PLEASURE_KEYWORDS: dict[PleasureCategory, list[str]] = {
        PleasureCategory.FACE_SLAP: [
            r"打脸",
            r"啪啪",
            r"[当众公然].{0,5}打",
            r"[羞惭尴]愧",
            r"无地自容",
            r"脸[色上].{0,5}(?:难看|变)",
            r"[不没]敢[相信抬头]",
            r"惊[呆愕]",
            r"反转.{0,5}打脸",
            r"谁[说以为].{0,10}结果",
        ],
        PleasureCategory.POWER_UP: [
            r"突破",
            r"瓶颈[松打]破",
            r"晋级",
            r"升级",
            r"实力[大增暴涨]",
            r"灵力.{0,5}(?:暴涨|涌动)",
            r"境界.{0,5}(?:提升|突破)",
            r"修[为炼].{0,5}(?:大涨|精进)",
            r"觉醒",
            r"领悟",
            r"顿悟",
        ],
        PleasureCategory.TREASURE: [
            r"宝物",
            r"机缘",
            r"奇遇",
            r"捡到",
            r"发现.{0,5}(?:秘籍|丹药|法宝)",
            r"传承",
            r"洞府",
            r"秘境",
            r"藏宝",
            r"天材地宝",
            r"灵药",
            r"神器",
        ],
        PleasureCategory.REVENGE: [
            r"复仇",
            r"报仇",
            r"血债",
            r"以牙还牙",
            r"终于[等找]到",
            r"这[一笔]账",
            r"血[恨仇]",
            r"不共戴天",
            r"清算",
        ],
        PleasureCategory.ROMANCE: [
            r"心跳",
            r"脸红",
            r"牵手",
            r"拥抱",
            r"表白",
            r"定情",
            r"告白",
            r"感情.{0,5}(?:升温|突破)",
            r"暧昧",
        ],
        PleasureCategory.MYSTERY_SOLVE: [
            r"原来是",
            r"真相[大揭]白",
            r"谜[底题].{0,5}(?:解开|揭晓)",
            r"终于[知明]白",
            r"原来如此",
            r"恍然大悟",
        ],
        PleasureCategory.PRESTIGE: [
            r"声望",
            r"名[声气]",
            r"[扬威]名",
            r"万人[敬仰瞩目]",
            r"佩服",
            r"崇拜",
            r"地位.{0,5}(?:提升|稳固)",
            r"势力.{0,5}(?:扩大|增强)",
        ],
        PleasureCategory.COUNTERATTACK: [
            r"绝[地处境]",
            r"反击",
            r"逆[袭转]",
            r"绝境.{0,5}(?:逢生|反击)",
            r"置之死地",
            r"以弱[胜击]强",
            r"翻盘",
        ],
        PleasureCategory.ALLIANCE: [
            r"结盟",
            r"联盟",
            r"联手",
            r"合作",
            r"收服",
            r"归顺",
            r"投靠",
            r"加入",
        ],
        PleasureCategory.BETRAYAL: [
            r"背叛",
            r"出卖",
            r"反水",
            r"倒戈",
            r"卧底",
            r"内奸",
            r"叛徒",
        ],
        PleasureCategory.SACRIFICE: [
            r"牺牲",
            r"献祭",
            r"舍[身命]",
            r"为了.{0,5}(?:保护|拯救)",
            r"赴死",
        ],
        PleasureCategory.COMEDY: [
            r"哈哈",
            r"搞笑",
            r"逗[比乐]",
            r"笑[喷死]",
            r"吐槽",
            r"玩梗",
            r"整活",
        ],
    }

    # 爽点强度系数 (某些类型天生更"爽")
    CATEGORY_INTENSITY_BASE: dict[PleasureCategory, float] = {
        PleasureCategory.FACE_SLAP: 0.9,
        PleasureCategory.POWER_UP: 0.8,
        PleasureCategory.COUNTERATTACK: 0.85,
        PleasureCategory.REVENGE: 0.9,
        PleasureCategory.TREASURE: 0.6,
        PleasureCategory.PRESTIGE: 0.65,
        PleasureCategory.MYSTERY_SOLVE: 0.55,
        PleasureCategory.ROMANCE: 0.5,
        PleasureCategory.ALLIANCE: 0.45,
        PleasureCategory.BETRAYAL: 0.4,
        PleasureCategory.SACRIFICE: 0.35,
        PleasureCategory.COMEDY: 0.3,
    }

    @classmethod
    def detect_pleasure_points(cls, text: str) -> list[PleasurePoint]:
        """检测全文爽点"""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        points: list[PleasurePoint] = []

        for i, para in enumerate(paragraphs):
            for category, patterns in cls.PLEASURE_KEYWORDS.items():
                match_count = 0
                for pattern in patterns:
                    if re.search(pattern, para):
                        match_count += 1
                if match_count > 0:
                    # 基础强度 = 类别基础系数 × 匹配密度
                    base = cls.CATEGORY_INTENSITY_BASE.get(category, 0.5)
                    intensity = min(base * (1 + (match_count - 1) * 0.2), 1.0)
                    points.append(
                        PleasurePoint(
                            category=category,
                            paragraph_index=i,
                            intensity=round(intensity, 2),
                            matched_text=para[:100],
                        )
                    )

        return points

    @classmethod
    def calculate_pleasure_score(
        cls,
        points: list[PleasurePoint],
        word_count: int,
        total_paragraphs: int,
        is_climax_chapter: bool = False,
    ) -> tuple[float, dict[str, Any]]:
        """计算综合爽点评分

        Returns:
            (score, diagnostics) — score 0.0~1.0
        """
        if not points or word_count == 0:
            return 0.0, {"reason": "无爽点或无正文"}

        diag: dict[str, Any] = {}

        # 1. 爽点密度 — 每千字爽点数
        density = len(points) / (word_count / 1000)
        diag["density_per_1k"] = round(density, 2)

        # 密度评分: 网文最佳 2-5个/千字
        if density >= 3:
            density_score = 1.0
        elif density >= 2:
            density_score = 0.8
        elif density >= 1:
            density_score = 0.5
        elif density >= 0.5:
            density_score = 0.3
        else:
            density_score = 0.1

        # 2. 爽点间隔 — 最大段落间隔
        sorted_indices = sorted(p.paragraph_index for p in points)
        if len(sorted_indices) > 1:
            gaps = [b - a for a, b in itertools.pairwise(sorted_indices)]
            max_gap = max(gaps) if gaps else 0
            avg_gap = sum(gaps) / len(gaps)
            diag["max_paragraph_gap"] = max_gap
            diag["avg_paragraph_gap"] = round(avg_gap, 1)

            # 间隔评分: 间隔越小越好 (但也要有呼吸空间)
            max_allowed_gap = total_paragraphs * 0.3  # 30%段落内无爽点=扣分
            if max_gap <= 3:
                gap_score = 1.0
            elif max_gap <= 5:
                gap_score = 0.8
            elif max_gap <= max_allowed_gap:
                gap_score = 0.5
            else:
                gap_score = 0.2
        else:
            gap_score = 0.5

        # 3. 爽点多样性
        categories = [p.category for p in points]
        unique_cats = set(categories)
        diversity_ratio = len(unique_cats) / len(PleasureCategory)
        diag["unique_categories"] = len(unique_cats)
        diag["diversity_ratio"] = round(diversity_ratio, 2)
        diversity_score = min(diversity_ratio * 2, 1.0)

        # 4. 爽点强度
        intensities = [p.intensity for p in points]
        avg_intensity = sum(intensities) / len(intensities)
        diag["avg_intensity"] = round(avg_intensity, 2)
        intensity_score = avg_intensity

        # 5. 类型疲劳 — 同类型连续出现
        fatigue_penalty = 0.0
        max_consecutive = 0
        current_cat = None
        current_count = 0
        for p in points:
            if p.category == current_cat:
                current_count += 1
            else:
                current_cat = p.category
                current_count = 1
            max_consecutive = max(max_consecutive, current_count)

        # 同类型连续超过4次严重疲劳
        if max_consecutive > 6:
            fatigue_penalty = 0.3
        elif max_consecutive > 4:
            fatigue_penalty = 0.15
        elif max_consecutive > 3:
            fatigue_penalty = 0.05

        diag["max_consecutive_same_type"] = max_consecutive
        diag["fatigue_penalty"] = fatigue_penalty

        # 综合评分
        weights = {
            "density": 0.30,
            "gap": 0.20,
            "diversity": 0.20,
            "intensity": 0.30,
        }

        # 高潮章密度权重加倍
        if is_climax_chapter:
            weights["density"] = 0.40
            weights["intensity"] = 0.25
            weights["gap"] = 0.15
            weights["diversity"] = 0.20

        score = (
            density_score * weights["density"]
            + gap_score * weights["gap"]
            + diversity_score * weights["diversity"]
            + intensity_score * weights["intensity"]
            - fatigue_penalty
        )

        diag["sub_scores"] = {
            "density": round(density_score, 2),
            "gap": round(gap_score, 2),
            "diversity": round(diversity_score, 2),
            "intensity": round(intensity_score, 2),
        }

        return round(max(score, 0.0), 2), diag

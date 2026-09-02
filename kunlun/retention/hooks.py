"""
昆仑创作引擎 — 钩子检测器 + 钩子强度评分器
"""

from __future__ import annotations

import re

from .types import HookResult, HookStrengthReport, HookType

# ─── Hook 检测器 ─────────────────────────────────────


class HookDetector:
    """章节钩子检测器 — 零 LLM 规则引擎

    检测6种钩子类型:
      - 章节开头钩子 (opening hook): 前3段的吸引力
      - 章节结尾钩子 (closing hook): 最后3段的悬念/预告
      - 中间钩子 (mid hook): 场景切换时的悬念

    基于关键词 + 句式模式 + 段落位置的综合检测。
    """

    # 钩子关键词库（中文网文高频钩子表达）
    HOOK_PATTERNS: dict[HookType, list[str]] = {
        HookType.CLIFFHANGER: [
            r"突然[，,]",
            r"就在这[一时]刻",
            r"他不知道的是",
            r"然而[，,]",
            r"但是[，,]",
            r"却[没不]",
            r"门[口后]",
            r"身后[传响]",
            r"一声[巨响爆]",
            r"[冷冷淡淡]笑",
            r"瞳孔[一猛]",
            r"猛地",
            r"骤然",
            r"霎[时那]",
        ],
        HookType.REVELATION: [
            r"原来[，他她这才]",
            r"竟然是",
            r"真相[是就]",
            r"终于[明发]现",
            r"才[知道明白]",
            r"秘密[是就]",
            r"难怪",
            r"所以[，这才]",
            r"答案[是就]",
        ],
        HookType.CONFRONTATION: [
            r"[你你敢]",
            r"找死",
            r"放肆",
            r"[住住]手",
            r"狂妄",
            r"[不没]可能",
            r"[绝决不]允许",
            r"岂[有能]",
            r"[大胆放肆]",
        ],
        HookType.PROMISE: [
            r"明[天日后]",
            r"等[着到]",
            r"很快[就便]",
            r"下一次",
            r"不久[之就以]",
            r"下次[再见]",
            r"三天[之以]后",
            r"即将",
        ],
        HookType.EMOTIONAL: [
            r"眼泪",
            r"[哭笑]了",
            r"感动",
            r"心[中头]",
            r"激动",
            r"[愤怒火]",
            r"颤抖",
            r"握紧[了双拳]",
            r"热血[沸涌]",
        ],
        HookType.MYSTERY: [
            r"为什么",
            r"那个[东西符号人]",
            r"到底[是]",
            r"究竟",
            r"这[到个]底[是]",
            r"什么[意思含义]",
            r"从未见过",
            r"无法[理解想象]",
        ],
        HookType.POWER_UP: [
            r"突破",
            r"瓶颈",
            r"晋级",
            r"升级",
            r"觉醒",
            r"领悟",
            r"境界",
            r"瓶颈松动",
            r"灵力[涌暴]",
        ],
        HookType.REVERSAL: [
            r"反转",
            r"没想到",
            r"出乎[意料]",
            r"谁[也又]没[有想]",
            r"竟然是",
            r"真正[的]",
            r"不是[，他她]",
            r"所有人都[错被骗]",
        ],
    }

    # 弱钩子模式 (降低评分的模式)
    WEAK_CLOSING_PATTERNS = [
        r"说完[，他她就].{0,10}(?:走了|离开了|回去了)",
        r"(?:天色|夜幕).{0,10}(?:降临|渐渐)",
        r"一夜无话",
        r"时间[一飞]",
        r"第[二三天].{0,5}(?:清晨|一早)",
        r"就这样[，].{0,10}(?:过去了|结束了)",
    ]

    @classmethod
    def detect_hooks(cls, text: str) -> list[HookResult]:
        """检测全文钩子"""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) < 3:
            return []

        results: list[HookResult] = []

        # 检测开头钩子（前3段）
        opening_range = min(3, len(paragraphs))
        for i in range(opening_range):
            hooks = cls._detect_in_paragraph(paragraphs[i], i, "opening")
            results.extend(hooks)

        # 检测结尾钩子（最后3段）
        closing_start = max(0, len(paragraphs) - 3)
        for i in range(closing_start, len(paragraphs)):
            hooks = cls._detect_in_paragraph(paragraphs[i], i, "closing")
            results.extend(hooks)

        # 检测中间钩子（每隔约5段取1段）
        mid_interval = max(5, len(paragraphs) // 4)
        for i in range(3, len(paragraphs) - 3, mid_interval):
            hooks = cls._detect_in_paragraph(paragraphs[i], i, "mid_chapter")
            results.extend(hooks)

        return results

    @classmethod
    def _detect_in_paragraph(cls, text: str, idx: int, position: str) -> list[HookResult]:
        """在单个段落中检测钩子"""
        results: list[HookResult] = []
        for hook_type, patterns in cls.HOOK_PATTERNS.items():
            matched_keywords: list[str] = []
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, text):
                    matched_keywords.append(pattern)
                    match_count += 1
            if match_count > 0:
                # 强度 = min(匹配数 / 3, 1.0) * 位置系数
                base_strength = min(match_count / 3.0, 1.0)
                position_mult = {"opening": 0.9, "closing": 1.2, "mid_chapter": 0.7}
                strength = min(base_strength * position_mult.get(position, 0.8), 1.0)
                results.append(
                    HookResult(
                        hook_type=hook_type,
                        position=position,
                        paragraph_index=idx,
                        strength=round(strength, 2),
                        matched_text=text[:100],
                        keywords_matched=matched_keywords,
                    )
                )
        return results

    @classmethod
    def calculate_hook_score(
        cls, hooks: list[HookResult], is_first_three_chapters: bool = False
    ) -> float:
        """计算综合钩子评分

        Args:
            hooks: 检测到的所有钩子
            is_first_three_chapters: 是否黄金三章 (权重加倍)
        """
        if not hooks:
            return 0.0

        # 分位置评分
        opening_hooks = [h for h in hooks if h.position == "opening"]
        closing_hooks = [h for h in hooks if h.position == "closing"]
        mid_hooks = [h for h in hooks if h.position == "mid_chapter"]

        opening_score = (
            sum(h.strength for h in opening_hooks) / max(len(opening_hooks), 1)
            if opening_hooks
            else 0
        )
        closing_score = (
            sum(h.strength for h in closing_hooks) / max(len(closing_hooks), 1)
            if closing_hooks
            else 0
        )
        mid_score = sum(h.strength for h in mid_hooks) / max(len(mid_hooks), 1) if mid_hooks else 0

        # 权重: 结尾钩子最重要(0.5)，开头次之(0.3)，中间(0.2)
        # 黄金三章开头权重提升
        weights = (0.45, 0.35, 0.20) if is_first_three_chapters else (0.30, 0.50, 0.20)

        score = opening_score * weights[0] + closing_score * weights[1] + mid_score * weights[2]

        # 结尾弱钩子惩罚
        weak_penalty = 0.0
        for pattern in cls.WEAK_CLOSING_PATTERNS:
            if closing_hooks:
                for h in closing_hooks:
                    if re.search(pattern, h.matched_text):
                        weak_penalty += 0.1
        score = max(0.0, score - weak_penalty)

        # 钩子多样性奖励
        unique_types = len({h.hook_type for h in hooks})
        diversity_bonus = min(unique_types / 6.0, 1.0) * 0.1
        score = min(score + diversity_bonus, 1.0)

        return round(score, 2)

    @classmethod
    def detect_weak_closing(cls, text: str) -> list[str]:
        """检测弱结尾模式"""
        issues: list[str] = []
        paragraphs = text.split("\n")
        if len(paragraphs) < 3:
            return issues
        closing_text = "\n".join(paragraphs[-3:])
        issues.extend(
            f"弱结尾: 匹配模式 '{pattern}'"
            for pattern in cls.WEAK_CLOSING_PATTERNS
            if re.search(pattern, closing_text)
        )
        return issues


# ─── 章节钩子强度评分器 ───────────────────────────────


class HookStrengthScorer:
    """章节钩子强度评分器 — 精细化评估章节各位置的钩子质量

    评分维度:
      1. 开头钩子 (30%): 前3段是否抓住读者
      2. 结尾钩子 (50%): 最后3段是否制造悬念/期待
      3. 中间锚点 (20%): 中间是否有保持注意力的锚点
    """

    @classmethod
    def score(cls, hooks: list[HookResult], _text: str = "") -> HookStrengthReport:
        """对章节钩子进行精细评分"""
        opening = [h for h in hooks if h.position == "opening"]
        closing = [h for h in hooks if h.position == "closing"]
        mid = [h for h in hooks if h.position == "mid_chapter"]

        opening_score = cls._score_group(opening, weight=0.9)
        closing_score = cls._score_group(closing, weight=1.0)
        mid_score = cls._score_group(mid, weight=0.7)

        overall = opening_score * 0.30 + closing_score * 0.50 + mid_score * 0.20
        overall = round(min(overall, 1.0), 2)

        weak_spots: list[str] = []
        if opening_score < 0.3:
            weak_spots.append("开头吸引力不足，建议前3段加入悬念/冲突/反常识信息")
        if closing_score < 0.3:
            weak_spots.append("结尾钩子严重不足，建议加入悬念断章/反转/预告")
        elif closing_score < 0.5:
            weak_spots.append("结尾钩子偏弱，考虑增强悬念或情绪")

        if mid_score < 0.2 and len(hooks) > 5:
            weak_spots.append("中间部分缺少阅读锚点，建议每5-8段插入小爽点/悬念")

        strengths: list[str] = []
        if opening_score >= 0.6:
            strengths.append("开头吸引力强")
        if closing_score >= 0.7:
            strengths.append("结尾悬念出色")
        if len({h.hook_type for h in hooks}) >= 4:
            strengths.append("钩子类型丰富")

        return HookStrengthReport(
            chapter_number=0,
            opening_hook_score=round(opening_score, 2),
            closing_hook_score=round(closing_score, 2),
            mid_hook_score=round(mid_score, 2),
            overall_score=overall,
            weak_spots=weak_spots,
            strengths=strengths,
            cliffhanger_present=any(h.hook_type == HookType.CLIFFHANGER for h in closing),
            emotional_peak_present=any(h.hook_type == HookType.EMOTIONAL for h in hooks),
            mystery_hook_present=any(h.hook_type == HookType.MYSTERY for h in hooks),
        )

    @classmethod
    def _score_group(cls, hooks: list[HookResult], weight: float) -> float:
        if not hooks:
            return 0.0
        high_count = sum(1 for h in hooks if h.strength >= 0.6)
        diversity = len({h.hook_type for h in hooks})
        avg_strength = sum(h.strength for h in hooks) / len(hooks)
        score = min(avg_strength * weight + diversity * 0.05 + high_count * 0.05, 1.0)
        return round(score, 2)

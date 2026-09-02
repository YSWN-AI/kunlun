"""
dialogue 角色辨识度检测器 — 多角色语音区分度分析
"""

from __future__ import annotations

import re
from collections import Counter

from kunlun.dialogue.parser import (
    DialogueLine,
    DialogueStyle,
    DistinctivenessLevel,
    SpeakerProfile,
)


class SpeakerDistinctiveness:
    """检测多个角色之间的对话区分度"""

    # 高频虚词（不用于辨识）
    STOP_WORDS = {
        "的",
        "了",
        "在",
        "是",
        "我",
        "你",
        "他",
        "她",
        "它",
        "们",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "会",
        "着",
        "没",
        "看",
        "好",
        "自己",
        "这",
        "那",
        "什么",
        "怎么",
        "为什么",
        "可以",
        "知道",
        "觉得",
        "想",
        "能",
        "吧",
        "吗",
        "呢",
        "啊",
        "哦",
        "嗯",
        "哈",
    }

    @classmethod
    def build_profile(
        cls, character_id: str, character_name: str, lines: list[DialogueLine]
    ) -> SpeakerProfile:
        """从对话行构建角色语音指纹"""
        profile = SpeakerProfile(character_id=character_id, character_name=character_name)

        all_text = " ".join(dl.text for dl in lines)
        profile.total_dialogue_lines = len(lines)
        profile.total_words = len(all_text)

        if not lines:
            return profile

        # 平均句长
        profile.avg_sentence_length = sum(dl.word_count for dl in lines) / len(lines)

        # 问句/感叹句占比
        profile.question_ratio = sum(1 for dl in lines if dl.has_question) / len(lines)
        profile.exclamation_ratio = sum(1 for dl in lines if dl.has_exclamation) / len(lines)

        # 省略号/破折号频率
        profile.ellipsis_ratio = sum(dl.ellipsis_count for dl in lines) / len(lines)
        profile.dash_ratio = sum(dl.dash_count for dl in lines) / len(lines)

        # 句末语气词
        for dl in lines:
            if dl.sentence_ender:
                profile.sentence_enders[dl.sentence_ender] += 1

        # 高频实词（2字及以上，过滤虚词）
        words = re.findall(r"[\u4e00-\u9fff]{2,}", all_text)
        for w in words:
            if w not in cls.STOP_WORDS:
                profile.high_freq_words[w] += 1

        # 语体分布
        style_counts: Counter = Counter()
        for dl in lines:
            style_counts[dl.style_hint.value] += 1
        total = len(lines)
        profile.style_distribution = {s: c / total for s, c in style_counts.most_common()}
        profile.dominant_style = (
            DialogueStyle(style_counts.most_common(1)[0][0])
            if style_counts
            else DialogueStyle.NATURAL
        )

        # 口头禅（出现≥3次且仅在当前角色中出现的高频词）
        profile.catchphrases = [
            w for w, c in profile.high_freq_words.most_common(20) if c >= 3 and len(w) >= 2
        ][:5]

        return profile

    @classmethod
    def compare_profiles(cls, profiles: dict[str, SpeakerProfile]) -> DistinctivenessLevel:
        """比较多个角色语音指纹，返回辨识度等级"""
        if len(profiles) < 2:
            return DistinctivenessLevel.HIGH

        profiles_list = profiles.values()

        # 1. 句末语气词重叠度
        all_enders: set[str] = set()
        for p in profiles_list:
            all_enders.update(p.sentence_enders.keys())
        ender_overlap = 0
        for ender in all_enders:
            users = sum(1 for p in profiles_list if p.sentence_enders.get(ender, 0) > 0)
            if users >= len(profiles_list) * 0.6:  # 60%以上角色共用
                ender_overlap += 1

        # 2. 语体重叠度
        styles = [p.dominant_style for p in profiles_list]
        unique_styles = len(set(styles))
        style_score = unique_styles / len(styles)

        # 3. 句长差异度
        lengths = [p.avg_sentence_length for p in profiles_list]
        length_cv = (max(lengths) - min(lengths)) / max(lengths) if max(lengths) > 0 else 0

        # 4. 高频词重叠
        all_top_words: set[str] = set()
        for p in profiles_list:
            all_top_words.update(w for w, _ in p.high_freq_words.most_common(10))
        word_overlap = 0
        for w in all_top_words:
            users = sum(1 for p in profiles_list if p.high_freq_words.get(w, 0) >= 2)
            if users >= len(profiles_list) * 0.5:
                word_overlap += 1
        word_overlap_ratio = word_overlap / max(len(all_top_words), 1)

        # 综合评分
        score = (
            style_score * 0.30
            + (1 - min(ender_overlap / max(len(all_enders), 1), 1)) * 0.20
            + min(length_cv * 2, 1) * 0.25
            + (1 - word_overlap_ratio) * 0.25
        )

        if score >= 0.7:
            return DistinctivenessLevel.HIGH
        if score >= 0.4:
            return DistinctivenessLevel.MEDIUM
        if score >= 0.2:
            return DistinctivenessLevel.LOW
        return DistinctivenessLevel.NONE

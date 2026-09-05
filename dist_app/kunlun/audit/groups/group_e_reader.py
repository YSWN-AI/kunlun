"""
E组: 情感弧线 (E1-E4) — 情绪曲线、情绪一致性、情感递进、读者共鸣
"""

from __future__ import annotations

from typing import Any

from .._base33 import DimResult


class Auditor33GroupE:
    """E组: 情感弧线 mixin"""

    _truth_manager: Any | None = None

    def _check_E1_emotion_curve(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        seg_len = max(1, len(draft) // 5)
        segments = [draft[i : i + seg_len] for i in range(0, len(draft), seg_len)]
        emotions = []
        for seg in segments[:5]:
            high = sum(
                seg.count(w)
                for w in ["怒", "惊", "喜", "爆", "震", "吼", "杀", "战", "热", "燃", "狂", "猛"]
            )
            low = sum(
                seg.count(w)
                for w in ["静", "默", "沉", "暗", "冷", "淡", "寂", "寞", "哀", "悲", "忧", "愁"]
            )
            if high > low * 1.5:
                emotions.append("high")
            elif low > high * 1.5:
                emotions.append("low")
            else:
                emotions.append("mid")

        unique = len(set(emotions))
        if unique < 2:
            emotion_label = emotions[0] if emotions else "?"
            if emotion_label == "mid":
                return DimResult(
                    "E1",
                    "情绪曲线",
                    78,
                    "PASS",
                    "情绪曲线为混合态(高低情绪并存),无明显单峰",
                    "",
                    False,
                )
            return DimResult(
                "E1",
                "情绪曲线",
                40,
                "FAIL",
                f"情绪过于单一(仅{emotion_label}),缺少起伏",
                "在章节中设计至少一处情绪转折",
                True,
            )
        return DimResult("E1", "情绪曲线", 85, "PASS", f"情绪曲线有变化: {'→'.join(emotions)}")

    def _check_E2_emotion_consistency(
        self, draft: str, _chapter: int, _blueprint: dict
    ) -> DimResult:
        if self._truth_manager:
            arcs = self._truth_manager.get("emotional_arcs")
            arc_data = arcs.get("arcs", {})
            issues = []
            for name, data in arc_data.items():
                if name not in draft:
                    continue
                points = data.get("points", [])
                if not points:
                    continue
                prev_emotion = points[-1].get("emotion", "")
                opposite_pairs = [
                    ("joy", "sadness"),
                    ("anger", "calm"),
                    ("fear", "courage"),
                    ("trust", "suspicion"),
                ]
                for pos, _neg in opposite_pairs:
                    if prev_emotion == pos:
                        neg_words = ["悲伤", "哭泣", "泪", "绝望", "痛苦"]
                        for w in neg_words:
                            if w in draft:
                                idx = draft.find(w)
                                context = draft[max(0, idx - 50) : idx + 50]
                                if name in context:
                                    issues.append(f"{name}从{pos}突变为负面情绪({w})")
                                    break
            if issues:
                return DimResult(
                    "E2",
                    "情绪一致性",
                    55,
                    "WARN",
                    f"情绪跳跃: {'; '.join(issues[:2])}",
                    "确保情绪变化有合理的触发事件",
                    False,
                )

        return DimResult("E2", "情绪一致性", 88, "PASS", "情绪衔接自然")

    def _check_E3_emotion_progression(
        self, draft: str, chapter: int, _blueprint: dict
    ) -> DimResult:
        if self._truth_manager:
            char_matrix = self._truth_manager.get("character_matrix")
            interactions = char_matrix.get("interactions", [])
            for inter in interactions:
                intimacy = inter.get("intimacy_level", 0)
                if intimacy > 0.5:
                    chapter_diff = chapter - inter.get("chapter", 0)
                    if chapter_diff <= 1:
                        a, b = inter.get("char_a", ""), inter.get("char_b", "")
                        if a and b and a in draft and b in draft:
                            quick_kw = ["表白", "拥抱", "亲吻", "告白"]
                            for kw in quick_kw:
                                if kw in draft:
                                    return DimResult(
                                        "E3",
                                        "情感递进",
                                        55,
                                        "WARN",
                                        f"{a}与{b}的情感发展可能过快"
                                        f"(亲密度{intimacy}出现在仅{chapter_diff}章后)",
                                        "增加情感铺垫章节,让关系发展更自然",
                                        False,
                                    )

        return DimResult("E3", "情感递进", 85, "PASS", "情感递进节奏正常")

    def _check_E4_reader_resonance(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        resonance_kw = {
            "justice": ["正义", "公平", "公道", "报仇", "雪耻", "不公", "冤屈"],
            "sympathy": ["同情", "可怜", "心疼", "不忍", "悲伤", "难过", "苦难"],
            "anger": ["愤怒", "气人", "憋屈", "可恨", "小人", "阴险", "卑鄙"],
            "anticipation": ["期待", "等待", "盼望", "预感", "即将", "就要"],
            "satisfaction": ["满足", "畅快", "过瘾", "痛快", "解气", "圆满"],
        }

        found_categories = []
        for category, keywords in resonance_kw.items():
            if any(kw in draft for kw in keywords):
                found_categories.append(category)

        if len(found_categories) < 2:
            return DimResult(
                "E4",
                "读者共鸣",
                55,
                "WARN",
                f"仅覆盖{len(found_categories)}类共鸣点,建议增加情感维度",
                "在章节中加入更多情感共鸣元素(正义/同情/期待/愤怒)",
                True,
            )

        return DimResult(
            "E4",
            "读者共鸣",
            85,
            "PASS",
            f"覆盖{len(found_categories)}类共鸣: {', '.join(found_categories)}",
        )

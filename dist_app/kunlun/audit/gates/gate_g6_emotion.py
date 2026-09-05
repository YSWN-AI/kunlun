"""
G6: 情绪一致性

检查正文前后1/3的情绪是否一致。
"""

from __future__ import annotations

from kunlun.audit.gates._base import GateLevel, GateResult


class GateG6EmotionConsistency:
    """G6: 情绪一致性"""

    EMOTION_WHEEL = {
        "joy": ["开心", "快乐", "喜悦", "兴奋", "幸福"],
        "trust": ["信任", "信赖", "安心", "可靠"],
        "fear": ["恐惧", "害怕", "惊慌", "不安"],
        "surprise": ["惊讶", "震惊", "意外", "诧异"],
        "sadness": ["悲伤", "难过", "伤心", "哀伤"],
        "disgust": ["厌恶", "恶心", "反感", "嫌弃"],
        "anger": ["愤怒", "生气", "怒火", "愤慨"],
        "anticipation": ["期待", "盼望", "预感", "预料"],
    }

    EMOTION_ORDER = [
        "joy",
        "trust",
        "fear",
        "surprise",
        "sadness",
        "disgust",
        "anger",
        "anticipation",
    ]

    def run(self, draft: str) -> GateResult:
        if len(draft) < 300:
            return GateResult(
                gate_id="G6",
                level=GateLevel.PASS,
                score=0.7,
                detail="文本过短，跳过情绪一致性检查",
            )

        third = len(draft) // 3
        front = draft[:third]
        back = draft[-third:]

        front_emotion = self._detect_dominant_emotion(front)
        back_emotion = self._detect_dominant_emotion(back)

        if not front_emotion or not back_emotion:
            return GateResult(
                gate_id="G6",
                level=GateLevel.WARN,
                score=0.6,
                detail="情绪关键词不足，无法检测一致性",
            )

        front_idx = (
            self.EMOTION_ORDER.index(front_emotion) if front_emotion in self.EMOTION_ORDER else -1
        )
        back_idx = (
            self.EMOTION_ORDER.index(back_emotion) if back_emotion in self.EMOTION_ORDER else -1
        )

        if front_idx == -1 or back_idx == -1:
            distance = 4
        else:
            distance = min(abs(front_idx - back_idx), 8 - abs(front_idx - back_idx))

        max_distance = 3
        if distance > max_distance:
            level = GateLevel.FAIL
            score = 0.3
        elif distance > max_distance * 0.7:
            level = GateLevel.WARN
            score = 0.6
        else:
            level = GateLevel.PASS
            score = 0.9 - distance * 0.1

        detail = f"前1/3情绪: {front_emotion}, 后1/3情绪: {back_emotion}, 距离: {distance}"
        return GateResult(
            gate_id="G6",
            level=level,
            score=score,
            detail=detail,
            data={"front": front_emotion, "back": back_emotion, "distance": distance},
        )

    def _detect_dominant_emotion(self, text: str) -> str | None:
        negation_prefixes = ["并不", "没有", "不是", "不要", "毫不", "并非", "绝非", "从未", "未曾"]
        double_negation_prefixes = ["不是不", "并非不", "并非没", "并不是不", "并不是没"]

        emotion_scores = dict.fromkeys(self.EMOTION_WHEEL, 0)
        for emotion, keywords in self.EMOTION_WHEEL.items():
            for kw in keywords:
                count = text.count(kw)
                if count > 0:
                    start = 0
                    valid_count = 0
                    for _ in range(count):
                        idx = text.find(kw, start)
                        if idx < 0:
                            break
                        prefix = text[max(0, idx - 8) : idx]
                        if any(dn in prefix for dn in double_negation_prefixes):
                            valid_count += 1
                            start = idx + 1
                            continue
                        has_negation = any(neg in prefix for neg in negation_prefixes)
                        if not has_negation:
                            valid_count += 1
                        start = idx + 1
                    emotion_scores[emotion] += valid_count

        if not any(emotion_scores.values()):
            return None
        return max(emotion_scores.items(), key=lambda x: x[1])[0]

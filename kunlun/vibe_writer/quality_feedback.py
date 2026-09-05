"""
昆仑创作引擎 — Vibe Writing 即时质量反馈

在写作过程中实时分析文本质量，提供：
  - 六维质量评分（节奏/爽感/人物/逻辑/文笔/创新）
  - AI率检测
  - 即时改进建议
  - 卡文检测
  - 读者弃书点预警
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class QualityFeedback:
    """即时质量反馈结果"""

    overall_score: float = 0.0
    overall_level: str = "fair"
    six_dim_scores: dict[str, float] = field(default_factory=dict)
    ai_rate: float = 0.0
    ai_level: str = "pass"
    word_count: int = 0
    paragraph_count: int = 0
    dialogue_ratio: float = 0.0
    is_stuck: bool = False
    stuck_reason: str = ""
    drop_off_points: list[str] = field(default_factory=list)
    immediate_suggestions: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    target_85: bool = False

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 3),
            "overall_level": self.overall_level,
            "six_dim_scores": {k: round(v, 3) for k, v in self.six_dim_scores.items()},
            "ai_rate": round(self.ai_rate, 1),
            "ai_level": self.ai_level,
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "dialogue_ratio": round(self.dialogue_ratio, 3),
            "is_stuck": self.is_stuck,
            "stuck_reason": self.stuck_reason,
            "drop_off_points": self.drop_off_points,
            "immediate_suggestions": self.immediate_suggestions,
            "strengths": self.strengths,
            "target_85": self.target_85,
        }

    def summary(self) -> str:
        """简短摘要（用于实时显示）"""
        parts = [f"质量{self.overall_score * 100:.0f}分"]
        if self.target_85:
            parts.append("已达85分目标")
        else:
            parts.append("未达85分")
        parts.append(f"AI率{self.ai_rate:.0f}%")
        if self.is_stuck:
            parts.append(f"卡文:{self.stuck_reason}")
        return " | ".join(parts)


class VibeQualityFeedback:
    """Vibe Writing 即时质量反馈引擎"""

    # 卡文检测阈值
    STUCK_NO_DIALOGUE_CHARS = 800  # 超过800字无对话
    STUCK_NO_ACTION_CHARS = 1000  # 超过1000字无动作
    STUCK_REPEAT_PARAGRAPH = 3  # 连续3段结构相似

    # 弃书点检测
    DROP_OFF_LONG_DESC = 500  # 超过500字纯描写
    DROP_OFF_NO_CONFLICT = 1500  # 超过1500字无冲突

    @classmethod
    def analyze(cls, text: str, chapter: int = 0) -> QualityFeedback:  # noqa: PLR0912, PLR0915
        """分析文本，生成即时质量反馈"""
        fb = QualityFeedback()
        if not text or len(text.strip()) < 20:
            fb.overall_level = "文本过短"
            fb.immediate_suggestions = ["继续写作，积累足够内容后再分析"]
            return fb

        fb.word_count = len(text.replace(" ", "").replace("\n", ""))
        fb.paragraph_count = len([p for p in text.split("\n") if p.strip()])

        # 1. 六维质量评分
        try:
            from kunlun.quality.six_dim_dashboard import six_dim_dashboard

            report = six_dim_dashboard.analyze(text, chapter)
            fb.overall_score = report.overall_score
            fb.overall_level = report.overall_level
            fb.six_dim_scores = {k: v.score for k, v in report.dimensions.items()}
            fb.target_85 = report.target_85
            fb.strengths = report.strengths[:2]
            # 从六维报告提取即时建议
            for dim in report.dimensions.values():
                if dim.score < 0.70 and dim.suggestions:
                    fb.immediate_suggestions.extend(dim.suggestions[:1])
        except Exception:
            fb.overall_score = 0.5
            fb.overall_level = "fair"

        # 2. AI率检测
        try:
            from kunlun.ai_rate import detect_ai_rate

            ai_report = detect_ai_rate(text)
            fb.ai_rate = ai_report.total_score
            if fb.ai_rate <= 35:
                fb.ai_level = "pass"
            elif fb.ai_rate <= 50:
                fb.ai_level = "warn"
                fb.immediate_suggestions.append(f"AI率{fb.ai_rate:.0f}%偏高，建议人类化改写")
            else:
                fb.ai_level = "fail"
                fb.immediate_suggestions.append(f"AI率{fb.ai_rate:.0f}%过高，必须改写")
        except Exception:
            fb.ai_rate = 0.0

        # 3. 对话占比
        dialogues = re.findall(r"[" "「『]([^" "」』]+)[" "」』]", text)
        dialogue_chars = sum(len(d) for d in dialogues)
        fb.dialogue_ratio = dialogue_chars / max(fb.word_count, 1)

        # 4. 卡文检测
        fb.is_stuck, fb.stuck_reason = cls._detect_stuck(text, fb)

        # 5. 弃书点检测
        fb.drop_off_points = cls._detect_drop_off(text, fb)

        # 6. 基于文本特征的差异化即时建议
        suggestions = []

        # 6.1 卡文针对性建议
        if fb.is_stuck:
            stuck_suggestions = {
                "长时间无对话": "当前段落缺乏对话，加入角色互动或内心独白打破沉闷",
                "长时间无动作": "当前段落缺乏动作，加入战斗、移动或肢体描写",
                "心理描写过多": "心理描写过多，用动作和对话代替部分内心活动",
                "段落开头重复": "段落开头重复，变化句式或视角避免单调",
            }
            if fb.stuck_reason in stuck_suggestions:
                suggestions.append(stuck_suggestions[fb.stuck_reason])
            else:
                suggestions.append("检测到卡文状态，尝试引入新冲突或切换视角")

        # 6.2 弃书点针对性建议
        if fb.drop_off_points:
            for point in fb.drop_off_points[:2]:
                if "纯描写" in point:
                    suggestions.append("长段纯描写可能导致读者流失，穿插对话或动作打破描写")
                elif "无冲突" in point:
                    suggestions.append("开头缺乏冲突信号，前300字内引入矛盾或悬念")
                elif "无爽点" in point:
                    suggestions.append("超过1500字无爽点，设置小高潮或反转提升阅读动力")

        # 6.3 AI率针对性建议
        if fb.ai_rate >= 50:
            suggestions.append(f"AI率{fb.ai_rate:.0f}%过高，必须进行人类化改写后再发布")
        elif fb.ai_rate >= 35:
            suggestions.append(f"AI率{fb.ai_rate:.0f}%偏高，建议替换高频AI词和冗余修饰")

        # 6.4 对话占比针对性建议
        if fb.dialogue_ratio < 0.10 and fb.word_count > 800:
            suggestions.append("对话占比极低，网文读者偏好对话驱动，增加角色互动")
        elif fb.dialogue_ratio < 0.20 and fb.word_count > 500:
            suggestions.append("对话偏少，用对话代替部分叙述提升节奏")
        elif fb.dialogue_ratio > 0.65:
            suggestions.append("对话过多，加入环境描写和角色动作平衡节奏")

        # 6.5 节奏针对性建议
        if fb.paragraph_count <= 2 and fb.word_count > 1000:
            suggestions.append("段落过少，长段落容易疲劳，适当分段提升可读性")

        # 6.6 六维评分最低维度建议
        if fb.six_dim_scores:
            lowest_dim = min(fb.six_dim_scores, key=lambda k: fb.six_dim_scores[k])
            lowest_score = fb.six_dim_scores[lowest_dim]
            if lowest_score < 0.6:
                dim_suggestions = {
                    "pacing": "节奏偏弱，每500字设置一个情节推进点",
                    "pleasure": "爽感不足，增加冲突强度或设置小高潮",
                    "character": "人物单薄，通过对话和细节展现角色性格",
                    "logic": "逻辑待加强，检查前后设定和因果关系",
                    "style": "文笔待提升，变化句式长度和增加感官描写",
                    "innovation": "创新不足，避免套路化表达，尝试独特设定",
                }
                if lowest_dim in dim_suggestions:
                    suggestions.append(dim_suggestions[lowest_dim])

        # 6.7 合并六维评分的建议
        for dim_name, dim_score in fb.six_dim_scores.items():
            if dim_score < 0.70:
                dim_sugs = {
                    "pacing": ["增加场景切换频率"],
                    "pleasure": ["增加动作描写和冲突场景"],
                    "character": ["增加角色个性化对话"],
                    "logic": ["确保因果关系清晰"],
                    "style": ["变化句式长度"],
                    "innovation": ["避免常见套路"],
                }
                if dim_name in dim_sugs and dim_sugs[dim_name][0] not in suggestions:
                    suggestions.append(dim_sugs[dim_name][0])

        # 6.8 如果没有建议，给出通用建议
        if not suggestions:
            if fb.overall_score >= 0.75:
                suggestions.append("质量良好，继续保持当前风格")
            else:
                suggestions.append("质量中等，可从节奏和爽感方面提升")

        fb.immediate_suggestions = list(dict.fromkeys(suggestions))[:5]

        return fb

    @classmethod
    def _detect_stuck(cls, text: str, fb: QualityFeedback) -> tuple[bool, str]:
        """检测卡文状态"""
        # 无对话
        if fb.word_count > cls.STUCK_NO_DIALOGUE_CHARS and fb.dialogue_ratio < 0.05:
            return True, "长时间无对话"

        # 无动作
        action_words = [
            "走",
            "跑",
            "跳",
            "打",
            "砍",
            "刺",
            "拳",
            "掌",
            "指",
            "转身",
            "迈步",
            "跃起",
        ]
        action_count = sum(text.count(w) for w in action_words)
        if fb.word_count > cls.STUCK_NO_ACTION_CHARS and action_count < 3:
            return True, "长时间无动作"

        # 纯心理描写
        psych_words = ["心想", "暗道", "想到", "觉得", "感觉", "心中", "内心"]
        psych_count = sum(text.count(w) for w in psych_words)
        if fb.word_count > 600 and psych_count > 10:
            return True, "心理描写过多"

        # 段落重复（简单检测）
        paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 50]
        if len(paragraphs) >= cls.STUCK_REPEAT_PARAGRAPH:
            # 检查连续段落开头是否相似
            starts = [p[:10] for p in paragraphs[-3:]]
            if len(set(starts)) <= 1:
                return True, "段落开头重复"

        return False, ""

    @classmethod
    def _detect_drop_off(cls, text: str, fb: QualityFeedback) -> list[str]:
        """检测读者弃书点"""
        points = []

        # 长段纯描写
        paragraphs = [p for p in text.split("\n") if p.strip()]
        for i, p in enumerate(paragraphs):
            if len(p) > cls.DROP_OFF_LONG_DESC:
                has_dialogue = bool(re.search(r"[" "「『]", p))
                has_action = any(w in p for w in ["说", "道", "喊", "叫", "走", "跑", "打"])
                if not has_dialogue and not has_action:
                    points.append(f"第{i + 1}段超过{len(p)}字纯描写")

        # 开头无冲突
        if fb.word_count > 300:
            first_300 = text[:300]
            conflict_words = [
                "不",
                "别",
                "滚",
                "杀",
                "打",
                "战",
                "敌",
                "仇",
                "恨",
                "怒",
                "惊",
                "恐",
            ]
            if not any(w in first_300 for w in conflict_words):
                points.append("开头300字无冲突信号")

        # 无爽点
        if fb.word_count > cls.DROP_OFF_NO_CONFLICT:
            pleasure_words = [
                "突破",
                "升级",
                "获得",
                "得到",
                "赢",
                "胜",
                "秒杀",
                "碾压",
                "震惊",
                "不敢相信",
            ]
            if not any(w in text for w in pleasure_words):
                points.append("超过1500字无爽点")

        return points[:3]


# 模块级单例
vibe_quality_feedback = VibeQualityFeedback()

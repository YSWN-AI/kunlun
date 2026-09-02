"""
F组: AI痕迹检测 (F1-F6) — 高频词、句式单调、过度总结、连词滥用、段落模式、结尾模板
"""

from __future__ import annotations

import re
from collections import Counter

from .._base33 import AI_FATIGUE_WORDS, DimResult


class Auditor33GroupF:
    """F组: AI痕迹检测 mixin"""

    def _check_F1_high_freq_words(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        words = AI_FATIGUE_WORDS["high_frequency"]
        counts = {w: draft.count(w) for w in words if draft.count(w) > 0}
        total = sum(counts.values())
        density = total / max(len(draft) / 1000, 1)
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]

        if density > 8:
            return DimResult(
                "F1",
                "AI高频词",
                20,
                "FAIL",
                f"AI高频词密度{density:.1f}/千字,最高: {dict(top)}",
                "替换高频词: 突然→骤然/猛然, 仿佛→宛若/恰似, 不由得→不禁, 似乎→隐约",
                True,
            )
        if density > 4:
            return DimResult(
                "F1",
                "AI高频词",
                55,
                "WARN",
                f"AI高频词密度偏高({density:.1f}/千字)",
                "注意替换常见AI套话词汇",
                True,
            )

        return DimResult("F1", "AI高频词", 90, "PASS", f"AI高频词密度正常({density:.1f}/千字)")

    def _check_F2_sentence_monotony(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        sentences = re.split(r"[。！？]", draft)
        first_chars = [s[:2] for s in sentences if len(s) >= 2]
        if not first_chars:
            return DimResult("F2", "句式单调", 85, "PASS", "通过")
        counter = Counter(first_chars)
        most_common = counter.most_common(1)[0]
        top_ratio = most_common[1] / len(first_chars)

        if top_ratio > 0.3:
            return DimResult(
                "F2",
                "句式单调",
                45,
                "WARN",
                f"'{most_common[0]}'开头占比{top_ratio:.1%},句式过于单一",
                "丰富句式开头: 用时间/地点/动作/声音/感官词作为句首",
                True,
            )
        return DimResult(
            "F2", "句式单调", 90, "PASS", f"句式开头多样化,最高{most_common[0]}:{top_ratio:.1%}"
        )

    def _check_F3_over_summary(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        markers = AI_FATIGUE_WORDS["over_summary_markers"]
        count = sum(draft.count(m) for m in markers)

        paragraphs = draft.split("\n\n")
        last_para = paragraphs[-1] if paragraphs else ""
        ending_summary = any(m in last_para for m in markers)

        if ending_summary:
            return DimResult(
                "F3",
                "过度总结",
                25,
                "FAIL",
                "结尾段落出现总结句式,AI味明显",
                "删除总结句,改用动作/神态/环境/悬念作为结尾",
                True,
            )
        if count > 5:
            return DimResult(
                "F3",
                "过度总结",
                55,
                "WARN",
                f"全文出现{count}处总结标记,偏多",
                "减少总结句式,让读者自己体会而非被告诉",
                True,
            )

        return DimResult("F3", "过度总结", 90, "PASS", f"总结句式{count}处,正常")

    def _check_F4_conjunction_abuse(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        conjunctions = [
            "然而",
            "但是",
            "因此",
            "所以",
            "于是",
            "随后",
            "接着",
            "不仅",
            "而且",
            "同时",
            "此外",
            "另外",
            "与此同时",
            "不过",
            "可是",
            "却",
            "从而",
            "进而",
            "总之",
        ]
        count = sum(draft.count(c) for c in conjunctions)
        density = count / max(len(draft) / 1000, 1)

        if density > 10:
            return DimResult(
                "F4",
                "连词滥用",
                35,
                "FAIL",
                f"连词密度{density:.1f}/千字,AI特征明显",
                "删除多余连接词,用动作/场景的自然切换代替",
                True,
            )
        if density > 5:
            return DimResult(
                "F4",
                "连词滥用",
                60,
                "WARN",
                f"连词密度偏高({density:.1f}/千字)",
                '适当删减连接词,拥抱"硬切换"的网文风格',
                True,
            )

        return DimResult("F4", "连词滥用", 88, "PASS", f"连词密度正常({density:.1f}/千字)")

    def _check_F5_paragraph_pattern(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        paragraphs = draft.split("\n\n")
        lengths = [len(p) for p in paragraphs if p.strip()]
        if len(lengths) < 3:
            return DimResult("F5", "段落模式", 85, "PASS", "段落少,跳过模式检测")

        avg_len = sum(lengths) / len(lengths)
        in_range = sum(1 for v in lengths if abs(v - avg_len) / max(avg_len, 1) < 0.2)

        if in_range > len(lengths) * 0.8 and len(lengths) > 5:
            return DimResult(
                "F5",
                "段落模式",
                30,
                "FAIL",
                f"{in_range}/{len(lengths)}段落长度高度一致(±20%),AI特征明显",
                "有意调整段落长度: 对话/动作短段落30-80字,描写/内心独白长段落150-300字",
                True,
            )
        return DimResult("F5", "段落模式", 85, "PASS", "段落长度变化自然")

    def _check_F6_ending_template(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        paragraphs = draft.split("\n\n")
        last_para = paragraphs[-1][:200] if paragraphs else ""

        template_patterns = [
            (r"接下来.*?将会", "展望句式"),
            (r"未来.*?将会", "展望句式"),
            (r"而.*?也将", "承接句式"),
            (r"这.*?只是.*?开始", "套路句式"),
            (r"真正.*?考验", "套路句式"),
            (r"未知.*?等待", "套路句式"),
            (r"一切.*?才刚", "套路句式"),
            (r"新的.*?篇章", "套话结尾"),
        ]

        for pat, label in template_patterns:
            if re.search(pat, last_para):
                return DimResult(
                    "F6",
                    "结尾模板",
                    40,
                    "WARN",
                    f"结尾出现模板化{label}: {pat}",
                    "避免套路化结尾,改用: 动作中断/新信息/悬念/反转",
                    True,
                )

        return DimResult("F6", "结尾模板", 90, "PASS", "结尾自然,无模板化句式")

"""
D组: 叙事质量 (D1-D6) — 节奏、弧线、大纲偏离、爽点密度、对话占比、描写密度
"""

from __future__ import annotations

import re

from .._base33 import DimResult


class Auditor33GroupD:
    """D组: 叙事质量 mixin"""

    def _check_D1_narrative_rhythm(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        paragraphs = draft.split("\n\n")
        if len(paragraphs) < 3:
            return DimResult(
                "D1",
                "叙事节奏",
                50,
                "WARN",
                "段落过少(<3段),无法评估节奏",
                "适当增加段落,丰富叙事层次",
                True,
            )

        lengths = [len(p) for p in paragraphs if p.strip()]
        if not lengths:
            return DimResult("D1", "叙事节奏", 0, "FAIL", "无有效段落")

        avg_len = sum(lengths) / len(lengths)
        variance = sum((v - avg_len) ** 2 for v in lengths) / len(lengths)
        cv = (variance**0.5) / avg_len if avg_len > 0 else 0

        if cv < 0.15:
            return DimResult(
                "D1",
                "叙事节奏",
                45,
                "WARN",
                f"段落长度过于均匀(CV={cv:.2f}),节奏单调",
                "交替使用短段落(30-80字)和长段落(150-300字)",
                True,
            )
        if cv > 1.2:
            return DimResult(
                "D1",
                "叙事节奏",
                55,
                "WARN",
                f"段落长度差异过大(CV={cv:.2f}),结构松散",
                "统一段落长度范围,避免极端差异",
                True,
            )
        return DimResult(
            "D1", "叙事节奏", 88, "PASS", f"段落节奏良好(CV={cv:.2f},均值={avg_len:.0f}字)"
        )

    def _check_D2_arc_compliance(self, draft: str, _chapter: int, blueprint: dict) -> DimResult:
        arc_stage = blueprint.get("arc_stage", "")
        if not arc_stage:
            return DimResult("D2", "弧线合规", 85, "PASS", "蓝图未指定弧线阶段,跳过合规检查")

        arc_keywords = {
            "setup": ["介绍", "日常", "平静", "普通", "平凡", "出场"],
            "inciting_incident": ["变故", "改变", "打破", "意外", "危机", "事件"],
            "rising_action": ["提升", "训练", "修行", "积累", "准备", "成长"],
            "midpoint": ["转折", "真相", "发现", "揭露", "震惊", "阴谋"],
            "climax": ["决战", "突破", "巅峰", "对决", "生死", "极限"],
            "falling_action": ["收尾", "恢复", "整理", "反思", "善后"],
            "resolution": ["结局", "告别", "离开", "新篇", "开启"],
        }

        expected = arc_keywords.get(arc_stage, [])
        if expected:
            match_count = sum(1 for kw in expected if kw in draft)
            match_ratio = match_count / len(expected) if expected else 0
            if match_ratio < 0.3:
                return DimResult(
                    "D2",
                    "弧线合规",
                    50,
                    "WARN",
                    f'弧线阶段"{arc_stage}"匹配度低({match_ratio:.0%}),正文可能偏离了弧线规划',
                    f'检查内容是否匹配"{arc_stage}"阶段预期',
                )

        return DimResult("D2", "弧线合规", 88, "PASS", f'弧线阶段"{arc_stage}"匹配正常')

    def _check_D3_outline_deviation(self, draft: str, _chapter: int, blueprint: dict) -> DimResult:
        scenes_planned = blueprint.get("scenes", [])
        if not scenes_planned:
            return DimResult("D3", "大纲偏离", 85, "PASS", "无蓝图场景,跳过偏离检查")
        covered = 0
        for s in scenes_planned:
            title = s.get("title", "")
            summary = s.get("summary", "")
            if (title and (title[:3] in draft or title in draft)) or (
                summary and summary[:15] in draft
            ):
                covered += 1

        ratio = covered / len(scenes_planned) if scenes_planned else 1
        if ratio < 0.5:
            return DimResult(
                "D3",
                "大纲偏离",
                35,
                "FAIL",
                f"蓝图{len(scenes_planned)}个场景仅覆盖{covered}个({ratio:.0%})",
                "重新审视蓝图场景,确保关键场景不被遗漏",
                True,
            )
        if ratio < 0.8:
            return DimResult(
                "D3",
                "大纲偏离",
                65,
                "WARN",
                f"{covered}/{len(scenes_planned)}场景覆盖({ratio:.0%})",
            )

        return DimResult(
            "D3", "大纲偏离", 88, "PASS", f"场景覆盖{covered}/{len(scenes_planned)}({ratio:.0%})"
        )

    def _check_D4_pleasure_density(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        pleasure_kw = [
            "突破",
            "升级",
            "打脸",
            "震惊",
            "觉醒",
            "获得",
            "击败",
            "碾压",
            "反转",
            "揭秘",
            "认可",
            "奖励",
            "晋升",
            "领悟",
            "觉醒",
            "秒杀",
            "吊打",
            "爆了",
            "轰动",
            "扬名",
            "崛起",
            "逆袭",
            "掌控",
            "解锁",
            "激活",
            "通关",
            "到手",
        ]
        count = sum(draft.count(kw) for kw in pleasure_kw)
        density = count / max(len(draft) / 1000, 1)

        if density < 0.5:
            return DimResult(
                "D4",
                "爽点密度",
                30,
                "FAIL",
                f"爽点密度极低({density:.1f}/千字),读者可能无感",
                "在关键位置加入爽点: 如角色突破/打脸对手/获得宝物",
                True,
            )
        if density < 1.0:
            return DimResult(
                "D4",
                "爽点密度",
                65,
                "WARN",
                f"爽点密度偏低({density:.1f}/千字)",
                '适当增加爽点: 可用信息差/智力碾压等"文爽"替代"武爽"',
                True,
            )
        return DimResult("D4", "爽点密度", 90, "PASS", f"爽点密度良好({density:.1f}/千字)")

    def _check_D5_dialogue_ratio(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        dialogue_chars = len(re.findall(r'[「「""][^」」""]+[」」""]', draft))
        total_chars = max(len(draft), 1)
        ratio = dialogue_chars / total_chars

        if ratio < 0.1:
            return DimResult(
                "D5",
                "对话占比",
                55,
                "WARN",
                f"对话过少({ratio:.1%}),叙事可能过于单调",
                "适当加入人物对话,用对话传递信息和推动剧情",
                True,
            )
        if ratio > 0.5:
            return DimResult(
                "D5",
                "对话占比",
                55,
                "WARN",
                f"对话过多({ratio:.1%}),场景可能缺少动作描写",
                "穿插动作描写和环境描写,缓和纯对话节奏",
                True,
            )
        return DimResult("D5", "对话占比", 90, "PASS", f"对话叙事平衡({ratio:.1%})")

    def _check_D6_description_density(
        self, draft: str, _chapter: int, _blueprint: dict
    ) -> DimResult:
        desc_markers = [
            "只见",
            "望去",
            "看到",
            "是一片",
            "呈现出",
            "弥漫着",
            "笼罩着",
            "映入眼帘",
            "放眼",
            "放眼望去",
            "远处",
            "近处",
            "四周",
        ]
        count = sum(draft.count(m) for m in desc_markers)

        sensory_kw = [
            "光",
            "影",
            "风",
            "雾",
            "雨",
            "雪",
            "气味",
            "烟雾",
            "月色",
            "日光",
            "灯火",
            "星辰",
            "花香",
            "血腥",
            "腐臭",
        ]
        sensory_count = sum(draft.count(k) for k in sensory_kw)

        total_chars = max(len(draft), 1)
        desc_density = (count + sensory_count) / (total_chars / 500)

        if desc_density < 2:
            return DimResult(
                "D6",
                "描写密度",
                55,
                "WARN",
                f"描写偏少({desc_density:.1f}/500字),缺乏沉浸感",
                "增加环境/感官描写,让读者身临其境",
                True,
            )
        if desc_density > 15:
            return DimResult(
                "D6",
                "描写密度",
                55,
                "WARN",
                f"描写偏多({desc_density:.1f}/500字),可能拖慢节奏",
                "精简环境描写,保留关键氛围即可",
                True,
            )

        return DimResult("D6", "描写密度", 88, "PASS", f"描写密度适中({desc_density:.1f}/500字)")

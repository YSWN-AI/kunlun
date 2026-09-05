"""
昆仑创作引擎 — 章节特征提取器
"""

from __future__ import annotations

import re

from .types import ChapterFeatures


class ChapterFeatureExtractor:
    """章节特征提取器 — 零 LLM 文本统计"""

    @classmethod
    def extract(cls, text: str, chapter_number: int) -> ChapterFeatures:
        """提取章节特征"""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        word_count = len(text.replace("\n", "").replace(" ", ""))

        # 对话比例 — 中文引号内的内容
        dialogue_chars = sum(len(m.group()) for m in re.finditer(r'[""][^""]*[""]', text))
        dialogue_chars += sum(len(m.group()) for m in re.finditer(r"[''][^'']*['']", text))
        dialogue_ratio = min(dialogue_chars / max(word_count, 1), 1.0)

        # 动作比例 — 动词密集段落
        action_verbs = r"(?:打|踢|跑|跳|飞|冲|杀|砍|刺|闪|躲|挡|击|轰|爆|劈|斩|挥|抓|推|拉|撞|摔)"
        action_count = len(re.findall(action_verbs, text))
        action_ratio = min(action_count / max(word_count / 10, 1), 1.0)

        # 描述比例 — 形容词密集段落
        desc_ratio = 1.0 - dialogue_ratio - min(action_ratio, 0.5)
        desc_ratio = max(desc_ratio, 0.1)

        # 场景数 — 空行或场景转换标记分隔
        scene_markers = (
            r"(?:───|\*\s*\*\s*\*|\.{3,}|——.{0,5}——|场景切换|与此同时|另一方面|画面一转)"
        )
        scene_splits = len(re.findall(scene_markers, text)) + 1

        # POV数量 — 简单启发式 (出现多个角色名聚焦)
        pov_markers = r"(?:视角|POV|[他她它]的.{0,5}(?:视角|眼中|看来))"
        pov_count = max(1, len(re.findall(pov_markers, text)) + 1)

        return ChapterFeatures(
            chapter_number=chapter_number,
            word_count=word_count,
            paragraph_count=len(paragraphs),
            dialogue_ratio=round(dialogue_ratio, 2),
            action_ratio=round(action_ratio, 2),
            description_ratio=round(desc_ratio, 2),
            scene_count=scene_splits,
            pov_count=min(pov_count, 5),  # 最多5个POV
        )

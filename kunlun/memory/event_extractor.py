"""
昆仑创作引擎 — 事件自动提取器 (Event Extractor)

纯规则、零LLM的章节事件自动提取，为情景记忆提供结构化事件输入。

提取规则:
  - 战斗事件: 匹配"杀/战/打/攻/防/招/轰/爆/碎/碾压/秒杀"等
  - 对话事件: 匹配引号包裹的对话段
  - 揭示事件: 匹配"原来/竟然/真相/秘密/发现/得知"等
  - 转折事件: 匹配"然而/但是/突然/没想到/就在这时"等
  - 过渡事件: 时间/地点转换段

每个事件输出:
  scene(段落定位), summary(段落前50字), participants(提取的人名),
  event_type, plot_relevance(关键词密度0.3-0.8), emotional_arc(情感词判断)

Author: 昆仑创作引擎
"""

from __future__ import annotations

import re
from typing import Any


class EventExtractor:
    """事件自动提取器 — 纯规则实现，零LLM依赖"""

    # 战斗关键词
    BATTLE_KEYWORDS: tuple[str, ...] = (
        "杀", "战", "打", "攻", "防", "招", "轰", "爆", "碎",
        "碾压", "秒杀", "斩", "劈", "刺", "拳", "掌", "剑",
        "刀", "枪", "对决", "交锋", "厮杀", "搏斗", "激战",
        "重创", "击溃", "击退", "击杀", "斩杀", "毙命",
    )

    # 揭示关键词
    REVELATION_KEYWORDS: tuple[str, ...] = (
        "原来", "竟然", "真相", "秘密", "发现", "得知",
        "揭开", "显露", "浮现", "露出", "暴露", "揭晓",
        "恍然大悟", "豁然开朗", "不可思议", "难以置信",
    )

    # 转折关键词
    TURNING_KEYWORDS: tuple[str, ...] = (
        "然而", "但是", "突然", "没想到", "就在这时",
        "忽然", "却", "可", "不料", "谁知", "岂料",
        "偏偏", "恰恰", "反倒", "反而",
    )

    # 时间/地点过渡词
    TRANSITION_KEYWORDS: tuple[str, ...] = (
        "次日", "翌日", "三日后", "数月后", "数年后",
        "十年后", "百年后", "此时", "此刻", "与此同时",
        "另一边", "与此同时", "画面一转", "镜头切换",
        "来到", "抵达", "进入", "走出", "离开",
        "清晨", "黄昏", "深夜", "正午", "傍晚",
    )

    # 积极情感词
    POSITIVE_EMOTIONS: tuple[str, ...] = (
        "喜", "笑", "欢", "乐", "悦", "兴奋", "激动",
        "开心", "高兴", "欣慰", "满意", "骄傲", "自豪",
        "畅快", "轻松", "温暖", "幸福", "期待",
    )

    # 消极情感词
    NEGATIVE_EMOTIONS: tuple[str, ...] = (
        "怒", "悲", "哀", "痛", "恨", "愤", "惧", "怕",
        "惊", "慌", "紧张", "焦虑", "绝望", "痛苦", "悲伤",
        "愤怒", "恐惧", "担忧", "不安", "沉重", "阴冷",
        "杀机", "戾气", "惨烈", "血腥",
    )

    # 人名提取模式：2-4字中文名 + 道/说/喊/叫/问/答/笑/怒/叹/喝/斥
    # 第4字（若有）不能是言语动词，避免贪婪匹配吞掉动词
    NAME_PATTERN = re.compile(
        r"([\u4e00-\u9fa5]{2,3}(?:(?![道说喊叫问答笑怒叹喝斥])[\u4e00-\u9fa5])?)"
        r"(?:道|说|喊|叫|问|答|笑|怒|叹|喝|斥)"
    )

    # 对话引号模式
    DIALOGUE_PATTERN = re.compile(r"[“\"]([^”\"]{2,})[”\"]")

    def extract_events(self, text: str, chapter: int) -> list[dict[str, Any]]:
        """从章节文本自动提取事件

        Args:
            text: 章节文本
            chapter: 章节号

        Returns:
            事件字典列表，每个含 scene/summary/participants/event_type/
            plot_relevance/emotional_arc
        """
        events: list[dict[str, Any]] = []
        # 按段落分割（空行分隔）
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        # 如果没有空行分隔，按句号分割成块
        if len(paragraphs) <= 1:
            sentences = re.split(r"(?<=[。！？])", text)
            paragraphs = [s.strip() for s in sentences if s.strip()]

        for idx, para in enumerate(paragraphs):
            event_type = self._detect_event_type(para)
            if event_type == "general" and len(para) < 20:
                # 太短的普通段落跳过
                continue

            participants = self.extract_characters(para)
            plot_relevance = self._calculate_plot_relevance(para, event_type)
            emotional_arc = self._detect_emotional_arc(para)

            event = {
                "scene": f"第{chapter}章段落{idx + 1}",
                "summary": para[:50],
                "participants": participants,
                "event_type": event_type,
                "plot_relevance": plot_relevance,
                "emotional_arc": emotional_arc,
            }
            events.append(event)

        return events

    def _detect_event_type(self, paragraph: str) -> str:
        """检测段落事件类型"""
        # 对话事件：包含引号对话
        if self.DIALOGUE_PATTERN.search(paragraph):
            return "dialogue"

        # 战斗事件
        battle_count = sum(1 for kw in self.BATTLE_KEYWORDS if kw in paragraph)
        if battle_count >= 2:
            return "battle"

        # 揭示事件
        for kw in self.REVELATION_KEYWORDS:
            if kw in paragraph:
                return "revelation"

        # 转折事件
        for kw in self.TURNING_KEYWORDS:
            if kw in paragraph:
                return "turning"

        # 过渡事件
        for kw in self.TRANSITION_KEYWORDS:
            if kw in paragraph:
                return "transition"

        return "general"

    def _calculate_plot_relevance(self, paragraph: str, event_type: str) -> float:
        """根据关键词密度计算情节相关性 (0.3-0.8)"""
        base = 0.3
        # 事件类型加成
        type_boost = {
            "battle": 0.3,
            "revelation": 0.35,
            "turning": 0.3,
            "dialogue": 0.15,
            "transition": 0.1,
            "general": 0.0,
        }.get(event_type, 0.0)

        # 关键词密度加成
        all_keywords = (
            self.BATTLE_KEYWORDS
            + self.REVELATION_KEYWORDS
            + self.TURNING_KEYWORDS
        )
        keyword_count = sum(1 for kw in all_keywords if kw in paragraph)
        density_boost = min(0.15, keyword_count * 0.03)

        relevance = base + type_boost + density_boost
        return max(0.3, min(0.8, relevance))

    def _detect_emotional_arc(self, paragraph: str) -> str:
        """根据情感词判断情感弧线"""
        positive_count = sum(1 for kw in self.POSITIVE_EMOTIONS if kw in paragraph)
        negative_count = sum(1 for kw in self.NEGATIVE_EMOTIONS if kw in paragraph)

        if positive_count > negative_count and positive_count >= 2:
            return "rising"
        if negative_count > positive_count and negative_count >= 2:
            return "falling"
        if positive_count >= 2 and negative_count >= 2:
            return "peak"
        if positive_count == 0 and negative_count == 0:
            return "neutral"
        return "neutral"

    def extract_characters(self, text: str) -> list[str]:
        """提取人名

        使用"XX道/说/喊/叫/问/答/笑/怒"模式 + 2-4字中文名

        Args:
            text: 输入文本

        Returns:
            去重后的人名列表
        """
        names = self.NAME_PATTERN.findall(text)
        # 过滤常见非人名（语气词等）
        stop_names = {"说道", "喊道", "叫道", "问道", "答道", "笑道", "怒道", "叹道"}
        filtered = [n for n in names if n not in stop_names and len(n) >= 2]
        # 去重保持顺序
        seen: set[str] = set()
        result: list[str] = []
        for name in filtered:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result

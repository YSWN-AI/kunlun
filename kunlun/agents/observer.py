"""
昆仑创作引擎 — Observer Agent（观察者）

借鉴 InkOS 的 Observer+Reflector 分离模式：
  - Observer: 从AI生成的章节中提取结构化事实（角色状态变更、事件、伏笔等）
  - Reflector: 将Observer提取的事实写入快照/知识图谱（不可变写入）

设计原则:
  1. Observer 只提取事实，不做判断
  2. 输出为 JSON delta，便于 Reflector 做不可变写入
  3. 零LLM成本 — 纯规则提取
  4. 可插拔 — 独立Agent，不影响现有流水线

数据流:
  AI输出章节 → Observer(提取事实JSON delta) → Reflector(写入KG/快照) → 下一章上下文
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class CharacterStateChange:
    """角色状态变更"""

    character_name: str
    character_uid: str = ""
    # 状态变更类型
    emotion_change: str | None = None  # 情绪变化: "愤怒", "喜悦", "悲伤"...
    location_change: str | None = None  # 位置变化: "从A移动到B"
    relationship_change: str | None = None  # 关系变化: "与X结盟/敌对"
    status_change: str | None = None  # 状态变化: "受伤", "突破", "死亡"
    inventory_change: str | None = None  # 物品变化: "获得/失去X"
    power_change: str | None = None  # 实力变化: "升级到X境界"
    secret_revealed: str | None = None  # 秘密揭示
    oath_made: str | None = None  # 誓约订立


@dataclass
class EventExtracted:
    """提取的事件"""

    event_name: str
    event_type: str = "plot"  # plot / battle / revelation / transition
    description: str = ""
    involved_characters: list[str] = field(default_factory=list)
    location: str = ""
    chapter: int = 0


@dataclass
class ForeshadowingDelta:
    """伏笔变更"""

    planted: list[str] = field(default_factory=list)  # 新埋下的伏笔
    revealed: list[str] = field(default_factory=list)  # 揭示的伏笔
    progressed: list[str] = field(default_factory=list)  # 推进的伏笔


@dataclass
class ObserverReport:
    """Observer 完整报告 — JSON delta 格式"""

    chapter: int
    book_id: str = ""
    # 角色状态变更
    character_changes: list[CharacterStateChange] = field(default_factory=list)
    # 事件提取
    events: list[EventExtracted] = field(default_factory=list)
    # 伏笔变更
    foreshadowing: ForeshadowingDelta = field(default_factory=ForeshadowingDelta)
    # 新实体（角色/地点/物品等）
    new_entities: dict[str, list[str]] = field(default_factory=dict)
    # 关键情节节点
    key_plot_points: list[str] = field(default_factory=list)
    # 章节摘要
    chapter_summary: str = ""
    # 元数据
    word_count: int = 0
    dialogue_ratio: float = 0.0
    scene_count: int = 0

    def to_json(self) -> str:
        """序列化为JSON"""
        return json.dumps(self, default=lambda o: o.__dict__, ensure_ascii=False, indent=2)


class Observer:
    """
    Observer Agent — 从AI生成文本中提取结构化事实

    用法:
        observer = Observer()
        report = observer.observe(draft, chapter=5, book_id="book_001", blueprint=blueprint)
    """

    # 中文情绪关键词映射
    EMOTION_MAP = {
        "愤怒": "anger",
        "暴怒": "anger",
        "生气": "anger",
        "恼火": "anger",
        "喜悦": "joy",
        "高兴": "joy",
        "兴奋": "joy",
        "开心": "joy",
        "悲伤": "sadness",
        "难过": "sadness",
        "痛苦": "sadness",
        "哭泣": "sadness",
        "恐惧": "fear",
        "害怕": "fear",
        "惊恐": "fear",
        "胆怯": "fear",
        "惊讶": "surprise",
        "震惊": "surprise",
        "吃惊": "surprise",
        "冷静": "calm",
        "平静": "calm",
        "淡定": "calm",
        "紧张": "tension",
        "焦虑": "anxiety",
        "不安": "anxiety",
        "绝望": "despair",
        "希望": "hope",
        "期待": "hope",
    }

    # 状态变更关键词
    STATUS_KEYWORDS = {
        "受伤": "injured",
        "重伤": "critically_injured",
        "死亡": "dead",
        "突破": "breakthrough",
        "升级": "level_up",
        "觉醒": "awakening",
        "昏迷": "unconscious",
        "中毒": "poisoned",
        "治愈": "healed",
    }

    # 关系变更关键词
    RELATION_KEYWORDS = {
        "结盟": "ally",
        "联盟": "ally",
        "联手": "ally",
        "敌对": "enemy",
        "反目": "enemy",
        "决裂": "enemy",
        "师徒": "master_disciple",
        "拜师": "master_disciple",
        "爱慕": "romance",
        "相爱": "romance",
        "表白": "romance",
        "背叛": "betrayal",
        "出卖": "betrayal",
    }

    def observe(
        self,
        draft: str,
        chapter: int = 0,
        book_id: str = "",
        blueprint: dict | None = None,
        known_characters: list[str] | None = None,
    ) -> ObserverReport:
        """
        观察AI生成的章节文本，提取结构化事实

        Args:
            draft: 章节正文
            chapter: 章节编号
            book_id: 作品ID
            blueprint: 蓝图（含场景/角色信息）
            known_characters: 已知角色名列表

        Returns:
            ObserverReport: 结构化的事实变更报告
        """
        report = ObserverReport(
            chapter=chapter,
            book_id=book_id,
            word_count=len(draft),
        )

        if not draft:
            return report

        # 1. 提取对话比例
        dialogue_chars = sum(len(m) for m in re.findall(r'[""「]([^""」]+)[""」]', draft))
        report.dialogue_ratio = dialogue_chars / max(len(draft), 1)

        # 2. 场景数量（按空行分割的有效段落组）
        paragraphs = [p.strip() for p in draft.split("\n\n") if len(p.strip()) > 50]
        report.scene_count = max(1, len(paragraphs) // 3)  # 粗略估计

        # 3. 提取角色状态变更
        bp_chars = set()
        if blueprint:
            for scene in blueprint.get("scenes", []):
                for c in scene.get("characters", []):
                    bp_chars.add(c)
            for c in blueprint.get("key_characters", []):
                bp_chars.add(c)

        all_characters = known_characters or []
        if bp_chars:
            all_characters = list(set(all_characters + list(bp_chars)))

        # 对每个已知角色检测状态变更
        for char_name in all_characters:
            if char_name in draft:
                change = self._detect_character_changes(char_name, draft, chapter)
                if change:
                    report.character_changes.append(change)

        # 4. 提取事件
        report.events = self._extract_events(draft, chapter, all_characters)

        # 5. 提取伏笔变更
        report.foreshadowing = self._extract_foreshadowing(draft, blueprint)

        # 6. 提取新实体
        report.new_entities = self._extract_new_entities(draft, all_characters)

        # 7. 提取关键情节节点
        report.key_plot_points = self._extract_key_plot_points(draft)

        # 8. 生成章节摘要
        report.chapter_summary = draft[:200] if draft else ""

        logger.info(
            f"[Observer] ch{chapter}: {len(report.character_changes)}角色变更, "
            f"{len(report.events)}事件, "
            f"伏笔({len(report.foreshadowing.planted)}埋/{len(report.foreshadowing.revealed)}揭)"
        )

        return report

    def _detect_character_changes(  # noqa: PLR0912
        self, char_name: str, text: str, _chapter: int
    ) -> CharacterStateChange | None:
        """检测单个角色的状态变更"""
        change = CharacterStateChange(character_name=char_name, character_uid=char_name)

        # 检测情绪变化 — 在角色名附近查找情绪词
        for emotion_cn in self.EMOTION_MAP:
            # 在角色名前后50字内查找
            for m in re.finditer(re.escape(char_name), text):
                context = text[max(0, m.start() - 50) : min(len(text), m.end() + 50)]
                if emotion_cn in context:
                    change.emotion_change = emotion_cn
                    break
            if change.emotion_change:
                break

        # 检测状态变化
        for status_cn in self.STATUS_KEYWORDS:
            if status_cn in text and char_name in text:
                # 确保状态词和角色名在同一段
                for para in text.split("\n\n"):
                    if char_name in para and status_cn in para:
                        change.status_change = status_cn
                        break
            if change.status_change:
                break

        # 检测关系变化
        for rel_cn in self.RELATION_KEYWORDS:
            if rel_cn in text and char_name in text:
                for para in text.split("\n\n"):
                    if char_name in para and rel_cn in para:
                        change.relationship_change = rel_cn
                        break
            if change.relationship_change:
                break

        # 检测位置变化（简化版：查找"来到/前往/到达"等词）
        for loc_verb in ["来到", "前往", "到达", "回到", "进入", "离开"]:
            if loc_verb in text and char_name in text:
                for para in text.split("\n\n"):
                    if char_name in para and loc_verb in para:
                        # 提取位置名
                        loc_match = re.search(rf"{loc_verb}[^\n。！？]{{0,20}}", para)
                        if loc_match:
                            change.location_change = loc_match.group().strip()
                        break
            if change.location_change:
                break

        # 如果没有任何变更，返回None
        if not any(
            [
                change.emotion_change,
                change.status_change,
                change.relationship_change,
                change.location_change,
            ]
        ):
            return None

        return change

    def _extract_events(
        self, text: str, chapter: int, characters: list[str]
    ) -> list[EventExtracted]:
        """提取关键事件"""
        events = []
        # 按段落组检测事件（以空行分隔的连续段落为一个场景/事件）
        scene_groups = text.split("\n\n\n") if "\n\n\n" in text else [text]

        for i, scene in enumerate(scene_groups):
            if len(scene) < 100:
                continue

            # 检测事件类型
            event_type = "plot"
            if any(kw in scene for kw in ["攻击", "战斗", "出招", "斩杀", "轰", "爆炸", "对决"]):
                event_type = "battle"
            elif any(kw in scene for kw in ["发现", "原来", "真相", "秘密", "竟然", "隐藏"]):
                event_type = "revelation"
            elif any(kw in scene for kw in ["第二天", "数日后", "时光", "转眼", "接下来"]):
                event_type = "transition"

            # 提取涉及的字符
            involved = [c for c in characters if c in scene]
            if not involved:
                continue

            # 生成事件描述（取场景前80字）
            desc = scene[:80].strip()

            event = EventExtracted(
                event_name=f"ch{chapter}_event_{i + 1}",
                event_type=event_type,
                description=desc,
                involved_characters=involved,
                chapter=chapter,
            )
            events.append(event)

        return events

    def _extract_foreshadowing(self, text: str, blueprint: dict | None) -> ForeshadowingDelta:
        """提取伏笔变更"""
        delta = ForeshadowingDelta()

        if blueprint:
            fp = blueprint.get("foreshadowing", {})
            delta.planted = fp.get("to_plant", [])
            delta.revealed = fp.get("to_reveal", [])

        # 额外从文本中检测伏笔模式
        # 埋伏笔: "谁也没想到"、"此时他还不知道"、"这个细节"
        plant_patterns = ["谁也没想到", "此时.*还不知道", "殊不知", "埋下了", "暗藏"]
        for pat in plant_patterns:
            matches = re.findall(pat, text)
            for m in matches[:3]:
                if m not in delta.planted:
                    delta.planted.append(m)

        # 揭示: "原来"、"竟然是"、"真相"
        reveal_patterns = ["原来是", "竟然是", "真相是", "原来如此"]
        for pat in reveal_patterns:
            matches = re.findall(pat, text)
            for m in matches[:3]:
                if m not in delta.revealed:
                    delta.revealed.append(m)

        return delta

    def _extract_new_entities(self, text: str, known_characters: list[str]) -> dict[str, list[str]]:
        """提取新出现的实体（角色/地点/物品）"""
        entities: dict[str, list[str]] = {}

        # 提取新角色名（不在已知列表中的2-4字中文名）
        all_names = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
        name_counts = {}
        for n in all_names:
            if n not in known_characters:
                name_counts[n] = name_counts.get(n, 0) + 1

        # 出现3次以上视为新角色
        new_chars = [n for n, c in name_counts.items() if c >= 3]
        if new_chars:
            entities["characters"] = new_chars[:5]

        # 提取地点（以"山/城/镇/谷/殿/府/阁/院/楼/洞/峰"结尾的词）
        location_suffixes = [
            "山",
            "城",
            "镇",
            "谷",
            "殿",
            "府",
            "阁",
            "院",
            "楼",
            "洞",
            "峰",
            "宗",
            "派",
            "门",
            "国",
            "界",
            "域",
        ]
        locations = set()
        for w in re.findall(r"[\u4e00-\u9fff]{2,6}", text):
            if any(w.endswith(s) for s in location_suffixes) and w not in known_characters:
                locations.add(w)
        if locations:
            entities["locations"] = list(locations)[:5]

        # 提取物品（以"剑/刀/丹/药/石/珠/玉/符/鼎/炉"结尾的词）
        item_suffixes = ["剑", "刀", "丹", "药", "石", "珠", "玉", "符", "鼎", "炉", "甲", "枪"]
        items = set()
        for w in re.findall(r"[\u4e00-\u9fff]{2,6}", text):
            if any(w.endswith(s) for s in item_suffixes) and w not in known_characters:
                items.add(w)
        if items:
            entities["items"] = list(items)[:5]

        return entities

    def _extract_key_plot_points(self, text: str) -> list[str]:
        """提取关键情节节点"""
        points = []

        # 检测高潮/转折信号
        climax_signals = [
            ("爆发出", "爆发"),
            ("终于", "终于"),
            ("突然", "突然转折"),
            ("就在这时", "关键时刻"),
            ("轰", "战斗高潮"),
        ]

        for signal, label in climax_signals:
            if signal in text:
                # 找到该信号附近的句子作为情节描述
                for m in re.finditer(re.escape(signal), text):
                    start = max(0, m.start() - 30)
                    end = min(len(text), m.end() + 50)
                    context = text[start:end].strip()
                    if len(context) > 10:
                        points.append(f"[{label}] {context}")
                        break
                if len(points) >= 5:
                    break

        return points[:5]


# 全局单例
observer = Observer()

"""
昆仑创作引擎 — 四层记忆架构

基于认知科学的四层记忆模型，为百万字长篇小说创作提供持久化、可检索、主动遗忘的记忆系统。

四层记忆:
  1. 工作记忆 (Working Memory) — 当前章节上下文，最近N章，Token预算内即时信息
  2. 情景记忆 (Episodic Memory) — 具体事件/场景/对话，按时间线组织，支持事件检索
  3. 语义记忆 (Semantic Memory) — 持久事实：人物/世界观/功法/地点/物品，结构化存储
  4. 程序记忆 (Procedural Memory) — 如何做：写作风格/套路模板/爽点模式/节奏控制/作者偏好

核心能力:
  - 自动记忆写入 — 从生成内容中提取信息，分层写入
  - 动态记忆检索 — 按查询类型加载对应层记忆
  - 主动遗忘机制 — 旧/不重要记忆压缩或丢弃
  - 渐进式摘要 — 详细事件→摘要→关键事实
  - 一致性检查 — 新内容与已有记忆的冲突检测
  - Token预算管理 — 检索结果不超过Token预算

与昆仑引擎集成:
  - 增强 kg/ 知识图谱（语义记忆的结构化存储）
  - 增强 context/ 上下文管理（工作记忆的Token预算）
  - 增强 truth/ 真相伏笔（情景记忆的事件追踪）
  - 为 vibe_writer/ 和 agents/ 提供统一记忆接口

Author: 昆仑创作引擎
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ══════════════════════════════════════════════════════
# 记忆类型定义
# ══════════════════════════════════════════════════════


class MemoryLayer(Enum):
    """记忆层级"""

    WORKING = "working"  # 工作记忆
    EPISODIC = "episodic"  # 情景记忆
    SEMANTIC = "semantic"  # 语义记忆
    PROCEDURAL = "procedural"  # 程序记忆


class MemoryImportance(Enum):
    """记忆重要度"""

    TRIVIAL = 1  # 琐碎，很快遗忘
    LOW = 2  # 低重要
    MEDIUM = 3  # 中等
    HIGH = 4  # 高重要
    CRITICAL = 5  # 关键，永久保留


class SemanticEntityType(Enum):
    """语义记忆实体类型"""

    CHARACTER = "character"  # 人物
    LOCATION = "location"  # 地点
    ITEM = "item"  # 物品
    TECHNIQUE = "technique"  # 功法/技能
    FACTION = "faction"  # 势力
    EVENT = "event"  # 重大事件
    RULE = "rule"  # 世界规则
    RELATIONSHIP = "relationship"  # 关系


# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


@dataclass
class MemoryItem:
    """通用记忆项"""

    id: str
    layer: MemoryLayer
    content: str
    importance: MemoryImportance = MemoryImportance.MEDIUM
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    compressed: bool = False
    source_chapter: int = 0

    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "layer": self.layer.value,
            "content": self.content,
            "importance": self.importance.value,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
            "metadata": self.metadata,
            "compressed": self.compressed,
            "source_chapter": self.source_chapter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryItem:
        return cls(
            id=data["id"],
            layer=MemoryLayer(data["layer"]),
            content=data["content"],
            importance=MemoryImportance(data.get("importance", 3)),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            compressed=data.get("compressed", False),
            source_chapter=data.get("source_chapter", 0),
        )


@dataclass
class SemanticEntity:
    """语义记忆实体"""

    id: str
    name: str
    entity_type: SemanticEntityType
    description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    first_appearance: int = 0
    last_appearance: int = 0
    appearance_count: int = 0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    aliases: list[str] = field(default_factory=list)
    status: str = "active"  # active / deceased / missing / sealed
    # L3 增强：关系图谱引用（运行时绑定，不序列化）
    relation_graph_ref: Any = None
    # L3 增强：时序属性（如实力随章节变化）
    temporal_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "attributes": self.attributes,
            "relationships": self.relationships,
            "first_appearance": self.first_appearance,
            "last_appearance": self.last_appearance,
            "appearance_count": self.appearance_count,
            "importance": self.importance.value,
            "aliases": self.aliases,
            "status": self.status,
            "temporal_attributes": self.temporal_attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticEntity:
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=SemanticEntityType(data["entity_type"]),
            description=data.get("description", ""),
            attributes=data.get("attributes", {}),
            relationships=data.get("relationships", []),
            first_appearance=data.get("first_appearance", 0),
            last_appearance=data.get("last_appearance", 0),
            appearance_count=data.get("appearance_count", 0),
            importance=MemoryImportance(data.get("importance", 3)),
            aliases=data.get("aliases", []),
            status=data.get("status", "active"),
            temporal_attributes=data.get("temporal_attributes", {}),
        )


@dataclass
class EpisodicEvent:
    """情景记忆事件"""

    id: str
    chapter: int
    scene: str
    summary: str
    participants: list[str] = field(default_factory=list)
    location: str = ""
    event_type: str = "general"  # battle / dialogue / revelation / transition / climax
    emotional_arc: str = "neutral"  # rising / falling / peak / trough / neutral
    plot_relevance: float = 0.5
    foreshadowing: list[str] = field(default_factory=list)
    resolved_hooks: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    compressed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodicEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProceduralPattern:
    """程序记忆模式"""

    id: str
    name: str
    pattern_type: str  # style / trope / pacing / climax / dialogue / description
    description: str
    trigger_conditions: list[str] = field(default_factory=list)
    template: str = ""
    examples: list[str] = field(default_factory=list)
    effectiveness: float = 0.5
    usage_count: int = 0
    author_preference: float = 0.5
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProceduralPattern:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MemoryQueryResult:
    """记忆查询结果"""

    working: list[MemoryItem] = field(default_factory=list)
    episodic: list[EpisodicEvent] = field(default_factory=list)
    semantic: list[SemanticEntity] = field(default_factory=list)
    procedural: list[ProceduralPattern] = field(default_factory=list)
    total_tokens: int = 0
    token_budget: int = 4000
    truncated: bool = False

    def summary(self) -> str:
        return (
            f"记忆检索: 工作{len(self.working)}条, 情景{len(self.episodic)}事件, "
            f"语义{len(self.semantic)}实体, 程序{len(self.procedural)}模式, "
            f"Token: {self.total_tokens}/{self.token_budget}"
        )


# ══════════════════════════════════════════════════════
# 工作记忆
# ══════════════════════════════════════════════════════


class WorkingMemory:
    """工作记忆 — 当前章节上下文，最近N章内容"""

    def __init__(self, max_chapters: int = 5, token_budget: int = 3000):
        self.max_chapters = max_chapters
        self.token_budget = token_budget
        self.current_chapter: int = 0
        self.current_context: str = ""
        self.recent_chapters: dict[int, str] = {}
        self.recent_summaries: dict[int, str] = {}
        self.temporary_notes: list[MemoryItem] = []
        # 增强：在场角色状态卡
        self.character_states: dict[str, dict[str, Any]] = {}
        # 增强：伏笔预警
        self.foreshadow_alerts: list[dict[str, Any]] = []

    def set_current_chapter(self, chapter: int, context: str = ""):
        self.current_chapter = chapter
        self.current_context = context

    def add_chapter(self, chapter: int, content: str, summary: str = ""):
        self.recent_chapters[chapter] = content
        if summary:
            self.recent_summaries[chapter] = summary
        # 保持最近N章
        if len(self.recent_chapters) > self.max_chapters:
            oldest = min(self.recent_chapters.keys())
            del self.recent_chapters[oldest]
            if oldest in self.recent_summaries:
                del self.recent_summaries[oldest]

    def add_note(
        self,
        content: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        tags: list[str] | None = None,
    ):
        item = MemoryItem(
            id=f"wm_{int(time.time() * 1000)}",
            layer=MemoryLayer.WORKING,
            content=content,
            importance=importance,
            tags=tags or [],
            source_chapter=self.current_chapter,
        )
        self.temporary_notes.append(item)
        return item

    def get_context(self, include_summaries: bool = True) -> str:
        parts = []
        if self.current_context:
            parts.append(f"【当前章节上下文】\n{self.current_context}")
        if include_summaries and self.recent_summaries:
            sorted_chapters = sorted(self.recent_summaries.keys(), reverse=True)
            parts.extend(
                f"【第{ch}章摘要】\n{self.recent_summaries[ch]}" for ch in sorted_chapters[:3]
            )
        return "\n\n".join(parts)

    def estimate_tokens(self) -> int:
        text = self.get_context()
        return len(text) // 2  # 中文约2字/token

    def set_character_state(self, name: str, state: dict[str, Any]):
        """设置在场角色状态卡

        Args:
            name: 角色名
            state: 状态字典（emotion/VAD, ability, known_info, motivation等）
        """
        self.character_states[name] = state

    def get_character_states(self) -> list[dict[str, Any]]:
        """获取所有在场角色状态卡"""
        return [{"name": name, **state} for name, state in self.character_states.items()]

    def add_foreshadow_alert(self, alert: dict[str, Any]):
        """添加伏笔预警

        Args:
            alert: 预警字典（type: 应揭示/应安插/逾期, content, chapter等）
        """
        self.foreshadow_alerts.append(alert)

    def get_context_enhanced(self) -> str:
        """增强上下文（原get_context + 角色状态卡 + 伏笔预警）"""
        parts = [self.get_context()]
        # 角色状态卡
        if self.character_states:
            state_lines = ["【在场角色状态】"]
            for name, state in self.character_states.items():
                emotion = state.get("emotion", "未知")
                motivation = state.get("motivation", "")
                ability = state.get("ability", "")
                line = f"  {name}: 情绪={emotion}"
                if ability:
                    line += f", 能力={ability}"
                if motivation:
                    line += f", 动机={motivation}"
                state_lines.append(line)
            parts.append("\n".join(state_lines))
        # 伏笔预警
        if self.foreshadow_alerts:
            alert_lines = ["【伏笔预警】"]
            for alert in self.foreshadow_alerts:
                atype = alert.get("type", "未知")
                acontent = alert.get("content", "")
                alert_lines.append(f"  [{atype}] {acontent}")
            parts.append("\n".join(alert_lines))
        return "\n\n".join(p for p in parts if p)

    def consolidate_to_episodic(self) -> list[EpisodicEvent]:
        """将工作记忆中的临时笔记巩固为情景记忆事件"""
        events: list[EpisodicEvent] = []
        for note in self.temporary_notes:
            if note.importance.value >= 2:  # 只巩固LOW及以上的笔记
                event = EpisodicEvent(
                    id=f"consolidated_{note.id}",
                    chapter=note.source_chapter,
                    scene="工作记忆巩固",
                    summary=note.content[:100],
                    participants=[],
                    event_type="general",
                    plot_relevance=0.3 + 0.1 * note.importance.value,
                    importance=note.importance,
                    created_at=note.created_at,
                )
                events.append(event)
        self.temporary_notes = [n for n in self.temporary_notes if n.importance.value < 2]
        return events

    def clear_temporary(self):
        self.temporary_notes = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_chapters": self.max_chapters,
            "token_budget": self.token_budget,
            "current_chapter": self.current_chapter,
            "current_context": self.current_context,
            "recent_chapters": self.recent_chapters,
            "recent_summaries": self.recent_summaries,
            "temporary_notes": [n.to_dict() for n in self.temporary_notes],
            "character_states": self.character_states,
            "foreshadow_alerts": self.foreshadow_alerts,
        }


# ══════════════════════════════════════════════════════
# 情景记忆
# ══════════════════════════════════════════════════════


class EpisodicMemory:
    """情景记忆 — 具体事件/场景/对话，按时间线组织"""

    def __init__(self, max_events: int = 500, compression_threshold: int = 100):
        from kunlun.memory.forgetting import EbbinghausForgetting

        self.max_events = max_events
        self.compression_threshold = compression_threshold
        self.events: list[EpisodicEvent] = []
        self.event_index: dict[str, list[int]] = {}  # tag -> event indices
        # 增强：摘要树（可选，默认None，启用时创建）
        self.summary_tree: Any = None  # SummaryTree | None
        # 增强：遗忘曲线实例
        self.forgetting = EbbinghausForgetting()

    def add_event(self, event: EpisodicEvent):
        self.events.append(event)
        # 索引
        for participant in event.participants:
            self.event_index.setdefault(participant, []).append(len(self.events) - 1)
        if event.location:
            self.event_index.setdefault(event.location, []).append(len(self.events) - 1)
        # 增强：同步更新摘要树（如果启用）
        if self.summary_tree is not None:
            self._sync_event_to_summary_tree(event)
        # 超过上限时压缩旧事件
        if len(self.events) > self.max_events:
            self._compress_old_events()

    def _sync_event_to_summary_tree(self, event: EpisodicEvent):
        """将事件同步到摘要树（内部方法）"""

        if self.summary_tree is None:
            return
        # 检查该章是否已有摘要，没有则用事件summary创建
        has_ch = False
        for vol in self.summary_tree.root.children:
            for ch in vol.children:
                if ch.chapter_range == (event.chapter, event.chapter):
                    has_ch = True
                    ch.event_ids.append(event.id)
                    break
        if not has_ch:
            self.summary_tree.add_chapter_summary(
                chapter=event.chapter,
                summary=event.summary[:80],
            )
            # 重新找到章节点并添加event_id
            for vol in self.summary_tree.root.children:
                for ch in vol.children:
                    if ch.chapter_range == (event.chapter, event.chapter):
                        ch.event_ids.append(event.id)
                        break

    def get_events_by_chapter(self, chapter: int) -> list[EpisodicEvent]:
        return [e for e in self.events if e.chapter == chapter]

    def get_events_by_participant(self, name: str, limit: int = 20) -> list[EpisodicEvent]:
        indices = self.event_index.get(name, [])
        result = [self.events[i] for i in indices if i < len(self.events)]
        return sorted(result, key=lambda e: e.chapter, reverse=True)[:limit]

    def get_events_by_type(self, event_type: str, limit: int = 20) -> list[EpisodicEvent]:
        result = [e for e in self.events if e.event_type == event_type]
        return sorted(result, key=lambda e: e.chapter, reverse=True)[:limit]

    def get_recent_events(self, n: int = 10, min_relevance: float = 0.3) -> list[EpisodicEvent]:
        result = [e for e in self.events if e.plot_relevance >= min_relevance]
        return sorted(result, key=lambda e: e.chapter, reverse=True)[:n]

    def get_plot_timeline(self) -> list[dict[str, Any]]:
        """获取情节时间线（压缩版）"""
        return [
            {
                "chapter": e.chapter,
                "scene": e.scene,
                "summary": e.summary[:100],
                "type": e.event_type,
                "relevance": e.plot_relevance,
            }
            for e in sorted(self.events, key=lambda e: e.chapter)
            if e.plot_relevance >= 0.5
        ]

    def _compress_old_events(self):
        """压缩旧事件：将低重要度事件合并为摘要"""
        old_events = [e for e in self.events if not e.compressed and e.plot_relevance < 0.4]
        if len(old_events) > self.compression_threshold:
            # 按章节分组压缩
            chapter_groups: dict[int, list[EpisodicEvent]] = {}
            for e in old_events:
                chapter_groups.setdefault(e.chapter, []).append(e)
            for chapter, group in chapter_groups.items():
                if len(group) >= 3:
                    # 合并为一个摘要事件
                    combined = EpisodicEvent(
                        id=f"compressed_{chapter}_{int(time.time())}",
                        chapter=chapter,
                        scene=f"第{chapter}章综合",
                        summary="；".join(e.summary[:50] for e in group[:5]),
                        participants=list({p for e in group for p in e.participants})[:5],
                        event_type="compressed",
                        plot_relevance=0.3,
                        compressed=True,
                    )
                    # 移除旧事件，添加压缩事件
                    for e in group:
                        if e in self.events:
                            self.events.remove(e)
                    self.events.append(combined)

    def search(self, query: str, limit: int = 10) -> list[EpisodicEvent]:
        """简单关键词搜索"""
        keywords = [k for k in re.split(r"[，。！？\s]", query) if len(k) >= 2]
        scored = []
        for e in self.events:
            score = 0
            for kw in keywords:
                if kw in e.summary:
                    score += 2
                if kw in e.scene:
                    score += 1
                if kw in e.participants:
                    score += 3
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def enable_summary_tree(self, volume_size: int = 50):
        """启用摘要树

        Args:
            volume_size: 每卷章数，默认50
        """
        from kunlun.memory.summary_tree import SummaryTree

        self.summary_tree = SummaryTree(volume_size=volume_size)
        # 将已有事件同步到摘要树
        chapter_summaries: dict[int, str] = {}
        for event in self.events:
            if event.chapter not in chapter_summaries:
                chapter_summaries[event.chapter] = event.summary[:80]
        for ch, summary in sorted(chapter_summaries.items()):
            self.summary_tree.add_chapter_summary(chapter=ch, summary=summary)

    def add_chapter_with_events(
        self,
        chapter: int,
        text: str,
        summary: str = "",
    ) -> list[EpisodicEvent]:
        """用 EventExtractor 自动提取事件并添加，同时添加摘要到摘要树

        Args:
            chapter: 章节号
            text: 章节文本
            summary: 章节摘要（空则自动取文本前100字）

        Returns:
            提取并添加的事件列表
        """
        from kunlun.memory.event_extractor import EventExtractor

        extractor = EventExtractor()
        event_dicts = extractor.extract_events(text, chapter)
        events: list[EpisodicEvent] = []
        for idx, ed in enumerate(event_dicts):
            event = EpisodicEvent(
                id=f"ev_auto_{chapter}_{idx}_{int(time.time() * 1000) % 100000}",
                chapter=chapter,
                scene=ed["scene"],
                summary=ed["summary"],
                participants=ed["participants"],
                event_type=ed["event_type"],
                emotional_arc=ed["emotional_arc"],
                plot_relevance=ed["plot_relevance"],
                importance=MemoryImportance.MEDIUM,
            )
            self.add_event(event)
            events.append(event)
        # 添加章节摘要到摘要树
        if self.summary_tree is not None:
            ch_summary = summary if summary else text[:100]
            self.summary_tree.add_chapter_summary(chapter=chapter, summary=ch_summary)
        return events

    def search_with_forgetting(
        self,
        query: str,
        limit: int = 10,
        current_time: float | None = None,
    ) -> list[EpisodicEvent]:
        """带遗忘加权的搜索（retention * relevance_score）

        Args:
            query: 搜索关键词
            limit: 返回数量上限
            current_time: 当前时间戳

        Returns:
            按遗忘加权得分排序的事件列表
        """
        keywords = [k for k in re.split(r"[，。！？\s]", query) if len(k) >= 2]
        scored: list[tuple[float, EpisodicEvent]] = []
        for e in self.events:
            relevance = 0
            for kw in keywords:
                if kw in e.summary:
                    relevance += 2
                if kw in e.scene:
                    relevance += 1
                if kw in e.participants:
                    relevance += 3
            if relevance > 0:
                retention = self.forgetting.calculate_retention(e, current_time)
                final_score = relevance * retention
                scored.append((final_score, e))
                # 访问增强
                self.forgetting.boost_memory(e.id, self.events)
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def get_events_by_chapter_with_summary(self, chapter: int) -> dict[str, Any]:
        """获取章节事件+摘要

        Args:
            chapter: 章节号

        Returns:
            含 chapter, events, summary 的字典
        """
        events = self.get_events_by_chapter(chapter)
        summary = ""
        if self.summary_tree is not None:
            for vol in self.summary_tree.root.children:
                for ch in vol.children:
                    if ch.chapter_range == (chapter, chapter):
                        summary = ch.summary
                        break
        return {
            "chapter": chapter,
            "events": events,
            "summary": summary,
            "event_count": len(events),
        }

    def apply_forgetting_cycle(self, current_time: float | None = None) -> int:
        """执行一次遗忘周期（清理低保持率事件）

        Args:
            current_time: 当前时间戳

        Returns:
            被遗忘清理的事件数量
        """
        kept, forgotten = self.forgetting.apply_forgetting(self.events, current_time)
        if forgotten:
            self.events = kept
            # 重建索引
            self.event_index = {}
            for i, event in enumerate(self.events):
                for p in event.participants:
                    self.event_index.setdefault(p, []).append(i)
                if event.location:
                    self.event_index.setdefault(event.location, []).append(i)
        return len(forgotten)

    def save(self, filepath: str):
        """L2持久化（events + summary_tree）"""
        import json

        data: dict[str, Any] = {
            "max_events": self.max_events,
            "compression_threshold": self.compression_threshold,
            "events": [e.to_dict() for e in self.events],
        }
        if self.summary_tree is not None:
            data["summary_tree"] = self.summary_tree.to_dict()
        with Path(filepath).open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def load(self, filepath: str):
        """从文件加载L2记忆（events + summary_tree）"""
        import json

        from kunlun.memory.summary_tree import SummaryTree

        with Path(filepath).open(encoding="utf-8") as f:
            data = json.load(f)
        self.max_events = data.get("max_events", self.max_events)
        self.compression_threshold = data.get("compression_threshold", self.compression_threshold)
        self.events = []
        self.event_index = {}
        for edata in data.get("events", []):
            event = EpisodicEvent.from_dict(edata)
            self.events.append(event)
            for p in event.participants:
                self.event_index.setdefault(p, []).append(len(self.events) - 1)
            if event.location:
                self.event_index.setdefault(event.location, []).append(len(self.events) - 1)
        if data.get("summary_tree"):
            self.summary_tree = SummaryTree.from_dict(data["summary_tree"])
        else:
            self.summary_tree = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "max_events": self.max_events,
            "events": [e.to_dict() for e in self.events],
        }
        if self.summary_tree is not None:
            data["summary_tree"] = self.summary_tree.to_dict()
        return data


# ══════════════════════════════════════════════════════
# 语义记忆
# ══════════════════════════════════════════════════════


class SemanticMemory:
    """语义记忆 — 持久事实：人物/世界观/功法/地点/物品"""

    def __init__(self):
        self.entities: dict[str, SemanticEntity] = {}
        self.name_index: dict[str, str] = {}  # name/alias -> entity_id
        self.type_index: dict[str, list[str]] = {}  # entity_type -> [entity_ids]

    def add_entity(self, entity: SemanticEntity):
        self.entities[entity.id] = entity
        self.name_index[entity.name] = entity.id
        for alias in entity.aliases:
            self.name_index[alias] = entity.id
        self.type_index.setdefault(entity.entity_type.value, []).append(entity.id)

    def get_entity(self, name_or_id: str) -> SemanticEntity | None:
        if name_or_id in self.entities:
            entity = self.entities[name_or_id]
            entity.last_appearance = int(time.time())
            return entity
        entity_id = self.name_index.get(name_or_id)
        if entity_id and entity_id in self.entities:
            return self.entities[entity_id]
        return None

    def get_entities_by_type(self, entity_type: str) -> list[SemanticEntity]:
        ids = self.type_index.get(entity_type, [])
        return [self.entities[i] for i in ids if i in self.entities]

    def get_characters(self) -> list[SemanticEntity]:
        return self.get_entities_by_type("character")

    def get_locations(self) -> list[SemanticEntity]:
        return self.get_entities_by_type("location")

    def get_techniques(self) -> list[SemanticEntity]:
        return self.get_entities_by_type("technique")

    def update_entity_appearance(self, name: str, chapter: int):
        entity = self.get_entity(name)
        if entity:
            entity.last_appearance = chapter
            entity.appearance_count += 1
            if entity.first_appearance == 0:
                entity.first_appearance = chapter

    def check_consistency(self, name: str, new_info: dict[str, Any]) -> dict[str, Any]:
        """检查新信息与已有实体的一致性"""
        entity = self.get_entity(name)
        if not entity:
            return {"consistent": True, "new_entity": True, "message": f"新实体: {name}"}

        conflicts = []
        for key, value in new_info.items():
            if key in entity.attributes:
                old_value = entity.attributes[key]
                if old_value != value and str(old_value) != str(value):
                    conflicts.append(
                        {
                            "attribute": key,
                            "old": old_value,
                            "new": value,
                        }
                    )

        return {
            "consistent": len(conflicts) == 0,
            "new_entity": False,
            "conflicts": conflicts,
            "message": f"发现{len(conflicts)}处冲突" if conflicts else "信息一致",
        }

    def get_character_relationships(self, character_name: str) -> list[dict[str, Any]]:
        entity = self.get_entity(character_name)
        if not entity:
            return []
        return entity.relationships

    def get_world_facts(self) -> list[SemanticEntity]:
        """获取世界观相关实体（规则、地点、势力）"""
        result = []
        for etype in ["rule", "location", "faction"]:
            result.extend(self.get_entities_by_type(etype))
        return result

    def search(self, query: str, limit: int = 10) -> list[SemanticEntity]:
        keywords = [k for k in re.split(r"[，。！？\s]", query) if len(k) >= 2]
        scored = []
        for entity in self.entities.values():
            score = 0
            for kw in keywords:
                if kw in entity.name:
                    score += 3
                if kw in entity.description:
                    score += 2
                if kw in entity.aliases:
                    score += 2
            if score > 0:
                scored.append((score, entity))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    # ── L3 增强：关系图谱方法 ──────────────────────────

    def set_relation_graph(self, graph: Any):
        """绑定实体关系图谱

        Args:
            graph: EntityRelationGraph 实例
        """
        self._relation_graph = graph
        # 同步绑定到所有实体
        for entity in self.entities.values():
            entity.relation_graph_ref = graph

    def add_entity_relation(
        self,
        source_name: str,
        target_name: str,
        rel_type: str,
        attributes: dict[str, Any] | None = None,
        valid_from_chapter: int = 0,
    ) -> Any | None:
        """通过名称查找实体并添加关系

        Args:
            source_name: 源实体名称
            target_name: 目标实体名称
            rel_type: 关系类型
            attributes: 关系属性
            valid_from_chapter: 关系起始章节

        Returns:
            创建的关系对象，未绑定图谱或实体不存在时返回 None
        """
        graph = getattr(self, "_relation_graph", None)
        if graph is None:
            return None
        source = self.get_entity(source_name)
        target = self.get_entity(target_name)
        if not source or not target:
            return None
        return graph.add_relation(
            source_id=source.id,
            target_id=target.id,
            rel_type=rel_type,
            attributes=attributes or {},
            valid_from_chapter=valid_from_chapter,
        )

    def get_entity_relations(
        self,
        name: str,
        direction: str = "both",
        chapter: int | None = None,
    ) -> list[dict[str, Any]]:
        """获取实体关系（支持时序过滤）

        Args:
            name: 实体名称
            direction: "out"/"in"/"both"
            chapter: 可选章节号，提供时只返回该章节有效的关系

        Returns:
            关系字典列表
        """
        graph = getattr(self, "_relation_graph", None)
        if graph is None:
            return []
        entity = self.get_entity(name)
        if not entity:
            return []
        if chapter is not None:
            relations = graph.get_relations_at_chapter(entity.id, chapter)
        else:
            relations = graph.get_relations(entity.id, direction=direction)
        return [r.to_dict() for r in relations]

    def get_entity_neighborhood(self, name: str, depth: int = 1) -> dict[str, Any]:
        """获取实体邻域子图（返回实体+关系的结构化数据）

        Args:
            name: 中心实体名称
            depth: 扩展深度

        Returns:
            含 center_entity, entities, relations 的字典
        """
        graph = getattr(self, "_relation_graph", None)
        if graph is None:
            return {
                "center": name,
                "entities": [],
                "relations": [],
                "entity_count": 0,
                "relation_count": 0,
            }
        entity = self.get_entity(name)
        if not entity:
            return {
                "center": name,
                "entities": [],
                "relations": [],
                "entity_count": 0,
                "relation_count": 0,
            }
        neighborhood = graph.get_neighborhood(entity.id, depth=depth)
        # 将实体 ID 转换为实体名称信息
        entity_details = []
        for eid in neighborhood.get("entities", []):
            # 反向查找实体
            ent = None
            for e in self.entities.values():
                if e.id == eid:
                    ent = e
                    break
            if ent:
                entity_details.append(
                    {
                        "id": ent.id,
                        "name": ent.name,
                        "entity_type": ent.entity_type.value,
                        "description": ent.description[:100],
                    }
                )
            else:
                entity_details.append({"id": eid, "name": eid, "entity_type": "unknown"})
        neighborhood["entity_details"] = entity_details
        neighborhood["center_entity"] = {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type.value,
        }
        return neighborhood

    def graphrag_search(self, query: str, limit: int = 5) -> dict[str, Any]:
        """GraphRAG式检索：实体搜索 + 关系扩展 + 上下文聚合

        Args:
            query: 搜索查询
            limit: 返回实体数量上限

        Returns:
            含 entities, relations, neighborhood_summary, context 的结构化上下文
        """
        # 第一步：实体搜索（复用现有 search）
        matched_entities = self.search(query, limit=limit)
        if not matched_entities:
            return {
                "query": query,
                "entities": [],
                "relations": [],
                "neighborhood_summary": "",
                "context": "",
            }

        graph = getattr(self, "_relation_graph", None)
        all_relations: list[dict[str, Any]] = []
        all_entity_ids: set[str] = set()
        neighborhood_parts: list[str] = []

        for entity in matched_entities:
            all_entity_ids.add(entity.id)
            if graph is not None:
                # 关系扩展：获取该实体的一阶邻域
                neighborhood = graph.get_neighborhood(entity.id, depth=1)
                for rel in neighborhood.get("relations", []):
                    if rel["id"] not in {r["id"] for r in all_relations}:
                        all_relations.append(rel)
                for eid in neighborhood.get("entities", []):
                    all_entity_ids.add(eid)
                # 构建邻域摘要
                neighbor_names = []
                for eid in neighborhood.get("entities", []):
                    if eid == entity.id:
                        continue
                    for e in self.entities.values():
                        if e.id == eid:
                            neighbor_names.append(e.name)
                            break
                if neighbor_names:
                    neighbor_str = ", ".join(neighbor_names[:5])
                    neighborhood_parts.append(f"{entity.name} 关联: {neighbor_str}")

        # 构建上下文文本
        entity_lines = [
            f"[{entity.entity_type.value}] {entity.name}: {entity.description[:80]}"
            for entity in matched_entities
        ]
        relation_lines = []
        for rel in all_relations[:20]:
            source_name = rel.get("source_id", "")
            target_name = rel.get("target_id", "")
            # 尝试转换为名称
            for e in self.entities.values():
                if e.id == rel.get("source_id"):
                    source_name = e.name
                if e.id == rel.get("target_id"):
                    target_name = e.name
            relation_lines.append(f"  {source_name} --[{rel.get('rel_type', '')}]--> {target_name}")

        context_parts = ["【GraphRAG 检索结果】"]
        context_parts.append("相关实体:")
        context_parts.extend(f"  {line}" for line in entity_lines)
        if relation_lines:
            context_parts.append("关系网络:")
            context_parts.extend(relation_lines)
        if neighborhood_parts:
            context_parts.append("邻域摘要:")
            context_parts.extend(f"  {p}" for p in neighborhood_parts)

        return {
            "query": query,
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "entity_type": e.entity_type.value,
                    "description": e.description,
                }
                for e in matched_entities
            ],
            "relations": all_relations,
            "neighborhood_summary": "; ".join(neighborhood_parts),
            "context": "\n".join(context_parts),
            "entity_count": len(all_entity_ids),
            "relation_count": len(all_relations),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
        }


# ══════════════════════════════════════════════════════
# 程序记忆
# ══════════════════════════════════════════════════════


class ProceduralMemory:
    """程序记忆 — 如何做：写作风格/套路模板/爽点模式/节奏控制"""

    def __init__(self):
        self.patterns: dict[str, ProceduralPattern] = {}
        self.type_index: dict[str, list[str]] = {}

    def add_pattern(self, pattern: ProceduralPattern):
        self.patterns[pattern.id] = pattern
        self.type_index.setdefault(pattern.pattern_type, []).append(pattern.id)

    def get_pattern(self, pattern_id: str) -> ProceduralPattern | None:
        return self.patterns.get(pattern_id)

    def get_patterns_by_type(self, pattern_type: str) -> list[ProceduralPattern]:
        ids = self.type_index.get(pattern_type, [])
        return [self.patterns[i] for i in ids if i in self.patterns]

    def get_recommended_patterns(self, scene_type: str, limit: int = 5) -> list[ProceduralPattern]:
        """根据场景类型推荐写作模式"""
        type_map = {
            "battle": ["climax", "pacing", "style"],
            "dialogue": ["dialogue", "style"],
            "description": ["description", "style"],
            "climax": ["climax", "pacing", "trope"],
            "transition": ["pacing", "trope"],
            "revelation": ["trope", "climax"],
        }
        target_types = type_map.get(scene_type, ["style", "trope"])
        candidates = []
        for ptype in target_types:
            candidates.extend(self.get_patterns_by_type(ptype))
        # 按效果和作者偏好排序
        scored = [(p.effectiveness * 0.6 + p.author_preference * 0.4, p) for p in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def record_usage(self, pattern_id: str, success: bool = True):
        pattern = self.patterns.get(pattern_id)
        if pattern:
            pattern.usage_count += 1
            if success:
                pattern.effectiveness = min(1.0, pattern.effectiveness + 0.02)
            else:
                pattern.effectiveness = max(0.0, pattern.effectiveness - 0.05)

    def load_default_tropes(self):
        """加载男频网文默认套路模式"""
        defaults = [
            ProceduralPattern(
                id="trope_face_slap",
                name="装逼打脸",
                pattern_type="trope",
                description="反派挑衅→主角隐忍→关键时刻爆发→反派震惊→众人膜拜",
                trigger_conditions=["反派挑衅", "看不起主角", "质疑实力"],
                template="第N波：{反派}轻蔑挑衅→主角表面平静→{契机}出现→主角一招制敌→{反派}脸色惨白→围观者倒吸凉气",
                effectiveness=0.85,
                author_preference=0.8,
                tags=["爽点", "打脸", "装逼"],
            ),
            ProceduralPattern(
                id="trope_underdog",
                name="废柴逆袭",
                pattern_type="trope",
                description="主角被轻视→隐藏实力曝光→震惊全场→地位逆转",
                trigger_conditions=["被轻视", "修为低", "出身差"],
                effectiveness=0.8,
                author_preference=0.75,
                tags=["爽点", "逆袭", "隐藏"],
            ),
            ProceduralPattern(
                id="trope_beauty_save",
                name="英雄救美",
                pattern_type="trope",
                description="美女遇险→主角出手→美女倾心→获得好感/资源",
                trigger_conditions=["美女遇险", "被围困", "危机时刻"],
                effectiveness=0.75,
                author_preference=0.7,
                tags=["爽点", "救美", "好感"],
            ),
            ProceduralPattern(
                id="pacing_fast_battle",
                name="快节奏战斗",
                pattern_type="pacing",
                description="短句为主，动词密集，每3-5句一个动作转折，对话穿插",
                trigger_conditions=["战斗场景", "追逐", "冲突"],
                template="短句！动作！反应！再动作！一句狠话！大招！结果！",
                effectiveness=0.9,
                author_preference=0.85,
                tags=["节奏", "战斗", "短句"],
            ),
            ProceduralPattern(
                id="climax_triple",
                name="三重高潮",
                pattern_type="climax",
                description="第一波小高潮→短暂回落→第二波中高潮→悬念→第三波大高潮→爆发收尾",
                trigger_conditions=["章末", "大战", "关键转折"],
                effectiveness=0.88,
                author_preference=0.8,
                tags=["高潮", "节奏", "章末"],
            ),
            ProceduralPattern(
                id="dialogue_witty",
                name="机智对话",
                pattern_type="dialogue",
                description="角色对话暗藏机锋，一语双关，表面客气实则较量",
                trigger_conditions=["谈判", "试探", "权谋"],
                effectiveness=0.7,
                author_preference=0.65,
                tags=["对话", "机智", "权谋"],
            ),
            ProceduralPattern(
                id="description_atmosphere",
                name="氛围描写",
                pattern_type="description",
                description="用环境描写烘托情绪，先写大环境再聚焦细节，最后落到人物感受",
                trigger_conditions=["新场景", "转折前", "意境营造"],
                effectiveness=0.75,
                author_preference=0.7,
                tags=["描写", "氛围", "意境"],
            ),
        ]
        for p in defaults:
            self.add_pattern(p)

    # ── L4 增强：场景模板库方法 ────────────────────────

    def set_template_library(self, library: Any):
        """绑定场景模板库

        Args:
            library: SceneTemplateLibrary 实例
        """
        self._template_library = library

    def get_scene_templates(self, scene_type: str, limit: int = 5) -> list[dict[str, Any]]:
        """获取场景模板

        Args:
            scene_type: 场景类型
            limit: 返回数量上限

        Returns:
            模板字典列表
        """
        library = getattr(self, "_template_library", None)
        if library is None:
            return []
        templates = library.get_templates_by_type(scene_type)
        return [t.to_dict() for t in templates[:limit]]

    def recommend_scene_template(
        self,
        scene_type: str,
        context_keywords: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """推荐场景模板

        Args:
            scene_type: 场景类型
            context_keywords: 上下文关键词

        Returns:
            推荐模板字典，未绑定模板库时返回 None
        """
        library = getattr(self, "_template_library", None)
        if library is None:
            return None
        templates = library.get_recommended_templates(scene_type, context_keywords, limit=1)
        if templates:
            return templates[0].to_dict()
        return None

    def extract_from_chapter(self, chapter_text: str, chapter_num: int = 0) -> dict[str, Any]:
        """从章节提取模式（委托给模板库）

        Args:
            chapter_text: 章节正文
            chapter_num: 章节号

        Returns:
            提取结果字典
        """
        library = getattr(self, "_template_library", None)
        if library is None:
            return {"matched_templates": [], "matched_pleasure_points": [], "analysis": {}}
        return library.extract_patterns_from_chapter(chapter_text, chapter_num)

    def get_pleasure_points(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取爽点模式

        Args:
            limit: 返回数量上限

        Returns:
            爽点模式字典列表
        """
        library = getattr(self, "_template_library", None)
        if library is None:
            return []
        points = library.get_pleasure_points(limit=limit)
        return [p.to_dict() for p in points]

    def to_dict(self) -> dict[str, Any]:
        return {
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
        }


# ══════════════════════════════════════════════════════
# 统一记忆管理器
# ══════════════════════════════════════════════════════


class MemoryManager:
    """统一记忆管理器 — 协调四层记忆，提供统一接口"""

    def __init__(self, book_id: str = "default", token_budget: int = 6000):
        self.book_id = book_id
        self.token_budget = token_budget
        self.working = WorkingMemory(token_budget=token_budget // 2)
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.procedural.load_default_tropes()
        self.forgetting_enabled = True
        self.forgetting_check_interval = 10  # 每10章检查一次遗忘
        self.last_forgetting_check = 0

    def write_chapter_memory(
        self,
        chapter: int,
        content: str,
        summary: str = "",
        events: list[dict] | None = None,
        entities: list[dict] | None = None,
    ):
        """写入章节记忆（自动分层）"""
        # 工作记忆
        self.working.add_chapter(chapter, content, summary)
        self.working.set_current_chapter(chapter, summary)

        # 情景记忆
        if events:
            for ev in events:
                event = EpisodicEvent(
                    id=f"ev_{chapter}_{int(time.time() * 1000)}_{len(self.episodic.events)}",
                    chapter=chapter,
                    scene=ev.get("scene", ""),
                    summary=ev.get("summary", ""),
                    participants=ev.get("participants", []),
                    location=ev.get("location", ""),
                    event_type=ev.get("event_type", "general"),
                    emotional_arc=ev.get("emotional_arc", "neutral"),
                    plot_relevance=ev.get("plot_relevance", 0.5),
                    foreshadowing=ev.get("foreshadowing", []),
                    resolved_hooks=ev.get("resolved_hooks", []),
                )
                self.episodic.add_event(event)

        # 语义记忆
        if entities:
            for idx, ent in enumerate(entities):
                entity_id = (
                    ent.get("id") or f"ent_{chapter}_{idx}_{int(time.time() * 1000) % 100000}"
                )
                entity = SemanticEntity(
                    id=entity_id,
                    name=ent.get("name", ""),
                    entity_type=SemanticEntityType(ent.get("entity_type", "character")),
                    description=ent.get("description", ""),
                    attributes=ent.get("attributes", {}),
                    relationships=ent.get("relationships", []),
                    first_appearance=ent.get("first_appearance", chapter),
                    last_appearance=chapter,
                    appearance_count=1,
                    importance=MemoryImportance(ent.get("importance", 3)),
                    aliases=ent.get("aliases", []),
                    status=ent.get("status", "active"),
                )
                existing = self.semantic.get_entity(entity.name)
                if existing:
                    existing.last_appearance = chapter
                    existing.appearance_count += 1
                else:
                    self.semantic.add_entity(entity)

        # 主动遗忘检查
        if (
            self.forgetting_enabled
            and (chapter - self.last_forgetting_check) >= self.forgetting_check_interval
        ):
            self._active_forgetting(chapter)
            self.last_forgetting_check = chapter

    def query(
        self,
        query: str,
        query_type: str = "general",
        chapter: int = 0,
        max_tokens: int | None = None,
    ) -> MemoryQueryResult:
        """统一记忆查询"""
        budget = max_tokens or self.token_budget
        result = MemoryQueryResult(token_budget=budget)

        # 工作记忆：总是包含当前上下文
        context = self.working.get_context()
        if context:
            result.working.append(
                MemoryItem(
                    id="current_context",
                    layer=MemoryLayer.WORKING,
                    content=context,
                    importance=MemoryImportance.HIGH,
                )
            )

        # 情景记忆：按查询类型检索
        if query_type in ["general", "plot", "events"]:
            result.episodic = self.episodic.search(query, limit=10)
            if not result.episodic and chapter > 0:
                result.episodic = self.episodic.get_recent_events(5)

        # 语义记忆：按查询类型检索
        if query_type in ["general", "characters", "world", "facts"]:
            result.semantic = self.semantic.search(query, limit=10)
            if not result.semantic and query_type in ["characters", "world"]:
                if query_type == "characters":
                    result.semantic = self.semantic.get_characters()[:10]
                else:
                    result.semantic = self.semantic.get_world_facts()[:10]

        # 程序记忆：按场景类型推荐
        if query_type in ["general", "style", "pacing", "trope"]:
            scene_type = "general"
            if "战斗" in query or "battle" in query:
                scene_type = "battle"
            elif "对话" in query or "dialogue" in query:
                scene_type = "dialogue"
            elif "描写" in query or "description" in query:
                scene_type = "description"
            elif "高潮" in query or "climax" in query:
                scene_type = "climax"
            result.procedural = self.procedural.get_recommended_patterns(scene_type, limit=5)

        # Token预算管理
        result.total_tokens = self._estimate_result_tokens(result)
        if result.total_tokens > budget:
            result.truncated = True
            result = self._truncate_to_budget(result, budget)

        return result

    def get_character_sheet(self, character_name: str) -> dict[str, Any]:
        """获取角色完整档案（语义+情景+关系）"""
        entity = self.semantic.get_entity(character_name)
        if not entity:
            return {"found": False, "name": character_name}

        events = self.episodic.get_events_by_participant(character_name, limit=20)
        relationships = self.semantic.get_character_relationships(character_name)

        return {
            "found": True,
            "name": entity.name,
            "type": entity.entity_type.value,
            "description": entity.description,
            "attributes": entity.attributes,
            "relationships": relationships,
            "aliases": entity.aliases,
            "status": entity.status,
            "first_appearance": entity.first_appearance,
            "last_appearance": entity.last_appearance,
            "appearance_count": entity.appearance_count,
            "recent_events": [
                {"chapter": e.chapter, "scene": e.scene, "summary": e.summary} for e in events[:10]
            ],
            "event_count": len(events),
        }

    def get_plot_recap(self, from_chapter: int = 1, to_chapter: int = 0) -> str:
        """获取情节回顾"""
        events = self.episodic.get_plot_timeline()
        if to_chapter > 0:
            events = [e for e in events if from_chapter <= e["chapter"] <= to_chapter]
        else:
            events = [e for e in events if e["chapter"] >= from_chapter]

        if not events:
            return "暂无情节记录"

        lines = ["【情节回顾】"]
        lines.extend(f"  第{e['chapter']}章 [{e['type']}]: {e['summary']}" for e in events)
        return "\n".join(lines)

    async def retrieve_for_writing(
        self,
        chapter_outline: dict[str, Any],
        present_characters: list[str],
    ) -> dict[str, Any]:
        """写作前记忆检索（整合L1角色状态+L2相关事件+L3世界观规则+L4模板建议）

        Args:
            chapter_outline: 章节大纲字典
            present_characters: 本章在场角色列表

        Returns:
            含 working_context, relevant_events, world_rules, patterns 的字典
        """
        # L1：角色状态
        character_states = [
            {"name": name, **self.working.character_states[name]}
            for name in present_characters
            if name in self.working.character_states
        ]
        # L1：增强上下文
        working_context = self.working.get_context_enhanced()

        # L2：相关事件（按角色和大纲关键词搜索）
        relevant_events: list[EpisodicEvent] = []
        outline_text = str(chapter_outline)
        for name in present_characters:
            events = self.episodic.get_events_by_participant(name, limit=5)
            relevant_events.extend(events)
        # 去重
        seen_ids: set[str] = set()
        unique_events: list[EpisodicEvent] = []
        for e in relevant_events:
            if e.id not in seen_ids:
                seen_ids.add(e.id)
                unique_events.append(e)
        # 如果摘要树启用，获取范围摘要
        range_summary = ""
        if self.episodic.summary_tree is not None:
            current_ch = chapter_outline.get("chapter", self.working.current_chapter)
            from_ch = max(1, current_ch - 5)
            range_summary = self.episodic.summary_tree.get_summary_for_range(
                from_ch, current_ch, max_level=2
            )

        # L3：世界观规则
        world_rules = self.semantic.get_world_facts()

        # L4：写作模板建议
        scene_type = chapter_outline.get("scene_type", "general")
        patterns = self.procedural.get_recommended_patterns(scene_type, limit=3)

        # L3-L4 增强：实体关系、场景模板、爽点、GraphRAG 上下文
        entity_relations: list[dict[str, Any]] = []
        recommended_templates: list[dict[str, Any]] = []
        pleasure_point_suggestions: list[dict[str, Any]] = []
        graph_context: dict[str, Any] = {}

        semantic_graph = getattr(self.semantic, "_relation_graph", None)
        template_lib = getattr(self.procedural, "_template_library", None)

        # 在场角色的关系列表
        if semantic_graph is not None:
            for name in present_characters:
                entity = self.semantic.get_entity(name)
                if entity:
                    rels = semantic_graph.get_relations(entity.id, direction="both")
                    for rel in rels:
                        rel_dict = rel.to_dict()
                        # 转换 ID 为名称
                        for ent in self.semantic.entities.values():
                            if ent.id == rel.source_id:
                                rel_dict["source_name"] = ent.name
                            if ent.id == rel.target_id:
                                rel_dict["target_name"] = ent.name
                        entity_relations.append(rel_dict)

        # 基于章节大纲 scene_type 推荐场景模板
        if template_lib is not None:
            rec_templates = template_lib.get_recommended_templates(
                scene_type, context_keywords=None, limit=3
            )
            recommended_templates = [t.to_dict() for t in rec_templates]
            # 爽点模式建议
            pp_suggestions = template_lib.get_pleasure_points(limit=5)
            pleasure_point_suggestions = [p.to_dict() for p in pp_suggestions]

        # GraphRAG 检索上下文（基于大纲关键词）
        if semantic_graph is not None:
            outline_summary = str(chapter_outline.get("summary", ""))
            outline_keywords = " ".join(present_characters) + " " + outline_summary
            graph_context = self.semantic.graphrag_search(outline_keywords, limit=5)

        return {
            "working_context": working_context,
            "character_states": character_states,
            "relevant_events": [
                {
                    "chapter": e.chapter,
                    "scene": e.scene,
                    "summary": e.summary,
                    "type": e.event_type,
                }
                for e in unique_events[:10]
            ],
            "range_summary": range_summary,
            "world_rules": [
                {"name": r.name, "description": r.description} for r in world_rules[:5]
            ],
            "patterns": [{"name": p.name, "description": p.description} for p in patterns],
            "foreshadow_alerts": self.working.foreshadow_alerts,
            # L3-L4 增强字段
            "entity_relations": entity_relations,
            "recommended_templates": recommended_templates,
            "pleasure_point_suggestions": pleasure_point_suggestions,
            "graph_context": graph_context,
        }

    # ── L3-L4 增强：便捷方法 ───────────────────────────

    def init_advanced_memory(self):
        """初始化 EntityRelationGraph 和 SceneTemplateLibrary 并绑定

        自动加载默认模板和爽点模式。
        """
        from kunlun.memory.entity_graph import EntityRelationGraph
        from kunlun.memory.scene_templates import SceneTemplateLibrary

        graph = EntityRelationGraph()
        self.semantic.set_relation_graph(graph)

        library = SceneTemplateLibrary()
        library.load_default_templates()
        library.load_default_pleasure_points()
        self.procedural.set_template_library(library)

    def add_character_relation(
        self,
        source_name: str,
        target_name: str,
        rel_type: str,
        attributes: dict[str, Any] | None = None,
        chapter: int = 0,
    ) -> Any | None:
        """便捷添加角色关系

        Args:
            source_name: 源角色名
            target_name: 目标角色名
            rel_type: 关系类型
            attributes: 关系属性
            chapter: 关系起始章节

        Returns:
            创建的关系对象
        """
        return self.semantic.add_entity_relation(
            source_name=source_name,
            target_name=target_name,
            rel_type=rel_type,
            attributes=attributes or {},
            valid_from_chapter=chapter,
        )

    def get_character_relation_network(self, name: str, depth: int = 2) -> dict[str, Any]:
        """获取角色关系网络

        Args:
            name: 角色名称
            depth: 网络扩展深度

        Returns:
            含 center, entities, relations, layers 的关系网络字典
        """
        return self.semantic.get_entity_neighborhood(name, depth=depth)

    def store_after_writing(
        self,
        chapter: int,
        text: str,
        summary: str = "",
    ) -> dict[str, Any]:
        """写作后记忆写入（自动提取事件+更新摘要树+巩固工作记忆）

        Args:
            chapter: 章节号
            text: 章节正文
            summary: 章节摘要

        Returns:
            含 extracted_events, consolidated_count 的字典
        """
        # 启用摘要树（如果未启用）
        if self.episodic.summary_tree is None:
            self.episodic.enable_summary_tree()

        # 自动提取事件并添加
        events = self.episodic.add_chapter_with_events(chapter, text, summary)

        # 更新工作记忆
        self.working.add_chapter(chapter, text, summary)
        self.working.set_current_chapter(chapter, summary)

        # 巩固工作记忆到情景记忆
        consolidated = self.working.consolidate_to_episodic()
        for event in consolidated:
            self.episodic.add_event(event)

        return {
            "extracted_events": len(events),
            "consolidated_count": len(consolidated),
            "chapter": chapter,
        }

    def get_enhanced_context(self) -> str:
        """获取增强上下文（调用 working.get_context_enhanced()）"""
        return self.working.get_context_enhanced()

    def _active_forgetting(self, current_chapter: int):
        """主动遗忘：压缩/丢弃旧的低重要度记忆"""
        # 工作记忆：自动保留最近N章（已在add_chapter中处理）

        # 情景记忆：压缩旧的低相关度事件（已在add_event中处理）

        # 语义记忆：标记长期未出现的实体
        for entity in self.semantic.entities.values():
            if entity.last_appearance < current_chapter - 50 and entity.importance.value <= 2:
                entity.status = "inactive"

    def _estimate_result_tokens(self, result: MemoryQueryResult) -> int:
        total = 0
        for item in result.working:
            total += len(item.content) // 2
        for event in result.episodic:
            total += len(event.summary) // 2 + 20
        for entity in result.semantic:
            total += len(entity.description) // 2 + len(entity.name) + 30
        for pattern in result.procedural:
            total += len(pattern.description) // 2 + 20
        return total

    def _truncate_to_budget(self, result: MemoryQueryResult, budget: int) -> MemoryQueryResult:
        """按优先级截断到Token预算内"""
        # 优先级：工作记忆 > 语义记忆 > 情景记忆 > 程序记忆
        current = 0
        truncated = MemoryQueryResult(token_budget=budget, truncated=True)

        for item in result.working:
            cost = len(item.content) // 2
            if current + cost <= budget:
                truncated.working.append(item)
                current += cost

        for entity in result.semantic:
            cost = len(entity.description) // 2 + 30
            if current + cost <= budget:
                truncated.semantic.append(entity)
                current += cost

        for event in result.episodic:
            cost = len(event.summary) // 2 + 20
            if current + cost <= budget:
                truncated.episodic.append(event)
                current += cost

        for pattern in result.procedural:
            cost = len(pattern.description) // 2 + 20
            if current + cost <= budget:
                truncated.procedural.append(pattern)
                current += cost

        truncated.total_tokens = current
        return truncated

    def save(self, filepath: str):
        """保存记忆到文件（完整保存四层记忆）"""
        data = {
            "book_id": self.book_id,
            "token_budget": self.token_budget,
            "working": self.working.to_dict(),
            "episodic": self.episodic.to_dict(),
            "semantic": self.semantic.to_dict(),
            "procedural": self.procedural.to_dict(),
            "forgetting_enabled": self.forgetting_enabled,
            "forgetting_check_interval": self.forgetting_check_interval,
            "last_forgetting_check": self.last_forgetting_check,
        }
        with Path(filepath).open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def load(self, filepath: str):
        """从文件加载记忆（完整加载四层记忆）"""
        from kunlun.memory.summary_tree import SummaryTree

        with Path(filepath).open(encoding="utf-8") as f:
            data = json.load(f)
        self.book_id = data.get("book_id", self.book_id)
        self.token_budget = data.get("token_budget", self.token_budget)
        self.forgetting_enabled = data.get("forgetting_enabled", True)
        self.forgetting_check_interval = data.get("forgetting_check_interval", 10)
        self.last_forgetting_check = data.get("last_forgetting_check", 0)

        # 加载工作记忆
        if "working" in data:
            wd = data["working"]
            self.working.max_chapters = wd.get("max_chapters", self.working.max_chapters)
            self.working.token_budget = wd.get("token_budget", self.working.token_budget)
            self.working.current_chapter = wd.get("current_chapter", 0)
            self.working.current_context = wd.get("current_context", "")
            self.working.recent_chapters = {
                int(k): v for k, v in wd.get("recent_chapters", {}).items()
            }
            self.working.recent_summaries = {
                int(k): v for k, v in wd.get("recent_summaries", {}).items()
            }
            self.working.temporary_notes = [
                MemoryItem.from_dict(n) for n in wd.get("temporary_notes", [])
            ]
            self.working.character_states = wd.get("character_states", {})
            self.working.foreshadow_alerts = wd.get("foreshadow_alerts", [])

        # 加载情景记忆
        if "episodic" in data:
            ed = data["episodic"]
            self.episodic.max_events = ed.get("max_events", self.episodic.max_events)
            self.episodic.events = []
            self.episodic.event_index = {}
            for edata in ed.get("events", []):
                event = EpisodicEvent.from_dict(edata)
                self.episodic.events.append(event)
                for p in event.participants:
                    self.episodic.event_index.setdefault(p, []).append(
                        len(self.episodic.events) - 1
                    )
                if event.location:
                    self.episodic.event_index.setdefault(event.location, []).append(
                        len(self.episodic.events) - 1
                    )
            if ed.get("summary_tree"):
                self.episodic.summary_tree = SummaryTree.from_dict(ed["summary_tree"])
            else:
                self.episodic.summary_tree = None

        # 加载语义记忆
        if "semantic" in data:
            self.semantic.entities = {}
            self.semantic.name_index = {}
            self.semantic.type_index = {}
            for eid, edata in data["semantic"].get("entities", {}).items():
                entity = SemanticEntity.from_dict(edata)
                self.semantic.entities[eid] = entity
                self.semantic.name_index[entity.name] = eid
                for alias in entity.aliases:
                    self.semantic.name_index[alias] = eid
                self.semantic.type_index.setdefault(entity.entity_type.value, []).append(eid)

        # 加载程序记忆
        if "procedural" in data:
            self.procedural.patterns = {}
            self.procedural.type_index = {}
            for pid, pdata in data["procedural"].get("patterns", {}).items():
                pattern = ProceduralPattern.from_dict(pdata)
                self.procedural.patterns[pid] = pattern
                self.procedural.type_index.setdefault(pattern.pattern_type, []).append(pid)


# ══════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════


def create_memory_manager(book_id: str = "default", token_budget: int = 6000) -> MemoryManager:
    return MemoryManager(book_id=book_id, token_budget=token_budget)


def extract_entities_from_text(text: str) -> list[dict[str, Any]]:
    """从文本中简单提取实体（人物/地点/物品）"""
    # 简单的人名提取（"XXX道"、"XXX说"模式）
    name_patterns = re.findall(r"([\u4e00-\u9fa5]{2,4})(?:道|说|喊|叫|问|答|笑|怒|叹)", text)
    return [
        {
            "name": name,
            "entity_type": "character",
            "description": f"在文本中出现的人物: {name}",
        }
        for name in set(name_patterns)
    ]

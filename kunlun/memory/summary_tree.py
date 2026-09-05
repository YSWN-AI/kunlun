"""
昆仑创作引擎 — 摘要树 (Summary Tree)

层级化摘要结构，为长篇小说提供从全书到场景的多级摘要检索。

层级定义:
  L0 — 全书摘要 (Book)
  L1 — 卷摘要 (Volume)，每 volume_size 章一卷
  L2 — 章摘要 (Chapter)
  L3 — 场景摘要 (Scene)

核心能力:
  - 自动挂载章节摘要到对应卷节点
  - 按范围聚合摘要（支持层级选择）
  - 从子节点重建全书摘要（拼接+压缩）
  - 完整序列化/反序列化

Author: 昆仑创作引擎
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SummaryTreeNode:
    """摘要树节点"""

    level: int  # 0=全书, 1=卷, 2=章, 3=场景
    title: str
    summary: str = ""
    chapter_range: tuple[int, int] | None = None
    children: list[SummaryTreeNode] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（递归）"""
        return {
            "level": self.level,
            "title": self.title,
            "summary": self.summary,
            "chapter_range": list(self.chapter_range) if self.chapter_range else None,
            "children": [c.to_dict() for c in self.children],
            "event_ids": self.event_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SummaryTreeNode:
        """从字典反序列化（递归）"""
        cr = data.get("chapter_range")
        chapter_range: tuple[int, int] | None = None
        if cr is not None and isinstance(cr, list) and len(cr) == 2:
            chapter_range = (int(cr[0]), int(cr[1]))
        node = cls(
            level=int(data["level"]),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            chapter_range=chapter_range,
            event_ids=list(data.get("event_ids", [])),
        )
        for child_data in data.get("children", []):
            node.children.append(cls.from_dict(child_data))
        return node


class SummaryTree:
    """摘要树 — 层级化小说摘要管理"""

    def __init__(self, volume_size: int = 50):
        self.volume_size = volume_size
        self.root = SummaryTreeNode(level=0, title="全书摘要")

    def _get_or_create_volume(self, volume_idx: int) -> SummaryTreeNode:
        """获取或创建卷节点（volume_idx 从0开始）"""
        # 查找已有卷节点
        for child in self.root.children:
            if child.chapter_range and child.chapter_range[0] == volume_idx * self.volume_size + 1:
                return child
        # 创建新卷节点
        start_ch = volume_idx * self.volume_size + 1
        end_ch = (volume_idx + 1) * self.volume_size
        volume = SummaryTreeNode(
            level=1,
            title=f"第{volume_idx + 1}卷",
            chapter_range=(start_ch, end_ch),
        )
        self.root.children.append(volume)
        # 按卷起始章排序
        self.root.children.sort(key=lambda n: n.chapter_range[0] if n.chapter_range else 0)
        return volume

    def _get_or_create_chapter(self, volume: SummaryTreeNode, chapter: int) -> SummaryTreeNode:
        """获取或创建章节点"""
        for child in volume.children:
            if child.chapter_range == (chapter, chapter):
                return child
        ch_node = SummaryTreeNode(
            level=2,
            title=f"第{chapter}章",
            chapter_range=(chapter, chapter),
        )
        volume.children.append(ch_node)
        volume.children.sort(key=lambda n: n.chapter_range[0] if n.chapter_range else 0)
        return ch_node

    def add_chapter_summary(
        self,
        chapter: int,
        summary: str,
        scene_summaries: list[dict] | None = None,
    ) -> None:
        """添加章节摘要，自动挂载到对应卷节点

        Args:
            chapter: 章节号（从1开始）
            summary: 章节摘要文本
            scene_summaries: 场景摘要列表，每个dict含 title/summary
        """
        volume_idx = (chapter - 1) // self.volume_size
        volume = self._get_or_create_volume(volume_idx)
        ch_node = self._get_or_create_chapter(volume, chapter)
        ch_node.summary = summary

        # 添加场景节点
        if scene_summaries:
            for idx, sc in enumerate(scene_summaries):
                scene_node = SummaryTreeNode(
                    level=3,
                    title=str(sc.get("title", f"场景{idx + 1}")),
                    summary=str(sc.get("summary", "")),
                    event_ids=list(sc.get("event_ids", [])),
                )
                ch_node.children.append(scene_node)

        # 更新卷摘要（拼接子章节摘要，截断）
        self._update_volume_summary(volume)
        # 更新全书摘要
        self.rebuild_book_summary()

    def _update_volume_summary(self, volume: SummaryTreeNode) -> None:
        """从子章节更新卷摘要"""
        chapter_summaries = [c.summary for c in volume.children if c.summary]
        if chapter_summaries:
            combined = "；".join(chapter_summaries)
            # 压缩：超过500字截断
            if len(combined) > 500:
                combined = combined[:500] + "..."
            volume.summary = combined

    def get_summary_for_range(
        self,
        from_ch: int,
        to_ch: int,
        max_level: int = 2,
    ) -> str:
        """获取指定范围的摘要（按层级聚合）

        Args:
            from_ch: 起始章
            to_ch: 结束章
            max_level: 最大聚合层级（2=章摘要, 1=卷摘要, 0=全书摘要）

        Returns:
            聚合后的摘要文本
        """
        parts: list[str] = []

        if max_level <= 0:
            return self.get_book_summary()

        if max_level == 1:
            # 用卷摘要
            for volume in self.root.children:
                if not volume.chapter_range:
                    continue
                v_start, v_end = volume.chapter_range
                if v_end >= from_ch and v_start <= to_ch and volume.summary:
                        parts.append(f"【{volume.title}】{volume.summary}")
        else:
            # 用章摘要（max_level >= 2）
            for volume in self.root.children:
                if not volume.chapter_range:
                    continue
                for ch_node in volume.children:
                    if not ch_node.chapter_range:
                        continue
                    ch_num = ch_node.chapter_range[0]
                    if from_ch <= ch_num <= to_ch and ch_node.summary:
                        parts.append(f"【第{ch_num}章】{ch_node.summary}")

        return "\n\n".join(parts) if parts else ""

    def get_book_summary(self) -> str:
        """全书摘要（L0）"""
        return self.root.summary

    def get_volume_summary(self, volume: int) -> str:
        """获取某卷摘要

        Args:
            volume: 卷号（从1开始）
        """
        volume_idx = volume - 1
        if 0 <= volume_idx < len(self.root.children):
            return self.root.children[volume_idx].summary
        return ""

    def rebuild_book_summary(self) -> None:
        """从子节点重建全书摘要（拼接+压缩）"""
        volume_summaries = [v.summary for v in self.root.children if v.summary]
        if not volume_summaries:
            self.root.summary = ""
            return
        combined = "\n".join(f"【{v.title}】{v.summary}" for v in self.root.children if v.summary)
        # 压缩：超过1000字截断
        if len(combined) > 1000:
            combined = combined[:1000] + "..."
        self.root.summary = combined

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "volume_size": self.volume_size,
            "root": self.root.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SummaryTree:
        """从字典反序列化"""
        tree = cls(volume_size=int(data.get("volume_size", 50)))
        if "root" in data:
            tree.root = SummaryTreeNode.from_dict(data["root"])
        return tree

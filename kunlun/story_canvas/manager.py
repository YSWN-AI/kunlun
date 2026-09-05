"""
昆仑创作引擎 — 故事画布管理器

提供故事画布的节点和连线管理，支持按故事线分组查看，数据持久化到 JSON 文件。

数据模型：
  CanvasNode  — 画布节点（故事线/伏笔/高潮/事件）
  CanvasEdge  — 画布连线（流程/伏笔/并行）
  StoryCanvas — 完整画布（节点列表 + 连线列表）

Usage:
    manager = StoryCanvasManager("mybook")
    node = manager.add_node({"type": "climax", "x": 100, "y": 200, "title": "大决战"})
    edge = manager.add_edge({"from_node": node.id, "to_node": "other_id", "label": "导致"})
    canvas = manager.get_canvas()
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger


class CanvasNode:
    """画布节点

    Attributes:
        id: 节点唯一标识
        type: 节点类型（storyline/foreshadow/climax/event）
        x: 画布 X 坐标
        y: 画布 Y 坐标
        title: 节点标题
        description: 节点描述
        color: 节点颜色
        volume: 所属卷
        chapter: 所属章节
    """

    VALID_TYPES = {"storyline", "foreshadow", "climax", "event"}

    def __init__(
        self,
        id: str = "",
        type: str = "event",
        x: float = 0.0,
        y: float = 0.0,
        title: str = "",
        description: str = "",
        color: str = "#4A90D9",
        volume: int = 0,
        chapter: int = 0,
    ) -> None:
        self.id = id or f"node_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        self.type = type if type in self.VALID_TYPES else "event"
        self.x = float(x)
        self.y = float(y)
        self.title = title
        self.description = description
        self.color = color
        self.volume = volume
        self.chapter = chapter

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "volume": self.volume,
            "chapter": self.chapter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanvasNode:
        """从字典反序列化"""
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "event"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            color=data.get("color", "#4A90D9"),
            volume=data.get("volume", 0),
            chapter=data.get("chapter", 0),
        )


class CanvasEdge:
    """画布连线

    Attributes:
        id: 连线唯一标识
        from_node: 起始节点 ID
        to_node: 目标节点 ID
        label: 连线标签
        type: 连线类型（flow/foreshadow/parallel）
    """

    VALID_TYPES = {"flow", "foreshadow", "parallel"}

    def __init__(
        self,
        id: str = "",
        from_node: str = "",
        to_node: str = "",
        label: str = "",
        type: str = "flow",
    ) -> None:
        self.id = id or f"edge_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        self.from_node = from_node
        self.to_node = to_node
        self.label = label
        self.type = type if type in self.VALID_TYPES else "flow"

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "label": self.label,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanvasEdge:
        """从字典反序列化"""
        return cls(
            id=data.get("id", ""),
            from_node=data.get("from_node", ""),
            to_node=data.get("to_node", ""),
            label=data.get("label", ""),
            type=data.get("type", "flow"),
        )


class StoryCanvas:
    """故事画布

    Attributes:
        id: 画布 ID
        book_id: 所属书籍 ID
        nodes: 节点列表
        edges: 连线列表
        updated_at: 最后更新时间
    """

    def __init__(
        self,
        id: str = "",
        book_id: str = "",
        nodes: list[CanvasNode] | None = None,
        edges: list[CanvasEdge] | None = None,
        updated_at: str = "",
    ) -> None:
        self.id = id or f"canvas_{uuid.uuid4().hex[:8]}"
        self.book_id = book_id
        self.nodes: list[CanvasNode] = nodes or []
        self.edges: list[CanvasEdge] = edges or []
        self.updated_at = updated_at or time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryCanvas:
        """从字典反序列化"""
        nodes = [CanvasNode.from_dict(n) for n in data.get("nodes", [])]
        edges = [CanvasEdge.from_dict(e) for e in data.get("edges", [])]
        return cls(
            id=data.get("id", ""),
            book_id=data.get("book_id", ""),
            nodes=nodes,
            edges=edges,
            updated_at=data.get("updated_at", ""),
        )


class StoryCanvasManager:
    """故事画布管理器

    管理指定书籍的故事画布，支持节点和连线的增删改查，
    数据持久化到 data/books/book_<id>/story_canvas.json。

    Usage:
        manager = StoryCanvasManager("mybook")
        canvas = manager.get_canvas()
    """

    def __init__(self, book_id: str, data_dir: str = "data") -> None:
        """初始化管理器

        Args:
            book_id: 书籍 ID
            data_dir: 数据根目录，默认 "data"
        """
        self.book_id = book_id
        self._data_dir = Path(data_dir) / "books" / f"book_{book_id}"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = self._data_dir / "story_canvas.json"
        self._canvas: StoryCanvas | None = None

    # ── 持久化 ────────────────────────────────────────

    def _load(self) -> StoryCanvas:
        """从磁盘加载画布"""
        if self._canvas is not None:
            return self._canvas

        if self._file_path.exists():
            try:
                with self._file_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                self._canvas = StoryCanvas.from_dict(data)
                self._canvas.book_id = self.book_id
                return self._canvas
            except (json.JSONDecodeError, OSError, KeyError, TypeError) as e:
                logger.warning(f"[StoryCanvas] 加载画布失败，创建新画布: {e}")

        self._canvas = StoryCanvas(book_id=self.book_id)
        return self._canvas

    def _save(self) -> bool:
        """保存画布到磁盘"""
        if self._canvas is None:
            return False
        self._canvas.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._file_path.open("w", encoding="utf-8") as f:
                json.dump(self._canvas.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except OSError as e:
            logger.error(f"[StoryCanvas] 保存画布失败: {e}")
            return False

    # ── 核心方法 ──────────────────────────────────────

    def get_canvas(self) -> StoryCanvas:
        """获取完整画布数据

        Returns:
            StoryCanvas 对象
        """
        return self._load()

    def add_node(self, node_data: dict[str, Any]) -> CanvasNode:
        """添加节点

        Args:
            node_data: 节点数据字典，可包含 type/x/y/title/description/color/volume/chapter

        Returns:
            创建的 CanvasNode 对象
        """
        canvas = self._load()
        node = CanvasNode(
            type=node_data.get("type", "event"),
            x=node_data.get("x", 0.0),
            y=node_data.get("y", 0.0),
            title=node_data.get("title", ""),
            description=node_data.get("description", ""),
            color=node_data.get("color", "#4A90D9"),
            volume=node_data.get("volume", 0),
            chapter=node_data.get("chapter", 0),
        )
        canvas.nodes.append(node)
        self._save()
        return node

    def update_node(self, node_id: str, updates: dict[str, Any]) -> CanvasNode | None:
        """更新节点

        Args:
            node_id: 节点 ID
            updates: 要更新的字段字典

        Returns:
            更新后的 CanvasNode，节点不存在时返回 None
        """
        canvas = self._load()
        for node in canvas.nodes:
            if node.id == node_id:
                if "type" in updates and updates["type"] in CanvasNode.VALID_TYPES:
                    node.type = updates["type"]
                if "x" in updates:
                    node.x = float(updates["x"])
                if "y" in updates:
                    node.y = float(updates["y"])
                if "title" in updates:
                    node.title = updates["title"]
                if "description" in updates:
                    node.description = updates["description"]
                if "color" in updates:
                    node.color = updates["color"]
                if "volume" in updates:
                    node.volume = int(updates["volume"])
                if "chapter" in updates:
                    node.chapter = int(updates["chapter"])
                self._save()
                return node
        return None

    def delete_node(self, node_id: str) -> bool:
        """删除节点（同时删除关联的连线）

        Args:
            node_id: 节点 ID

        Returns:
            是否删除成功
        """
        canvas = self._load()
        before = len(canvas.nodes)
        canvas.nodes = [n for n in canvas.nodes if n.id != node_id]
        if len(canvas.nodes) == before:
            return False
        # 级联删除关联连线
        canvas.edges = [e for e in canvas.edges if node_id not in (e.from_node, e.to_node)]
        self._save()
        return True

    def add_edge(self, edge_data: dict[str, Any]) -> CanvasEdge:
        """添加连线

        Args:
            edge_data: 连线数据字典，包含 from_node/to_node/label/type

        Returns:
            创建的 CanvasEdge 对象
        """
        canvas = self._load()
        edge = CanvasEdge(
            from_node=edge_data.get("from_node", ""),
            to_node=edge_data.get("to_node", ""),
            label=edge_data.get("label", ""),
            type=edge_data.get("type", "flow"),
        )
        canvas.edges.append(edge)
        self._save()
        return edge

    def delete_edge(self, edge_id: str) -> bool:
        """删除连线

        Args:
            edge_id: 连线 ID

        Returns:
            是否删除成功
        """
        canvas = self._load()
        before = len(canvas.edges)
        canvas.edges = [e for e in canvas.edges if e.id != edge_id]
        if len(canvas.edges) == before:
            return False
        self._save()
        return True

    def get_storylines(self) -> list[dict[str, Any]]:
        """按故事线分组节点

        Returns:
            故事线分组列表，每个分组包含故事线节点及其关联的事件节点
        """
        canvas = self._load()
        storyline_nodes = [n for n in canvas.nodes if n.type == "storyline"]
        result: list[dict[str, Any]] = []

        # 构建邻接表
        adjacency: dict[str, list[str]] = {}
        for edge in canvas.edges:
            adjacency.setdefault(edge.from_node, []).append(edge.to_node)
            adjacency.setdefault(edge.to_node, []).append(edge.from_node)

        for sl in storyline_nodes:
            # 收集与该故事线直接关联的节点
            related_ids = set(adjacency.get(sl.id, []))
            related_nodes = [n for n in canvas.nodes if n.id in related_ids]
            result.append(
                {
                    "storyline": sl.to_dict(),
                    "related_nodes": [n.to_dict() for n in related_nodes],
                    "related_count": len(related_nodes),
                }
            )

        # 如果没有故事线节点，按类型分组所有节点
        if not result:
            by_type: dict[str, list[dict[str, Any]]] = {}
            for n in canvas.nodes:
                by_type.setdefault(n.type, []).append(n.to_dict())
            for node_type, nodes in by_type.items():
                result.append(
                    {
                        "storyline": {
                            "id": f"group_{node_type}",
                            "type": node_type,
                            "title": f"{node_type}组",
                        },
                        "related_nodes": nodes,
                        "related_count": len(nodes),
                    }
                )

        return result

    def clear(self) -> bool:
        """清空画布（删除所有节点和连线）

        Returns:
            是否清空成功
        """
        canvas = self._load()
        canvas.nodes = []
        canvas.edges = []
        return self._save()

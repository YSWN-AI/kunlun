"""
昆仑创作引擎 — 故事画布模块

提供可视化故事结构管理，支持节点（故事线/伏笔/高潮/事件）和连线
（流程/伏笔/并行）的增删改查，数据持久化到 data/books/book_<id>/story_canvas.json。
"""

from kunlun.story_canvas.manager import CanvasEdge, CanvasNode, StoryCanvas, StoryCanvasManager

__all__ = [
    "CanvasEdge",
    "CanvasNode",
    "StoryCanvas",
    "StoryCanvasManager",
]

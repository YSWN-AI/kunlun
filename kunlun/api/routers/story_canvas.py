"""
昆仑创作引擎 — 故事画布 API 路由

前缀 /story-canvas，提供画布节点和连线的增删改查：
  GET    /story-canvas              — 获取画布数据
  POST   /story-canvas/nodes        — 添加节点
  PUT    /story-canvas/nodes/{id}   — 更新节点
  DELETE /story-canvas/nodes/{id}   — 删除节点
  POST   /story-canvas/edges        — 添加连线
  DELETE /story-canvas/edges/{id}   — 删除连线
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/story-canvas", tags=["故事画布"])


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------
class NodeCreateRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")
    type: str = Field(default="event", description="节点类型: storyline/foreshadow/climax/event")
    x: float = Field(default=0.0, description="X坐标")
    y: float = Field(default=0.0, description="Y坐标")
    title: str = Field(default="", description="节点标题")
    description: str = Field(default="", description="节点描述")
    color: str = Field(default="#4A90D9", description="节点颜色")
    volume: int = Field(default=0, description="所属卷")
    chapter: int = Field(default=0, description="所属章节")


class NodeUpdateRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")
    type: str | None = Field(default=None, description="节点类型")
    x: float | None = Field(default=None, description="X坐标")
    y: float | None = Field(default=None, description="Y坐标")
    title: str | None = Field(default=None, description="节点标题")
    description: str | None = Field(default=None, description="节点描述")
    color: str | None = Field(default=None, description="节点颜色")
    volume: int | None = Field(default=None, description="所属卷")
    chapter: int | None = Field(default=None, description="所属章节")


class EdgeCreateRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")
    from_node: str = Field(..., description="起始节点ID")
    to_node: str = Field(..., description="目标节点ID")
    label: str = Field(default="", description="连线标签")
    type: str = Field(default="flow", description="连线类型: flow/foreshadow/parallel")


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@router.get("", summary="获取画布数据")
async def get_canvas(book_id: str = "default") -> dict:
    """获取指定书籍的完整故事画布数据。"""
    try:
        from kunlun.story_canvas import StoryCanvasManager

        manager = StoryCanvasManager(book_id)
        canvas = manager.get_canvas()
        storylines = manager.get_storylines()
        return {
            "success": True,
            "canvas": canvas.to_dict(),
            "storylines": storylines,
        }
    except Exception as e:
        logger.error(f"[story-canvas] get 失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/nodes", summary="添加节点")
async def add_node(req: NodeCreateRequest) -> dict:
    """向故事画布添加一个节点。"""
    try:
        from kunlun.story_canvas import StoryCanvasManager

        manager = StoryCanvasManager(req.book_id)
        node = manager.add_node(
            {
                "type": req.type,
                "x": req.x,
                "y": req.y,
                "title": req.title,
                "description": req.description,
                "color": req.color,
                "volume": req.volume,
                "chapter": req.chapter,
            }
        )
        return {"success": True, "node": node.to_dict(), "id": node.id}
    except Exception as e:
        logger.error(f"[story-canvas] add_node 失败: {e}")
        return {"success": False, "error": str(e)}


@router.put("/nodes/{node_id}", summary="更新节点")
async def update_node(node_id: str, req: NodeUpdateRequest) -> dict:
    """更新画布中指定节点的属性。"""
    try:
        from kunlun.story_canvas import StoryCanvasManager

        manager = StoryCanvasManager(req.book_id)
        updates: dict[str, Any] = req.model_dump(exclude_unset=True, exclude={"book_id"})
        node = manager.update_node(node_id, updates)
        if node is None:
            return {"success": False, "error": "node not found"}
        return {"success": True, "node": node.to_dict()}
    except Exception as e:
        logger.error(f"[story-canvas] update_node 失败: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/nodes/{node_id}", summary="删除节点")
async def delete_node(node_id: str, book_id: str = "default") -> dict:
    """删除画布中指定节点（级联删除关联连线）。"""
    try:
        from kunlun.story_canvas import StoryCanvasManager

        manager = StoryCanvasManager(book_id)
        deleted = manager.delete_node(node_id)
        if not deleted:
            return {"success": False, "error": "node not found"}
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[story-canvas] delete_node 失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/edges", summary="添加连线")
async def add_edge(req: EdgeCreateRequest) -> dict:
    """向故事画布添加一条连线。"""
    try:
        from kunlun.story_canvas import StoryCanvasManager

        manager = StoryCanvasManager(req.book_id)
        edge = manager.add_edge(
            {
                "from_node": req.from_node,
                "to_node": req.to_node,
                "label": req.label,
                "type": req.type,
            }
        )
        return {"success": True, "edge": edge.to_dict(), "id": edge.id}
    except Exception as e:
        logger.error(f"[story-canvas] add_edge 失败: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/edges/{edge_id}", summary="删除连线")
async def delete_edge(edge_id: str, book_id: str = "default") -> dict:
    """删除画布中指定连线。"""
    try:
        from kunlun.story_canvas import StoryCanvasManager

        manager = StoryCanvasManager(book_id)
        deleted = manager.delete_edge(edge_id)
        if not deleted:
            return {"success": False, "error": "edge not found"}
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[story-canvas] delete_edge 失败: {e}")
        return {"success": False, "error": str(e)}

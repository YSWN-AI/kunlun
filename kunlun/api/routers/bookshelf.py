"""
昆仑创作引擎 — 书架作品管理 API 路由

/bookshelf/books              — 书籍列表（分组/排序/搜索）
/bookshelf/books/{book_id}    — 书籍详情
/bookshelf/groups             — 分组列表/创建分组
/bookshelf/groups/{group_id}  — 删除分组
/bookshelf/books/{book_id}/group — 移动书籍到分组
/bookshelf/recycle            — 回收站列表/移到回收站
/bookshelf/recycle/{book_id}/restore — 恢复
/bookshelf/recycle/{book_id}  — 永久删除
/bookshelf/books/{book_id}/quick-actions — 快速操作
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from kunlun.bookshelf.models import CreateGroupRequest, MoveToGroupRequest

router = APIRouter(prefix="/bookshelf", tags=["书架作品管理"])


@router.get("/books", summary="书籍列表（支持分组/排序/搜索）")
async def list_books_endpoint(
    group: str = Query(default="", description="分组ID筛选，留空表示全部"),
    sort_by: str = Query(
        default="last_modified",
        description="排序字段：last_modified/word_count/progress/title",
    ),
    search: str = Query(default="", description="关键词搜索（标题/题材）"),
) -> dict:
    """获取书架书籍列表，支持分组筛选、排序和关键词搜索。"""
    from kunlun.bookshelf.service import list_books

    books = list_books(
        group=group or None,
        sort_by=sort_by,
        search=search or None,
    )
    return {
        "success": True,
        "count": len(books),
        "books": [b.model_dump() for b in books],
    }


@router.get("/books/{book_id}", summary="书籍详情")
async def get_book_endpoint(book_id: str) -> dict:
    """获取单本书籍的详细信息。"""
    from kunlun.bookshelf.service import get_book

    book = get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"书籍不存在: {book_id}")
    return {"success": True, "book": book.model_dump()}


@router.get("/groups", summary="分组列表")
async def list_groups_endpoint() -> dict:
    """获取所有书架分组及其书籍数量。"""
    from kunlun.bookshelf.service import list_groups

    groups = list_groups()
    return {
        "success": True,
        "count": len(groups),
        "groups": [g.model_dump() for g in groups],
    }


@router.post("/groups", summary="创建分组")
async def create_group_endpoint(req: CreateGroupRequest) -> dict:
    """创建新的书架分组。"""
    from kunlun.bookshelf.service import create_group

    group_id = create_group(req.name)
    return {
        "success": True,
        "message": f"分组 '{req.name}' 创建成功",
        "group_id": group_id,
    }


@router.delete("/groups/{group_id}", summary="删除分组")
async def delete_group_endpoint(group_id: str) -> dict:
    """删除分组。分组内的书籍将移回默认分组。默认分组不可删除。"""
    if group_id == "default":
        raise HTTPException(status_code=400, detail="默认分组不可删除")

    from kunlun.bookshelf.service import delete_group

    deleted = delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"分组不存在: {group_id}")
    return {"success": True, "message": f"分组已删除: {group_id}"}


@router.put("/books/{book_id}/group", summary="移动书籍到分组")
async def move_to_group_endpoint(book_id: str, req: MoveToGroupRequest) -> dict:
    """将指定书籍移动到目标分组。"""
    from kunlun.bookshelf.service import move_to_group

    moved = move_to_group(book_id, req.group_id)
    if not moved:
        raise HTTPException(
            status_code=400,
            detail=f"移动失败：书籍或分组不存在 (book_id={book_id}, group_id={req.group_id})",
        )
    return {
        "success": True,
        "message": f"书籍已移动到分组: {req.group_id}",
    }


@router.get("/recycle", summary="回收站列表")
async def get_recycle_endpoint() -> dict:
    """获取回收站中的书籍列表。"""
    from kunlun.bookshelf.service import get_recycle_bin

    books = get_recycle_bin()
    return {
        "success": True,
        "count": len(books),
        "books": [b.model_dump() for b in books],
    }


@router.post("/recycle/{book_id}", summary="移到回收站")
async def move_to_recycle_endpoint(book_id: str) -> dict:
    """将书籍移到回收站（软删除，可恢复）。"""
    from kunlun.bookshelf.service import move_to_recycle

    moved = move_to_recycle(book_id)
    if not moved:
        raise HTTPException(status_code=404, detail=f"书籍不存在: {book_id}")
    return {"success": True, "message": f"书籍已移到回收站: {book_id}"}


@router.post("/recycle/{book_id}/restore", summary="从回收站恢复")
async def restore_from_recycle_endpoint(book_id: str) -> dict:
    """从回收站恢复书籍。"""
    from kunlun.bookshelf.service import restore_from_recycle

    restored = restore_from_recycle(book_id)
    if not restored:
        raise HTTPException(status_code=404, detail=f"书籍不在回收站中: {book_id}")
    return {"success": True, "message": f"书籍已从回收站恢复: {book_id}"}


@router.delete("/recycle/{book_id}", summary="永久删除")
async def permanently_delete_endpoint(book_id: str) -> dict:
    """
    永久删除书籍（不可逆操作）。
    会删除 data/books/{book_id}/ 整个目录及所有数据。
    """
    from kunlun.bookshelf.service import permanently_delete

    deleted = permanently_delete(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"书籍不存在: {book_id}")
    return {"success": True, "message": f"书籍已永久删除: {book_id}"}


@router.get("/books/{book_id}/quick-actions", summary="快速操作信息")
async def get_quick_actions_endpoint(book_id: str) -> dict:
    """获取书籍的快速操作信息（继续写作/查看大纲/质量报告/导出）。"""
    from kunlun.bookshelf.service import get_quick_actions

    actions = get_quick_actions(book_id)
    if actions is None:
        raise HTTPException(status_code=404, detail=f"书籍不存在: {book_id}")
    return {"success": True, "quick_actions": actions.model_dump()}

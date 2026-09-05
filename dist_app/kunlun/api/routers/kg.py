"""
昆仑创作引擎 —— 知识图谱路由
/kg/query, /kg/entities/{entity_type}, /kg/foreshadowing/overdue,
/books/{book_id}/snapshots/latest, /books/{book_id}/snapshots/{snapshot_id}
"""

import re as _re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from kunlun.config import settings
from kunlun.kg.client import kg_client

router = APIRouter(tags=["知识图谱", "快照"])


class KGQueryRequest(BaseModel):
    cypher: str = Field(..., description="Cypher查询语句")
    params: dict | None = Field(default=None, description="查询参数")


@router.post("/kg/query", summary="执行 Cypher 查询")
async def kg_query(req: KGQueryRequest) -> dict:
    """执行 Cypher 查询语句，支持 Neo4j 和 SQLite 图降级。"""
    cypher_stripped = req.cypher.strip()
    cypher_no_comments = _re.sub(r"/\*.*?\*/", "", cypher_stripped, flags=_re.DOTALL)
    cypher_no_comments = _re.sub(r"//[^\n]*", "", cypher_no_comments)
    cypher_normalized = _re.sub(r"\s+", " ", cypher_no_comments).strip()
    cypher_upper = cypher_normalized.upper()

    write_patterns = [
        r"\bCREATE\b",
        r"\bSET\b",
        r"\bDELETE\b",
        r"\bMERGE\b",
        r"\bREMOVE\b",
        r"\bDROP\b",
        r"\bDETACH\b",
        r"\bLOAD\b",
        r"\bFOREACH\b",
    ]
    if (
        any(_re.search(pat, cypher_upper) for pat in write_patterns)
        and settings.app_env != "development"
    ):
        raise HTTPException(status_code=403, detail="只允许只读查询（MATCH/RETURN/WHERE/ORDER BY）")
    if _re.search(r"\bCALL\b", cypher_upper) or "DB." in cypher_upper:
        raise HTTPException(status_code=403, detail="禁止执行存储过程或管理命令")

    for key, val in (req.params or {}).items():
        if isinstance(val, str) and len(val) > 0:
            val_upper = val.strip().upper()
            if any(
                val_upper.startswith(kw) for kw in ["CREATE ", "SET ", "DELETE ", "MERGE ", "DROP "]
            ):
                raise HTTPException(status_code=403, detail=f"参数 '{key}' 包含非法的 Cypher 语法")

    try:
        results = kg_client.query_cypher(cypher_stripped, req.params)
        return {"success": True, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/kg/entities/{entity_type}", summary="列出实体")
async def list_entities(
    entity_type: str,
    _book_id: str = Query(default="default", description="书籍ID"),
    limit: int = Query(default=50, le=200, description="返回上限"),
) -> dict:
    valid_types = [
        "character",
        "item",
        "skill",
        "location",
        "event",
        "foreshadowing",
        "organization",
    ]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效实体类型: {entity_type}")

    cypher = f"MATCH (e:{entity_type.capitalize()}) RETURN e LIMIT $limit"
    results = kg_client.query_cypher(cypher, {"limit": limit})
    return {"success": True, "count": len(results), "entities": results}


@router.get("/kg/foreshadowing/overdue", summary="逾期伏笔")
async def get_overdue_foreshadowing(
    _book_id: str = Query(default="default", description="书籍ID"),
    current_chapter: int = Query(default=0, description="当前章节编号"),
) -> dict:
    results = kg_client.query_cypher(
        """
        MATCH (f:Foreshadowing)
        WHERE f.book_id = $book_id AND f.status = 'planted' AND f.expectedRevealChapter <= $chapter
        RETURN f ORDER BY f.priority DESC
        """,
        {"book_id": _book_id, "chapter": current_chapter},
    )
    return {"success": True, "count": len(results), "overdue": results}


@router.get("/books/{book_id}/snapshots/latest", summary="最新快照")
async def get_latest_snapshot(book_id: str) -> dict:
    from kunlun.kg.snapshot import snapshot_manager

    snapshot = snapshot_manager.get_latest(book_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"未找到 {book_id} 的快照")
    return {
        "success": True,
        "data": {
            "snapshot_id": snapshot.snapshot_id,
            "book_id": snapshot.book_id,
            "chapter": snapshot.chapter,
            "entity_count": snapshot.entity_count,
            "relationship_count": snapshot.relationship_count,
            "summary": snapshot.to_summary(),
        },
    }


@router.get("/books/{book_id}/snapshots/{snapshot_id}", summary="获取快照")
async def get_snapshot(_book_id: str, snapshot_id: str) -> dict:
    from kunlun.kg.snapshot import snapshot_manager

    snapshot = snapshot_manager.get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"快照不存在: {snapshot_id}")
    return {"success": True, "data": snapshot.to_context_dict()}

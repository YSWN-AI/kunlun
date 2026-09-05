"""
昆仑创作引擎 — 作品管理路由
/books/create, /books/list, /books/{book_id},
/books/{book_id}/initialize, /books/{book_id}/chapters/{chapter}/content
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.api.security_middleware import validate_book_id, validate_chapter_number
from kunlun.config import settings
from kunlun.kg.client import kg_client

router = APIRouter(tags=["作品管理"])


class CreateBookRequest(BaseModel):
    book_id: str = Field(..., description="作品唯一ID")
    title: str = Field(..., description="作品名称")
    genre: str = Field(default="玄幻", description="题材")
    description: str = Field(default="", description="简介")
    tags: list[str] = Field(default_factory=list, description="标签")
    target_words: int = Field(default=500000, description="目标字数")


class BookInitializeRequest(BaseModel):
    baseline_params: dict = Field(default_factory=dict, description="各维度baseline参数")


@router.post("/books/create", summary="创建新作品")
async def create_book(req: CreateBookRequest) -> dict:
    """创建新作品：KG建节点 + 初始化真相文件 + 偏好学习器"""
    try:
        kg_client.query_cypher(
            """MERGE (b:Book {uid: $uid})
            SET b.title = $title, b.genre = $genre,
                b.description = $desc, b.tags = $tags,
                b.createdAt = datetime(), b.status = 'active'
            """,
            {
                "uid": req.book_id,
                "title": req.title,
                "genre": req.genre,
                "desc": req.description,
                "tags": ",".join(req.tags),
            },
        )
        try:
            from kunlun.truth import get_truth_manager

            get_truth_manager(req.book_id)
        except Exception as e:
            logger.debug(f"Truth 管理器初始化跳过: {e}")
        try:
            from kunlun.learn import get_learner

            get_learner(req.book_id)
        except Exception as e:
            logger.debug(f"Learner 初始化跳过: {e}")
        return {"success": True, "message": f"作品 '{req.title}' 创建成功", "book_id": req.book_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/books/list", summary="列出所有作品")
async def list_books() -> dict:
    """列出知识图谱中的所有作品"""
    try:
        results = kg_client.query_cypher(
            "MATCH (b:Book) RETURN b.uid AS uid, b.title AS title, "
            "b.genre AS genre, b.description AS description, "
            "b.status AS status, b.createdAt AS created_at ORDER BY b.createdAt DESC"
        )
        return {"success": True, "count": len(results), "books": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/books/{book_id}", summary="获取作品详情")
async def get_book(book_id: str) -> dict:
    """获取作品详情含统计"""
    try:
        books = kg_client.query_cypher(
            "MATCH (b:Book {uid: $uid}) RETURN b.title AS title, "
            "b.genre AS genre, b.description AS description, b.status AS status",
            {"uid": book_id},
        )
        if not books:
            raise HTTPException(status_code=404, detail=f"作品不存在: {book_id}")
        stats = kg_client.query_cypher(
            """MATCH (b:Book {uid:$uid})
            OPTIONAL MATCH (b)-[:HAS_CHAPTER]->(ch:Chapter)
            OPTIONAL MATCH (b)-[:HAS_CHARACTER]->(c:Character)
            RETURN count(DISTINCT ch) AS chapters, count(DISTINCT c) AS characters,
                   sum(ch.wordCount) AS total_words""",
            {"uid": book_id},
        )
        row = books[0]
        s = stats[0] if stats else {}
        return {
            "success": True,
            "book": {
                **row,
                "chapters": s.get("chapters", 0),
                "characters": s.get("characters", 0),
                "total_words": s.get("total_words", 0),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/books/{book_id}", summary="删除作品")
async def delete_book(book_id: str) -> dict:
    """删除作品及所有关联数据"""
    try:
        kg_client.query_cypher(
            """
            MATCH (b:Book {uid:$uid})
            OPTIONAL MATCH (b)-[r]-()
            OPTIONAL MATCH (ch:Chapter) WHERE ch.book_id = $uid
            OPTIONAL MATCH (c:Character) WHERE c.book_id = $uid
            OPTIONAL MATCH (f:Foreshadowing) WHERE f.book_id = $uid
            DELETE r, ch, c, f, b
            """,
            {"uid": book_id},
        )
        return {"success": True, "message": f"作品 {book_id} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/books/{book_id}/initialize", summary="开书全量推演(44维)")
async def initialize_book(book_id: str, req: BookInitializeRequest) -> dict:
    """
    执行一次44维全量社会推演，结果存入向量库。
    之后每章通过RAG召回，不再重复44维LLM调用。
    """
    try:
        from kunlun.agents.sociologist import sociologist

        results = await sociologist.full_deduce_for_book(book_id, req.baseline_params)
        return {
            "success": True,
            "message": f"推演完成: {len(results)}维",
            "dimensions": list(results.keys()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/books/{book_id}/chapters/{chapter}/content", summary="获取已发布章节内容")
async def get_chapter_content(book_id: str, chapter: int) -> dict:
    """获取已发布的章节正文和元数据"""
    book_id = validate_book_id(book_id)
    chapter = validate_chapter_number(chapter)
    try:
        rows = kg_client.query_cypher(
            "MATCH (ch:Chapter {uid:$uid}) RETURN ch.wordCount AS wc, ch.status AS st",
            {"uid": f"{book_id}_ch{chapter}"},
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"章节{chapter}未找到")
        try:
            base_dir = settings.get_book_safe_path(book_id, "published")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        path = base_dir / f"ch{chapter:04d}.txt"
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        return {
            "success": True,
            "chapter": chapter,
            "content": content,
            "word_count": rows[0].get("wc", 0),
            "status": rows[0].get("st", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

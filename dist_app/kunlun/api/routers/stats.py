"""
昆仑创作引擎 — 全书统计路由 (v2)
/books/{book_id}/stats: 综合统计面板（章节/角色/伏笔/爽点/审计）
"""

import asyncio

from fastapi import APIRouter

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/books", tags=["统计"])


# 辅助查询函数从 routes.py 延迟导入（避免重复代码）
def _query_chapter_stats(kg_client, book_id: str) -> dict:
    chapters = kg_client.query_cypher(
        """
        MATCH (ch:Chapter)
        WHERE ch.book_id = $book_id
        RETURN ch.chapterNumber AS num,
               ch.status AS status,
               ch.wordCount AS word_count,
               ch.writtenAt AS written_at
        ORDER BY ch.chapterNumber
        """,
        {"book_id": book_id},
    )
    return {
        "total": len(chapters),
        "written": sum(1 for c in chapters if c.get("status") == "written"),
        "planned": sum(1 for c in chapters if c.get("status") == "planned"),
        "total_words": sum(c.get("word_count", 0) for c in chapters),
        "list": chapters,
    }


def _query_character_stats(kg_client, book_id: str) -> dict:
    characters = kg_client.query_cypher(
        """
        MATCH (c:Character)
        WHERE c.book_id = $book_id
        OPTIONAL MATCH (c)-[r:APPEARS_IN]->(ch:Chapter)
        WITH c, count(r) AS appearance_count
        RETURN c.name AS name,
               c.type AS type,
               c.description AS description,
               appearance_count
        ORDER BY appearance_count DESC
        """,
        {"book_id": book_id},
    )
    return {
        "total": len(characters),
        "protagonist": sum(1 for c in characters if c.get("type") == "protagonist"),
        "supporting": sum(1 for c in characters if c.get("type") == "supporting"),
        "antagonist": sum(1 for c in characters if c.get("type") == "antagonist"),
        "unused": sum(1 for c in characters if c.get("appearance_count", 0) == 0),
        "top5": characters[:5],
    }


def _query_foreshadowing_stats(kg_client, book_id: str, written_chapters: int) -> dict:
    foreshadowing = kg_client.query_cypher(
        """
        MATCH (f:Foreshadowing)
        WHERE f.book_id = $book_id
        RETURN f.name AS name,
               f.status AS status,
               f.priority AS priority,
               f.expectedRevealChapter AS expected_chapter,
               f.revealedChapter AS revealed_chapter
        ORDER BY f.priority DESC
        """,
        {"book_id": book_id},
    )
    return {
        "total": len(foreshadowing),
        "resolved": sum(1 for f in foreshadowing if f.get("status") == "resolved"),
        "unresolved": sum(1 for f in foreshadowing if f.get("status") == "planted"),
        "overdue": sum(
            1
            for f in foreshadowing
            if f.get("status") == "planted" and f.get("expected_chapter", 999) < written_chapters
        ),
        "list": foreshadowing,
    }


def _query_pleasure_stats(kg_client, book_id: str) -> dict:
    pleasure_points = kg_client.query_cypher(
        """
        MATCH (pp:PleasurePoint)-[:BELONGS_TO]->(ch:Chapter)
        WHERE ch.book_id = $book_id
        RETURN pp.type AS type,
               pp.strength AS strength,
               ch.chapterNumber AS chapter
        ORDER BY ch.chapterNumber
        """,
        {"book_id": book_id},
    )
    by_chapter: dict[int, int] = {}
    for pp in pleasure_points:
        ch = pp.get("chapter", 0)
        by_chapter[ch] = by_chapter.get(ch, 0) + 1
    return {"total": len(pleasure_points), "by_chapter": by_chapter}


def _query_audit_summary() -> dict:
    try:
        from kunlun.audit.gates import AUDIT_GATES

        gate_names = [g.get("id", f"G{i + 1}") for i, g in enumerate(AUDIT_GATES)]
        gate_descs = [g.get("name", "") for g in AUDIT_GATES]
    except Exception:
        gate_names = [
            "G1_arc",
            "G2_info",
            "G3_ai",
            "G4_gap",
            "G5_diversity",
            "G6_emotion",
            "G7_dialogue",
            "G8_battle",
        ]
        gate_descs = ["弧线", "信息", "去AI", "爽点间隔", "爽点多样性", "情绪", "对话", "战斗"]
    return {
        "gates": gate_names,
        "description": f"{len(gate_names)}道审核关: {'/'.join(gate_descs)}",
    }


@router.get("/{book_id}/stats", summary="全书统计面板")
async def get_book_stats(book_id: str) -> dict:
    """获取书籍的综合统计面板：章节进度、角色分布、伏笔状态、爽点密度、审计摘要"""
    kg_client = cached_import("kunlun.kg.client", "kg_client")

    # 章节统计先算（伏笔依赖已写章数）
    chapters = _query_chapter_stats(kg_client, book_id)
    written = chapters["written"]

    # 并行执行3个独立查询
    characters, foreshadowing, pleasure_points = await asyncio.gather(
        asyncio.to_thread(_query_character_stats, kg_client, book_id),
        asyncio.to_thread(_query_foreshadowing_stats, kg_client, book_id, written),
        asyncio.to_thread(_query_pleasure_stats, kg_client, book_id),
    )
    audit_summary = _query_audit_summary()

    return {
        "success": True,
        "data": {
            "book_id": book_id,
            "chapters": chapters,
            "characters": characters,
            "foreshadowing": foreshadowing,
            "pleasure_points": pleasure_points,
            "audit_summary": audit_summary,
        },
    }

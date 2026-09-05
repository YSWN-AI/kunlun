# mypy: ignore-errors
"""
昆仑创作引擎 — 降AI工作台 API 路由
统一前缀 /api/v1/ai-workbench，提供12维度AI率分析、8种改写策略、
批量处理、前后对比、策略/维度元信息查询，以及章节级降AI处理。
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ai-workbench", tags=["降AI工作台"])


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="待分析文本")


class HumanizeRequest(BaseModel):
    text: str = Field(..., description="待改写文本")
    strategies: list[str] = Field(
        default_factory=lambda: ["replace_high_risk", "remove_redundancy"],
        description="改写策略列表，可选: replace_high_risk/remove_redundancy/"
        "restructure_sentence/diversify_dialogue/add_oral_expression/"
        "break_paragraph/inject_rhetoric/simplify_writing",
    )


class BatchRequest(BaseModel):
    texts: list[str] = Field(..., description="待批量处理的文本列表")
    strategies: list[str] = Field(
        default_factory=lambda: ["replace_high_risk", "remove_redundancy"],
        description="改写策略列表",
    )


class CompareRequest(BaseModel):
    original: str = Field(..., description="原始文本")
    rewritten: str = Field(..., description="改写后文本")


class ChapterHumanizeRequest(BaseModel):
    strategies: list[str] = Field(
        default_factory=lambda: [
            "replace_high_risk",
            "remove_redundancy",
            "restructure_sentence",
            "diversify_dialogue",
        ],
        description="改写策略列表",
    )
    save: bool = Field(default=False, description="是否将改写结果保存回章节")


# ---------------------------------------------------------------------------
# 辅助：将 Pydantic 模型转为 dict（处理嵌套模型）
# ---------------------------------------------------------------------------
def _model_to_dict(obj) -> dict:
    """递归将 Pydantic 模型转为可 JSON 序列化的 dict。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _model_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_model_to_dict(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# 1. 文本AI率分析
# ---------------------------------------------------------------------------
@router.post("/analyze", summary="12维度AI率分析")
async def analyze_endpoint(req: AnalyzeRequest) -> dict:
    """对文本进行12维度AI率分析，返回各维度得分、风险短语（带位置）、总体AI率。"""
    try:
        from kunlun.ai_rate.workbench import analyze_text

        result = analyze_text(req.text)
        return {"success": True, "result": _model_to_dict(result)}
    except Exception as e:
        logger.error(f"[ai-workbench] analyze 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 2. 按策略改写
# ---------------------------------------------------------------------------
@router.post("/humanize", summary="按策略改写降AI")
async def humanize_endpoint(req: HumanizeRequest) -> dict:
    """按指定策略列表改写文本，返回改写后文本、修改记录、AI率变化。"""
    try:
        from kunlun.ai_rate.workbench import humanize_with_strategy

        result = humanize_with_strategy(req.text, req.strategies)
        return {"success": True, "result": _model_to_dict(result)}
    except Exception as e:
        logger.error(f"[ai-workbench] humanize 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 3. 批量处理
# ---------------------------------------------------------------------------
@router.post("/batch", summary="批量降AI处理")
async def batch_endpoint(req: BatchRequest) -> dict:
    """批量处理多段文本，每段独立分析和改写。"""
    try:
        from kunlun.ai_rate.workbench import batch_process

        results = batch_process(req.texts, req.strategies)
        return {
            "success": True,
            "count": len(results),
            "results": [_model_to_dict(r) for r in results],
        }
    except Exception as e:
        logger.error(f"[ai-workbench] batch 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 4. 前后对比
# ---------------------------------------------------------------------------
@router.post("/compare", summary="改写前后对比")
async def compare_endpoint(req: CompareRequest) -> dict:
    """对比原文和改写文，返回差异高亮数据、AI率变化、各维度改善。"""
    try:
        from kunlun.ai_rate.workbench import compare_before_after

        result = compare_before_after(req.original, req.rewritten)
        return {"success": True, "result": _model_to_dict(result)}
    except Exception as e:
        logger.error(f"[ai-workbench] compare 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 5. 获取可用改写策略列表
# ---------------------------------------------------------------------------
@router.get("/strategies", summary="获取可用改写策略")
async def strategies_endpoint() -> dict:
    """获取8种可用改写策略的元信息（标识、名称、说明、分类）。"""
    try:
        from kunlun.ai_rate.workbench import get_strategies

        strategies = get_strategies()
        return {
            "success": True,
            "count": len(strategies),
            "strategies": [_model_to_dict(s) for s in strategies],
        }
    except Exception as e:
        logger.error(f"[ai-workbench] strategies 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 6. 获取12个分析维度说明
# ---------------------------------------------------------------------------
@router.get("/dimensions", summary="获取12个分析维度")
async def dimensions_endpoint() -> dict:
    """获取12个分析维度的元信息（标识、名称、说明、权重）。"""
    try:
        from kunlun.ai_rate.workbench import get_dimensions

        dimensions = get_dimensions()
        return {
            "success": True,
            "count": len(dimensions),
            "dimensions": [_model_to_dict(d) for d in dimensions],
        }
    except Exception as e:
        logger.error(f"[ai-workbench] dimensions 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 7. 对指定章节进行降AI
# ---------------------------------------------------------------------------
@router.post("/chapter/{book_id}/{chapter_id}", summary="章节级降AI处理")
async def chapter_humanize_endpoint(
    book_id: str,
    chapter_id: str,
    req: ChapterHumanizeRequest,
) -> dict:
    """读取指定章节内容→分析→改写→可选保存。

    章节内容从知识图谱(Neo4j)读取，节点uid格式为 {book_id}_ch{chapter_id}。
    """
    try:
        from kunlun.ai_rate.workbench import analyze_text, humanize_with_strategy
        from kunlun.config import settings

        # 校验 book_id
        try:
            settings.get_book_safe_path(book_id)
        except ValueError as e:
            return {"success": False, "error": f"book_id 不合法: {e}"}

        # 从 KG 读取章节内容
        try:
            from kunlun.kg.client import kg_client

            uid = f"{book_id}_ch{chapter_id}"
            rows = kg_client.query_cypher(
                """MATCH (ch:Chapter {uid: $uid})
                   RETURN ch.contentPreview AS content, ch.wordCount AS word_count,
                          ch.chapterNumber AS num, ch.title AS title""",
                {"uid": uid},
            )
        except Exception as kg_err:
            logger.warning(f"[ai-workbench] KG查询失败，尝试本地文件: {kg_err}")
            rows = []

        if not rows or not rows[0].get("content"):
            # 尝试从本地文件读取（兼容模式）
            content = _read_chapter_from_file(book_id, chapter_id)
            if not content:
                return {
                    "success": False,
                    "error": f"章节 {book_id}_ch{chapter_id} 未找到或内容为空",
                }
            chapter_title = f"第{chapter_id}章"
            word_count = len(content.replace(" ", "").replace("\n", ""))
        else:
            r = rows[0]
            content = r["content"]
            chapter_title = r.get("title", f"第{chapter_id}章")
            word_count = r.get("word_count", 0)

        # 分析
        analysis = analyze_text(content)

        # 改写
        humanize_result = humanize_with_strategy(content, req.strategies)

        result_data = {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "chapter_title": chapter_title,
            "word_count": word_count,
            "analysis": _model_to_dict(analysis),
            "humanize": _model_to_dict(humanize_result),
            "saved": False,
        }

        # 可选保存
        if req.save:
            saved = _save_chapter_content(book_id, chapter_id, humanize_result.rewritten_text)
            result_data["saved"] = saved
            if not saved:
                result_data["save_error"] = "保存失败，请检查KG连接或文件权限"

        return {"success": True, "result": result_data}
    except Exception as e:
        logger.error(f"[ai-workbench] chapter humanize 失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 章节文件读写辅助（兼容本地文件存储模式）
# ---------------------------------------------------------------------------
def _read_chapter_from_file(book_id: str, chapter_id: str) -> str:
    """从本地文件系统读取章节内容（兼容模式）。"""
    from pathlib import Path

    candidates = [
        Path("data/books") / f"book_{book_id}" / "chapters" / f"chapter_{chapter_id}.txt",
        Path("data/books") / f"book_{book_id}" / f"chapter_{chapter_id}.txt",
        Path("output") / book_id / f"第{chapter_id}章.txt",
    ]
    for path in candidates:
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                continue
    return ""


def _save_chapter_content(book_id: str, chapter_id: str, content: str) -> bool:
    """保存章节内容（优先KG，失败则本地文件）。"""
    # 尝试保存到 KG
    try:
        from kunlun.kg.client import kg_client

        uid = f"{book_id}_ch{chapter_id}"
        word_count = len(content.replace(" ", "").replace("\n", ""))
        kg_client.query_cypher(
            """MATCH (ch:Chapter {uid: $uid})
               SET ch.contentPreview = $content,
                   ch.wordCount = $word_count,
                   ch.updatedAt = datetime()""",
            {"uid": uid, "content": content, "word_count": word_count},
        )
        return True
    except Exception as kg_err:
        logger.warning(f"[ai-workbench] KG保存失败，尝试本地文件: {kg_err}")

    #  fallback 到本地文件
    try:
        from pathlib import Path

        save_dir = Path("data/books") / f"book_{book_id}" / "chapters"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"chapter_{chapter_id}.txt"
        save_path.write_text(content, encoding="utf-8")
        return True
    except Exception as file_err:
        logger.error(f"[ai-workbench] 本地文件保存也失败: {file_err}")
        return False

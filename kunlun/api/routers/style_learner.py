"""
昆仑创作引擎 — 爆款仿写四维度分析 API 路由

前缀 /style-learner，提供：
  POST /style-learner/analyze   — 对参考文本执行四维度分析
  GET  /style-learner/history    — 获取历史分析记录
  POST /style-learner/compare    — 多书对比提炼共性规律
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/style-learner", tags=["爆款仿写"])


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")
    reference_text: str = Field(..., description="参考文本")
    title: str = Field(default="未命名", description="书名/标题")
    dimensions: list[str] = Field(
        default_factory=lambda: ["setting", "plot", "style", "structure"],
        description="分析维度: setting/plot/style/structure",
    )


class CompareRequest(BaseModel):
    book_id: str = Field(default="default", description="书籍ID")
    analysis_ids: list[str] = Field(..., description="要对比的分析记录ID列表（最多3个）")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _analysis_dir(book_id: str) -> Path:
    path = Path("data/books") / f"book_{book_id}" / "style_analysis"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_analysis(book_id: str, analysis_id: str) -> dict[str, Any] | None:
    path = _analysis_dir(book_id) / f"{analysis_id}.json"
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@router.post("/analyze", summary="四维度仿写分析")
async def analyze_endpoint(req: AnalyzeRequest) -> dict:
    """对参考文本执行设定/情节/正文风格/结构四维度分析。"""
    try:
        from kunlun.style_learner import StyleLearner

        learner = StyleLearner()
        result = learner.analyze_book(
            title=req.title,
            text=req.reference_text,
            dimensions=req.dimensions,
            book_id=req.book_id,
        )
        return {"success": True, "analysis": result}
    except Exception as e:
        logger.error(f"[style-learner] analyze 失败: {e}")
        return {"success": False, "error": str(e)}


@router.get("/history", summary="历史分析记录")
async def history_endpoint(book_id: str = "default") -> dict:
    """获取指定书籍的历史风格分析记录列表。"""
    try:
        index_path = _analysis_dir(book_id) / "_index.json"
        if not index_path.exists():
            return {"success": True, "records": [], "total": 0}
        with index_path.open(encoding="utf-8") as f:
            records = json.load(f)
        # 按时间倒序
        records.sort(key=lambda r: r.get("analyzed_at", ""), reverse=True)
        return {"success": True, "records": records, "total": len(records)}
    except Exception as e:
        logger.error(f"[style-learner] history 失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/compare", summary="多书对比提炼共性")
async def compare_endpoint(req: CompareRequest) -> dict:
    """对最多3本参考书的分析结果进行对比，提炼共性规律（黄金公式）。"""
    try:
        from kunlun.style_learner import StyleLearner

        analyses: list[dict[str, Any]] = []
        for aid in req.analysis_ids[:3]:
            data = _load_analysis(req.book_id, aid)
            if data:
                analyses.append(data)
            else:
                logger.warning(f"[style-learner] 分析记录不存在: {aid}")

        if not analyses:
            return {"success": False, "error": "未找到有效的分析记录"}

        learner = StyleLearner()
        result = learner.extract_common_patterns(analyses)
        return {"success": True, "comparison": result}
    except Exception as e:
        logger.error(f"[style-learner] compare 失败: {e}")
        return {"success": False, "error": str(e)}

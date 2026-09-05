"""
Humanize API 路由 —— AI文本人性化（降AI率）

端点:
  POST /humanize          —— 执行人性化处理
  POST /humanize/detect   —— 检测AI痕迹
  POST /humanize/compare  —— 对比处理前后效果
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/humanize", tags=["humanize"])


class HumanizeRequest(BaseModel):
    text: str = Field(..., description="待处理文本", min_length=10)
    strategy: str = Field(
        default="standard",
        description="处理策略: none/minimal/standard/aggressive/opening",
        pattern="^(none|minimal|standard|aggressive|opening)$",
    )
    chapter_type: str = Field(
        default="normal",
        description="章节类型: normal/opening/climax/daily/fight",
    )
    auto_strategy: bool = Field(
        default=False,
        description="是否自动选择策略（基于AI检测结果）",
    )


class HumanizeResponse(BaseModel):
    success: bool = True
    original: str = ""
    humanized: str = ""
    strategy: str = ""
    fingerprint_before: dict = {}
    fingerprint_after: dict = {}
    ai_score_before: float = 0.0
    ai_score_after: float = 0.0
    reduction_pct: float = 0.0
    markers_before: int = 0
    markers_after: int = 0
    warnings: list[str] = []


class DetectRequest(BaseModel):
    text: str = Field(..., description="待检测文本", min_length=10)


class DetectResponse(BaseModel):
    success: bool = True
    ai_likelihood: float = 0.0
    risk_level: str = ""
    fingerprint: dict = {}
    markers: dict = {}
    needs_humanization: bool = False
    recommended_strategy: str = ""


class CompareRequest(BaseModel):
    original: str = Field(..., min_length=10)
    humanized: str = Field(..., min_length=10)


class CompareResponse(BaseModel):
    success: bool = True
    perplexity: dict = {}
    burstiness: dict = {}
    sentence_cv: dict = {}
    ai_likelihood: dict = {}


@router.post("", response_model=HumanizeResponse)
async def humanize_text(request: HumanizeRequest):
    """执行AI文本人性化处理"""
    try:
        from kunlun.humanize.engine import humanize_engine

        result = await humanize_engine.humanize(
            text=request.text,
            strategy=request.strategy,
            chapter_type=request.chapter_type,
            auto_strategy=request.auto_strategy,
        )

        return HumanizeResponse(
            success=True,
            original=result.original[:200] + "..."
            if len(result.original) > 200
            else result.original,
            humanized=result.humanized,
            strategy=result.strategy,
            fingerprint_before=result.fingerprint_before,
            fingerprint_after=result.fingerprint_after,
            ai_score_before=result.ai_score_before,
            ai_score_after=result.ai_score_after,
            reduction_pct=result.reduction_pct,
            markers_before=result.markers_before,
            markers_after=result.markers_after,
            warnings=result.warnings,
        )
    except Exception as e:
        logger.error(f"Humanize API 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/detect", response_model=DetectResponse)
async def detect_ai(request: DetectRequest):
    """检测文本的AI痕迹"""
    try:
        from kunlun.humanize.engine import anti_ai_detector

        result = anti_ai_detector.detect(request.text)

        return DetectResponse(
            success=True,
            ai_likelihood=result["ai_likelihood"],
            risk_level=result["risk_level"],
            fingerprint=result["fingerprint"],
            markers=result["markers"],
            needs_humanization=result["needs_humanization"],
            recommended_strategy=result["recommended_strategy"],
        )
    except Exception as e:
        logger.error(f"Humanize detect API 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/compare", response_model=CompareResponse)
async def compare_texts(request: CompareRequest):
    """对比处理前后效果"""
    try:
        from kunlun.humanize.fingerprint import text_fingerprint

        comparison = text_fingerprint.compare(request.original, request.humanized)

        return CompareResponse(
            success=True,
            perplexity=comparison["perplexity"],
            burstiness=comparison["burstiness"],
            sentence_cv=comparison["sentence_cv"],
            ai_likelihood=comparison["ai_likelihood"],
        )
    except Exception as e:
        logger.error(f"Humanize compare API 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

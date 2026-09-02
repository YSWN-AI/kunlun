"""
黄金三章路由 — /golden-triple/*

提供:
- GET  /golden-triple/archetypes     列出6种开篇原型
- POST /golden-triple/analyze        分析开篇钩子质量
- POST /golden-triple/generate-plan  生成黄金三章写作计划
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["黄金三章"])


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10, description="待分析的开篇文本")
    genre: str = Field(default="", description="题材（如都市/玄幻/悬疑）")
    chapter_number: int = Field(default=1, ge=1, le=3, description="章节号（1-3）")
    platform: str = Field(default="起点", description="目标平台")


class GeneratePlanRequest(BaseModel):
    archetype: str = Field(default="", description="开篇原型slug（为空则自动推荐）")
    genre: str = Field(default="", description="题材")
    theme: str = Field(default="", description="主题（热血/烧脑/爽文/轻松）")
    protagonist: str = Field(default="", description="主角简述")
    core_conflict: str = Field(default="", description="核心冲突简述")
    platform: str = Field(default="起点", description="目标平台")


@router.get("/golden-triple/archetypes", summary="列出所有开篇原型")
async def list_archetypes() -> dict:
    """返回6种开篇原型及其详细信息"""
    from kunlun.golden_triple.engine import golden_triple_engine

    archetypes = golden_triple_engine.list_archetypes()
    return {
        "success": True,
        "count": len(archetypes),
        "archetypes": archetypes,
        "hook_dimensions": {
            "conflict_intensity": "冲突强度 (权重0.25)",
            "information_gap": "信息差 (权重0.25)",
            "emotional_impact": "情绪冲击 (权重0.20)",
            "immersion": "代入感 (权重0.15)",
            "rhythm_score": "节奏感 (权重0.15)",
        },
    }


@router.post("/golden-triple/analyze", summary="分析开篇钩子质量")
async def analyze_opening(req: AnalyzeRequest) -> dict:
    """分析开篇文本的钩子质量 (0-100分)，5维纯文本统计"""
    from kunlun.golden_triple.engine import golden_triple_engine

    result = golden_triple_engine.analyze_opening(
        text=req.text,
        genre=req.genre,
        chapter_number=req.chapter_number,
    )

    return {
        "success": True,
        "hook_score": {
            "total": result.total,
            "level": result.level,
            "breakdown": {
                "conflict_intensity": result.conflict_intensity,
                "information_gap": result.information_gap,
                "emotional_impact": result.emotional_impact,
                "immersion": result.immersion,
                "rhythm_score": result.rhythm_score,
            },
        },
        "suggestions": result.suggestions,
        "text_length": len(req.text),
        "chapter_number": req.chapter_number,
    }


@router.post("/golden-triple/generate-plan", summary="生成黄金三章写作计划")
async def generate_plan(req: GeneratePlanRequest) -> dict:
    """生成黄金三章写作计划，含原型推荐、章节结构、钩子蓝图"""
    from kunlun.golden_triple.engine import golden_triple_engine

    gr = golden_triple_engine.generate_plan(
        archetype_slug=req.archetype,
        genre=req.genre,
        theme=req.theme,
        protagonist=req.protagonist,
        core_conflict=req.core_conflict,
        platform=req.platform,
    )

    if not gr.success or not gr.plan:
        return {"success": False, "error": gr.error or "计划生成失败"}

    plan = gr.plan

    return {
        "success": True,
        "plan": {
            "archetype": {
                "name": plan.archetype.name if plan.archetype else "",
                "slug": plan.archetype.slug if plan.archetype else "",
                "description": plan.archetype.description if plan.archetype else "",
            },
            "match_info": {
                "archetype_name": gr.archetype_match.archetype.name
                if gr.archetype_match and gr.archetype_match.archetype
                else "",
                "match_score": gr.archetype_match.match_score if gr.archetype_match else 0,
                "match_reason": gr.archetype_match.match_reason if gr.archetype_match else "",
                "alternatives": gr.archetype_match.alternative_archetypes
                if gr.archetype_match
                else [],
            },
            "chapters": plan.chapters,
            "estimated_words": plan.estimated_words,
            "hook_blueprint": plan.hook_blueprint,
            "core_conflict": plan.core_conflict,
            "protagonist_anchor": plan.protagonist_anchor,
            "specific_suggestions": plan.specific_suggestions,
            "genre_tips": plan.genre_tips,
        },
    }

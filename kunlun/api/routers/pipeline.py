"""
昆仑创作引擎 —— 全管线 API 路由

整合所有网文创作全生命周期模块的统一 API：
  - 世界观: /api/world/*
  - 角色: /api/character/*
  - 情节: /api/plot/*
  - 结构: /api/structure/*
  - 连贯性: /api/coherence/*
  - 审校: /api/proofread/*
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/pipeline", tags=["创作全管线"])


# ──────────────────────────────────────────────
# 请求/响应模型
# ──────────────────────────────────────────────


class WorldInitRequest(BaseModel):
    book_id: str = "default"
    genre: str = "xuanhuan"


class WorldSummaryResponse(BaseModel):
    genre: str
    atlas: dict
    factions: dict
    timeline: dict
    contradictions: dict


class CharacterRegisterRequest(BaseModel):
    character_id: str
    name: str
    role: str = "supporting"
    arc_type: str = "positive_change"
    personality: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)


class ChapterAnalysisRequest(BaseModel):
    text: str
    chapter_num: int = 1
    total_chapters: int = 100


class ProofreadRequest(BaseModel):
    text: str
    level: str = "standard"


class CoherenceCheckRequest(BaseModel):
    chapter_num: int = 1


# ──────────────────────────────────────────────
# 世界观路由
# ──────────────────────────────────────────────


@router.post("/world/init", summary="初始化世界观")
async def init_world(req: WorldInitRequest):
    try:
        from kunlun.worlds import create_world_builder

        builder = create_world_builder(book_id=req.book_id, genre=req.genre)
        return {"success": True, "summary": builder.get_full_world_summary()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/world/summary", summary="世界观摘要")
async def world_summary(book_id: str = "default", genre: str = "xuanhuan"):
    try:
        from kunlun.worlds import create_world_builder

        builder = create_world_builder(book_id=book_id, genre=genre)
        return builder.get_full_world_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/world/contradictions", summary="世界观矛盾检测")
async def world_contradictions(book_id: str = "default", genre: str = "xuanhuan"):
    try:
        from kunlun.worlds import create_world_builder

        builder = create_world_builder(book_id=book_id, genre=genre)
        return builder.auto_detect_contradictions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ──────────────────────────────────────────────
# 角色路由
# ──────────────────────────────────────────────


@router.post("/character/register", summary="注册角色")
async def register_character(req: CharacterRegisterRequest):
    try:
        from kunlun.character import (
            CharacterArcType,
            CharacterProfile,
            CharacterRole,
            character_engine,
        )

        profile = CharacterProfile(
            character_id=req.character_id,
            name=req.name,
            role=CharacterRole(req.role),
            arc_type=CharacterArcType(req.arc_type),
            personality=req.personality,
            abilities=req.abilities,
        )
        character_engine.register_character(profile)
        return {"success": True, "character_id": req.character_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/character/cast", summary="演员表")
async def character_cast():
    try:
        from kunlun.character import character_engine

        return character_engine.get_cast_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/character/{character_id}/arc", summary="角色弧线")
async def character_arc(character_id: str, chapter_num: int = 1, total_chapters: int = 100):
    try:
        from kunlun.character import character_engine

        profile = character_engine.get_character(character_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"角色 {character_id} 不存在")

        arc_info = character_engine.arc_engine.get_current_stage(
            profile.arc_type, chapter_num, total_chapters
        )
        return {"character": profile.name, **arc_info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/character/{character_id}/check", summary="角色一致性检查")
async def character_check(character_id: str, dialogue: str = "", narration: str = ""):
    try:
        from kunlun.character import character_engine

        return character_engine.consistency_checker.full_check(character_id, dialogue, narration)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ──────────────────────────────────────────────
# 情节路由
# ──────────────────────────────────────────────


@router.get("/plot/foreshadowing/stats", summary="伏笔统计")
async def foreshadowing_stats():
    try:
        from kunlun.plot import foreshadowing_manager

        return foreshadowing_manager.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/plot/foreshadowing/overdue", summary="过期伏笔检查")
async def foreshadowing_overdue(current_chapter: int = 1):
    try:
        from kunlun.plot import foreshadowing_manager

        overdue = foreshadowing_manager.check_overdue(current_chapter)
        return {
            "overdue_count": len(overdue),
            "items": [
                {"name": i.name, "planted_chapter": i.planted_chapter, "status": i.status.value}
                for i in overdue
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/plot/conflict/detect", summary="冲突检测")
async def conflict_detect(text: str):
    try:
        from kunlun.plot import conflict_engine

        scores = conflict_engine.detect_conflicts(text)
        has_conflict = conflict_engine.has_sufficient_conflict(text)
        primary = conflict_engine.get_primary_conflict(text)
        return {
            "scores": {k.value: round(v, 3) for k, v in scores.items()},
            "has_sufficient_conflict": has_conflict,
            "primary_conflict": primary.value if primary else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ──────────────────────────────────────────────
# 故事结构路由
# ──────────────────────────────────────────────


@router.post("/structure/analyze", summary="章节结构分析")
async def structure_analyze(req: ChapterAnalysisRequest):
    try:
        from kunlun.structure import structure_analyzer, tension_curve

        structure = structure_analyzer.analyze_chapter(
            req.text, req.chapter_num, req.total_chapters
        )
        tension = tension_curve.calculate_tension(req.text)
        next_beat = structure_analyzer.suggest_next_beat(req.chapter_num, req.total_chapters)

        return {
            "chapter_num": structure.chapter_num,
            "position_pct": structure.position_pct,
            "detected_beat": structure.detected_beat_stc.value
            if structure.detected_beat_stc
            else None,
            "expected_beat": structure.expected_beat_stc.value
            if structure.expected_beat_stc
            else None,
            "detected_hero_stage": structure.detected_stage_hero.value
            if structure.detected_stage_hero
            else None,
            "on_track": structure.on_track,
            "notes": structure.notes,
            "tension": tension.tension_score,
            "tension_is_flat": tension.is_flat,
            "next_beat_suggestion": next_beat,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/structure/health", summary="结构健康度")
async def structure_health():
    try:
        # 基础健康检查（无章节数据时）
        return {
            "status": "active",
            "supported_frameworks": [
                "Save the Cat 15节拍",
                "Hero's Journey 12阶段",
                "Dramatica 12故事要点",
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ──────────────────────────────────────────────
# 连贯性路由
# ──────────────────────────────────────────────


@router.get("/coherence/health", summary="连贯性健康报告")
async def coherence_health():
    try:
        from kunlun.coherence import coherence_engine

        return coherence_engine.get_health_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/coherence/check", summary="跨章节一致性检查")
async def coherence_check(chapter_a: int = 1, chapter_b: int = 5):
    try:
        from kunlun.coherence import coherence_engine

        issues = coherence_engine.check_cross_chapter_consistency(chapter_a, chapter_b)
        return {
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "description": i.description,
                    "entity": i.entity_name,
                }
                for i in issues
            ],
            "total": len(issues),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/coherence/context", summary="获取章节上下文")
async def coherence_context(chapter_num: int = 1):
    try:
        from kunlun.coherence import coherence_engine

        context = coherence_engine.build_chapter_context(chapter_num)
        return {"chapter_num": chapter_num, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ──────────────────────────────────────────────
# 审校路由
# ──────────────────────────────────────────────


@router.post("/proofread", summary="文本审校")
async def proofread_text(req: ProofreadRequest):
    try:
        from kunlun.proofread import proofread_engine

        report = proofread_engine.proofread(req.text, level=req.level)
        return {
            "score": report.score,
            "total_issues": report.total_issues,
            "by_category": report.by_category,
            "by_severity": report.by_severity,
            "summary": report.summary,
            "issues": [
                {
                    "category": i.category.value,
                    "severity": i.severity.value,
                    "message": i.message,
                    "suggestion": i.suggestion,
                    "original": i.original,
                }
                for i in report.issues[:20]  # 限制返回前20条
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/proofread/diff", summary="生成差异报告")
async def proofread_diff(original: str, corrected: str = ""):
    try:
        from kunlun.proofread import proofread_engine

        if not corrected:
            report = proofread_engine.proofread(original)
            corrected = report.corrected
        diff = proofread_engine.diff_reporter.generate_diff(original, corrected)
        return {
            "total_changes": diff.total_changes,
            "improvement_score": diff.improvement_score,
            "markdown_report": proofread_engine.diff_reporter.format_as_markdown(diff),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

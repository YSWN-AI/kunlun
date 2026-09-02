"""
昆仑创作引擎 — Vibe Writing 路由
/vibe/master, /vibe/master/status, /vibe/express, /vibe/write,
/vibe/refine, /vibe/suggest, /vibe/conversation
"""

from fastapi import APIRouter, Query

router = APIRouter(tags=["Vibe Writing"])

# ─── Vibe Writing 创作对话（单章级）───
_vibe_sessions: dict[str, dict] = {}


@router.post("/vibe/master", summary="Vibe总调度: 对AI说一句话")
async def vibe_master(text: str = Query(..., description="你的创作指令，一句话")) -> dict:
    """Vibe 总调度器入口

    你只需要说一句话，AI 自动判断你想做什么并执行。
    全流程覆盖：开书 → 世界观 → 角色 → 大纲 → 写作 → 修改 → 质量 → 导出
    """
    try:
        from kunlun.vibe_writer.orchestrator import get_orchestrator

        master = get_orchestrator()
        result = await master.say(text)
        return {
            "success": result.get("success", True),
            "message": result.get("message", ""),
            "project": result.get("project"),
            "has_project": master.has_project,
        }
    except Exception as e:
        return {"success": False, "message": f"出错了: {e!s}"}


@router.get("/vibe/master/status", summary="Vibe总调度: 查看状态")
async def vibe_master_status() -> dict:
    """查看总调度器的当前状态和项目进度"""
    from kunlun.vibe_writer.orchestrator import get_orchestrator

    master = get_orchestrator()
    status = master.get_status()
    return {"success": True, "status": status}


@router.post("/vibe/express", summary="Vibe Writing: 表达创作意图")
async def vibe_express(
    book_id: str = Query(..., description="作品ID"),
    intent: str = Query(..., description="你的创作意图，一句话"),
) -> dict:
    """Vibe Writing 第一步：表达你的创作意图"""
    try:
        from kunlun.vibe_writer import VibeWriter

        if book_id not in _vibe_sessions:
            _vibe_sessions[book_id] = {"writer": VibeWriter(book_id)}
        session = _vibe_sessions[book_id]
        writer: VibeWriter = session["writer"]

        parsed = await writer.express(intent)
        return {
            "success": True,
            "message": (
                f"理解了，你要写{parsed.emotion or '未知情感'}的"
                f"{parsed.scene_type or '场景'}"
            ),
            "parsed_intent": {
                "scene_type": parsed.scene_type,
                "emotion": parsed.emotion,
                "pace": parsed.pace,
                "intensity": parsed.intensity,
                "key_elements": parsed.key_elements,
            },
            "suggestions": ["直接生成", "调整后生成", "换个方向"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/vibe/write", summary="Vibe Writing: 让AI开始创作")
async def vibe_write(book_id: str = Query(..., description="作品ID")) -> dict:
    """Vibe Writing 第二步：AI 根据你的意图开始创作"""
    try:
        session = _vibe_sessions.get(book_id)
        if not session:
            return {"success": False, "error": "请先表达你的创作意图 (/vibe/express)"}
        writer = session["writer"]

        response = await writer.write()
        return {
            "success": True,
            "draft": response.draft,
            "feeling": response.feeling,
            "confidence": response.confidence,
            "alternatives": response.alternatives,
            "can_refine": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/vibe/refine", summary="Vibe Writing: 用感受调整创作")
async def vibe_refine(
    book_id: str = Query(..., description="作品ID"),
    feedback: str = Query(..., description="你的感受反馈"),
) -> dict:
    """Vibe Writing 第三步：用感受来调整"""
    try:
        session = _vibe_sessions.get(book_id)
        if not session:
            return {"success": False, "error": "请先表达你的创作意图 (/vibe/express)"}
        writer = session["writer"]

        response = await writer.refine(feedback)
        return {
            "success": True,
            "draft": response.draft,
            "feeling": response.feeling,
            "confidence": response.confidence,
            "applied_feedback": feedback,
            "alternatives": response.alternatives,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/vibe/suggest", summary="Vibe Writing: 让AI建议下一步")
async def vibe_suggest(book_id: str = Query(..., description="作品ID")) -> dict:
    """Vibe Writing: 让 AI 主动建议创作方向"""
    try:
        session = _vibe_sessions.get(book_id)
        if not session:
            return {"success": False, "error": "请先开始创作"}
        writer = session["writer"]
        suggestions = await writer.suggest_next()
        return {
            "success": True,
            "suggestions": suggestions,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/vibe/conversation", summary="Vibe Writing: 查看创作对话")
async def vibe_conversation(book_id: str = Query(..., description="作品ID")) -> dict:
    """查看你和AI的完整创作对话"""
    try:
        session = _vibe_sessions.get(book_id)
        if not session:
            return {"success": False, "error": "暂无创作对话"}
        writer = session["writer"]
        return {
            "success": True,
            "conversation": writer.get_conversation(),
            "summary": writer.summary(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

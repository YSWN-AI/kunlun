"""
昆仑创作引擎 — AI 对话路由
/chat, /editor/chat
"""

from fastapi import APIRouter, Request
from loguru import logger

from kunlun.api.routers._shared import (
    ChatRequest,
    EditorChatRequest,
    cached_import,
    check_chat_rate,
)

router = APIRouter(tags=["AI"])


@router.post("/chat", summary="AI 对话（轻量级，不走流水线）")
async def ai_chat(req: ChatRequest, request: Request) -> dict:
    """直接调用 LLM 对话，用于智能开书、AI辅助等交互场景"""
    # 限流保护
    client_ip = request.client.host if request.client else "unknown"
    if not check_chat_rate(client_ip):
        return {"success": False, "error": "请求频率过高，请稍后再试（每分钟20次）"}
    try:
        gacha_engine = cached_import("kunlun.gacha.engine", "gacha_engine")
        result = await gacha_engine.chat(
            messages=req.messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return {
            "success": True,
            "content": result.get("content", ""),
            "model": req.model,
            "usage": result.get("usage", {}),
        }
    except (TimeoutError, ConnectionError, OSError) as e:
        logger.error(f"AI 对话网络错误: {e}")
        return {"success": False, "error": f"网络错误: {e}"}
    except ValueError as e:
        logger.error(f"AI 对话参数错误: {e}")
        return {"success": False, "error": f"参数错误: {e}"}
    except Exception as e:
        logger.error(f"AI 对话未知错误: {e}")
        return {"success": False, "error": "内部服务错误"}


@router.post("/editor/chat", summary="主编对话（多Agent总调度）")
async def editor_chat_endpoint(req: EditorChatRequest, request: Request) -> dict:
    """
    与主编Agent对话，自动分配任务给7个专业Agent。
    支持：写章、规划大纲、设定世界观、设计角色、审计、文风仿写、续写。
    """
    client_ip = request.client.host if request.client else "unknown"
    if not check_chat_rate(client_ip):
        return {"success": False, "error": "请求频率过高，请稍后再试", "type": "error"}
    try:
        editor_chat = cached_import("kunlun.agents.editor", "editor_chat")
        return await editor_chat(req.book_id, req.message, req.context)
    except Exception as e:
        logger.error(f"主编对话失败: {e}")
        return {"success": False, "error": str(e), "type": "error"}

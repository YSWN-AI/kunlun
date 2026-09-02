"""
昆仑创作引擎 — 流式生成 + 扩展路由
/stream/generate, /api/orchestrate, /api/agents, /api/truth-status, /api/auto-fix
"""

import json
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from kunlun.api.rate_limit import get_limiter
from kunlun.api.routers._shared import cached_import
from kunlun.config import settings

router = APIRouter(tags=["流式", "扩展"])
_limiter = get_limiter()
_gen_rate_limit = (
    _limiter.limit(f"{settings.rate_limit_generate_per_minute}/minute") if _limiter else lambda f: f
)


@router.get("/stream/generate", summary="流式生成章节(SSE)")
@_gen_rate_limit
async def stream_generate(
    book_id: str,
    chapter: int,
    request: Request = None,
    prompt: str = "",
    mode: str = "single_fix",
    agent: str = "writer",
):
    """SSE流式生成，前端用EventSource接收"""
    from kunlun.api.streaming import streaming_generator

    return StreamingResponse(
        streaming_generator.stream_generate(book_id, chapter, prompt, mode, agent),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/orchestrate", summary="编排Agent执行")
async def orchestrate(request: dict):
    """接收前端意图，返回 Agent 执行计划。"""
    from kunlun.agents.message_bus import InProcessMessageBus

    bus = InProcessMessageBus()
    available = bus.list_agents() if hasattr(bus, "list_agents") else []
    intent = request.get("intent", "")
    if not intent:
        return {"success": False, "error": "缺少 intent 参数"}

    gacha_engine = cached_import("kunlun.gacha.engine", "gacha_engine")
    plan_prompt = f"""可用 Agent: {available}
用户需求: {intent}
输出 JSON 格式执行计划: {{"steps": [{{"agent": "agent_name", "input": "子任务"}}]}}"""

    try:
        result = await gacha_engine.generate(plan_prompt, mode="single_fix")
        plan_text = result.get("best_text", "")
        json_match = re.search(r"\{.*\}", plan_text, re.DOTALL)
        plan = json.loads(json_match.group()) if json_match else {"steps": []}
    except Exception as e:
        return {"success": False, "error": f"生成执行计划失败: {e}"}

    return {"success": True, "plan": plan}


@router.get("/agents", summary="列出所有已注册 Agent")
async def list_agents():
    """返回所有已注册 Agent 及其能力描述"""
    from kunlun.agents.message_bus import InProcessMessageBus

    bus = InProcessMessageBus()
    agents = []
    if hasattr(bus, "describe_agents"):
        agents = bus.describe_agents()
    else:
        agents = [
            {"name": "architect", "description": "章节蓝图生成"},
            {"name": "writer", "description": "正文生成（多模型抽卡）"},
            {"name": "auditor", "description": "8门禁质量审计"},
            {"name": "sociologist", "description": "社会深层推演"},
            {"name": "style_engineer", "description": "去 AI 味润色"},
            {"name": "publisher", "description": "章节发布"},
        ]
    return {"agents": agents}


@router.get("/truth-status", summary="真相文件系统状态")
async def truth_status(book_id: str = "default"):
    """返回真相文件系统当前快照"""
    try:
        from kunlun.truth import get_truth_manager

        tm = get_truth_manager(book_id)
        return {
            "success": True,
            "files": list(tm.files.keys()) if hasattr(tm, "files") else [],
            "consistency_report": tm.get_consistency_report(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/auto-fix", summary="自动修复 Python 语法错误")
async def auto_fix_endpoint(request: Request):
    """扫描项目 Python 代码并自动修复语法错误"""
    if request.client and request.client.host not in ("127.0.0.1", "localhost", "::1"):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "仅允许本地访问"},
        )
    from kunlun.auto_fix import auto_fix

    result = auto_fix()
    return {"success": True, "report": result}

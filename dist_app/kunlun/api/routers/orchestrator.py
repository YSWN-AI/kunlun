"""
交互式创作系统 — API 端点

提供自然语言驱动的创作能力，支持：
- 自然语言输入创作需求
- 实时进度追踪
- 人工干预与确认
- 端到端创作流程
"""

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from kunlun.vibe_writer.orchestrator import get_orchestrator

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_master: object | None = None


class CreateRequest(BaseModel):
    """创作请求"""

    instruction: str
    book_id: str | None = None
    auto_approve: bool = False


class OrchestratorResponse(BaseModel):
    """创作响应"""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    task_id: str | None = None


class TaskProgress(BaseModel):
    """任务进度"""

    task_id: str
    subtask_name: str
    status: str
    progress: int
    message: str


class ApprovalRequest(BaseModel):
    """审批请求"""

    task_id: str
    subtask_id: str
    approved: bool
    comment: str | None = None


# 存储活跃的WebSocket连接
active_connections: list[WebSocket] = []


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """实时进度推送 WebSocket"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket message from {client_id}: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_progress(task_id: str, message: str):
    """广播进度消息"""
    from contextlib import suppress

    for connection in active_connections:
        with suppress(Exception):
            await connection.send_text(f"{task_id}: {message}")


@router.post("/say", response_model=OrchestratorResponse)
async def handle_natural_language(request: CreateRequest):
    """
    自然语言创作接口

    用户用自然语言表达创作需求，系统自动理解并执行。

    示例:
    - "我想写一本玄幻小说，主角从废柴开始逆袭" → 开书
    - "构建一个东方玄幻世界观" → 世界观设定
    - "设计三个主要角色" → 角色设计
    - "写第一章，主角获得奇遇" → 章节创作
    - "让节奏更快一些" → 修改调整
    - "检查质量" → 质量审计
    - "导出为EPUB" → 导出
    - "这本书怎么样了" → 状态查询
    """
    logger.info(f"[Orchestrator] 用户指令: {request.instruction}")

    orchestrator = get_orchestrator()
    result = await orchestrator.say(request.instruction)

    return OrchestratorResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        data=result,
    )


@router.post("/execute-chapter", response_model=OrchestratorResponse)
async def execute_chapter_generation(
    book_id: str,
    chapter: int,
    mode: str = "gacha_parallel_3",
    chapter_type: str = "normal",
    auto_approve: bool = False,
):
    """
    执行章节生成任务

    完整的章节创作流水线:
    1. KG快照拍摄
    2. 社会推演 + Architect蓝图 (并行)
    3. Writer多模型抽卡
    4. 8门禁审计
    5. 去AI味润色
    6. 知识图谱更新
    7. 章节发布
    """
    logger.info(f"[Orchestrator] 开始生成章节: {book_id} 第{chapter}章")

    # 延迟导入重型依赖（kunlun.agents ~970ms），仅在实际执行时加载
    from kunlun.agents.scheduler import TaskDecomposer, TaskPlan, scheduler

    # 分解任务
    plan = TaskDecomposer.decompose_chapter_generation(book_id, chapter, mode, chapter_type)

    # 注册进度回调
    async def progress_callback(task_plan: TaskPlan, msg: str):
        await broadcast_progress(task_plan.task_id, msg)
        logger.info(f"[Scheduler] {msg}")

    scheduler.on_progress(progress_callback)

    # 执行任务
    result = await scheduler.execute_plan(
        plan,
        {
            "book_id": book_id,
            "chapter": chapter,
            "chapter_type": chapter_type,
        },
        auto_approve=auto_approve,
    )

    success = result.get("success", False)
    message = "章节生成完成" if success else "章节生成失败"

    return OrchestratorResponse(
        success=success,
        message=message,
        data=result,
        task_id=plan.task_id,
    )


@router.post("/approve", response_model=OrchestratorResponse)
async def approve_subtask(request: ApprovalRequest):
    """
    人工审批子任务

    当子任务设置了 human_approval_required=True 时，
    需要调用此接口进行人工确认后才能继续执行。
    """
    logger.info(
        f"[Orchestrator] 审批: {request.task_id} - {request.subtask_id} - "
        f"{'通过' if request.approved else '拒绝'}"
    )

    # 在实际实现中，这里需要与调度器集成
    # 暂时返回成功
    return OrchestratorResponse(
        success=True, message=f"子任务已{'通过' if request.approved else '拒绝'}"
    )


@router.get("/status")
async def get_status():
    """获取创作系统状态"""
    orchestrator = get_orchestrator()
    return orchestrator.get_status()


@router.get("/conversation")
async def get_conversation():
    """获取创作对话历史"""
    orchestrator = get_orchestrator()
    return orchestrator.get_conversation()


@router.post("/reset")
async def reset_orchestrator():
    """重置创作系统"""
    global _master  # noqa: PLW0603
    _master = None
    return {"success": True, "message": "创作系统已重置"}

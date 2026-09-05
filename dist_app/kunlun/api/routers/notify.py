"""
昆仑创作引擎 — 统一通知路由 (v2)
4通道并行 + 飞书卡片

端点:
  GET  /notify/channels — 通知渠道状态
  POST /notify/send     — 发送测试通知
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/notify", tags=["通知"])


class SendNotifyRequest(BaseModel):
    channel: str = Field(..., description="渠道: log/feishu/email/sms")
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    level: str = Field(default="info", description="级别: info/warning/error")


@router.get("/channels")
async def notify_channels():
    """获取通知渠道状态"""
    notify = cached_import("kunlun.notify", "Notifier")
    return {"success": True, "data": notify.get_channels()}


@router.post("/send")
async def send_notify(req: SendNotifyRequest):
    """发送测试通知"""
    notify = cached_import("kunlun.notify", "Notifier")
    result = notify.send(req.channel, req.title, req.content, req.level)
    return {"success": True, "data": result}

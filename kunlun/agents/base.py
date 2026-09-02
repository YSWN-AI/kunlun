"""
昆仑创作引擎 — Agent 基类
所有 Agent 继承此基类，统一消息格式和生命周期
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from loguru import logger

from kunlun.agents.message_bus import message_bus


class AgentStatus(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Agent 间消息格式"""

    msg_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    from_agent: str = ""
    to_agent: str = ""
    msg_type: str = ""  # BLUEPRINT_READY, AUDIT_RESULT, 等
    payload: dict = field(default_factory=dict)
    correlation_id: str = ""  # 关联任务ID
    kg_snapshot_id: str = ""  # KG快照ID (如有)
    timestamp: float = field(default_factory=time.monotonic)


class BaseAgent(ABC):
    """
    Agent 基类

    每个 Agent:
    - 有唯一名称 (agent_name)
    - 有明确的能力边界声明 (capabilities)
    - 通过 post_message 发送消息到消息总线
    - 通过 on_message 接收消息
    - 有状态 (status)
    """

    agent_name: str = "base"
    capabilities: ClassVar[list[str]] = []

    def __init__(self, nats_client=None):
        self.status = AgentStatus.IDLE
        self._nats = nats_client
        self._nats_provided = nats_client is not None
        self._bus_subscribed = False
        self._message_bus = message_bus

    async def _ensure_nats_connected(self) -> bool:
        """检查真实 NATS 是否可用。不可用时返回 False，不创建 MockNATS。"""
        if not self._nats_provided:
            return False
        if hasattr(self._nats, "is_connected") and not self._nats.is_connected:
            try:
                await self._nats.connect()
            except Exception as e:
                logger.warning(f"[{self.agent_name}] NATS连接失败: {e}")
                return False
        return self._nats is not None

    async def _ensure_bus_subscribed(self):
        """确保已订阅进程内消息总线（惰性订阅，首次 post_message 时触发）"""
        if not self._bus_subscribed:
            await self._message_bus.subscribe(
                f"kunlun.agent.{self.agent_name}",
                self._handle_bus_message,
            )
            self._bus_subscribed = True
            logger.debug(f"{self.agent_name}: 已订阅进程内消息总线")

    async def _handle_bus_message(self, data: dict):
        """处理来自进程内消息总线的消息 → 调用 on_message → 转发响应"""
        msg = AgentMessage(**data)
        response = await self.on_message(msg)
        if response and response.to_agent:
            await self.post_message(
                response.to_agent,
                response.msg_type,
                response.payload,
                correlation_id=response.correlation_id,
                kg_snapshot_id=response.kg_snapshot_id,
            )

    async def post_message(
        self,
        to: str,
        msg_type: str,
        payload: dict,
        correlation_id: str = "",
        kg_snapshot_id: str = "",
    ) -> None:
        """发送消息到另一个 Agent。优先 NATS（真实），回退进程内消息总线。"""
        msg = AgentMessage(
            from_agent=self.agent_name,
            to_agent=to,
            msg_type=msg_type,
            payload=payload,
            correlation_id=correlation_id,
            kg_snapshot_id=kg_snapshot_id,
        )

        if await self._ensure_nats_connected():
            subject = f"kunlun.agent.{to}"
            await self._nats.publish(subject, msg.__dict__)
        else:
            await self._ensure_bus_subscribed()
            await self._message_bus.publish(f"kunlun.agent.{to}", msg.__dict__)

    @abstractmethod
    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        """处理接收到的消息，返回响应消息（如有）"""
        ...

    @abstractmethod
    async def execute(self, task: dict) -> dict:
        """执行任务的主要入口。返回执行结果。"""
        ...

    def health_check(self) -> dict:
        return {"agent": self.agent_name, "status": self.status.value}

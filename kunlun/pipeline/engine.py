"""
pipeline 流水线引擎 — 多节点串联+状态管理+人工干预

核心能力:
1. 定义流水线节点（DAG拓扑）
2. 节点状态追踪（等待/运行/成功/失败/跳过）
3. 人工干预点（暂停-审核-继续/修改-重新运行）
4. 流水线整体状态管理
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule


class NodeStatus(Enum):
    """节点状态"""

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    SKIPPED = "skipped"  # 已跳过
    INTERVENTION = "intervention"  # 需要人工干预


@dataclass
class PipelineNode:
    """流水线节点"""

    node_id: str
    name: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)  # 依赖的前置节点ID
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    retries: int = 0
    max_retries: int = 3

    @property
    def duration(self) -> float:
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return 0.0

    def can_run(self, all_nodes: dict[str, PipelineNode]) -> bool:
        """检查依赖是否满足"""
        for dep_id in self.depends_on:
            dep = all_nodes.get(dep_id)
            if not dep or dep.status != NodeStatus.SUCCESS:
                return False
        return True

    def reset(self):
        """重置节点状态"""
        self.status = NodeStatus.PENDING
        self.result = None
        self.error = ""
        self.started_at = 0.0
        self.finished_at = 0.0


@dataclass
class PipelineState:
    """流水线状态"""

    pipeline_id: str
    name: str
    nodes: list[PipelineNode] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    created_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    @property
    def total_nodes(self) -> int:
        return len(self.nodes)

    @property
    def completed_nodes(self) -> int:
        return sum(1 for n in self.nodes if n.status == NodeStatus.SUCCESS)

    @property
    def failed_nodes(self) -> int:
        return sum(1 for n in self.nodes if n.status == NodeStatus.FAILED)

    @property
    def progress(self) -> float:
        if not self.nodes:
            return 0.0
        completed = self.completed_nodes + self.failed_nodes
        return completed / len(self.nodes)

    def summary(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "status": self.status.value,
            "progress": f"{self.progress:.0%}",
            "total": self.total_nodes,
            "completed": self.completed_nodes,
            "failed": self.failed_nodes,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "name": n.name,
                    "status": n.status.value,
                    "duration": f"{n.duration:.1f}s" if n.duration else "-",
                    "error": n.error[:100] if n.error else "",
                }
                for n in self.nodes
            ],
        }


@dataclass
class InterventionAction:
    """人工干预动作"""

    action_id: str
    pipeline_id: str
    node_id: str
    action_type: str  # approve / reject / modify / skip / retry
    comment: str = ""
    modified_input: Any = None
    timestamp: float = field(default_factory=time.time)


class PipelineInterventionManager(BaseExtensionModule):
    """流水线干预管理器"""

    SUBDIR = "pipeline"

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._interventions: dict[str, list[InterventionAction]] = {}

    def request_intervention(
        self, pipeline_id: str, node_id: str, reason: str
    ) -> InterventionAction:
        """请求人工干预"""
        action = InterventionAction(
            action_id=f"int_{pipeline_id}_{node_id}_{int(time.time())}",
            pipeline_id=pipeline_id,
            node_id=node_id,
            action_type="pending",
            comment=reason,
        )
        if pipeline_id not in self._interventions:
            self._interventions[pipeline_id] = []
        self._interventions[pipeline_id].append(action)
        logger.info(f"请求人工干预: {pipeline_id}/{node_id} — {reason}")
        return action

    def approve(self, action_id: str) -> bool:
        """批准干预"""
        for actions in self._interventions.values():
            for a in actions:
                if a.action_id == action_id:
                    a.action_type = "approve"
                    a.timestamp = time.time()
                    logger.info(f"已批准: {action_id}")
                    return True
        return False

    def reject(self, action_id: str, reason: str = "") -> bool:
        """拒绝干预"""
        for actions in self._interventions.values():
            for a in actions:
                if a.action_id == action_id:
                    a.action_type = "reject"
                    a.comment = reason or a.comment
                    a.timestamp = time.time()
                    logger.info(f"已拒绝: {action_id}")
                    return True
        return False

    def modify(self, action_id: str, modified_input: Any) -> bool:
        """修改后继续"""
        for actions in self._interventions.values():
            for a in actions:
                if a.action_id == action_id:
                    a.action_type = "modify"
                    a.modified_input = modified_input
                    a.timestamp = time.time()
                    logger.info(f"已修改: {action_id}")
                    return True
        return False

    def get_pending(self, pipeline_id: str = "") -> list[InterventionAction]:
        """获取待处理的干预"""
        if pipeline_id:
            return [
                a for a in self._interventions.get(pipeline_id, []) if a.action_type == "pending"
            ]
        pending = []
        for actions in self._interventions.values():
            pending.extend(a for a in actions if a.action_type == "pending")
        return pending


class PipelineRunner(BaseExtensionModule):
    """流水线执行器 — 串联执行节点，处理人工干预"""

    SUBDIR = "pipeline"

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._pipelines: dict[str, PipelineState] = {}
        self._intervention_mgr = PipelineInterventionManager(book_id)

    def create_pipeline(
        self,
        pipeline_id: str,
        name: str,
        node_defs: list[dict[str, Any]],
    ) -> PipelineState:
        """创建流水线"""
        nodes = [
            PipelineNode(
                node_id=nd["node_id"],
                name=nd["name"],
                description=nd.get("description", ""),
                depends_on=nd.get("depends_on", []),
                max_retries=nd.get("max_retries", 3),
            )
            for nd in node_defs
        ]
        state = PipelineState(pipeline_id=pipeline_id, name=name, nodes=nodes)
        self._pipelines[pipeline_id] = state
        logger.info(f"流水线已创建: {pipeline_id} ({len(nodes)}个节点)")
        return state

    def get_pipeline(self, pipeline_id: str) -> PipelineState | None:
        return self._pipelines.get(pipeline_id)

    def run_node(
        self,
        pipeline_id: str,
        node_id: str,
        executor: Callable[[Any], Any],
        input_data: Any = None,
    ) -> NodeStatus:
        """执行单个节点"""
        state = self._pipelines.get(pipeline_id)
        if not state:
            logger.error(f"流水线不存在: {pipeline_id}")
            return NodeStatus.FAILED

        nodes_dict = {n.node_id: n for n in state.nodes}
        node = nodes_dict.get(node_id)
        if not node:
            logger.error(f"节点不存在: {node_id}")
            return NodeStatus.FAILED

        # 检查依赖
        if not node.can_run(nodes_dict):
            logger.warning(f"节点{node_id}依赖未满足")
            return NodeStatus.PENDING

        # 执行
        node.status = NodeStatus.RUNNING
        node.started_at = time.time()

        try:
            node.result = executor(input_data)
            node.status = NodeStatus.SUCCESS
            node.finished_at = time.time()
            logger.info(f"节点完成: {node_id} ({node.duration:.1f}s)")

            # 检查是否需要人工干预
            if hasattr(executor, "needs_intervention") and executor.needs_intervention():
                node.status = NodeStatus.INTERVENTION
                self._intervention_mgr.request_intervention(
                    pipeline_id, node_id, "节点请求人工审核"
                )
        except Exception as e:
            node.error = str(e)
            node.retries += 1
            if node.retries < node.max_retries:
                logger.warning(f"节点{node_id}失败，重试{node.retries}/{node.max_retries}: {e}")
                node.status = NodeStatus.PENDING
                node.result = None
            else:
                node.status = NodeStatus.FAILED
                node.finished_at = time.time()
                logger.error(f"节点{node_id}失败: {e}")

        # 更新流水线状态
        self._update_pipeline_status(state)
        return node.status

    def run_all(
        self,
        pipeline_id: str,
        executors: dict[str, Callable[[Any], Any]],
        input_data: Any = None,
    ) -> PipelineState:
        """按拓扑顺序执行所有节点"""
        state = self._pipelines.get(pipeline_id)
        if not state:
            logger.error(f"流水线不存在: {pipeline_id}")
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        nodes_dict = {n.node_id: n for n in state.nodes}

        while state.status in (NodeStatus.PENDING, NodeStatus.RUNNING):
            state.status = NodeStatus.RUNNING
            ran_any = False

            for node in state.nodes:
                if node.status in (NodeStatus.PENDING,) and node.can_run(nodes_dict):
                    executor = executors.get(node.node_id)
                    if executor:
                        result = self.run_node(pipeline_id, node.node_id, executor, input_data)
                        ran_any = True
                        if result == NodeStatus.FAILED:
                            # 关键节点失败则停止流水线
                            logger.error(f"关键节点{node.node_id}失败，流水线终止")
                            state.status = NodeStatus.FAILED
                            state.finished_at = time.time()
                            return state
                        if result == NodeStatus.INTERVENTION:
                            # 暂停等待人工干预
                            state.status = NodeStatus.INTERVENTION
                            logger.info(f"流水线{pipeline_id}暂停，等待人工干预")
                            return state

            if not ran_any:
                break

        # 检查是否全部完成
        if all(n.status == NodeStatus.SUCCESS for n in state.nodes):
            state.status = NodeStatus.SUCCESS
            state.finished_at = time.time()
            logger.info(f"流水线完成: {pipeline_id}")

        return state

    def resume_after_intervention(
        self,
        pipeline_id: str,
        action_id: str,
        decision: str,  # "approve" or "reject" or "modify"
        modified_input: Any = None,
    ) -> PipelineState:
        """人工干预后恢复流水线"""
        state = self._pipelines.get(pipeline_id)
        if not state:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        if decision == "approve":
            self._intervention_mgr.approve(action_id)
            # 找到被干预的节点，标记为成功继续
            for node in state.nodes:
                if node.status == NodeStatus.INTERVENTION:
                    node.status = NodeStatus.SUCCESS
                    node.finished_at = time.time()
                    break
        elif decision == "modify":
            self._intervention_mgr.modify(action_id, modified_input)
            for node in state.nodes:
                if node.status == NodeStatus.INTERVENTION:
                    node.status = NodeStatus.PENDING  # 重新执行
                    node.result = None
                    break
        elif decision == "reject":
            self._intervention_mgr.reject(action_id)
            for node in state.nodes:
                if node.status == NodeStatus.INTERVENTION:
                    node.status = NodeStatus.SKIPPED
                    break

        state.status = NodeStatus.PENDING  # 恢复为待执行
        logger.info(f"流水线{pipeline_id}已恢复")
        return state

    def _update_pipeline_status(self, state: PipelineState):
        """更新流水线整体状态"""
        statuses = {n.status for n in state.nodes}
        if NodeStatus.FAILED in statuses:
            state.status = NodeStatus.FAILED
            state.finished_at = time.time()
        elif NodeStatus.INTERVENTION in statuses:
            state.status = NodeStatus.INTERVENTION
        elif all(s == NodeStatus.SUCCESS for s in statuses):
            state.status = NodeStatus.SUCCESS
            state.finished_at = time.time()
        elif any(s == NodeStatus.RUNNING for s in statuses):
            state.status = NodeStatus.RUNNING
        else:
            state.status = NodeStatus.PENDING


class PipelineInterventionStub:
    """管线干预外观 — 供 makefile 调用的轻量接口"""

    def create_pipeline(self, pipeline_id: str, book_id: str, chapter: int):
        logger.debug(f"管线干预: create_pipeline({pipeline_id=}, {book_id=}, {chapter=})")

    def advance_node(self, pipeline_id: str, node_id: str, status, _data: dict | None = None):
        logger.debug(f"管线干预: advance_node({pipeline_id=}, {node_id=}, {status=})")


pipeline_intervention = PipelineInterventionStub()

_runners: dict[str, PipelineRunner] = {}


def get_pipeline_runner(book_id: str = "") -> PipelineRunner:
    """获取流水线执行器实例"""
    if book_id not in _runners:
        _runners[book_id] = PipelineRunner(book_id=book_id)
    return _runners[book_id]

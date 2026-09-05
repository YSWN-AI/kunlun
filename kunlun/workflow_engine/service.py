"""
工作流引擎 — 服务层

提供工作流定义的 CRUD、执行、监控，以及预设工作流管理。
自定义工作流存储在 data/workflows/ 目录（JSON 文件），
执行记录存储在 data/workflows/executions/。
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kunlun.workflow_engine import executor
from kunlun.workflow_engine.models import WorkflowDefinition, WorkflowExecution
from kunlun.workflow_engine.presets import get_presets


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_data_dir() -> Path:
    """获取工作流数据目录（延迟导入 settings，避免循环依赖）。"""
    from kunlun.config import settings

    return Path(settings.DATA_DIR) / "workflows"


def _get_workflows_dir() -> Path:
    d = _get_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_executions_dir() -> Path:
    d = _get_data_dir() / "executions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _workflow_path(workflow_id: str) -> Path:
    return _get_workflows_dir() / f"{workflow_id}.json"


def _execution_path(execution_id: str) -> Path:
    return _get_executions_dir() / f"{execution_id}.json"


def _save_workflow(workflow: WorkflowDefinition) -> None:
    """将工作流定义持久化到 JSON 文件。"""
    path = _workflow_path(workflow.id)
    path.write_text(
        workflow.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _load_workflow(workflow_id: str) -> WorkflowDefinition | None:
    """从 JSON 文件加载工作流定义。"""
    path = _workflow_path(workflow_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowDefinition(**data)


def _save_execution(execution: WorkflowExecution) -> None:
    """将执行记录持久化到 JSON 文件。"""
    path = _execution_path(execution.id)
    path.write_text(
        execution.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _load_execution(execution_id: str) -> WorkflowExecution | None:
    """从 JSON 文件加载执行记录。"""
    path = _execution_path(execution_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowExecution(**data)


class WorkflowService:
    """工作流服务层 — 单例模式。"""

    _instance: WorkflowService | None = None

    def __new__(cls) -> WorkflowService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── 工作流 CRUD ─────────────────────────────────────────

    def list_workflows(
        self, category: str | None = None, search: str | None = None
    ) -> list[WorkflowDefinition]:
        """
        列出工作流（包含预设 + 自定义）。

        支持按分类筛选和名称搜索。
        """
        workflows: list[WorkflowDefinition] = []

        # 预设工作流
        workflows.extend(get_presets())

        # 自定义工作流
        wf_dir = _get_workflows_dir()
        if wf_dir.exists():
            for f in wf_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    wf = WorkflowDefinition(**data)
                    workflows.append(wf)
                except Exception:
                    continue

        # 筛选
        if category:
            workflows = [w for w in workflows if w.category == category]
        if search:
            search_lower = search.lower()
            workflows = [
                w
                for w in workflows
                if search_lower in w.name.lower() or search_lower in w.description.lower()
            ]

        return workflows

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """获取单个工作流定义（先查预设，再查自定义）。"""
        # 预设
        for preset in get_presets():
            if preset.id == workflow_id:
                return preset
        # 自定义
        return _load_workflow(workflow_id)

    def create_workflow(self, data: dict[str, Any]) -> WorkflowDefinition:
        """创建自定义工作流。"""
        workflow_id = data.get("id") or f"wf_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        workflow = WorkflowDefinition(
            id=workflow_id,
            name=data.get("name", "未命名工作流"),
            description=data.get("description", ""),
            category=data.get("category", "自定义"),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            variables=data.get("variables", {}),
            is_preset=False,
            created_at=now,
            updated_at=now,
        )
        _save_workflow(workflow)
        return workflow

    def update_workflow(self, workflow_id: str, data: dict[str, Any]) -> WorkflowDefinition | None:
        """更新自定义工作流。"""
        existing = _load_workflow(workflow_id)
        if existing is None:
            # 预设工作流不允许修改
            for preset in get_presets():
                if preset.id == workflow_id:
                    raise ValueError("预设工作流不可修改，请先复制为自定义工作流")
            return None

        update_data = data.copy()
        update_data["id"] = workflow_id
        update_data["is_preset"] = False
        update_data["created_at"] = existing.created_at
        update_data["updated_at"] = _now_iso()

        # 合并节点和边
        if "nodes" not in update_data:
            update_data["nodes"] = existing.nodes
        if "edges" not in update_data:
            update_data["edges"] = existing.edges

        workflow = WorkflowDefinition(**update_data)
        _save_workflow(workflow)
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        """删除自定义工作流。"""
        # 预设不可删除
        for preset in get_presets():
            if preset.id == workflow_id:
                raise ValueError("预设工作流不可删除")

        path = _workflow_path(workflow_id)
        if path.exists():
            path.unlink()
            return True
        return False

    # ── 预设管理 ────────────────────────────────────────────

    def list_presets(self) -> list[WorkflowDefinition]:
        """列出所有预设工作流。"""
        return get_presets()

    # ── 执行管理 ────────────────────────────────────────────

    def execute(self, workflow_id: str, inputs: dict[str, Any]) -> WorkflowExecution:
        """执行工作流。"""
        workflow = self.get_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"工作流不存在: {workflow_id}")

        execution = executor.execute_workflow(workflow, inputs)
        _save_execution(execution)
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """获取执行状态（先查内存，再查磁盘）。"""
        execution = executor.get_execution(execution_id)
        if execution is not None:
            return execution
        return _load_execution(execution_id)

    def list_executions(self, workflow_id: str | None = None) -> list[WorkflowExecution]:
        """列出执行记录。"""
        # 内存中的执行记录
        executions = executor.list_executions(workflow_id)
        # 磁盘中的执行记录（补充不在内存中的）
        exec_dir = _get_executions_dir()
        if exec_dir.exists():
            memory_ids = {e.id for e in executions}
            for f in exec_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    exec_record = WorkflowExecution(**data)
                    if exec_record.id not in memory_ids and (
                        workflow_id is None or exec_record.workflow_id == workflow_id
                    ):
                        executions.append(exec_record)
                except Exception:
                    continue
        return executions

    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行。"""
        result = executor.cancel_execution(execution_id)
        if result:
            execution = executor.get_execution(execution_id)
            if execution:
                _save_execution(execution)
        return result


# 便捷函数（模块级单例访问）
_service_cache: dict[str, WorkflowService] = {}


def _get_service() -> WorkflowService:
    if "instance" not in _service_cache:
        _service_cache["instance"] = WorkflowService()
    return _service_cache["instance"]


def list_workflows(
    category: str | None = None, search: str | None = None
) -> list[WorkflowDefinition]:
    return _get_service().list_workflows(category, search)


def get_workflow(workflow_id: str) -> WorkflowDefinition | None:
    return _get_service().get_workflow(workflow_id)


def create_workflow(data: dict[str, Any]) -> WorkflowDefinition:
    return _get_service().create_workflow(data)


def update_workflow(workflow_id: str, data: dict[str, Any]) -> WorkflowDefinition | None:
    return _get_service().update_workflow(workflow_id, data)


def delete_workflow(workflow_id: str) -> bool:
    return _get_service().delete_workflow(workflow_id)


def list_presets() -> list[WorkflowDefinition]:
    return _get_service().list_presets()


def execute_workflow(workflow_id: str, inputs: dict[str, Any]) -> WorkflowExecution:
    return _get_service().execute(workflow_id, inputs)


def get_execution(execution_id: str) -> WorkflowExecution | None:
    return _get_service().get_execution(execution_id)


def list_executions(workflow_id: str | None = None) -> list[WorkflowExecution]:
    return _get_service().list_executions(workflow_id)


def cancel_execution(execution_id: str) -> bool:
    return _get_service().cancel_execution(execution_id)

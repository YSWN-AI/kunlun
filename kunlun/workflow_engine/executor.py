"""
工作流引擎 — 执行引擎

支持拓扑排序、条件分支、循环执行、节点级日志记录。
LLM 节点使用模拟生成（不调用真实 LLM），确保离线可用。
"""

from __future__ import annotations

import re
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from kunlun.workflow_engine.models import WorkflowDefinition, WorkflowExecution, WorkflowNode

# 循环最大迭代次数，防止死循环
MAX_LOOP_ITERATIONS = 5

# 执行记录内存存储（同时持久化到磁盘）
_executions: dict[str, WorkflowExecution] = {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _add_log(execution: WorkflowExecution, node_id: str, message: str, level: str = "info") -> None:
    """向执行记录追加一条日志。"""
    execution.logs.append(
        {
            "timestamp": _now_iso(),
            "node_id": node_id,
            "message": message,
            "level": level,
        }
    )


# ── 拓扑排序 ──────────────────────────────────────────────────
def topological_sort(workflow: WorkflowDefinition) -> list[str]:
    """
    对工作流节点进行拓扑排序（Kahn 算法）。

    对于含循环的图（如降AI流程的改写循环），会打破循环边后排序。
    返回节点 ID 的有序列表。
    """
    node_ids = {node.id for node in workflow.nodes}
    # 构建入度表（仅统计非循环边）
    in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}

    # 先构建完整邻接表
    for edge in workflow.edges:
        if edge.source in node_ids and edge.target in node_ids:
            adjacency[edge.source].append(edge.target)

    # 检测并打破循环：使用 DFS 标记，遇到回边则跳过
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycle_edges: set[tuple[str, str]] = set()

    def _dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        for neighbor in adjacency[node]:
            if neighbor not in visited:
                _dfs(neighbor)
            elif neighbor in in_stack:
                cycle_edges.add((node, neighbor))
        in_stack.discard(node)

    for nid in node_ids:
        if nid not in visited:
            _dfs(nid)

    # 重新构建入度（排除循环边）
    for edge in workflow.edges:
        if (
            edge.source in node_ids
            and edge.target in node_ids
            and (edge.source, edge.target) not in cycle_edges
        ):
            in_degree[edge.target] += 1

    queue: deque[str] = deque([nid for nid, deg in in_degree.items() if deg == 0])
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adjacency[node]:
            if (node, neighbor) not in cycle_edges:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    # 若有未排序节点（循环中的节点），追加到末尾
    remaining = [nid for nid in node_ids if nid not in order]
    order.extend(remaining)

    return order


# ── 节点执行器 ────────────────────────────────────────────────
def _execute_input_node(
    node: WorkflowNode, inputs: dict[str, Any], execution: WorkflowExecution
) -> Any:
    """执行 input 节点：从全局输入中读取变量。"""
    var_name = node.config.get("variable_name", "input")
    value = inputs.get(var_name, inputs.get("input", ""))
    _add_log(execution, node.id, f"读取输入变量 '{var_name}'，长度={len(str(value))}")
    return value


def _execute_output_node(
    node: WorkflowNode, upstream_output: Any, execution: WorkflowExecution
) -> Any:
    """执行 output 节点：记录输出变量。"""
    var_name = node.config.get("variable_name", "output")
    _add_log(execution, node.id, f"输出变量 '{var_name}' 已就绪，长度={len(str(upstream_output))}")
    return upstream_output


def _execute_llm_node(
    node: WorkflowNode, upstream_output: Any, execution: WorkflowExecution
) -> str:
    """
    执行 LLM 节点（模拟）。

    不调用真实 LLM，返回模板化文本并标注为模拟执行。
    """
    config = node.config
    model = config.get("model", "gpt-4o-mini")
    prompt_template = config.get("prompt_template", "{{input}}")
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens", 2048)

    # 简单模板替换
    prompt = prompt_template
    prompt = re.sub(r"\{\{\s*input\s*\}\}", str(upstream_output)[:500], prompt)
    prompt = re.sub(r"\{\{\s*\w+\s*\}\}", str(upstream_output)[:200], prompt)

    # 模拟生成：基于输入长度生成一段模板化文本
    input_len = len(str(upstream_output))
    simulated = (
        f"【模拟执行 · {model}】\n"
        f"提示词: {prompt[:120]}...\n"
        f"参数: temperature={temperature}, max_tokens={max_tokens}\n"
        f"---\n"
        f"这是模拟生成的内容。原始输入长度 {input_len} 字符。\n"
        f"在真实环境中，此处将调用 {model} 生成完整文本。\n"
        f"模拟输出包含与输入相关的结构化结果，用于验证工作流连通性。"
    )

    _add_log(
        execution,
        node.id,
        f"LLM 模拟调用 model={model}, temp={temperature}, 输入长度={input_len}",
    )
    return simulated


def _execute_text_process_node(
    node: WorkflowNode, upstream_output: Any, execution: WorkflowExecution
) -> Any:
    """执行文本处理节点：真实执行字符串操作。"""
    config = node.config
    operation = config.get("operation", "trim")
    params = config.get("params", {})
    text = str(upstream_output)

    result: Any = text
    if operation == "uppercase":
        result = text.upper()
    elif operation == "lowercase":
        result = text.lower()
    elif operation == "trim":
        result = text.strip()
    elif operation == "replace":
        old = params.get("old", "")
        new = params.get("new", "")
        result = text.replace(old, new)
    elif operation == "split":
        sep = params.get("sep", "\n")
        result = text.split(sep)
    elif operation == "join":
        sep = params.get("sep", "\n")
        result = sep.join(str(item) for item in text) if isinstance(text, list) else text

    _add_log(
        execution,
        node.id,
        f"文本处理 operation={operation}, 输入长度={len(text)}, 输出长度={len(str(result))}",
    )
    return result


def _execute_quality_check_node(
    node: WorkflowNode, upstream_output: Any, execution: WorkflowExecution
) -> dict[str, Any]:
    """
    执行质量检查节点（模拟）。

    基于文本长度和简单规则生成模拟评分。
    """
    config = node.config
    dimensions = config.get("dimensions", ["质量"])
    threshold = config.get("threshold", 0.6)
    text = str(upstream_output)
    text_len = len(text)

    # 模拟评分：基于文本长度的基础分 + 随机扰动（确定性伪随机）
    base_score = min(0.9, 0.4 + text_len / 5000)
    scores: dict[str, float] = {}
    for i, dim in enumerate(dimensions):
        # 使用文本长度和维度索引生成确定性分数
        variation = ((text_len * (i + 1)) % 30) / 100  # 0~0.29
        scores[dim] = round(min(0.95, base_score + variation - 0.1), 3)

    avg_score = round(sum(scores.values()) / len(scores), 3)
    passed = avg_score >= threshold

    result = {
        "score": avg_score,
        "passed": passed,
        "threshold": threshold,
        "dimensions": scores,
        "text_length": text_len,
    }

    _add_log(
        execution,
        node.id,
        f"质量检查: 综合分={avg_score}, 阈值={threshold}, {'通过' if passed else '未通过'}, "
        f"维度数={len(dimensions)}",
    )
    return result


def _execute_condition_node(
    node: WorkflowNode, upstream_output: Any, execution: WorkflowExecution
) -> dict[str, Any]:
    """执行条件节点：根据字段值判断分支。"""
    config = node.config
    field = config.get("field", "score")
    operator = config.get("operator", "gte")
    value = config.get("value", 0.6)

    # 从上游输出中提取字段
    if isinstance(upstream_output, dict):
        actual = upstream_output.get(field, upstream_output)
    else:
        actual = upstream_output

    # 执行比较
    condition_result = False
    try:
        if operator == "gt":
            condition_result = float(actual) > float(value)
        elif operator == "gte":
            condition_result = float(actual) >= float(value)
        elif operator == "lt":
            condition_result = float(actual) < float(value)
        elif operator == "lte":
            condition_result = float(actual) <= float(value)
        elif operator == "eq":
            condition_result = str(actual) == str(value)
        elif operator == "ne":
            condition_result = str(actual) != str(value)
        elif operator == "contains":
            condition_result = str(value) in str(actual)
    except (ValueError, TypeError):
        condition_result = False

    branch = "true" if condition_result else "false"
    next_node = config.get(f"{branch}_branch", "")

    _add_log(
        execution,
        node.id,
        f"条件判断: {field} {operator} {value} → 实际值={actual} → {branch}分支 → {next_node}",
    )

    return {
        "condition_passed": condition_result,
        "branch": branch,
        "next_node": next_node,
        "actual": actual,
    }


def _execute_human_review_node(
    node: WorkflowNode, upstream_output: Any, execution: WorkflowExecution
) -> Any:
    """执行人审节点：模拟自动通过。"""
    instructions = node.config.get("instructions", "请审核")
    _add_log(
        execution,
        node.id,
        f"人工审核（模拟通过）: {instructions[:50]}",
        level="warning",
    )
    return upstream_output


_NODE_EXECUTORS = {
    "input": _execute_input_node,
    "output": _execute_output_node,
    "llm_call": _execute_llm_node,
    "text_process": _execute_text_process_node,
    "quality_check": _execute_quality_check_node,
    "condition": _execute_condition_node,
    "human_review": _execute_human_review_node,
}


# ── 主执行函数 ────────────────────────────────────────────────
def execute_workflow(workflow: WorkflowDefinition, inputs: dict[str, Any]) -> WorkflowExecution:
    """
    执行工作流。

    采用拓扑排序确定基础顺序，条件节点动态选择分支，
    支持循环（带最大迭代次数保护）。
    """
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    execution = WorkflowExecution(
        id=execution_id,
        workflow_id=workflow.id,
        status="running",
        started_at=_now_iso(),
    )

    _add_log(
        execution,
        "",
        f"开始执行工作流 '{workflow.name}' (id={workflow.id})，输入变量: {list(inputs.keys())}",
    )

    # 构建节点查找表
    node_map = {node.id: node for node in workflow.nodes}

    # 构建邻接表（按 source_handle 区分分支）
    outgoing: dict[str, list[tuple[str, str]]] = {}  # node_id -> [(target, handle)]
    for edge in workflow.edges:
        outgoing.setdefault(edge.source, []).append((edge.target, edge.source_handle))

    # 拓扑排序获取基础顺序
    base_order = topological_sort(workflow)
    _add_log(execution, "", f"拓扑排序结果: {base_order}")

    # 执行循环
    visited_count: dict[str, int] = {}
    current_idx = 0
    results: dict[str, Any] = {}

    while current_idx < len(base_order):
        node_id = base_order[current_idx]
        node = node_map.get(node_id)
        if node is None:
            current_idx += 1
            continue

        # 循环保护
        visited_count[node_id] = visited_count.get(node_id, 0) + 1
        if visited_count[node_id] > MAX_LOOP_ITERATIONS:
            _add_log(
                execution,
                node_id,
                f"节点达到最大循环次数 ({MAX_LOOP_ITERATIONS})，强制跳出循环",
                level="error",
            )
            current_idx += 1
            continue

        execution.current_node = node_id
        _add_log(execution, node_id, f"▶ 执行节点 [{node.name}] (类型={node.type})")

        # 收集上游输出
        upstream_outputs = [results[inp_id] for inp_id in node.inputs if inp_id in results]

        # 选择上游输出：单输入直接传，多输入合并
        if len(upstream_outputs) == 0:
            upstream_data: Any = inputs if node.type == "input" else ""
        elif len(upstream_outputs) == 1:
            upstream_data = upstream_outputs[0]
        else:
            upstream_data = upstream_outputs

        # 执行节点
        try:
            executor = _NODE_EXECUTORS.get(node.type)
            if executor is None:
                _add_log(execution, node_id, f"未知节点类型: {node.type}", level="error")
                results[node_id] = None
                current_idx += 1
                continue

            if node.type == "input":
                output = executor(node, inputs, execution)
            else:
                output = executor(node, upstream_data, execution)

            results[node_id] = output

            # 条件节点：动态跳转
            if node.type == "condition" and isinstance(output, dict):
                next_node = output.get("next_node", "")
                if next_node and next_node in node_map:
                    _add_log(
                        execution,
                        node_id,
                        f"条件分支跳转到: {next_node}",
                    )
                    # 找到目标节点在 base_order 中的位置
                    if next_node in base_order:
                        target_idx = base_order.index(next_node)
                        current_idx = target_idx
                        continue

        except Exception as e:
            _add_log(execution, node_id, f"节点执行失败: {e}", level="error")
            execution.status = "failed"
            execution.completed_at = _now_iso()
            _executions[execution_id] = execution
            return execution

        current_idx += 1

    # 执行完成
    execution.results = results
    execution.status = "completed"
    execution.current_node = ""
    execution.completed_at = _now_iso()
    _add_log(
        execution,
        "",
        f"工作流执行完成，共执行 {len(results)} 个节点，耗时节点数={len(execution.logs)}",
    )

    _executions[execution_id] = execution
    return execution


def get_execution(execution_id: str) -> WorkflowExecution | None:
    """获取执行状态。"""
    return _executions.get(execution_id)


def cancel_execution(execution_id: str) -> bool:
    """取消执行。"""
    execution = _executions.get(execution_id)
    if execution is None:
        return False
    if execution.status in ("completed", "failed", "cancelled"):
        return False
    execution.status = "cancelled"
    execution.completed_at = _now_iso()
    _add_log(execution, execution.current_node, "执行被用户取消", level="warning")
    return True


def list_executions(workflow_id: str | None = None) -> list[WorkflowExecution]:
    """列出执行记录。"""
    if workflow_id:
        return [e for e in _executions.values() if e.workflow_id == workflow_id]
    return list(_executions.values())

"""
工作流引擎 — 预设工作流模板

内置 3 个可直接执行的预设工作流：
1. 章节生成流程
2. 爆款仿写流程
3. 降AI处理流程
"""

from __future__ import annotations

from kunlun.workflow_engine.models import WorkflowDefinition, WorkflowEdge, WorkflowNode

# 预设缓存（使用可变容器避免 global 语句）
_preset_cache: dict[str, list[WorkflowDefinition]] = {}


# ── 预设 1：章节生成流程 ──────────────────────────────────────
def _chapter_generation_preset() -> WorkflowDefinition:
    """章节生成流程：输入 → 大纲提取 → 蓝图生成 → 正文生成 → 质量检查 → 条件分支。"""
    nodes = [
        WorkflowNode(
            id="input_chapter",
            type="input",
            name="章节参数输入",
            position={"x": 80, "y": 200},
            config={
                "variable_name": "chapter_params",
                "description": "章节标题、大纲、字数要求",
            },
            inputs=[],
            outputs=["outline_extract"],
        ),
        WorkflowNode(
            id="outline_extract",
            type="text_process",
            name="大纲提取",
            position={"x": 280, "y": 200},
            config={"operation": "trim", "params": {}},
            inputs=["input_chapter"],
            outputs=["llm_blueprint"],
        ),
        WorkflowNode(
            id="llm_blueprint",
            type="llm_call",
            name="LLM生成(蓝图)",
            position={"x": 480, "y": 120},
            config={
                "model": "gpt-4o-mini",
                "prompt_template": (
                    "根据章节参数 {{chapter_params}}，生成章节蓝图（场景、冲突、转折）"
                ),
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            inputs=["outline_extract"],
            outputs=["llm_body"],
        ),
        WorkflowNode(
            id="llm_body",
            type="llm_call",
            name="LLM生成(正文)",
            position={"x": 680, "y": 120},
            config={
                "model": "gpt-4o-mini",
                "prompt_template": (
                    "根据蓝图 {{blueprint}}，撰写完整章节正文，要求节奏紧凑、冲突鲜明"
                ),
                "temperature": 0.8,
                "max_tokens": 4096,
            },
            inputs=["llm_blueprint"],
            outputs=["quality_check"],
        ),
        WorkflowNode(
            id="quality_check",
            type="quality_check",
            name="质量检查(8维度)",
            position={"x": 880, "y": 120},
            config={
                "dimensions": [
                    "连贯性",
                    "逻辑性",
                    "文采",
                    "节奏",
                    "人物",
                    "情节",
                    "设定",
                    "吸引力",
                ],
                "threshold": 0.6,
            },
            inputs=["llm_body"],
            outputs=["condition_quality"],
        ),
        WorkflowNode(
            id="condition_quality",
            type="condition",
            name="质量达标?",
            position={"x": 1080, "y": 120},
            config={
                "field": "score",
                "operator": "gte",
                "value": 0.6,
                "true_branch": "output_pass",
                "false_branch": "human_review",
            },
            inputs=["quality_check"],
            outputs=["output_pass", "human_review"],
        ),
        WorkflowNode(
            id="output_pass",
            type="output",
            name="输出(达标)",
            position={"x": 1280, "y": 60},
            config={"variable_name": "chapter_text", "description": "最终章节正文"},
            inputs=["condition_quality"],
            outputs=[],
        ),
        WorkflowNode(
            id="human_review",
            type="human_review",
            name="人工审核",
            position={"x": 1280, "y": 200},
            config={"instructions": "章节质量未达标，请人工审核并修改"},
            inputs=["condition_quality"],
            outputs=["output_review"],
        ),
        WorkflowNode(
            id="output_review",
            type="output",
            name="输出(审核后)",
            position={"x": 1480, "y": 200},
            config={
                "variable_name": "chapter_text_reviewed",
                "description": "人工审核后的章节正文",
            },
            inputs=["human_review"],
            outputs=[],
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="input_chapter", target="outline_extract"),
        WorkflowEdge(id="e2", source="outline_extract", target="llm_blueprint"),
        WorkflowEdge(id="e3", source="llm_blueprint", target="llm_body"),
        WorkflowEdge(id="e4", source="llm_body", target="quality_check"),
        WorkflowEdge(id="e5", source="quality_check", target="condition_quality"),
        WorkflowEdge(
            id="e6", source="condition_quality", target="output_pass", source_handle="true"
        ),
        WorkflowEdge(
            id="e7", source="condition_quality", target="human_review", source_handle="false"
        ),
        WorkflowEdge(id="e8", source="human_review", target="output_review"),
    ]

    return WorkflowDefinition(
        id="preset_chapter_generation",
        name="章节生成流程",
        description=(
            "标准章节生成管线：参数输入 → 大纲提取 → 蓝图生成 → 正文生成 → "
            "8维质量检查 → 条件分支 → 输出/人工审核"
        ),
        category="章节生成",
        nodes=nodes,
        edges=edges,
        variables={"chapter_params": "章节标题、大纲、字数要求"},
        is_preset=True,
    )


# ── 预设 2：爆款仿写流程 ──────────────────────────────────────
def _viral_imitation_preset() -> WorkflowDefinition:
    """爆款仿写流程：输入 → 风格提取 → 结构分析 → 仿写大纲 → 仿写正文 → 输出。"""
    nodes = [
        WorkflowNode(
            id="input_ref",
            type="input",
            name="参考文本+目标题材",
            position={"x": 80, "y": 200},
            config={
                "variable_name": "reference_and_target",
                "description": "参考爆款文本 + 目标题材",
            },
            inputs=[],
            outputs=["style_extract", "structure_analyze"],
        ),
        WorkflowNode(
            id="style_extract",
            type="text_process",
            name="风格提取",
            position={"x": 300, "y": 100},
            config={"operation": "trim", "params": {}},
            inputs=["input_ref"],
            outputs=["llm_outline"],
        ),
        WorkflowNode(
            id="structure_analyze",
            type="text_process",
            name="结构分析",
            position={"x": 300, "y": 300},
            config={"operation": "split", "params": {"sep": "\n\n"}},
            inputs=["input_ref"],
            outputs=["llm_outline"],
        ),
        WorkflowNode(
            id="llm_outline",
            type="llm_call",
            name="LLM生成(仿写大纲)",
            position={"x": 540, "y": 200},
            config={
                "model": "gpt-4o-mini",
                "prompt_template": (
                    "参考风格 {{style}} 和结构 {{structure}}，为目标题材生成仿写大纲"
                ),
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            inputs=["style_extract", "structure_analyze"],
            outputs=["llm_body"],
        ),
        WorkflowNode(
            id="llm_body",
            type="llm_call",
            name="LLM生成(仿写正文)",
            position={"x": 760, "y": 200},
            config={
                "model": "gpt-4o-mini",
                "prompt_template": "根据仿写大纲 {{outline}}，模仿参考风格撰写正文",
                "temperature": 0.8,
                "max_tokens": 4096,
            },
            inputs=["llm_outline"],
            outputs=["style_check"],
        ),
        WorkflowNode(
            id="style_check",
            type="quality_check",
            name="风格相似度检查",
            position={"x": 980, "y": 200},
            config={
                "dimensions": [
                    "风格相似度",
                    "节奏匹配",
                    "用词习惯",
                    "句式结构",
                    "情感基调",
                ],
                "threshold": 0.65,
            },
            inputs=["llm_body"],
            outputs=["output_result"],
        ),
        WorkflowNode(
            id="output_result",
            type="output",
            name="输出(仿写结果)",
            position={"x": 1200, "y": 200},
            config={"variable_name": "imitated_text", "description": "仿写完成的正文"},
            inputs=["style_check"],
            outputs=[],
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="input_ref", target="style_extract"),
        WorkflowEdge(id="e2", source="input_ref", target="structure_analyze"),
        WorkflowEdge(id="e3", source="style_extract", target="llm_outline"),
        WorkflowEdge(id="e4", source="structure_analyze", target="llm_outline"),
        WorkflowEdge(id="e5", source="llm_outline", target="llm_body"),
        WorkflowEdge(id="e6", source="llm_body", target="style_check"),
        WorkflowEdge(id="e7", source="style_check", target="output_result"),
    ]

    return WorkflowDefinition(
        id="preset_viral_imitation",
        name="爆款仿写流程",
        description=(
            "爆款文本仿写管线：参考文本+目标题材 → 风格提取+结构分析 → "
            "仿写大纲 → 仿写正文 → 风格相似度检查 → 输出"
        ),
        category="爆款仿写",
        nodes=nodes,
        edges=edges,
        variables={"reference_and_target": "参考爆款文本 + 目标题材"},
        is_preset=True,
    )


# ── 预设 3：降AI处理流程 ──────────────────────────────────────
def _de_ai_preset() -> WorkflowDefinition:
    """降AI处理流程：输入 → AI率检测 → 条件 → 多策略改写 → 重新检测 → 循环。"""
    nodes = [
        WorkflowNode(
            id="input_text",
            type="input",
            name="文本输入",
            position={"x": 80, "y": 200},
            config={"variable_name": "raw_text", "description": "待降AI的原始文本"},
            inputs=[],
            outputs=["ai_detect"],
        ),
        WorkflowNode(
            id="ai_detect",
            type="quality_check",
            name="AI率检测(12维度)",
            position={"x": 300, "y": 200},
            config={
                "dimensions": [
                    "句式重复",
                    "过渡词滥用",
                    "排比堆砌",
                    "形容词过载",
                    "空洞套话",
                    "逻辑模板化",
                    "情感扁平",
                    "细节缺失",
                    "节奏均匀",
                    "词汇单一",
                    "标点模式",
                    "段落结构",
                ],
                "threshold": 0.3,
            },
            inputs=["input_text"],
            outputs=["condition_ai_rate"],
        ),
        WorkflowNode(
            id="condition_ai_rate",
            type="condition",
            name="AI率>30%?",
            position={"x": 520, "y": 200},
            config={
                "field": "score",
                "operator": "gt",
                "value": 0.3,
                "true_branch": "rewrite",
                "false_branch": "output_clean",
            },
            inputs=["ai_detect"],
            outputs=["rewrite", "output_clean"],
        ),
        WorkflowNode(
            id="rewrite",
            type="llm_call",
            name="多策略改写",
            position={"x": 740, "y": 120},
            config={
                "model": "gpt-4o-mini",
                "prompt_template": (
                    "对以下文本进行降AI改写：打破句式、增加口语化表达、替换套话、丰富细节 {{text}}"
                ),
                "temperature": 0.9,
                "max_tokens": 4096,
            },
            inputs=["condition_ai_rate"],
            outputs=["re_detect"],
        ),
        WorkflowNode(
            id="re_detect",
            type="quality_check",
            name="重新检测",
            position={"x": 960, "y": 120},
            config={
                "dimensions": [
                    "句式重复",
                    "过渡词滥用",
                    "排比堆砌",
                    "形容词过载",
                    "空洞套话",
                    "逻辑模板化",
                    "情感扁平",
                    "细节缺失",
                    "节奏均匀",
                    "词汇单一",
                    "标点模式",
                    "段落结构",
                ],
                "threshold": 0.3,
            },
            inputs=["rewrite"],
            outputs=["condition_pass"],
        ),
        WorkflowNode(
            id="condition_pass",
            type="condition",
            name="达标?",
            position={"x": 1180, "y": 120},
            config={
                "field": "score",
                "operator": "lte",
                "value": 0.3,
                "true_branch": "output_clean",
                "false_branch": "rewrite",
            },
            inputs=["re_detect"],
            outputs=["output_clean", "rewrite"],
        ),
        WorkflowNode(
            id="output_clean",
            type="output",
            name="输出(降AI完成)",
            position={"x": 1400, "y": 200},
            config={"variable_name": "de_ai_text", "description": "降AI处理后的文本"},
            inputs=["condition_ai_rate", "condition_pass"],
            outputs=[],
        ),
    ]

    edges = [
        WorkflowEdge(id="e1", source="input_text", target="ai_detect"),
        WorkflowEdge(id="e2", source="ai_detect", target="condition_ai_rate"),
        WorkflowEdge(id="e3", source="condition_ai_rate", target="rewrite", source_handle="true"),
        WorkflowEdge(
            id="e4", source="condition_ai_rate", target="output_clean", source_handle="false"
        ),
        WorkflowEdge(id="e5", source="rewrite", target="re_detect"),
        WorkflowEdge(id="e6", source="re_detect", target="condition_pass"),
        WorkflowEdge(id="e7", source="condition_pass", target="output_clean", source_handle="true"),
        WorkflowEdge(id="e8", source="condition_pass", target="rewrite", source_handle="false"),
    ]

    return WorkflowDefinition(
        id="preset_de_ai",
        name="降AI处理流程",
        description=(
            "降AI管线：文本输入 → 12维AI率检测 → 条件判断 → "
            "多策略改写 → 重新检测 → 循环直至达标 → 输出"
        ),
        category="降AI",
        nodes=nodes,
        edges=edges,
        variables={"raw_text": "待降AI的原始文本"},
        is_preset=True,
    )


# ── 预设注册表 ────────────────────────────────────────────────
_PRESET_FACTORIES = [
    _chapter_generation_preset,
    _viral_imitation_preset,
    _de_ai_preset,
]


def get_presets() -> list[WorkflowDefinition]:
    """获取所有预设工作流（带缓存）。"""
    if "data" not in _preset_cache:
        _preset_cache["data"] = [factory() for factory in _PRESET_FACTORIES]
    return _preset_cache["data"]


def list_presets() -> list[WorkflowDefinition]:
    """获取预设工作流列表（别名，供 service 层调用）。"""
    return get_presets()


def get_preset(preset_id: str) -> WorkflowDefinition | None:
    """根据 ID 获取单个预设工作流。"""
    for preset in get_presets():
        if preset.id == preset_id:
            return preset
    return None

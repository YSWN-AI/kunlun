"""
昆仑创作引擎 — 7Agent 协作流程核心引擎

对标马良写作的多智能体协作系统，实现 supervisor / structure / blueprint /
generation / setting / consistency / correction 七个 Agent 的定义、配置管理
与串行协作写作流程。

协作流程（多 Agent 模式）:
    structure → blueprint → generation → consistency → correction

单 Agent 模式:
    仅执行 generation 一步

每步记录 agent_id / status / output / duration_ms / tokens / model，
LLM 调用统一通过 kunlun.gacha.engine.chat()，不可用时优雅降级为模拟结果。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ── 7 Agent 定义 ──────────────────────────────────────────────────────────

AGENT_DEFINITIONS: list[dict[str, str]] = [
    {
        "id": "supervisor",
        "name": "主管Agent",
        "role": "任务分配与流程协调",
        "description": "负责任务拆解、Agent 调度、整体流程协调与质量把关，是协作流程的中枢。",
        "default_model": "",
    },
    {
        "id": "structure",
        "name": "结构Agent",
        "role": "大纲结构校验",
        "description": "确保每章内容符合整体大纲与卷纲结构，校验章节在全书叙事弧中的位置与作用。",
        "default_model": "",
    },
    {
        "id": "blueprint",
        "name": "蓝图Agent",
        "role": "单章计划拆解",
        "description": "将卷纲拆解为单章写作计划，按开场→发展→高潮→收尾"
        "四节点规划本章节奏与情节推进。",
        "default_model": "",
    },
    {
        "id": "generation",
        "name": "生成Agent",
        "role": "核心正文写作",
        "description": "根据蓝图计划输出高质量正文，是协作流程的核心写作执行单元。",
        "default_model": "",
    },
    {
        "id": "setting",
        "name": "设定Agent",
        "role": "世界观设定管理",
        "description": "管理世界观、力量体系、地理、势力等设定的一致性，"
        "在写作过程中提供设定查询与冲突预警。",
        "default_model": "",
    },
    {
        "id": "consistency",
        "name": "一致性Agent",
        "role": "多维度矛盾校验",
        "description": "对生成正文进行人物、情节、时间线、设定等多维度"
        "一致性校验，发现潜在矛盾与逻辑漏洞。",
        "default_model": "",
    },
    {
        "id": "correction",
        "name": "纠错Agent",
        "role": "文笔优化与逻辑修复",
        "description": "根据一致性校验结果进行文笔优化、逻辑修复与表达精炼，输出最终定稿正文。",
        "default_model": "",
    },
]

# 多 Agent 模式下的五步串行流程（使用 7 个 Agent 中的 5 个）
MULTI_AGENT_FLOW: list[str] = [
    "structure",
    "blueprint",
    "generation",
    "consistency",
    "correction",
]

# 单 Agent 模式下仅执行生成
SINGLE_AGENT_FLOW: list[str] = ["generation"]


# ── 数据类 ────────────────────────────────────────────────────────────────


@dataclass
class PipelineConfig:
    """协作流程配置。

    Attributes:
        mode: 运行模式，"single" 单 Agent 或 "multi" 多 Agent。
        agent_models: 每个 Agent 可配置不同模型，key 为 agent_id。
        enabled_agents: 启用的 Agent id 列表。
        max_retries: 单步失败重试次数。
    """

    mode: str = "multi"
    agent_models: dict[str, str] = field(default_factory=dict)
    enabled_agents: list[str] = field(default_factory=lambda: [a["id"] for a in AGENT_DEFINITIONS])
    max_retries: int = 2


@dataclass
class StepResult:
    """单步执行结果。

    Attributes:
        agent_id: 执行该步的 Agent id。
        name: Agent 显示名称。
        status: 执行状态 pending / running / done / failed。
        output: 该步输出文本。
        duration_ms: 耗时（毫秒）。
        tokens: 消耗 token 数（估算）。
        model: 实际使用的模型。
    """

    agent_id: str
    name: str
    status: str = "pending"
    output: str = ""
    duration_ms: int = 0
    tokens: int = 0
    model: str = ""


# ── 各 Agent 提示词构建 ───────────────────────────────────────────────────


def _build_structure_prompt(
    chapter_number: int, chapter_title: str, context: dict[str, Any]
) -> str:
    """构建结构 Agent 提示词。"""
    outline = context.get("outline", "（未提供大纲）")
    volume_outline = context.get("volume_outline", "（未提供卷纲）")
    return (
        f"你是结构Agent。请校验第{chapter_number}章「{chapter_title}」"
        f"在全书大纲与卷纲中的位置是否合理。\n\n"
        f"【全书大纲】\n{outline}\n\n"
        f"【本卷卷纲】\n{volume_outline}\n\n"
        f"请输出：1) 本章在叙事弧中的位置；2) 结构合理性评估；"
        f"3) 需要注意的结构要点。"
    )


def _build_blueprint_prompt(
    chapter_number: int,
    chapter_title: str,
    context: dict[str, Any],
    structure_output: str,
) -> str:
    """构建蓝图 Agent 提示词。"""
    previous_chapter = context.get("previous_chapter", "（无前章摘要）")
    return (
        f"你是蓝图Agent。请根据结构评估，为第{chapter_number}章"
        f"「{chapter_title}」制定单章写作计划。\n\n"
        f"【结构评估】\n{structure_output}\n\n"
        f"【前章摘要】\n{previous_chapter}\n\n"
        f"请按四节点输出：1) 开场（钩子与场景建立）；2) 发展"
        f"（冲突推进与人物互动）；3) 高潮（核心冲突爆发）；"
        f"4) 收尾（悬念与过渡）。每个节点包含情节要点、人物动作、"
        f"情绪基调。"
    )


def _build_generation_prompt(
    chapter_number: int,
    chapter_title: str,
    context: dict[str, Any],
    blueprint_output: str,
) -> str:
    """构建生成 Agent 提示词。"""
    style_guide = context.get("style_guide", "（未提供风格指南）")
    characters = context.get("characters", "（未提供人物设定）")
    target_words = context.get("target_words", 3000)
    return (
        f"你是生成Agent。请根据蓝图计划撰写第{chapter_number}章"
        f"「{chapter_title}」的完整正文。\n\n"
        f"【蓝图计划】\n{blueprint_output}\n\n"
        f"【人物设定】\n{characters}\n\n"
        f"【风格指南】\n{style_guide}\n\n"
        f"要求：1) 字数约{target_words}字；2) 严格按蓝图四节点推进；"
        f"3) 对话生动，动作描写具体；4) 保持人物性格一致；"
        f"5) 直接输出正文，不要包含分析或注释。"
    )


def _build_consistency_prompt(
    chapter_number: int,
    chapter_title: str,
    context: dict[str, Any],
    generated_text: str,
) -> str:
    """构建一致性 Agent 提示词。"""
    world_setting = context.get("world_setting", "（未提供世界观设定）")
    return (
        f"你是一致性Agent。请对第{chapter_number}章「{chapter_title}」"
        f"的正文进行多维度一致性校验。\n\n"
        f"【世界观设定】\n{world_setting}\n\n"
        f"【待校验正文】\n{generated_text}\n\n"
        f"请从以下维度检查并列出问题：1) 人物一致性（性格/能力/关系）；"
        f"2) 情节一致性（与前文是否矛盾）；3) 时间线一致性；"
        f"4) 设定一致性（力量体系/地理/规则）；5) 逻辑漏洞。"
        f"如无问题，明确说明「未发现一致性问题」。"
    )


def _build_correction_prompt(
    chapter_number: int,
    chapter_title: str,
    context: dict[str, Any],
    generated_text: str,
    consistency_output: str,
) -> str:
    """构建纠错 Agent 提示词。"""
    style_guide = context.get("style_guide", "（未提供风格指南）")
    return (
        f"你是纠错Agent。请根据一致性校验结果，对第{chapter_number}章"
        f"「{chapter_title}」的正文进行修正与优化。\n\n"
        f"【一致性校验结果】\n{consistency_output}\n\n"
        f"【风格指南】\n{style_guide}\n\n"
        f"【原始正文】\n{generated_text}\n\n"
        f"要求：1) 修复所有指出的一致性问题和逻辑漏洞；2) 优化文笔"
        f"表达，去除冗余；3) 保持情节和人物不变；4) 直接输出修正后的"
        f"完整正文，不要包含分析或注释。"
    )


# ── 模拟结果（LLM 不可用时降级）──────────────────────────────────────────


def _mock_structure_output(chapter_number: int, chapter_title: str) -> str:
    """模拟结构 Agent 输出。"""
    return (
        f"【结构评估 - 第{chapter_number}章「{chapter_title}」】\n"
        f"1. 叙事位置：本章处于故事发展阶段，承担承上启下作用。\n"
        f"2. 结构合理性：章节定位清晰，与前后章衔接自然。\n"
        f"3. 注意要点：需确保开场钩子足够有力，高潮部分冲突密度达标。\n"
        f"（模拟模式 - LLM 不可用时的降级输出）"
    )


def _mock_blueprint_output(chapter_number: int, chapter_title: str) -> str:
    """模拟蓝图 Agent 输出。"""
    return (
        f"【单章蓝图 - 第{chapter_number}章「{chapter_title}」】\n"
        f"一、开场：场景切入，主角面临新的挑战，建立紧张感。\n"
        f"二、发展：冲突逐步升级，配角介入，揭示关键信息。\n"
        f"三、高潮：核心冲突爆发，主角做出关键抉择，局势逆转。\n"
        f"四、收尾：暂时平息，埋下新的悬念，为下章铺垫。\n"
        f"（模拟模式 - LLM 不可用时的降级输出）"
    )


def _mock_generation_output(chapter_number: int, chapter_title: str) -> str:
    """模拟生成 Agent 输出。"""
    return (
        f"第{chapter_number}章 {chapter_title}\n\n"
        f"夜色如墨，风掠过山脊，带来一丝不安的气息。\n\n"
        f"主角站在崖边，目光锐利地注视着远方。身后传来脚步声，"
        f"他没有回头，只是淡淡开口：「你终于来了。」\n\n"
        f"「我以为你会逃走。」来人的声音低沉，带着几分嘲讽。\n\n"
        f"「该面对的，终究要面对。」主角缓缓转身，眼中闪过一丝"
        f"决然。\n\n"
        f"风更大了，两人之间的空气仿佛凝固。一场不可避免的对决"
        f"即将展开……\n\n"
        f"（模拟模式 - LLM 不可用时的降级输出，实际使用时请配置 API Key）"
    )


def _mock_consistency_output() -> str:
    """模拟一致性 Agent 输出。"""
    return (
        "【一致性校验报告】\n"
        "1. 人物一致性：未发现明显问题。\n"
        "2. 情节一致性：未发现与前文矛盾之处。\n"
        "3. 时间线一致性：时间线连贯。\n"
        "4. 设定一致性：符合世界观设定。\n"
        "5. 逻辑漏洞：未发现明显逻辑漏洞。\n"
        "结论：未发现一致性问题。\n"
        "（模拟模式 - LLM 不可用时的降级输出）"
    )


def _mock_correction_output(generated_text: str) -> str:
    """模拟纠错 Agent 输出（直接返回原文，模拟无修正）。"""
    return generated_text + "\n\n（模拟模式 - 纠错Agent未做修改，LLM不可用）"


# ── 核心引擎 ──────────────────────────────────────────────────────────────


class AgentPipeline:
    """7Agent 协作流程引擎。

    管理 Agent 定义、流程配置，并执行单章协作写作流程。配置持久化到
    data/books/book_<id>/agent_pipeline.json。

    Attributes:
        book_id: 书籍 ID。
        data_dir: 数据根目录，默认 "data"。
        config: 当前流程配置。
    """

    def __init__(self, book_id: str, data_dir: str = "data") -> None:
        """初始化协作流程引擎。

        Args:
            book_id: 书籍 ID。
            data_dir: 数据根目录路径。
        """
        self.book_id = book_id
        self.data_dir = data_dir
        self.config = PipelineConfig()
        self.load_config()

    # ── 配置持久化 ──────────────────────────────────────────────────────

    @property
    def _config_path(self) -> Path:
        """配置文件路径。"""
        return Path(self.data_dir) / "books" / f"book_{self.book_id}" / "agent_pipeline.json"

    def load_config(self) -> PipelineConfig:
        """从磁盘加载配置，不存在则使用默认配置。

        Returns:
            加载后的 PipelineConfig。
        """
        try:
            if self._config_path.exists():
                with self._config_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                self.config = PipelineConfig(
                    mode=data.get("mode", "multi"),
                    agent_models=data.get("agent_models", {}),
                    enabled_agents=data.get("enabled_agents", [a["id"] for a in AGENT_DEFINITIONS]),
                    max_retries=data.get("max_retries", 2),
                )
                logger.debug(f"[AgentPipeline] 配置已加载: {self._config_path}")
        except Exception as e:
            logger.warning(f"[AgentPipeline] 配置加载失败，使用默认: {e}")
            self.config = PipelineConfig()
        return self.config

    def save_config(self) -> None:
        """将当前配置持久化到磁盘。"""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with self._config_path.open("w", encoding="utf-8") as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
            logger.debug(f"[AgentPipeline] 配置已保存: {self._config_path}")
        except Exception as e:
            logger.error(f"[AgentPipeline] 配置保存失败: {e}")

    def update_config(self, config: dict[str, Any]) -> PipelineConfig:
        """更新配置并持久化。

        Args:
            config: 配置字典，可包含 mode / agent_models /
                enabled_agents / max_retries 字段。

        Returns:
            更新后的 PipelineConfig。
        """
        if "mode" in config:
            mode = config["mode"]
            if mode not in ("single", "multi"):
                raise ValueError(f"无效的 mode: {mode}，应为 'single' 或 'multi'")
            self.config.mode = mode
        if "agent_models" in config:
            self.config.agent_models = dict(config["agent_models"])
        if "enabled_agents" in config:
            valid_ids = {a["id"] for a in AGENT_DEFINITIONS}
            self.config.enabled_agents = [
                aid for aid in config["enabled_agents"] if aid in valid_ids
            ]
        if "max_retries" in config:
            self.config.max_retries = int(config["max_retries"])
        self.save_config()
        return self.config

    # ── Agent 查询 ──────────────────────────────────────────────────────

    def get_agents(self) -> list[dict[str, Any]]:
        """返回 7 个 Agent 的定义及当前配置状态。

        Returns:
            Agent 定义列表，每项包含 id / name / role / description /
            default_model / configured_model / enabled。
        """
        return [
            {
                "id": agent["id"],
                "name": agent["name"],
                "role": agent["role"],
                "description": agent["description"],
                "default_model": agent["default_model"],
                "configured_model": self.config.agent_models.get(agent["id"], ""),
                "enabled": agent["id"] in self.config.enabled_agents,
            }
            for agent in AGENT_DEFINITIONS
        ]

    # ── LLM 调用封装 ────────────────────────────────────────────────────

    async def _call_agent_llm(self, agent_id: str, prompt: str) -> tuple[str, str, int]:
        """调用指定 Agent 的 LLM，失败时降级为模拟结果。

        Args:
            agent_id: Agent id。
            prompt: 提示词。

        Returns:
            (output_text, model_name, token_count) 三元组。
        """
        model = self.config.agent_models.get(agent_id, "")
        try:
            from kunlun.gacha.engine import gacha_engine

            messages = [{"role": "user", "content": prompt}]
            result = await gacha_engine.chat(
                messages=messages,
                model=model,
                agent=agent_id,
            )
            content = result.get("content", "")
            used_model = result.get("model", model)
            usage = result.get("usage", {})
            tokens = int(usage.get("total_tokens", len(prompt) // 2))
            if content and not result.get("error"):
                return content, used_model, tokens
            logger.warning(
                f"[AgentPipeline] {agent_id} LLM 返回空或错误，降级模拟: "
                f"{result.get('error', 'empty content')}"
            )
        except Exception as e:
            logger.warning(f"[AgentPipeline] {agent_id} LLM 调用失败，降级模拟: {e}")

        # 降级为模拟结果
        mock_output = self._get_mock_output(agent_id, prompt)
        estimated_tokens = len(prompt) // 2 + len(mock_output) // 2
        return mock_output, "mock", estimated_tokens

    def _get_mock_output(self, agent_id: str, prompt: str) -> str:
        """根据 Agent id 返回对应的模拟输出。

        Args:
            agent_id: Agent id。
            prompt: 原始提示词（用于提取章节信息）。

        Returns:
            模拟输出文本。
        """
        # 从 prompt 中粗略提取章节号和标题（模拟模式下不需要精确）
        chapter_number = 1
        chapter_title = "未命名"
        for line in prompt.split("\n"):
            if "第" in line and "章" in line:
                chapter_title = line.strip()
                break

        if agent_id == "structure":
            return _mock_structure_output(chapter_number, chapter_title)
        if agent_id == "blueprint":
            return _mock_blueprint_output(chapter_number, chapter_title)
        if agent_id == "generation":
            return _mock_generation_output(chapter_number, chapter_title)
        if agent_id == "consistency":
            return _mock_consistency_output()
        if agent_id == "correction":
            return _mock_correction_output("")
        return f"（{agent_id} 模拟输出）"

    # ── 单步执行 ────────────────────────────────────────────────────────

    async def _execute_step(
        self,
        agent_id: str,
        prompt: str,
    ) -> StepResult:
        """执行单个 Agent 步骤，含重试逻辑。

        Args:
            agent_id: Agent id。
            prompt: 该步提示词。

        Returns:
            StepResult 执行结果。
        """
        agent_def = next((a for a in AGENT_DEFINITIONS if a["id"] == agent_id), None)
        name = agent_def["name"] if agent_def else agent_id
        step = StepResult(agent_id=agent_id, name=name, status="running")

        start = time.perf_counter()
        last_error = ""
        for attempt in range(self.config.max_retries + 1):
            try:
                output, model, tokens = await self._call_agent_llm(agent_id, prompt)
                step.output = output
                step.model = model
                step.tokens = tokens
                step.status = "done"
                break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[AgentPipeline] {agent_id} 第{attempt + 1}次尝试失败: {e}")
                if attempt < self.config.max_retries:
                    await asyncio_sleep(0.5 * (attempt + 1))
        else:
            step.status = "failed"
            step.output = f"执行失败（重试{self.config.max_retries}次）: {last_error}"

        step.duration_ms = int((time.perf_counter() - start) * 1000)
        return step

    # ── 主流程 ──────────────────────────────────────────────────────────

    async def run_chapter(
        self,
        chapter_number: int,
        chapter_title: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行完整的单章协作写作流程。

        多 Agent 模式: structure → blueprint → generation → consistency →
        correction 五步串行。
        单 Agent 模式: 仅执行 generation 一步。

        Args:
            chapter_number: 章节号。
            chapter_title: 章节标题。
            context: 上下文信息，可包含 outline / volume_outline /
                previous_chapter / style_guide / characters / world_setting /
                target_words 等。

        Returns:
            包含 success / task_id / steps / final_text / total_duration_ms
            的结果字典。
        """
        if context is None:
            context = {}

        task_id = str(uuid.uuid4())[:8]
        flow = MULTI_AGENT_FLOW if self.config.mode == "multi" else SINGLE_AGENT_FLOW

        # 过滤掉未启用的 Agent
        active_flow = [aid for aid in flow if aid in self.config.enabled_agents]
        if not active_flow:
            active_flow = ["generation"]  # 兜底：至少执行生成

        logger.info(
            f"[AgentPipeline] 开始执行 第{chapter_number}章「{chapter_title}」"
            f" mode={self.config.mode} flow={active_flow} task={task_id}"
        )

        steps: list[StepResult] = []
        final_text = ""
        total_start = time.perf_counter()

        # 各步输出缓存，用于后续步骤引用
        outputs: dict[str, str] = {}

        for agent_id in active_flow:
            prompt = self._build_step_prompt(
                agent_id, chapter_number, chapter_title, context, outputs
            )
            step = await self._execute_step(agent_id, prompt)
            steps.append(step)
            outputs[agent_id] = step.output

            if agent_id == "generation" or (agent_id == "correction" and step.status == "done"):
                final_text = step.output

            if step.status == "failed" and agent_id == "generation":
                # 生成失败则无法继续
                logger.error(f"[AgentPipeline] 生成Agent失败，终止流程 task={task_id}")
                break

        total_duration_ms = int((time.perf_counter() - total_start) * 1000)

        logger.info(
            f"[AgentPipeline] 完成 第{chapter_number}章 task={task_id} "
            f"耗时={total_duration_ms}ms steps={len(steps)}"
        )

        return {
            "success": all(s.status == "done" for s in steps),
            "task_id": task_id,
            "steps": [asdict(s) for s in steps],
            "final_text": final_text,
            "total_duration_ms": total_duration_ms,
        }

    def _build_step_prompt(
        self,
        agent_id: str,
        chapter_number: int,
        chapter_title: str,
        context: dict[str, Any],
        outputs: dict[str, str],
    ) -> str:
        """根据 Agent id 和已有输出构建对应步骤的提示词。

        Args:
            agent_id: 当前 Agent id。
            chapter_number: 章节号。
            chapter_title: 章节标题。
            context: 上下文信息。
            outputs: 之前步骤的输出缓存。

        Returns:
            构建好的提示词。
        """
        if agent_id == "structure":
            return _build_structure_prompt(chapter_number, chapter_title, context)
        if agent_id == "blueprint":
            return _build_blueprint_prompt(
                chapter_number, chapter_title, context, outputs.get("structure", "")
            )
        if agent_id == "generation":
            return _build_generation_prompt(
                chapter_number,
                chapter_title,
                context,
                outputs.get("blueprint", ""),
            )
        if agent_id == "consistency":
            return _build_consistency_prompt(
                chapter_number,
                chapter_title,
                context,
                outputs.get("generation", ""),
            )
        if agent_id == "correction":
            return _build_correction_prompt(
                chapter_number,
                chapter_title,
                context,
                outputs.get("generation", ""),
                outputs.get("consistency", ""),
            )
        return f"你是{agent_id} Agent。请处理第{chapter_number}章「{chapter_title}」。"


def asyncio_sleep(seconds: float) -> Any:
    """异步 sleep 封装，延迟导入 asyncio。

    Args:
        seconds: 休眠秒数。

    Returns:
        asyncio.sleep 协程。
    """
    import asyncio

    return asyncio.sleep(seconds)

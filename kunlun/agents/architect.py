"""
昆仑创作引擎 — Architect (蓝图生成)

职责: 章节大纲 + KG快照 + 偏好 → LLM 生成详细蓝图
输出: 场景设计 / 情绪曲线 / 爽点设置 / 伏笔安插 / 审计预标
"""

from __future__ import annotations

import json
import re
from typing import ClassVar

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.context.budget import ContextBudgetAllocator
from kunlun.gacha.engine import gacha_engine
from kunlun.kg.client import kg_client
from kunlun.kg.embedder import embedder
from kunlun.prompt_manager import prompt_manager


class Architect(BaseAgent):
    """
    总规划师

    能力边界:
    - ✅ 从大纲+KG+偏好生成章节级详细蓝图
    - ✅ 规划情绪曲线和爽点分布
    - ✅ 推断弧线阶段 + 伏笔安插/揭示计划
    - ✅ 预标可能触发的审计风险点
    - ❌ 不许写正文
    - ❌ 不许改大纲（只标注偏差）
    """

    agent_name = "architect"
    capabilities: ClassVar[list] = [
        "blueprint_generation",
        "emotion_curve_planning",
        "pleasure_point_scheduling",
        "foreshadowing_management",
        "arc_stage_inference",
        "audit_risk_premarking",
    ]

    # 章节类型模板
    CHAPTER_TEMPLATES: ClassVar[dict] = {
        "normal": {
            "word_count_range": (2000, 3000),
            "scene_count": (2, 4),
            "pleasure_point_min": 1,
            "hook_required": True,
        },
        "climax": {
            "word_count_range": (2500, 4000),
            "scene_count": (1, 3),
            "pleasure_point_min": 2,
            "hook_required": True,
        },
        "transition": {
            "word_count_range": (1500, 2500),
            "scene_count": (2, 3),
            "pleasure_point_min": 0,
            "hook_required": True,
        },
        "battle": {
            "word_count_range": (2000, 5000),
            "scene_count": (1, 2),
            "pleasure_point_min": 1,
            "hook_required": True,
        },
    }

    def __init__(self, nats_client=None):
        super().__init__(nats_client)
        self._gacha = None  # lazy init

    def _get_gacha(self):
        if self._gacha is None:
            self._gacha = gacha_engine
        return self._gacha

    async def execute(self, task: dict) -> dict:
        """生成章节蓝图"""
        book_id = task.get("book_id")
        chapter = task.get("chapter")
        kg_snapshot_id = task.get("kg_snapshot_id", "")
        chapter_type = task.get("chapter_type", "normal")
        preference_hints = task.get("preference_hints", "")
        kg_summary = task.get("kg_summary", "")
        template = self.CHAPTER_TEMPLATES.get(chapter_type, self.CHAPTER_TEMPLATES["normal"])

        # 尝试 LLM 生成蓝图
        llm_blueprint = await self._llm_generate_blueprint(
            book_id=book_id,
            chapter=chapter,
            chapter_type=chapter_type,
            template=template,
            kg_summary=kg_summary,
            preference_hints=preference_hints,
        )

        # 合并 LLM 输出与模板默认值
        blueprint = self._merge_blueprint(
            llm_blueprint, template, book_id, chapter, chapter_type, kg_snapshot_id
        )

        logger.info(
            f"Architect: ch{chapter} 蓝图生成完成 "
            f"({chapter_type}, {len(blueprint.get('scenes', []))} 场景)"
        )
        return {
            "success": True,
            "blueprint": blueprint,
            "template": template,
        }

    async def _llm_generate_blueprint(
        self,
        book_id: str,
        chapter: int,
        chapter_type: str,
        template: dict,
        kg_summary: str,
        preference_hints: str,
    ) -> dict:
        """调用 LLM 生成结构化蓝图（含 RAG 语义检索 + token 预算控制）"""
        # 从 Qdrant 检索相关前文段落
        rag_context = await self._retrieve_relevant_context(
            book_id, chapter, chapter_type, kg_summary
        )

        prompt = self._build_blueprint_prompt(
            chapter, chapter_type, template, kg_summary, preference_hints, rag_context
        )
        # 注入用户自定义提示词
        try:
            prompt = prompt_manager.inject_into_prompt(prompt, "architect", book_id or "default")
        except Exception as e:
            logger.exception(f"[Architect] 提示词注入跳过: {e}")
            logger.debug(f"[Architect] 提示词注入跳过: {e}")

        try:
            gacha = self._get_gacha()
            result = await gacha.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")

            # 从 LLM 回复中提取 JSON
            blueprint = self._parse_blueprint_json(text)
            if blueprint:
                return blueprint
        except Exception as e:
            logger.exception(f"Architect: LLM 蓝图生成失败: {e}")
            logger.warning(f"Architect: LLM 蓝图生成失败: {e}")

        # 降级：返回空 dict，由 _merge_blueprint 用模板默认值填充
        return {}

    # Token 预算配置（可被 settings 覆盖）
    _MAX_CONTEXT_TOKENS = 6000  # LLM 上下文预算（中文估算：1 token ≈ 1.5 字符）
    _MAX_RAG_PARAGRAPHS = 8  # 语义检索最多注入段落数

    async def _retrieve_relevant_context(
        self, _book_id: str, chapter: int, chapter_type: str, kg_summary: str
    ) -> str:
        """从 Qdrant 向量库检索与当前章节最相关的前文段落（RAG 语义层）"""
        try:
            # 用 kg_summary 或章节类型描述作为查询向量
            query_text = f"第{chapter}章 {chapter_type} {kg_summary[:500] if kg_summary else ''}"
            if not embedder.available:
                return ""

            query_vec = embedder.encode(query_text)
            results = kg_client.qdrant.search(
                collection_name="kunlun_entities",
                query_vector=query_vec.tolist(),
                limit=self._MAX_RAG_PARAGRAPHS,
                score_threshold=0.3,
            )
            if not results:
                return ""

            lines = ["\n## 语义相关前文片段 (RAG)\n"]
            for r in results:
                payload = r.payload or {}
                lines.append(
                    f"- [第{payload.get('chapter', '?')}章] {payload.get('text', '')[:200]}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.exception(f"Architect: RAG 检索跳过 ({e})")
            logger.debug(f"Architect: RAG 检索跳过 ({e})")
            return ""

    def _build_blueprint_prompt(
        self,
        chapter: int,
        chapter_type: str,
        template: dict,
        kg_summary: str,
        preference_hints: str,
        rag_context: str = "",
    ) -> str:
        """构建蓝图生成提示词（含 RAG 语义上下文 + Token 预算控制，参考 WenShape 6段分配）"""
        word_min, word_max = template.get("word_count_range", (2000, 3000))
        scene_min, scene_max = template.get("scene_count", (2, 4))
        pleasure_min = template.get("pleasure_point_min", 1)

        system_rules = f"""你是网文架构师。为第{chapter}章（类型={chapter_type}）生成详细蓝图。

要求:
- 字数: {word_min}-{word_max}字
- 场景: {scene_min}-{scene_max}个
- 爽点: 至少{pleasure_min}个
- 结尾钩子: 必须

输出 JSON 格式:
{{
  "arc_stage": "从 ordinary_world/call_to_adventure/refusal/mentor/crossing/\
tests/approach/ordeal/reward/road_back/resurrection/return 中选一个",
  "scenes": [
    {{
      "title": "场景标题", "function": "introduce/develop/climax/resolve/transition",
      "location": "地点", "word_estimate": 800, "summary": "场景概要 (1-2句)",
      "characters_involved": ["角色名"], "emotion": "开场情绪", "pleasure_points": []
    }}
  ],
  "emotion_curve": {{ "start_emotion": "开场情绪", "end_emotion": "结尾情绪",
    "peak_chart": [{{"position_pct": 0.3, "emotion": "excitement", "intensity": 0.8}}] }},
  "pleasure_points": [
    {{"type": "slap_face/level_up/treasure/revenge/revelation/romance/show_off",\
 "scene_at": 0, "description": "描述"}}
  ],
  "foreshadowing": {{ "to_plant": ["新伏笔1"], "to_reveal": ["应揭示的伏笔"] }},
  "hook_requirement": {{ "type": "question/twist/cliffhanger/emotional",\
        "description": "钩子设计" }},
  "audit_risk_marks": {{ "G2_info_dump_risk": false, "G6_emotion_shift_risk": false }}
}}
"""

        # 使用 WenShape 风格的 Token 预算分配器裁剪上下文
        # 分配策略：system_rules（含JJON模板）占40%，RAG占20%，其余按比例
        blueprint_allocation = {
            "system_rules": 0.40,  # 模板+指令占大头
            "character_cards": 0.15,  # KG摘要
            "chapter_summaries": 0.20,  # RAG相关段落
            "dynamic_facts": 0.05,  # 偏好提示
            "output_reserve": 0.20,  # 输出预留
        }
        allocator = ContextBudgetAllocator(
            total_budget=int(self._MAX_CONTEXT_TOKENS * 1.5),  # 中文 1 token≈1.5字符
            allocation=blueprint_allocation,
            current_chapter=chapter,
        )
        assembled = allocator.assemble(
            {
                "system_rules": system_rules,
                "character_cards": (kg_summary or "")[:3000],
                "chapter_summaries": (rag_context or ""),
                "dynamic_facts": (preference_hints or ""),
            }
        )

        # 按分配顺序拼接上下文
        prompt = assembled["system_rules"]
        if assembled.get("character_cards"):
            prompt += "\n## 参考上下文\n" + assembled["character_cards"]
        if assembled.get("chapter_summaries"):
            prompt += "\n## RAG 相关段落\n" + assembled["chapter_summaries"]
        if assembled.get("dynamic_facts"):
            prompt += "\n## 偏好提示\n" + assembled["dynamic_facts"]
        prompt += "\n只输出 JSON，不要任何额外解释。"
        return prompt

    def _parse_blueprint_json(self, text: str) -> dict | None:
        """从 LLM 回复中提取 JSON 蓝图"""
        if not text:
            return None

        # 移除 markdown 代码块标记
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)

        # 找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None

        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            # 尝试修复常见问题：尾随逗号、单引号
            try:
                fixed = text[start : end + 1]
                fixed = re.sub(r",\s*}", "}", fixed)
                fixed = re.sub(r",\s*]", "]", fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                logger.warning("Architect: JSON 解析失败，降级为模板默认")
                return None

    def _merge_blueprint(
        self,
        llm_output: dict,
        template: dict,
        book_id: str,
        chapter: int,
        chapter_type: str,
        kg_snapshot_id: str,
    ) -> dict:
        """合并 LLM 输出与模板默认值"""
        return {
            "book_id": book_id,
            "chapter": chapter,
            "chapter_type": chapter_type,
            "word_count_target": sum(template["word_count_range"]) // 2,
            "kg_snapshot_id": kg_snapshot_id,
            # LLM 生成内容（存在则用，否则空）
            "arc_stage": llm_output.get("arc_stage", ""),
            "scenes": llm_output.get("scenes", []),
            "emotion_curve": llm_output.get(
                "emotion_curve",
                {
                    "start_emotion": "neutral",
                    "end_emotion": "tension",
                    "peak_chart": [],
                },
            ),
            "pleasure_points": llm_output.get("pleasure_points", []),
            "foreshadowing": llm_output.get(
                "foreshadowing",
                {
                    "to_plant": [],
                    "to_reveal": [],
                    "overdue": [],
                },
            ),
            "hook_requirement": llm_output.get(
                "hook_requirement",
                {
                    "type": "question",
                    "description": "",
                    "strength_target": 0.7,
                },
            ),
            "audit_risk_marks": llm_output.get(
                "audit_risk_marks",
                {
                    "G1_arc_deviation": False,
                    "G2_info_dump": False,
                    "G3_ai_detection": False,
                    "G4_pleasure_gap": False,
                    "G6_emotion_shift": False,
                },
            ),
            "style_hints": llm_output.get("style_hints", []),
            "dependencies": llm_output.get("dependencies", []),
        }

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        if msg.msg_type == "GENERATE_BLUEPRINT":
            result = await self.execute(msg.payload)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="BLUEPRINT_READY",
                payload=result,
                correlation_id=msg.correlation_id,
                kg_snapshot_id=msg.kg_snapshot_id,
            )
        return None

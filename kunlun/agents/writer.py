"""
昆仑创作引擎 — Writer (正文生成)
职责: 蓝图 + KG → LLM抽卡生成 → 评分 → 选最优段落
"""

from __future__ import annotations

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.gacha.engine import gacha_engine


class Writer(BaseAgent):
    """
    写手

    能力边界:
    - ✅ 从蓝图生成正文
    - ✅ 多模型并行生成
    - ✅ 根据审计报告修订
    - ❌ 不许改蓝图/大纲
    - ❌ 不许做审计判断
    """

    agent_name = "writer"
    capabilities = [
        "draft_generation",
        "multi_model_parallel",
        "audit_fix_revision",
        "style_injection",
    ]

    def __init__(self, nats_client=None):
        super().__init__(nats_client)
        self.gacha = gacha_engine
        self._budget_allocator = None  # 懒加载缓存，避免每次 prompt 构建都重新实例化

    async def execute(self, task: dict) -> dict:
        """生成或修订正文"""
        action = task.get("action", "generate")

        if action == "generate":
            return await self._generate(task)
        if action == "revise":
            return await self._revise(task)
        return {"success": False, "error": f"未知动作: {action}"}

    async def _generate(self, task: dict) -> dict:
        """多模型抽卡生成正文"""
        blueprint = task.get("blueprint", {})
        mode = task.get("mode", "gacha_parallel_3")
        kg_snapshot_id = task.get("kg_snapshot_id", "")
        preference_hints = task.get("preference_hints", "")

        # 构建提示词
        prompt = self._build_prompt(blueprint, kg_snapshot_id, preference_hints)

        # 调用抽卡引擎
        result = await self.gacha.generate(prompt, mode=mode)

        logger.info(f"Writer: ch{blueprint.get('chapter')} 生成完成 (模式={mode})")

        # 输出质量验证
        is_valid, issues = self._validate_output(result["best_text"])
        draft = result["best_text"]
        if not is_valid:
            logger.warning(f"Writer 质量警告: {'; '.join(issues)}")

        return {
            "success": True,
            "draft": draft,
            "gacha_details": result.get("details", {}),
            "model_used": result.get("model_used"),
            "scores": result.get("scores", {}),
            "warnings": issues if not is_valid else [],
        }

    async def _revise(self, task: dict) -> dict:
        """根据审计报告修订 — 4模式分类（InkOS: spot-fix/rewrite/polish/anti-detect）

        模式选择逻辑:
        - 仅G3(AI痕迹)失败 → anti-detect（最低成本，去AI专项）
        - 仅G7(对话)失败 → spot-fix（精准修复问题段落）
        - 3个以下门禁失败 → polish（全面优化）
        - 3个以上/G1(弧线)失败 → rewrite（重大重写）
        """
        draft = task.get("draft", "")
        audit_report = task.get("audit_report", {})

        # 提取失败的审计项
        failed_gates = [
            g
            for g, r in audit_report.get("gates", {}).items()
            if r.get("level") in ("FAIL", "CRITICAL")
        ]

        # ── 智能选择修订模式 ──
        if set(failed_gates) <= {"G3"}:
            # 仅AI痕迹问题 → anti-detect（最低成本）
            mode = "anti_detect"
            fix_prompt = self._build_anti_detect_prompt(draft)
            logger.info("Writer: 选择 anti-detect 模式 (仅G3失败)")
        elif set(failed_gates) <= {"G7", "G6"}:
            # 仅对话/情感问题 → spot-fix（段落级修复）
            mode = "spot_fix"
            fix_prompt = self._build_spot_fix_prompt(draft, audit_report, failed_gates)
            logger.info(f"Writer: 选择 spot-fix 模式 ({len(failed_gates)}个门禁)")
        elif len(failed_gates) <= 3 and "G1" not in failed_gates:
            # 3个以下非关键门禁 → polish
            mode = "polish"
            fix_prompt = self._build_fix_prompt(draft, audit_report, failed_gates)
            logger.info(f"Writer: 选择 polish 模式 ({len(failed_gates)}个门禁)")
        else:
            # 3个以上或G1失败 → rewrite（全文重写）
            mode = "rewrite"
            fix_prompt = self._build_rewrite_prompt(draft, audit_report, failed_gates)
            logger.info("Writer: 选择 rewrite 模式 (严重问题)")

        # 执行修订（spot-fix/anti-detect 用 single_fix 节省成本，rewrite则走并行抽卡）
        effective_mode = "single_fix" if mode in ("spot_fix", "anti_detect", "polish") else mode
        result = await self.gacha.generate(fix_prompt, mode=effective_mode)

        revised_draft = result.get("best_text", draft)
        if len(revised_draft) < len(draft) * 0.5:
            logger.warning(f"Writer: 修订后文本过短 ({len(revised_draft)}字)，保留原文")
            revised_draft = draft

        logger.info(f"Writer: {mode} 修订完成，修复 {len(failed_gates)} 个失败门禁")
        return {
            "success": True,
            "draft": revised_draft,
            "fixed_gates": failed_gates,
            "revision_mode": mode,
        }

    def _build_spot_fix_prompt(
        self, draft: str, audit_report: dict, failed_gates: list[str]
    ) -> str:
        """构建精准段落修复提示词"""
        issues_detail = self._format_audit_issues(audit_report, failed_gates)
        return (
            f"请对以下文本进行**精准修复**，只修改有问题段落，保持其余内容完全不变。\n\n"
            f"需要修复的问题:\n{issues_detail}\n\n"
            f"原文:\n{draft[:6000]}\n\n"
            f"要求:\n"
            f"1. 只修改有问题的地方，无关段落一字不改\n"
            f"2. 保持原意、字数、风格\n"
            f"3. 直接输出修改后的全文"
        )

    def _build_anti_detect_prompt(self, draft: str) -> str:
        """构建反AI检测改写提示词"""
        return (
            f"请对以下文本做**反AI检测改写**，移除AI生成痕迹。\n\n"
            f"原文:\n{draft[:6000]}\n\n"
            f"要求:\n"
            f"1. 替换'仿佛/忽然/似乎'等套话词为具体描写\n"
            f"2. 长短句交替，打破均匀段落节奏\n"
            f"3. 减少'然而/因此/此外'等连词，用直接叙述推进\n"
            f"4. 在对话中加入语气词和动作描写\n"
            f"5. 保持原意和字数不变\n"
            f"6. 直接输出改写后的全文"
        )

    def _build_rewrite_prompt(self, draft: str, audit_report: dict, failed_gates: list[str]) -> str:
        """构建全文重写提示词"""
        issues_detail = self._format_audit_issues(audit_report, failed_gates)
        return (
            f"请对以下文本进行**全文重写**，以解决所有质量问题。\n\n"
            f"需要解决的关键问题:\n{issues_detail}\n\n"
            f"原文:\n{draft[:6000]}\n\n"
            f"要求:\n"
            f"1. 保持核心情节和人物不变\n"
            f"2. 提高文笔质量\n"
            f"3. 解决所有提到的质量问题\n"
            f"4. 字数与原章相近（±20%）\n"
            f"5. 直接输出重写后的全文"
        )

    @staticmethod
    def _format_audit_issues(audit_report: dict, failed_gates: list[str]) -> str:
        """格式化审计问题"""
        lines = []
        gates = audit_report.get("gates", {})
        for g in failed_gates:
            info = gates.get(g, {})
            lines.append(f"- {g}: {info.get('detail', '')}")
        return "\n".join(lines) if lines else "质量问题"

    def _validate_output(self, draft: str) -> tuple:
        """验证输出质量，返回 (is_valid, issues)。

        检查项:
        - 基线: draft 非空且 >= 50 字符
        - 段落: 至少 2 个自然段（\n\n 分割）
        - AI 味: 高频 AI 短语 >= 2 个即警告
        - 中文引号配对: " 和 " 数量相等
        - 连续重复标点: ，， 和 。。
        """
        issues = []

        # 1. 基线检查
        if not draft or len(draft) < 50:
            issues.append("正文为空或不足50字符")
            return (False, issues)

        # 2. 段落检查
        paragraphs = [p for p in draft.split("\n\n") if p.strip()]
        if len(paragraphs) < 2:
            issues.append("自然段落不足2个")

        # 3. AI 味快速检测
        ai_phrases = [
            "值得注意的是",
            "综上所述",
            "另外",
            "此外",
            "首先其次然后最后",
            "总的来说",
            "毫无疑问",
            "由此可见",
        ]
        ai_count = sum(draft.count(phrase) for phrase in ai_phrases)
        if ai_count >= 2:
            issues.append(f"检测到高频AI短语模式({ai_count}处)")

        # 4. 中文引号配对
        left_count = draft.count("\u201c")  # "
        right_count = draft.count("\u201d")  # "
        if left_count != right_count:
            issues.append(f"中文引号不配对(左{left_count}右{right_count})")

        # 5. 连续重复标点
        if "\uff0c\uff0c" in draft:
            issues.append("检测到连续逗号(，，)")
        if "\u3002\u3002" in draft:
            issues.append("检测到连续句号(。。)")

        is_valid = len(issues) == 0
        return (is_valid, issues)

    def _build_prompt(
        self, blueprint: dict, kg_snapshot_id: str, preference_hints: str = ""
    ) -> str:
        """构建生成提示词 — 使用 WenShape 风格 Token 预算控制"""
        chapter = blueprint.get("chapter", 0)
        chapter_type = blueprint.get("chapter_type", "normal")
        word_count = blueprint.get("word_count_target", 2500)
        hook_req = blueprint.get("hook_requirement", {})
        hook_type = hook_req.get("type", "question")
        hook_desc = hook_req.get("description", "")

        scenes = blueprint.get("scenes", [])
        emotion_curve = blueprint.get("emotion_curve", {})
        pleasure_points = blueprint.get("pleasure_points", [])
        foreshadowing = blueprint.get("foreshadowing", {})
        arc_stage = blueprint.get("arc_stage", "")
        audit_risk_marks = blueprint.get("audit_risk_marks", {})

        base = f"""写网文第{chapter}章，类型{chapter_type}，字数目标{word_count}。

KG快照: {kg_snapshot_id}

## 章节蓝图
- 弧线阶段: {arc_stage}
- 情绪曲线: {emotion_curve.get("start_emotion", "")} → {emotion_curve.get("end_emotion", "")}
- 结尾钩子: {hook_type} ({hook_desc})

## 场景设计 ({len(scenes)}个)
"""
        for i, scene in enumerate(scenes, 1):
            base += (
                f"{i}. 【{scene.get('title', '未命名')}】"
                f"{scene.get('function', '')} - {scene.get('summary', '')}\n"
            )
            if scene.get("characters_involved"):
                base += f"   涉及角色: {', '.join(scene['characters_involved'])}\n"
            if scene.get("pleasure_points"):
                pps = scene["pleasure_points"]
                if pps and isinstance(pps[0], dict):
                    pps = [p.get("name", str(p)) for p in pps]
                base += f"   爽点: {', '.join(pps)}\n"

        if pleasure_points:
            base += f"\n## 爽点排布 ({len(pleasure_points)}个)\n"
            for pp in pleasure_points:
                base += (
                    f"- {pp.get('type', '')}: {pp.get('description', '')} "
                    f"(场景{pp.get('scene_at', 0) + 1})\n"
                )

        if foreshadowing:
            to_reveal = foreshadowing.get("to_reveal", [])
            to_plant = foreshadowing.get("to_plant", [])
            base += "\n## 伏笔指令\n"
            if to_reveal:
                base += f"必须揭示: {', '.join(to_reveal)}\n"
            if to_plant:
                base += f"必须安插: {', '.join(to_plant)}\n"

        if audit_risk_marks:
            risks = [k for k, v in audit_risk_marks.items() if v]
            if risks:
                base += "\n## 审计风险预标 (需特别注意)\n"
                for risk in risks:
                    base += f"- {risk}\n"

        base += f"""
## 写作要求
- 严格按场景顺序和功能推进
- 实现情绪曲线: {emotion_curve.get("start_emotion", "")} → {emotion_curve.get("end_emotion", "")}
- 结尾必须实现 {hook_type} 钩子: {hook_desc}
- 不使用明显的AI写作用语(然而/此外/首先其次/总而言之)
- 句式长短交替，段落长度不均匀
- 对话自然口语化
- 爽点要自然融入情节，不突兀
"""

        if preference_hints:
            base += f"\n## 作者偏好提示\n{preference_hints}"

        # Token 预算控制：仅当提示词过长时截断（缓存allocator实例避免重复创建）
        try:
            if self._budget_allocator is None:
                from kunlun.config import settings
                from kunlun.context.budget import ContextBudgetAllocator

                writer_budget = getattr(settings, "writer_context_budget", 8000)
                self._budget_allocator = ContextBudgetAllocator(
                    total_budget=writer_budget,
                    allocation={
                        "system_rules": 0.10,
                        "current_blueprint": 0.50,
                        "character_cards": 0.10,
                        "chapter_summaries": 0.10,
                        "output_reserve": 0.20,
                    },
                    current_chapter=chapter,
                )
            budget = self._budget_allocator.get_segment_budget("current_blueprint")
            # 中文 1 token ≈ 1.5 字符
            char_limit = int(budget * 1.5)
            if len(base) > char_limit:
                base = base[:char_limit]
                logger.debug(f"[Writer] 提示词已按预算截断至 {char_limit} 字")
        except ImportError as e:
            from kunlun.exceptions import WriterBudgetError

            logger.debug(f"[Writer] 上下文预算模块未安装，跳过截断: {e}")
            raise WriterBudgetError(f"上下文预算模块导入失败: {e}") from e
        except (ValueError, TypeError) as e:
            from kunlun.exceptions import WriterBudgetError

            logger.debug(f"[Writer] 上下文预算截断跳过: {e}")
            raise WriterBudgetError(f"上下文预算计算异常: {e}") from e

        return base

    def _build_fix_prompt(self, draft: str, audit: dict, failed_gates: list) -> str:
        """构建修订提示词（含智能截断，避免超大prompt浪费Token）"""
        issues = "\n".join(
            f"- {g}: {audit['gates'].get(g, {}).get('detail', '')}" for g in failed_gates
        )
        # 智能截断：修订场景只需关心中间段落，头尾各保留1500字
        _max_draft_chars = 8000
        if len(draft) > _max_draft_chars:
            head = draft[:1500]
            tail = draft[-1500:]
            draft = (
                f"{head}\n\n...[中间{len(draft) - 3000}字已省略，请参考头尾风格修复]...\n\n{tail}"
            )
        return f"""以下网文章节未通过质检，请修复以下问题并重写:

问题:
{issues}

原始正文:
{draft}

修复后的正文（保持原有情节，只修复上述问题）:
"""

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        if msg.msg_type in ("GENERATE_DRAFT", "REVISE"):
            action = "revise" if msg.msg_type == "REVISE" else "generate"
            result = await self.execute({**msg.payload, "action": action})
            response_type = "DRAFT_READY"
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type=response_type,
                payload=result,
                correlation_id=msg.correlation_id,
                kg_snapshot_id=msg.kg_snapshot_id,
            )
        return None

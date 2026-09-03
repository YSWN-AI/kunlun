"""
昆仑创作引擎 — 辩论管线集成与自适应终止 (DebatePipelineIntegration)

在创作管线的关键节点自动触发多Agent辩论，实现：
  1. 纯规则触发判断（零LLM成本）
  2. 调用 DebateOrchestrator 执行辩论
  3. 自适应终止（共识度阈值 / 最大轮次 / 连续无新共识）
  4. 生成最终决议和修订优先级
  5. 持久化到 DebateStore

辩论触发点:
  - blueprint_review: 蓝图评审阶段（大纲生成后）
  - chapter_final: 章节终评阶段（初稿完成后）
  - quality_gate: 质量门禁阶段（审计不通过时）
"""

from __future__ import annotations

from typing import Any

from loguru import logger

# ══════════════════════════════════════════════════════
# 辩论触发点常量
# ══════════════════════════════════════════════════════

TRIGGER_BLUEPRINT_REVIEW = "blueprint_review"
TRIGGER_CHAPTER_FINAL = "chapter_final"
TRIGGER_QUALITY_GATE = "quality_gate"

VALID_TRIGGERS = (TRIGGER_BLUEPRINT_REVIEW, TRIGGER_CHAPTER_FINAL, TRIGGER_QUALITY_GATE)


# ══════════════════════════════════════════════════════
# DebatePipelineIntegration
# ══════════════════════════════════════════════════════


class DebatePipelineIntegration:
    """辩论管线集成器

    在创作管线的关键节点自动触发辩论，管理辩论生命周期，
    计算共识度，自适应终止，生成决议并持久化。

    所有触发判断、共识度计算、终止判断、决议生成都用纯规则实现，
    不调用LLM。辩论执行本身委托给 DebateOrchestrator。
    """

    # 触发阈值
    BLUEPRINT_COMPLEXITY_CHAPTER_THRESHOLD = 10
    BLUEPRINT_COMPLEXITY_CHARACTER_THRESHOLD = 5
    BLUEPRINT_QUALITY_THRESHOLD = 70
    CHAPTER_QUALITY_THRESHOLD = 80

    def __init__(
        self,
        debate_orchestrator: Any = None,
        debate_store: Any = None,
        max_rounds: int = 3,
        consensus_threshold: float = 0.7,
    ) -> None:
        self.debate_orchestrator = debate_orchestrator
        self.debate_store = debate_store
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self._debate_enabled = True

    # ── 触发判断（纯规则，零LLM） ──────────────────────

    def should_trigger_debate(
        self,
        trigger_type: str,
        chapter_data: dict[str, Any],
        quality_score: float | None = None,
    ) -> bool:
        """判断是否需要触发辩论（纯规则，零LLM）

        Args:
            trigger_type: 触发点类型
            chapter_data: 章节数据（包含章节数、角色数、问题列表等）
            quality_score: 质量评分（可选）

        Returns:
            是否触发辩论
        """
        if trigger_type not in VALID_TRIGGERS:
            logger.warning(f"[DebatePipeline] 未知触发点: {trigger_type}")
            return False

        if trigger_type == TRIGGER_BLUEPRINT_REVIEW:
            return self._should_trigger_blueprint(chapter_data, quality_score)
        if trigger_type == TRIGGER_CHAPTER_FINAL:
            return self._should_trigger_chapter_final(chapter_data, quality_score)
        if trigger_type == TRIGGER_QUALITY_GATE:
            return self._should_trigger_quality_gate(chapter_data)
        return False

    def _should_trigger_blueprint(
        self, chapter_data: dict[str, Any], quality_score: float | None
    ) -> bool:
        """蓝图评审触发判断

        规则: 大纲复杂度>阈值（章节数>10或角色数>5）或质量分<70
        """
        chapter_count = chapter_data.get("chapter_count", 0)
        character_count = chapter_data.get("character_count", 0)

        is_complex = (
            chapter_count > self.BLUEPRINT_COMPLEXITY_CHAPTER_THRESHOLD
            or character_count > self.BLUEPRINT_COMPLEXITY_CHARACTER_THRESHOLD
        )
        is_low_quality = (
            quality_score is not None
            and quality_score < self.BLUEPRINT_QUALITY_THRESHOLD
        )

        return is_complex or is_low_quality

    def _should_trigger_chapter_final(
        self, chapter_data: dict[str, Any], quality_score: float | None
    ) -> bool:
        """章节终评触发判断

        规则: 质量分<80或检测到严重问题（毒点/逻辑硬伤）
        """
        is_low_quality = (
            quality_score is not None
            and quality_score < self.CHAPTER_QUALITY_THRESHOLD
        )

        # 检测严重问题
        issues = chapter_data.get("issues", [])
        has_severe_issue = False
        severe_keywords = ("毒点", "逻辑硬伤", "严重", "致命", "崩坏")
        for issue in issues:
            issue_text = issue if isinstance(issue, str) else str(issue.get("description", ""))
            severity = issue.get("severity", 0) if isinstance(issue, dict) else 0
            if any(kw in issue_text for kw in severe_keywords) or severity >= 4:
                has_severe_issue = True
                break

        # 也检查chapter_data中的severe_issues标记
        if chapter_data.get("has_severe_issues", False):
            has_severe_issue = True

        return is_low_quality or has_severe_issue

    def _should_trigger_quality_gate(self, chapter_data: dict[str, Any]) -> bool:
        """质量门禁触发判断

        规则: 审计门禁未通过（G1-G8任一不通过）
        """
        # 检查audit_passed标记
        if chapter_data.get("audit_passed", True) is False:
            return True

        # 检查gates字典
        gates = chapter_data.get("gates", {})
        if gates:
            for gate_name, passed in gates.items():
                if gate_name.startswith("G") and not passed:
                    return True

        # 检查failed_gates列表
        failed_gates = chapter_data.get("failed_gates", [])
        return bool(failed_gates)

    # ── 辩论执行 ────────────────────────────────────────

    async def run_debate_at_stage(
        self,
        trigger_type: str,
        text: str,
        chapter: int,
        outline: str = "",
        context: str = "",
        book_id: str = "default",
    ) -> dict[str, Any]:
        """在关键节点自动触发辩论的完整流程

        流程:
          1. should_trigger_debate 判断是否需要
          2. 如果需要，调用 debate_orchestrator.orchestrate_debate()
          3. 自适应终止判断
          4. 生成最终决议
          5. 保存到 debate_store
          6. 返回结果

        Args:
            trigger_type: 触发点类型
            text: 章节文本
            chapter: 章节号
            outline: 大纲信息
            context: 上下文
            book_id: 书籍ID

        Returns:
            {triggered, debate_result, final_decision, record_id}
            或 {triggered: False, reason}
        """
        # 1. 触发判断
        chapter_data = self._build_chapter_data(text, outline)
        quality_score = self._estimate_quality_score(text)

        if not self.should_trigger_debate(trigger_type, chapter_data, quality_score):
            reason = self._get_skip_reason(trigger_type, chapter_data, quality_score)
            logger.info(f"[DebatePipeline] 跳过辩论 ({trigger_type}): {reason}")
            return {"triggered": False, "reason": reason}

        # 2. 执行辩论
        if self.debate_orchestrator is None:
            # 延迟导入默认orchestrator
            from kunlun.agents.debate_orchestrator import DebateOrchestrator

            self.debate_orchestrator = DebateOrchestrator(max_rounds=self.max_rounds)

        logger.info(f"[DebatePipeline] 触发辩论 ({trigger_type}): 第{chapter}章")
        debate_context = f"{outline}\n{context}".strip()
        debate_result = await self.debate_orchestrator.orchestrate_debate(
            text=text, chapter=chapter, context=debate_context
        )

        # 3. 计算共识度和自适应终止（辩论已由orchestrator执行完毕，
        #    这里基于最终结果做终止判断和决议生成）
        consensus = self.calculate_consensus(debate_result)

        # 4. 生成最终决议
        final_decision = self.generate_final_decision(debate_result)

        # 5. 提取修订优先级
        revision_priority = self.get_revision_priority(debate_result)

        # 6. 保存到store
        record_id = ""
        if self.debate_store is not None:
            from kunlun.agents.debate_store import DebateRecord

            record = DebateRecord(
                record_id="",
                book_id=book_id,
                chapter=chapter,
                debate_type=trigger_type,
                debate_result=debate_result.to_dict() if hasattr(debate_result, "to_dict") else {},
                final_decision=final_decision,
                revision_suggestions=revision_priority,
                consensus_score=consensus,
                status="resolved",
                metadata={
                    "trigger_type": trigger_type,
                    "quality_score": quality_score,
                    "consensus": consensus,
                },
            )
            record_id = self.debate_store.save_record(record)

        # 7. 返回结果
        result_dict = (
            debate_result.to_dict() if hasattr(debate_result, "to_dict") else {}
        )
        return {
            "triggered": True,
            "debate_result": result_dict,
            "final_decision": final_decision,
            "record_id": record_id,
            "consensus_score": consensus,
            "revision_priority": revision_priority,
        }

    # ── 共识度计算 ──────────────────────────────────────

    def calculate_consensus(self, debate_result: Any) -> float:
        """计算辩论共识度

        公式: agreed_issues / (agreed_issues + unresolved_issues)
        如果总数为0返回1.0（无问题=完全共识）

        Args:
            debate_result: DebateResult对象或字典

        Returns:
            共识度 0.0-1.0
        """
        if isinstance(debate_result, dict):
            agreed = debate_result.get("agreed_issues", 0)
            unresolved = debate_result.get("unresolved_issues", 0)
        else:
            agreed = getattr(debate_result, "agreed_issues", 0)
            unresolved = getattr(debate_result, "unresolved_issues", 0)

        total = agreed + unresolved
        if total == 0:
            return 1.0
        return round(agreed / total, 3)

    # ── 自适应终止判断 ──────────────────────────────────

    def should_continue_debate(
        self,
        round_results: list[Any],
        current_round: int,
        max_rounds: int | None = None,
        consensus_threshold: float | None = None,
    ) -> bool:
        """自适应终止判断

        规则:
          - 如果当前轮次>=max_rounds，终止
          - 如果共识度>=consensus_threshold，提前终止
          - 如果连续2轮无新问题达成共识，终止
          - 否则继续

        Args:
            round_results: 各轮辩论结果列表（DebateResult或dict）
            current_round: 当前轮次（从1开始）
            max_rounds: 最大轮次（None则用实例默认值）
            consensus_threshold: 共识度阈值（None则用实例默认值）

        Returns:
            True=继续辩论，False=终止
        """
        if max_rounds is None:
            max_rounds = self.max_rounds
        if consensus_threshold is None:
            consensus_threshold = self.consensus_threshold

        # 规则1: 达到最大轮次
        if current_round >= max_rounds:
            logger.debug(f"[DebatePipeline] 达到最大轮次 {max_rounds}，终止")
            return False

        # 规则2: 共识度达到阈值
        if round_results:
            latest = round_results[-1]
            consensus = self.calculate_consensus(latest)
            if consensus >= consensus_threshold:
                logger.debug(
                    f"[DebatePipeline] 共识度 {consensus:.2f} >= "
                    f"阈值 {consensus_threshold}，提前终止"
                )
                return False

        # 规则3: 连续2轮无新共识
        if len(round_results) >= 2:
            last_two = round_results[-2:]
            no_new_consensus = True
            for r in last_two:
                agreed = self._get_agreed_count(r)
                if agreed > 0:
                    no_new_consensus = False
                    break
            if no_new_consensus:
                logger.debug("[DebatePipeline] 连续2轮无新共识，终止")
                return False

        return True

    @staticmethod
    def _get_agreed_count(debate_result: Any) -> int:
        """从辩论结果中获取达成共识的问题数"""
        if isinstance(debate_result, dict):
            return debate_result.get("agreed_issues", 0)
        return getattr(debate_result, "agreed_issues", 0)

    # ── 最终决议生成 ────────────────────────────────────

    def generate_final_decision(self, debate_result: Any) -> str:
        """基于辩论结果生成最终决议文本

        规则:
          - 共识度>=0.8: "通过，建议按修订建议优化后发布"
          - 共识度0.5-0.8: "有条件通过，需重点修复达成共识的问题"
          - 共识度<0.5: "不通过，建议重写或大幅修改"

        包含具体的问题统计和优先级建议。

        Args:
            debate_result: DebateResult对象或字典

        Returns:
            最终决议文本
        """
        consensus = self.calculate_consensus(debate_result)

        if isinstance(debate_result, dict):
            agreed = debate_result.get("agreed_issues", 0)
            unresolved = debate_result.get("unresolved_issues", 0)
            total_score = debate_result.get("total_score", 0.0)
            suggestions = debate_result.get("revision_suggestions", [])
        else:
            agreed = getattr(debate_result, "agreed_issues", 0)
            unresolved = getattr(debate_result, "unresolved_issues", 0)
            total_score = getattr(debate_result, "total_score", 0.0)
            suggestions = getattr(debate_result, "revision_suggestions", [])

        # 基础决议
        if consensus >= 0.8:
            base_decision = "通过，建议按修订建议优化后发布"
        elif consensus >= 0.5:
            base_decision = "有条件通过，需重点修复达成共识的问题"
        else:
            base_decision = "不通过，建议重写或大幅修改"

        # 问题统计
        high_priority_count = sum(
            1
            for s in suggestions
            if isinstance(s, dict) and s.get("priority", 3) <= 2
        )

        decision_text = (
            f"【最终决议】{base_decision}\n"
            f"共识度: {consensus:.1%} (达成共识{agreed}个，未解决{unresolved}个)\n"
            f"综合评分: {total_score:.1f}/100\n"
            f"高优先级修订项: {high_priority_count}个"
        )

        if high_priority_count > 0:
            decision_text += "\n建议优先处理高优先级问题后再进入下一阶段。"

        return decision_text

    # ── 修订优先级提取 ──────────────────────────────────

    def get_revision_priority(
        self, debate_result: Any, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """从辩论结果中提取优先级最高的修订建议

        按priority排序，去重（按issue文本）。

        Args:
            debate_result: DebateResult对象或字典
            top_k: 返回数量上限

        Returns:
            修订建议列表，按优先级从高到低
        """
        if isinstance(debate_result, dict):
            suggestions = debate_result.get("revision_suggestions", [])
        else:
            suggestions = getattr(debate_result, "revision_suggestions", [])

        if not suggestions:
            return []

        # 标准化建议格式
        normalized: list[dict[str, Any]] = []
        seen_issues: set[str] = set()
        for sug in suggestions:
            if not isinstance(sug, dict):
                continue
            issue = sug.get("issue", "")
            if not issue or issue in seen_issues:
                continue
            seen_issues.add(issue)
            normalized.append(
                {
                    "issue": issue,
                    "suggestion": sug.get("suggestion", ""),
                    "priority": sug.get("priority", 3),
                    "round": sug.get("round", 0),
                }
            )

        # 按priority排序（数字越小优先级越高）
        normalized.sort(key=lambda s: s.get("priority", 3))
        return normalized[:top_k]

    # ── 管线集成接口 ────────────────────────────────────

    def integrate_with_pipeline(self, pipeline_engine: Any) -> None:
        """与创作管线集成的接口方法

        检查pipeline_engine是否有register_hook方法，
        如果有，注册辩论钩子到blueprint_review和chapter_final阶段。
        如果没有，记录日志但不报错。

        不实际修改pipeline代码，只提供集成接口。

        Args:
            pipeline_engine: 管线引擎实例
        """
        if pipeline_engine is None:
            logger.warning("[DebatePipeline] pipeline_engine为None，跳过集成")
            return

        if hasattr(pipeline_engine, "register_hook"):
            try:
                pipeline_engine.register_hook(
                    "blueprint_review", self._make_hook(TRIGGER_BLUEPRINT_REVIEW)
                )
                pipeline_engine.register_hook(
                    "chapter_final", self._make_hook(TRIGGER_CHAPTER_FINAL)
                )
                logger.info("[DebatePipeline] 已注册辩论钩子到管线")
            except Exception as e:
                logger.warning(f"[DebatePipeline] 注册钩子失败: {e}")
        else:
            logger.info(
                "[DebatePipeline] pipeline_engine无register_hook方法，"
                "辩论集成需手动调用run_debate_at_stage()"
            )

    def _make_hook(self, trigger_type: str):
        """创建管线钩子回调"""

        async def hook(context: dict[str, Any]) -> dict[str, Any]:
            text = context.get("text", context.get("draft", ""))
            chapter = context.get("chapter", 0)
            outline = context.get("outline", "")
            book_id = context.get("book_id", "default")
            return await self.run_debate_at_stage(
                trigger_type=trigger_type,
                text=text,
                chapter=chapter,
                outline=outline,
                book_id=book_id,
            )

        return hook

    # ── 内部工具 ────────────────────────────────────────

    @staticmethod
    def _build_chapter_data(text: str, outline: str) -> dict[str, Any]:
        """从文本和大纲中构建章节数据（用于触发判断）"""
        # 简单估算章节数和角色数
        chapter_count = text.count("第") + outline.count("第") if outline else 0
        # 角色数估算：统计常见姓氏+名字模式（简化）
        character_count = 0
        if outline:
            character_count = outline.count("：") // 2 if "：" in outline else 0

        return {
            "chapter_count": min(chapter_count, 50),
            "character_count": min(character_count, 20),
            "text_length": len(text),
            "has_outline": bool(outline),
        }

    @staticmethod
    def _estimate_quality_score(text: str) -> float:
        """基于文本长度简单估算质量分（用于触发判断的初始值）"""
        if not text:
            return 0.0
        length = len(text)
        # 长度在2000-5000字之间给较高基础分
        if 2000 <= length <= 5000:
            return 75.0
        if length > 5000:
            return 70.0
        return 60.0

    @staticmethod
    def _get_skip_reason(
        trigger_type: str, chapter_data: dict[str, Any], quality_score: float | None
    ) -> str:
        """生成跳过辩论的原因文本"""
        if trigger_type == TRIGGER_BLUEPRINT_REVIEW:
            return (
                f"大纲复杂度低 (章节数{chapter_data.get('chapter_count', 0)}, "
                f"角色数{chapter_data.get('character_count', 0)}) "
                f"且质量分{quality_score:.0f}>=70"
            )
        if trigger_type == TRIGGER_CHAPTER_FINAL:
            return f"质量分{quality_score:.0f}>=80且未检测到严重问题"
        if trigger_type == TRIGGER_QUALITY_GATE:
            return "审计门禁全部通过"
        return "不满足触发条件"

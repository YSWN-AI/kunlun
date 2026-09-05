"""
33维度连续性审计员 — 对照7个真相文件，全面检查每章草稿

维度分组:
  A: 角色一致性 (A1-A8)    — 记忆、性格、外貌、能力、位置、关系、情感、对话风格
  B: 物资连续性 (B1-B4)    — 物品、金钱、装备、消耗品
  C: 伏笔管理 (C1-C5)      — 种伏、回收、逾期、优先级、信息边界
  D: 叙事质量 (D1-D6)       — 节奏、弧线、大纲偏离、爽点密度、对话占比、描写密度
  E: 情感弧线 (E1-E4)       — 情绪曲线、情绪一致性、情感递进、读者共鸣
  F: AI痕迹检测 (F1-F6)     — 高频词、句式单调、过度总结、连词滥用、段落模式、结尾模板

使用方式:
    from kunlun.audit.audit33 import Auditor33, auditor33, Audit33Report, DimResult

    auditor = Auditor33()
    report = auditor.run_audit(draft, chapter=1, blueprint={}, book_id="my_book")
    if report.passed:
        print("33维审计通过")
    else:
        print(f"发现{report.fatal_count}个致命问题")

与8门禁系统(gates.py)的关系:
    audit33.py 是 gates.py 的超集和升级版。gates.py 的8个门禁(G1-G8)映射到
    audit33.py 的33个维度中。当 audit33.py 可用时，建议优先使用33维审计；
    gates.py 保留作为轻量级快速检查的备选方案。

实现架构:
    auditor33.py — 主类(Auditor33) + 编排逻辑
    _base33.py   — 共享数据(AI_FATIGUE_WORDS, DimResult, Audit33Report)
    groups/       — 6个分组 mixin(每个包含对应维度的检查方法):
        group_a_character.py   A1-A8 角色一致性
        group_b_plot.py        B1-B4 物资连续性
        group_c_structure.py   C1-C5 伏笔管理
        group_d_style.py       D1-D6 叙事质量
        group_e_reader.py      E1-E4 情感弧线
        group_f_ai.py          F1-F6 AI痕迹检测
"""

from __future__ import annotations

from loguru import logger

from ._base33 import Audit33Report, DimResult
from .groups import (
    Auditor33GroupA,
    Auditor33GroupB,
    Auditor33GroupC,
    Auditor33GroupD,
    Auditor33GroupE,
    Auditor33GroupF,
)


class Auditor33(
    Auditor33GroupA,
    Auditor33GroupB,
    Auditor33GroupC,
    Auditor33GroupD,
    Auditor33GroupE,
    Auditor33GroupF,
):
    """33维连续性审计员

    对照7个真相文件(checkpoint),全面检查每章草稿的:
    - 角色一致性(A1-A8): 记忆、性格、外貌、能力、位置、关系、情感、对话风格
    - 物资连续性(B1-B4): 物品、金钱、装备、消耗品
    - 伏笔管理(C1-C5): 种伏、回收、逾期、优先级、信息边界
    - 叙事质量(D1-D6): 节奏、弧线、大纲偏离、爽点密度、对话占比、描写密度
    - 情感弧线(E1-E4): 情绪曲线、情绪一致性、情感递进、读者共鸣
    - AI痕迹检测(F1-F6): 高频词、句式单调、过度总结、连词滥用、段落模式、结尾模板
    """

    def __init__(self):
        self._truth_manager = None

    def set_truth_manager(self, book_id: str):
        """绑定真相文件管理器"""
        from kunlun.truth import get_truth_manager

        self._truth_manager = get_truth_manager(book_id)

    # ═══════════════════════════════════════════════════════════════
    # 主接口
    # ═══════════════════════════════════════════════════════════════

    def _all_checks(self) -> list:
        """返回所有33个检查函数"""
        return [
            # A组: 角色一致性
            self._check_A1_character_memory,
            self._check_A2_character_personality,
            self._check_A3_appearance,
            self._check_A4_ability_consistency,
            self._check_A5_location,
            self._check_A6_relationship,
            self._check_A7_emotional_state,
            self._check_A8_dialogue_style,
            # B组: 物资连续性
            self._check_B1_inventory,
            self._check_B2_money,
            self._check_B3_equipment,
            self._check_B4_consumables,
            # C组: 伏笔管理
            self._check_C1_hook_planted,
            self._check_C2_hook_revealed,
            self._check_C3_overdue_hooks,
            self._check_C4_hook_priority,
            self._check_C5_info_boundary,
            # D组: 叙事质量
            self._check_D1_narrative_rhythm,
            self._check_D2_arc_compliance,
            self._check_D3_outline_deviation,
            self._check_D4_pleasure_density,
            self._check_D5_dialogue_ratio,
            self._check_D6_description_density,
            # E组: 情感弧线
            self._check_E1_emotion_curve,
            self._check_E2_emotion_consistency,
            self._check_E3_emotion_progression,
            self._check_E4_reader_resonance,
            # F组: AI痕迹检测
            self._check_F1_high_freq_words,
            self._check_F2_sentence_monotony,
            self._check_F3_over_summary,
            self._check_F4_conjunction_abuse,
            self._check_F5_paragraph_pattern,
            self._check_F6_ending_template,
        ]

    def run_audit(
        self, draft: str, chapter: int, blueprint: dict | None = None, book_id: str = ""
    ) -> Audit33Report:
        """运行33维审计

        Args:
            draft: 正文草稿
            chapter: 章节号
            blueprint: 蓝图字典 (包含 arc_stage, scenes, foreshadowing 等)
            book_id: 作品ID,用于加载真相文件

        Returns:
            Audit33Report 综合审计报告
        """
        if not draft or len(draft.strip()) < 50:
            report = Audit33Report(chapter=chapter)
            report.overall_score = 0
            report.passed = False
            report.summary = "草稿为空或过短(<50字符)，跳过审计"
            report.dimensions = []
            return report

        if book_id and not self._truth_manager:
            self.set_truth_manager(book_id)

        report = Audit33Report(chapter=chapter)
        bp = blueprint or {}

        for check_fn in self._all_checks():
            try:
                result = check_fn(draft, chapter, bp)
            except Exception as e:
                logger.error(f"[Audit33] {check_fn.__name__} 执行失败: {e}")
                result = DimResult(
                    dim_id=check_fn.__name__.split("_")[2][:2].upper(),
                    name=check_fn.__name__,
                    score=50.0,
                    level="WARN",
                    detail=f"检查执行异常: {str(e)[:50]}",
                )
            report.dimensions.append(result)
            if result.level == "FAIL":
                report.fatal_count += 1
            elif result.level == "WARN":
                report.warn_count += 1

        scores = [d.score for d in report.dimensions]
        report.overall_score = sum(scores) / len(scores) if scores else 0

        f_scores = [d.score for d in report.dimensions if d.dim_id.startswith("F")]
        report.ai_detection_score = sum(f_scores) / len(f_scores) if f_scores else 100

        report.passed = report.fatal_count == 0
        report.summary = (
            f"33维审计: {report.overall_score:.1f}分, "
            f"致命{report.fatal_count}, 警告{report.warn_count}, "
            f"AI痕迹评分{report.ai_detection_score:.1f}"
        )

        logger.info(f"[Audit33] 第{chapter}章审计完成: {report.summary}")
        return report

    async def auto_fix_ai_patterns(self, draft: str) -> str:
        """自动修复AI痕迹模式 — 调用LLM做反检测改写

        当F组多个维度检测到AI痕迹时,调用此方法进行改写。
        使用gacha_engine的single_fix模式进行精准修订。

        Args:
            draft: 待修复的正文

        Returns:
            修复后的正文
        """
        from kunlun.gacha.engine import gacha_engine

        prompt = f"""你是反AI检测专家。请重写以下文本，移除所有AI生成的痕迹。要求：

1. 替换高频套话词（突然/仿佛/似乎→更具体的描写）
2. 变化句式开头（避免连续"他/她"开头）
3. 删除总结性结尾（不要"通过这件事/这次经历"等）
4. 打断均匀段落（长短交替，战斗章用短段落）
5. 注入口语化表达（人物对话加语气词、口癖）
6. 保持原意和字数不变
7. 删除冗余连接词（然而/因此/于是→直接叙述）

原文：
{draft[:12000]}

直接输出改写后的全文，不要任何解释。"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            fixed_text = result.get("best_text", draft)
            if fixed_text == draft:
                logger.warning("[Audit33] LLM改写返回空或相同内容")
            return fixed_text
        except Exception as e:
            logger.error(f"[Audit33] 反检测改写失败: {e}")
            return draft


auditor33 = Auditor33()

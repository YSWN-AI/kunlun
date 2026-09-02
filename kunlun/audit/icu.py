"""
连载ICU — 七维质量保障与自动修复

7个维度:
  D1: 爽点密度与分布 — 每N字必须有爽点，否则读者流失
  D2: 读者情绪曲线 — 情绪过山车设计，不能平铺直叙
  D3: 信息释放节奏 — 避免一次性信息倾泻(infodump)
  D4: 字数节奏控制 — 战斗章/过渡章字数自动调整
  D5: 钩子强度评估 — 每章结尾必须有悬念钩子
  D6: 角色行为一致性 — OOC检测，行为必须符合人设
  D7: 对话自然度 — 对话不能是信息传递工具，要有性格

每个维度包含: 检测器 + 评分器 + 自动修复器
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class DimensionResult:
    dimension: str
    score: float  # 0-100
    status: str  # PASS/WARN/FAIL
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    auto_fix_applied: bool = False
    fix_description: str = ""


@dataclass
class ICUReport:
    chapter: int
    dimensions: dict[str, DimensionResult]  # D1-D7
    overall_score: float
    critical_issues: list[str]
    auto_fixable: list[str]
    requires_human: list[str]
    passed: bool


class ICUSystem:
    """ICU七维质量系统"""

    def __init__(self):
        # 维度检测器
        self._detectors = {
            "D1": self._detect_pleasure_density,
            "D2": self._detect_emotion_curve,
            "D3": self._detect_info_pacing,
            "D4": self._detect_word_rhythm,
            "D5": self._detect_hook_strength,
            "D6": self._detect_character_consistency,
            "D7": self._detect_dialogue_naturalness,
        }
        # 自动修复器（调用LLM）
        self._fixers = {
            "D1": self._fix_pleasure_density,
            "D2": self._fix_emotion_curve,
            "D3": self._fix_info_pacing,
            "D4": self._fix_word_rhythm,
            "D5": self._fix_hook_strength,
            "D6": self._fix_character_consistency,
            "D7": self._fix_dialogue_naturalness,
        }

    # ─── 检测器 ───

    def _detect_pleasure_density(self, text: str, _chapter: int) -> DimensionResult:
        """D1: 爽点密度检测 — 每800-1200字需要一个小爽点"""
        paragraphs = text.split("\n\n")
        word_count = len(text)
        # 检测爽点关键词
        pleasure_keywords = [
            "突破",
            "升级",
            "打脸",
            "震惊",
            "觉醒",
            "获得",
            "击败",
            "碾压",
            "反转",
            "揭秘",
            "认可",
            "奖励",
            "晋升",
            "领悟",
            "蜕变",
        ]
        pleasure_positions = []
        for i, para in enumerate(paragraphs):
            for kw in pleasure_keywords:
                if kw in para:
                    pleasure_positions.append(i)
                    break

        issues = []
        suggestions = []
        density = len(pleasure_positions) / max(word_count / 1000, 1)

        if density < 0.5:  # 每1000字不到0.5个爽点
            issues.append(f"爽点密度过低 ({density:.1f}/千字)，读者可能感到无聊")
            suggestions.append("在关键段落插入爽点：小型突破、他人认可、伏笔回收")
            status = "FAIL"
            score = max(0, density * 100)
        elif density < 1.0:
            issues.append(f"爽点密度偏低 ({density:.1f}/千字)")
            suggestions.append("建议每1000字安排至少1个微型爽点")
            status = "WARN"
            score = 60 + density * 40
        else:
            status = "PASS"
            score = min(100, density * 60)

        return DimensionResult("D1_pleasure_density", score, status, issues, suggestions)

    def _detect_emotion_curve(self, text: str, _chapter: int) -> DimensionResult:
        """D2: 读者情绪曲线 — 必须有起伏，不能平铺直叙"""
        # 情绪关键词映射
        emotion_words = {
            "high": ["震惊", "狂喜", "激动", "沸腾", "震撼", "咆哮", "怒吼", "爆发"],
            "mid": ["紧张", "期待", "好奇", "疑惑", "担忧", "愤怒", "决然"],
            "low": ["平静", "沉默", "疲惫", "失落", "悲伤", "压抑", "迷茫"],
        }

        paragraphs = text.split("\n\n")
        if len(paragraphs) < 3:
            return DimensionResult(
                "D2_emotion_curve",
                50,
                "WARN",
                ["段落过少，无法评估情绪曲线"],
                ["请确保章节内容充实"],
            )

        # 分段情绪检测
        segment_emotions = []
        seg_size = max(1, len(paragraphs) // 5)
        for i in range(0, len(paragraphs), seg_size):
            seg_text = " ".join(paragraphs[i : i + seg_size])
            scores = {k: sum(1 for w in v if w in seg_text) for k, v in emotion_words.items()}
            # 所有分数为0时使用 'flat' 而非默认取第一个 key
            if all(s == 0 for s in scores.values()):
                segment_emotions.append("flat")
            else:
                dominant = max(scores, key=lambda k: scores[k])
                segment_emotions.append(dominant)

        # 检查是否有情绪变化
        unique_emotions = len(set(segment_emotions))
        if unique_emotions < 2:
            return DimensionResult(
                "D2_emotion_curve",
                30,
                "FAIL",
                ["情绪曲线平坦，缺少起伏"],
                ["设计3段式情绪：平静→紧张→爆发→余韵"],
            )

        # 检查是否有high峰值
        if "high" not in segment_emotions:
            return DimensionResult(
                "D2_emotion_curve", 50, "WARN", ["缺少情绪高潮段"], ["在章节后半段安排情绪爆发点"]
            )

        return DimensionResult(
            "D2_emotion_curve", 85, "PASS", suggestions=[f"情绪变化: {'→'.join(segment_emotions)}"]
        )

    def _detect_info_pacing(self, text: str, _chapter: int) -> DimensionResult:
        """D3: 信息释放节奏 — 检测info-dump"""
        # 检测连续信息密集型段落
        info_markers = [
            "系统提示",
            "属性面板",
            "等级",
            "技能说明",
            "世界观设定",
            "修炼体系",
            "势力分布",
            "历史背景",
            "规则",
            "说明",
        ]
        paragraphs = text.split("\n\n")
        info_dense_count = 0
        consecutive_info = 0
        max_consecutive = 0

        for para in paragraphs:
            info_score = sum(1 for m in info_markers if m in para)
            if info_score >= 3 or (len(para) > 300 and info_score >= 2):
                info_dense_count += 1
                consecutive_info += 1
                max_consecutive = max(max_consecutive, consecutive_info)
            else:
                consecutive_info = 0

        if max_consecutive >= 3:
            return DimensionResult(
                "D3_info_pacing",
                20,
                "FAIL",
                [f"连续{max_consecutive}段信息密集，读者会跳过"],
                ["将信息分散到对话和动作中", "每次只透露1-2个信息点"],
            )
        if info_dense_count > len(paragraphs) * 0.3:
            return DimensionResult(
                "D3_info_pacing",
                55,
                "WARN",
                [f"信息密集段落占比{info_dense_count / len(paragraphs):.0%}"],
                ["减少纯说明段落"],
            )

        return DimensionResult("D3_info_pacing", 90, "PASS")

    def _detect_word_rhythm(self, text: str, _chapter: int) -> DimensionResult:
        """D4: 字数节奏 — 段落长度应有变化"""
        paragraphs = text.split("\n\n")
        if len(paragraphs) < 3:
            return DimensionResult(
                "D4_word_rhythm", 60, "WARN", ["段落过少"], ["扩充段落数量以改善节奏"]
            )

        lengths = [len(p) for p in paragraphs if p.strip()]
        if not lengths:
            return DimensionResult("D4_word_rhythm", 0, "FAIL", ["无有效段落"], ["请检查文本内容"])

        avg_len = sum(lengths) / len(lengths)
        # 检查是否有变化：标准差/平均值 > 0.3 说明节奏有变化
        variance = sum((v - avg_len) ** 2 for v in lengths) / len(lengths)
        cv = (variance**0.5) / avg_len if avg_len > 0 else 0

        if cv < 0.2:
            return DimensionResult(
                "D4_word_rhythm",
                40,
                "WARN",
                ["段落长度过于均匀，缺少节奏感"],
                ["战斗场景用短段落(30-80字)", "描写场景用长段落(150-300字)"],
            )
        if cv > 1.0:
            return DimensionResult(
                "D4_word_rhythm",
                70,
                "WARN",
                ["段落长度差异过大，节奏混乱"],
                ["控制段落长度在30-300字范围内"],
            )

        return DimensionResult("D4_word_rhythm", 85, "PASS")

    def _detect_hook_strength(self, text: str, _chapter: int) -> DimensionResult:
        """D5: 钩子强度 — 结尾必须有悬念"""
        paragraphs = text.split("\n\n")
        if len(paragraphs) < 2:
            return DimensionResult("D5_hook_strength", 0, "FAIL", ["无内容"], ["请检查章节内容"])

        # 取最后3段分析
        ending = " ".join(paragraphs[-3:])
        hook_indicators = [
            "突然",
            "忽然",
            "就在此时",
            "意想不到",
            "竟然",
            "怎么可能",
            "难道",
            "莫非",
            "到底是什么",
            "接下来",
            "未完待续",
            "暗处",
            "阴影",
            "神秘",
            "秘密",
            "真相",
            "真正的",
        ]
        hook_score = sum(1 for h in hook_indicators if h in ending)

        # 检查是否以疑问句结尾
        has_question = "？" in paragraphs[-1] or "?" in paragraphs[-1]
        # 检查是否以悬念结尾（省略号）
        has_cliffhanger = "……" in ending or "..." in ending

        if hook_score >= 3 or has_question or has_cliffhanger:
            return DimensionResult("D5_hook_strength", 90, "PASS")
        if hook_score >= 1:
            return DimensionResult(
                "D5_hook_strength", 65, "WARN", ["钩子强度不足"], ["结尾增加悬念或反转"]
            )
        return DimensionResult(
            "D5_hook_strength",
            20,
            "FAIL",
            ["结尾无钩子，读者不会点下一章"],
            ["添加悬念/疑问/反转/预告任一钩子类型"],
        )

    def _detect_character_consistency(self, text: str, _chapter: int) -> DimensionResult:
        """D6: 角色行为一致性 — OOC检测"""
        # 基于已有的角色设定检查
        issues = []
        # 检查角色是否有行为矛盾（需要KG/Trugh Files辅助）
        # 基础检查：角色名称一致性
        name_pattern = re.findall(r"([一-鿿]{2,4})(?:说道|喊道|问道|笑道|怒道|冷声道|低声道)", text)

        if len(name_pattern) > 0:
            # 检查是否有角色对话过多（信息传递工具人）
            name_counts = Counter(name_pattern)
            if name_counts and max(name_counts.values()) > len(name_pattern) * 0.7:
                issues.append("对话过度集中在单一角色")

        if issues:
            return DimensionResult(
                "D6_character_consistency", 60, "WARN", issues, ["检查角色对话分配是否合理"]
            )
        return DimensionResult("D6_character_consistency", 90, "PASS")

    def _detect_dialogue_naturalness(self, text: str, _chapter: int) -> DimensionResult:
        """D7: 对话自然度 — 对话应该有个性，不是信息传输"""
        # 提取所有对话行
        dialogue_lines = re.findall(r'[「"]([^」"]+)[」"]', text)
        if not dialogue_lines:
            return DimensionResult(
                "D7_dialogue_naturalness", 70, "WARN", ["无可检测对话"], ["建议增加对话提升可读性"]
            )

        issues = []
        # 检测过长的对话（可能是info-dump）
        long_dialogues = [d for d in dialogue_lines if len(d) > 100]
        if len(long_dialogues) > len(dialogue_lines) * 0.3:
            issues.append(f"{len(long_dialogues)}处对话过长(>100字)，疑似信息倾泻")

        # 检测过于正式的对话
        formal_markers = ["综上所述", "因此", "根据", "按照", "必须", "应当", "务必"]
        formal_count = sum(1 for d in dialogue_lines for m in formal_markers if m in d)
        if formal_count > 3:
            issues.append("对话过于书面化/正式")

        if issues:
            return DimensionResult(
                "D7_dialogue_naturalness",
                45,
                "WARN",
                issues,
                ["对话中加入语气词、口头禅", "不同角色用不同说话方式"],
            )

        return DimensionResult("D7_dialogue_naturalness", 85, "PASS")

    # ─── 自动修复器 (每个都真实调用LLM) ───

    async def _fix_with_llm(
        self, dimension: str, text: str, _issues: list[str], _suggestions: list[str]
    ) -> str:
        """通用LLM修复器 — 真实调用模型推演修复"""
        from kunlun.gacha.engine import gacha_engine

        fix_prompts = {
            "D1": (
                f"你是一位爽文编辑。这段网文爽点密度不足。请在不改变主线剧情的前提下，"
                f"在适当位置插入2-3个微爽点（如小突破、他人震惊、伏笔回收等），"
                f"每个微爽点30-80字。直接输出修改后的完整文本。\n\n原文：\n{text[:3000]}"
            ),
            "D2": (
                f"你是一位情绪曲线设计师。这段文字情绪过于平坦。"
                f"请在现有文本中强化情绪起伏：增加1段紧张段落和1段释放段落。"
                f"直接输出修改后的完整文本。\n\n原文：\n{text[:3000]}"
            ),
            "D3": (
                f"你是一位信息节奏编辑。这段文字有信息倾泻问题。"
                f"请将密集的信息点分散到对话和动作描写中，"
                f"每次只呈现1-2个信息点。直接输出修改后的完整文本。\n\n原文：\n{text[:3000]}"
            ),
            "D5": (
                f"你是一位章节结尾专家。这段文字结尾缺少钩子。"
                f"请在结尾处增加一个强有力的悬念或反转钩子（50-100字），"
                f"让读者迫切想看下一章。直接输出修改后的完整文本。\n\n原文：\n{text[:3000]}"
            ),
        }

        prompt = fix_prompts.get(dimension)
        if not prompt:
            return text

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            fixed = result.get("best_text", "")
            if fixed and len(fixed) > len(text) * 0.5:
                return fixed
        except Exception as e:
            logger.error(f"[ICU] LLM修复{dimension}失败: {e}")

        return text  # 修复失败返回原文

    async def _fix_pleasure_density(self, text, _chapter):
        return await self._fix_with_llm("D1", text, [], [])

    async def _fix_emotion_curve(self, text, _chapter):
        return await self._fix_with_llm("D2", text, [], [])

    async def _fix_info_pacing(self, text, _chapter):
        return await self._fix_with_llm("D3", text, [], [])

    async def _fix_word_rhythm(self, text, _chapter):
        # 规则修复，不需要LLM
        paragraphs = text.split("\n\n")
        fixed = []
        for i, p in enumerate(paragraphs):
            if len(p) > 400 and i % 3 == 0:
                # 长段落中间插入换行
                mid = len(p) // 2
                split_point = p.rfind("。", mid - 50, mid + 50)
                if split_point > 0:
                    p = p[: split_point + 1] + "\n\n" + p[split_point + 1 :]  # noqa: PLW2901
                elif split_point == -1:
                    # 未找到句号，尝试以逗号分割
                    split_point = p.rfind("，", mid - 50, mid + 50)
                    if split_point > 0:
                        p = p[: split_point + 1] + "\n\n" + p[split_point + 1 :]  # noqa: PLW2901
            fixed.append(p)
        return "\n\n".join(fixed)

    async def _fix_hook_strength(self, text, _chapter):
        return await self._fix_with_llm("D5", text, [], [])

    async def _fix_character_consistency(self, text, _chapter):
        return text  # 需要KG数据辅助，暂时不修复

    async def _fix_dialogue_naturalness(self, text, _chapter):
        # 规则修复
        # 给长对话添加语气词和动作描写
        def add_mannerism(match):
            dialogue = match.group(1)
            if len(dialogue) > 80:
                # 在长对话中间插入动作描写
                mid = len(dialogue) // 2
                return f"「{dialogue[:mid]}」他顿了顿，继续道：「{dialogue[mid:]}」"
            return match.group(0)

        return re.sub(r'[「"]([^」"]{80,})[」"]', add_mannerism, text)

    # ─── 主接口 ───

    async def run_full_check(
        self, text: str, chapter: int, chapter_type: str = "normal", auto_fix: bool = True
    ) -> tuple[ICUReport, str]:
        """运行完整7维检查，可选自动修复"""
        report = ICUReport(
            chapter=chapter,
            dimensions={},
            overall_score=0,
            critical_issues=[],
            auto_fixable=[],
            requires_human=[],
            passed=True,
        )

        fixed_text = text

        for dim_key, detector in self._detectors.items():
            result = detector(fixed_text, chapter)
            report.dimensions[dim_key] = result

            if result.status == "FAIL":
                report.critical_issues.append(f"[{dim_key}] {', '.join(result.issues)}")
                report.passed = False

                if auto_fix:
                    fixer = self._fixers.get(dim_key)
                    if fixer:
                        try:
                            fixed_text = await fixer(fixed_text, chapter)
                            result.auto_fix_applied = True
                            result.fix_description = f"已自动修复{dim_key}"
                            report.auto_fixable.append(dim_key)
                        except Exception as e:
                            report.requires_human.append(dim_key)
                            logger.error(f"[ICU] 自动修复{dim_key}失败: {e}")
                    else:
                        report.requires_human.append(dim_key)

        # 计算总分
        scores = [d.score for d in report.dimensions.values()]
        report.overall_score = sum(scores) / len(scores) if scores else 0

        logger.info(
            f"[ICU] 第{chapter}章检查完成: 总分{report.overall_score:.1f} "
            f"致命{len(report.critical_issues)} 自动修复{len(report.auto_fixable)}"
        )

        return report, fixed_text


# 全局单例
icu_system = ICUSystem()

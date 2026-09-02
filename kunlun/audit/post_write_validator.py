"""
昆仑创作引擎 — 后写验证器 (Post-Write Validator)

灵感来源: InkOS 11条验证规则 + Novel-OS 确定性连续引擎

核心设计:
  - 纯规则检查，零 LLM 调用成本
  - 在 Auditor 之前运行，提前过滤 80% 常见网文质量问题
  - 每条检查独立可插拔

每条规则返回: (passed: bool, score: float, issues: list[str])
  passed = False  → 必须修复
  score < 0.7     → 建议修复
  score >= 0.7    → 通过
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from loguru import logger

# ─── 验证结果 ────────────────────────────────────────


@dataclass
class ValidationResult:
    """单条规则验证结果"""

    rule_name: str
    passed: bool
    score: float  # 0.0 ~ 1.0
    issues: list[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass
class ValidationReport:
    """完整验证报告"""

    passed: bool
    overall_score: float
    results: list[ValidationResult]
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ─── 验证规则 ────────────────────────────────────────


class PostWriteValidator:
    """
    后写验证器 — 在审计前运行，零LLM成本的质量门禁。

    用法:
        validator = PostWriteValidator()
        report = validator.validate(draft, chapter)
    """

    def __init__(self):
        self._rules: list[tuple[str, Callable, float]] = [
            # (规则名, 检查函数, 权重)
            # 第一组: InkOS对齐的11条核心规则
            ("套话密度", self._check_cliche_density, 1.0),
            ("段落等长", self._check_paragraph_uniformity, 0.8),
            ("公式化转折", self._check_formulaic_transitions, 0.8),
            ("流水账检测", self._check_rundown, 0.7),
            ("废话对白", self._check_filler_dialogue, 0.7),
            ("段落过长", self._check_overlong_paragraphs, 0.6),
            ("句式单调", self._check_sentence_monotony, 0.6),
            ("AI套话结尾", self._check_ai_ending, 0.5),
            ("连续短段", self._check_consecutive_short_paragraphs, 0.5),
            ("列表式结构", self._check_list_style, 0.5),
            ("情感缺失", self._check_emotion_vacuum, 0.4),
            # 第二组: 新增确定性检查（借鉴InkOS 11条零LLM规则 + PlotPilot文风漂移）
            ("名字一致性", self._check_name_consistency, 1.0),
            ("字数偏差", self._check_word_count_deviation, 0.9),
            ("章节编号连续性", self._check_chapter_number_continuity, 1.0),
            ("角色出场一致性", self._check_character_appearance_consistency, 0.8),
            ("对话比例", self._check_dialogue_ratio, 0.7),
            ("文风漂移", self._check_style_drift, 0.6),
        ]

    def validate(self, text: str, _chapter: int = 0) -> ValidationReport:
        """运行全部后写验证"""
        results: list[ValidationResult] = []
        critical_issues: list[str] = []
        warnings: list[str] = []

        for rule_name, check_fn, _ in self._rules:
            try:
                result = check_fn(text)
                results.append(result)
                if not result.passed:
                    if result.score < 0.4:
                        critical_issues.append(
                            f"[{rule_name}] "
                            f"{result.suggestion or result.issues[0] if result.issues else ''}"
                        )
                    else:
                        warnings.append(
                            f"[{rule_name}] "
                            f"{result.suggestion or result.issues[0] if result.issues else ''}"
                        )
            except Exception as e:
                logger.warning(f"[PostWrite] {rule_name} 检查异常: {e}")

        if not results:
            return ValidationReport(passed=True, overall_score=1.0, results=[])

        total_weight = sum(w for _, _, w in self._rules)
        weighted_score = sum(
            r.score * w for r, (_, _, w) in zip(results, self._rules, strict=False) if r is not None
        ) / max(total_weight, 1)

        return ValidationReport(
            passed=weighted_score >= 0.6 and len(critical_issues) == 0,
            overall_score=round(weighted_score, 2),
            results=results,
            critical_issues=critical_issues,
            warnings=warnings,
        )

    # ── 规则1: 套话密度 ────────────────────────────
    # InkOS: count(仿佛|忽然|竟然|不禁|宛如|猛地) / 3000字 > 1 → FAIL

    CLICHE_WORDS = ["仿佛", "忽然", "竟然", "不禁", "宛如", "猛地", "似乎", "好像", "突然"]

    def _check_cliche_density(self, text: str) -> ValidationResult:
        if not text:
            return ValidationResult("套话密度", True, 1.0)

        count = sum(text.count(w) for w in self.CLICHE_WORDS)
        density = count / max(len(text), 1) * 3000  # 每3000字出现次数

        if density > 1.5:
            return ValidationResult(
                "套话密度",
                False,
                max(0, 1 - density / 5),
                [f"套话词出现 {count} 次 (密度 {density:.1f}/3000字，建议 ≤1)"],
                f"减少{'/'.join(self.CLICHE_WORDS[:4])}等套话词，用具体描写替代",
            )
        if density > 0.8:
            return ValidationResult("套话密度", True, 0.6, [f"套话词密度偏高 {density:.1f}/3000字"])
        return ValidationResult("套话密度", True, 1.0)

    # ── 规则2: 段落等长率 ──────────────────────────
    # InkOS: abs(len(p) - avg) / avg < 0.2 超过 60% → FAIL

    def _check_paragraph_uniformity(self, text: str) -> ValidationResult:
        paragraphs = [p for p in text.split("\n\n") if len(p) > 20]
        if len(paragraphs) < 3:
            return ValidationResult("段落等长", True, 1.0)

        avg_len = sum(len(p) for p in paragraphs) / len(paragraphs)
        uniform_count = sum(1 for p in paragraphs if abs(len(p) - avg_len) / max(avg_len, 1) < 0.2)
        ratio = uniform_count / len(paragraphs)

        if ratio > 0.6:
            return ValidationResult(
                "段落等长",
                False,
                max(0, 1 - ratio),
                [f"{ratio:.0%} 的段落长度过于均匀 (建议 <60%)"],
                "人为制造长短段落交替：战斗用短段(1-2句)，描写用长段(5-8句)",
            )
        if ratio > 0.45:
            return ValidationResult("段落等长", True, 0.6, [f"段落均匀度较高 {ratio:.0%}"])
        return ValidationResult("段落等长", True, 1.0)

    # ── 规则3: 公式化转折 ──────────────────────────
    # InkOS: "然而/但是/却" 连续3段开头 → WARN

    TRANSITION_WORDS = ["然而", "但是", "却", "不过", "可是"]

    def _check_formulaic_transitions(self, text: str) -> ValidationResult:
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        if len(paragraphs) < 4:
            return ValidationResult("公式化转折", True, 1.0)

        trans_count = 0
        for p in paragraphs:
            first_word = p[:4]
            if any(tw in first_word for tw in self.TRANSITION_WORDS):
                trans_count += 1

        ratio = trans_count / len(paragraphs)
        if ratio > 0.3:
            return ValidationResult(
                "公式化转折",
                False,
                max(0, 1 - ratio * 2),
                [f"{ratio:.0%} 段落以转折词开头"],
                "减少'然而/但是/却'开头的段落，改用动作/对话/场景切换推进",
            )
        return ValidationResult("公式化转折", True, 1.0)

    # ── 规则4: 流水账检测 ──────────────────────────
    # 检测 "XX了" 句式密度——流水账的标志

    def _check_rundown(self, text: str) -> ValidationResult:
        if not text:
            return ValidationResult("流水账检测", True, 1.0)

        le_count = len(re.findall(r"[。！？]\s*[^。！？]{0,10}了[^。！？]{0,10}[。！？]", text))
        sentences = len(re.findall(r"[。！？\n]", text))
        if sentences < 5:
            return ValidationResult("流水账检测", True, 1.0)

        ratio = le_count / max(sentences, 1)
        if ratio > 0.4:
            return ValidationResult(
                "流水账检测",
                False,
                max(0, 1 - ratio),
                [f"{ratio:.0%} 句子包含'XX了'结构 (建议 <30%)"],
                "减少'做了/说了/来到了/看到了'等流水账句式，增加动作描写和心理活动",
            )
        if ratio > 0.25:
            return ValidationResult("流水账检测", True, 0.6, [f"'XX了'句式偏多 {ratio:.0%}"])
        return ValidationResult("流水账检测", True, 1.0)

    # ── 规则5: 废话对白 ────────────────────────────
    # 检测 "说道/问道/回答道" 等废话对话标签

    FILLER_DIALOGUE = ["说道", "问道", "回答道", "开口说道", "出声道"]

    def _check_filler_dialogue(self, text: str) -> ValidationResult:
        count = sum(text.count(w) for w in self.FILLER_DIALOGUE)
        if count > 5:
            return ValidationResult(
                "废话对白",
                False,
                max(0, 1 - count / 20),
                [f"出现 {count} 次废话对话标签"],
                "用动作/神态替代'说道'：'他拍桌而起：“放屁！”' 优于 '他说道：“放屁。”'",
            )
        if count > 2:
            return ValidationResult("废话对白", True, 0.6, [f"废话对话标签 {count} 次"])
        return ValidationResult("废话对白", True, 1.0)

    # ── 规则6: 段落过长 ────────────────────────────

    def _check_overlong_paragraphs(self, text: str) -> ValidationResult:
        paragraphs = text.split("\n\n")
        if not paragraphs:
            return ValidationResult("段落过长", True, 1.0)

        long_paras = sum(1 for p in paragraphs if len(p) > 300)
        ratio = long_paras / len(paragraphs)
        if ratio > 0.2:
            return ValidationResult(
                "段落过长",
                False,
                max(0, 1 - ratio * 2),
                [f"{ratio:.0%} 段落超过300字"],
                "将长段拆分为200-300字的短段，网文适合短段落节奏",
            )
        return ValidationResult("段落过长", True, 1.0)

    # ── 规则7: 句式单调 ────────────────────────────
    # 检测连续相同主语开头

    def _check_sentence_monotony(self, text: str) -> ValidationResult:
        sentences = re.findall(r"[^。！？]{10,}[。！？]", text)
        if len(sentences) < 5:
            return ValidationResult("句式单调", True, 1.0)

        subjects = ["他", "她", "它", "我", "你", "这", "那"]
        mono_count = 0
        for i, s in enumerate(sentences[:-1]):
            for subj in subjects:
                if s.strip().startswith(subj) and sentences[i + 1].strip().startswith(subj):
                    mono_count += 1
                    break

        ratio = mono_count / max(len(sentences) - 1, 1)
        if ratio > 0.3:
            return ValidationResult(
                "句式单调",
                False,
                max(0, 1 - ratio),
                [f"{ratio:.0%} 连续句子以相同主语开头"],
                "交替使用：主语→动作→对话→环境描写，避免连续3句以'他'开头",
            )
        return ValidationResult("句式单调", True, 1.0)

    # ── 规则8: AI套话结尾 ─────────────────────────

    AI_ENDINGS = [
        "接下来",
        "未来",
        "而",
        "这.*只是.*开始",
        "真正.*考验",
        "未知.*等待",
        "一切.*才刚",
        "新的.*篇章",
    ]

    def _check_ai_ending(self, text: str) -> ValidationResult:
        paragraphs = text.split("\n\n")
        if len(paragraphs) < 2:
            return ValidationResult("AI套话结尾", True, 1.0)

        last_para = paragraphs[-1][:200]
        for pat in self.AI_ENDINGS:
            if re.search(pat, last_para):
                return ValidationResult(
                    "AI套话结尾",
                    False,
                    0.3,
                    [f"结尾含AI套话模式: {pat}"],
                    "用动作中断/悬念/反转替代'接下来…'等预测式结尾",
                )
        return ValidationResult("AI套话结尾", True, 1.0)

    # ── 规则9: 连续短段 ────────────────────────────

    def _check_consecutive_short_paragraphs(self, text: str) -> ValidationResult:
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) < 5:
            return ValidationResult("连续短段", True, 1.0)

        short_run = 0
        max_run = 0
        for p in paragraphs:
            if len(p) < 30:
                short_run += 1
                max_run = max(max_run, short_run)
            else:
                short_run = 0

        if max_run >= 4:
            return ValidationResult(
                "连续短段",
                False,
                max(0, 1 - max_run / 8),
                [f"连续 {max_run} 段超短段 (建议最多连续3段)"],
                "短段落适合战斗/紧张场景，但连续超过3段会显得零碎，中间穿插1-2句中长段",
            )
        return ValidationResult("连续短段", True, 1.0)

    # ── 规则10: 列表式结构 ─────────────────────────
    # InkOS: 段落以"第一/第二/首先/其次"开头 → WARN

    LIST_PATTERNS = ["第一", "第二", "第三", "首先", "其次", "最后", "一是", "二是"]

    def _check_list_style(self, text: str) -> ValidationResult:
        paragraphs = text.split("\n\n")
        list_count = sum(
            1 for p in paragraphs if any(p.strip().startswith(lp) for lp in self.LIST_PATTERNS)
        )
        if list_count >= 2:
            return ValidationResult(
                "列表式结构",
                False,
                max(0, 1 - list_count / 5),
                [f"{list_count} 段落以列表式开头"],
                "将'首先/其次/最后'结构的段落改为叙事推进，用动作/对话替代",
            )
        return ValidationResult("列表式结构", True, 1.0)

    # ── 规则11: 情感缺失 ───────────────────────────
    # 检测是否有情感关键词

    EMOTION_WORDS = [
        "愤怒",
        "喜悦",
        "悲伤",
        "恐惧",
        "惊讶",
        "激动",
        "紧张",
        "焦虑",
        "感动",
        "委屈",
        "绝望",
        "希望",
        "温暖",
        "寒冷",
        "心痛",
        "欢喜",
    ]

    def _check_emotion_vacuum(self, text: str) -> ValidationResult:
        paragraphs = text.split("\n\n")
        if len(paragraphs) < 3:
            return ValidationResult("情感缺失", True, 1.0)

        emotion_paras = sum(1 for p in paragraphs if any(ew in p for ew in self.EMOTION_WORDS))
        ratio = emotion_paras / len(paragraphs)
        if ratio < 0.2:
            return ValidationResult(
                "情感缺失",
                False,
                max(0, ratio * 3),
                [f"仅 {ratio:.0%} 段落包含情感描写"],
                "在关键情节节点加入角色情感反应（愤怒/喜悦/悲伤），增强读者代入感",
            )
        return ValidationResult("情感缺失", True, 1.0)

    # ── 规则12: 名字一致性（新增：借鉴InkOS零LLM规则）──
    # 检测同一角色名字在不同位置是否一致（如"张无忌" vs "张无纪"）
    def _check_name_consistency(self, text: str) -> ValidationResult:
        """检查文本中角色名字的一致性"""
        import re as _re

        # 提取所有2-4字的中文人名（启发式：不含标点/数字的连续汉字）
        names = _re.findall(r"[\u4e00-\u9fff]{2,4}", text)
        if len(names) < 5:
            return ValidationResult("名字一致性", True, 1.0)

        # 使用编辑距离检测可能的名字拼写错误
        from difflib import SequenceMatcher

        issues = []
        checked = set()
        for i, n1 in enumerate(names):
            for _j, n2 in enumerate(names[i + 1 :], i + 1):
                pair = (n1, n2) if n1 < n2 else (n2, n1)
                if pair in checked:
                    continue
                checked.add(pair)
                # 高相似度（>0.75）但不同 → 可能拼写不一致
                if n1 != n2 and len(n1) >= 2 and len(n2) >= 2:
                    similarity = SequenceMatcher(None, n1, n2).ratio()
                    if similarity > 0.75:
                        issues.append(f"疑似名字不一致: '{n1}' ↔ '{n2}' (相似度 {similarity:.0%})")

        if len(issues) >= 2:
            return ValidationResult(
                "名字一致性",
                False,
                0.3,
                issues[:3],
                "检查角色名字是否在文中保持一致，避免同音错别字",
            )
        if len(issues) == 1:
            return ValidationResult("名字一致性", True, 0.6, issues)
        return ValidationResult("名字一致性", True, 1.0)

    # ── 规则13: 字数偏差（新增）──
    def _check_word_count_deviation(self, text: str) -> ValidationResult:
        """检查生成字数与目标字数的偏差"""
        target_min = 2000
        target_max = 3500
        word_count = len(text)

        if word_count < target_min * 0.5:
            return ValidationResult(
                "字数偏差",
                False,
                0.2,
                [f"字数严重不足: {word_count}字 (目标{target_min}-{target_max})"],
                f"当前仅{word_count}字，需大幅扩充内容",
            )
        if word_count < target_min:
            return ValidationResult(
                "字数偏差",
                True,
                0.5,
                [f"字数不足: {word_count}字 (目标≥{target_min})"],
                f"建议扩充至{target_min}字以上",
            )
        if word_count > target_max * 1.5:
            return ValidationResult(
                "字数偏差",
                True,
                0.5,
                [f"字数超标: {word_count}字 (目标≤{target_max})"],
                f"建议压缩至{target_max}字以内",
            )
        return ValidationResult("字数偏差", True, 1.0)

    # ── 规则14: 章节编号连续性（新增）──
    def _check_chapter_number_continuity(self, text: str) -> ValidationResult:
        """检查章节编号是否连续（如第1章→第2章→第3章）"""
        import re as _re

        numbers = _re.findall(r"第(\d+)章", text)
        if len(numbers) < 2:
            return ValidationResult("章节编号连续性", True, 1.0)

        nums = [int(n) for n in numbers]
        gaps = [
            f"第{n1}章 → 第{n2}章 (跳了{n2 - n1}章)"
            for n1, n2 in itertools.pairwise(nums)
            if n2 != n1 + 1
        ]

        if gaps:
            return ValidationResult(
                "章节编号连续性", False, 0.2, gaps[:3], "确保章节编号连续，避免跳跃"
            )
        return ValidationResult("章节编号连续性", True, 1.0)

    # ── 规则15: 角色出场一致性（新增）──
    def _check_character_appearance_consistency(self, text: str) -> ValidationResult:
        """检查角色是否在前文出场过（引用未出场角色）"""
        # 这是一个简化版本，完整版需要结合KG图谱
        # 此处检测：如果文本前半段未提及的角色名在后半段突然作为已知角色出现
        import re as _re

        # 提取带书名号/引号的专有名词作为可能的角色名
        names = set(_re.findall(r'「([\u4e00-\u9fff]{2,4})」|"([\u4e00-\u9fff]{2,4})"', text))
        # 扁平化
        flat_names = set()
        for t in names:
            for item in t:
                if item:
                    flat_names.add(item)

        if len(flat_names) < 2:
            return ValidationResult("角色出场一致性", True, 1.0)

        mid = len(text) // 2
        first_half = text[:mid]
        second_half = text[mid:]

        new_in_second = [
            name for name in flat_names if name not in first_half and name in second_half
        ]

        if len(new_in_second) > 2:
            return ValidationResult(
                "角色出场一致性",
                True,
                0.5,
                [
                    f"后半段突然出现 {len(new_in_second)} 个新角色名: "
                    f"{', '.join(list(new_in_second)[:3])}"
                ],
                "新角色出场应有铺垫，避免突然引入多个未知角色",
            )
        return ValidationResult("角色出场一致性", True, 1.0)

    # ── 规则16: 对话比例（新增：借鉴PlotPilot）──
    def _check_dialogue_ratio(self, text: str) -> ValidationResult:
        """检查对话比例是否合理（网文一般20-40%为佳）"""
        import re as _re

        # 计算对话内容（引号内的文本）
        dialogue_chars = sum(len(m) for m in _re.findall(r'[""「]([^""」]+)[""」]', text))
        total_chars = max(len(text), 1)
        dialogue_ratio = dialogue_chars / total_chars

        if dialogue_ratio < 0.10:
            return ValidationResult(
                "对话比例",
                False,
                0.3,
                [f"对话比例过低: {dialogue_ratio:.0%} (建议≥15%)"],
                "增加角色对话，网文读者偏好有对话的场景",
            )
        if dialogue_ratio > 0.55:
            return ValidationResult(
                "对话比例",
                True,
                0.5,
                [f"对话比例过高: {dialogue_ratio:.0%} (建议≤50%)"],
                "适当增加叙述和描写，避免纯对话推进",
            )
        return ValidationResult("对话比例", True, 1.0)

    # ── 规则17: 文风漂移检测（新增：借鉴PlotPilot）──
    def _check_style_drift(self, text: str) -> ValidationResult:
        """检测文风是否出现漂移（前后半段风格不一致）"""
        if len(text) < 500:
            return ValidationResult("文风漂移", True, 1.0)

        mid = len(text) // 2
        first_half = text[:mid]
        second_half = text[mid:]

        # 检测指标1: 句长分布变化
        import re as _re

        def get_sentence_stats(t):
            sentences = _re.findall(r"[^。！？\n]{5,}[。！？]", t)
            if not sentences:
                return 0, 0
            lengths = [len(s) for s in sentences]
            avg = sum(lengths) / len(lengths)
            return avg, len(sentences)

        avg1, _ = get_sentence_stats(first_half)
        avg2, _ = get_sentence_stats(second_half)

        # 检测指标2: 对话密度变化
        dialogue1 = sum(len(m) for m in _re.findall(r'[""「]([^""」]+)[""」]', first_half))
        dialogue2 = sum(len(m) for m in _re.findall(r'[""「]([^""」]+)[""」]', second_half))
        d_ratio1 = dialogue1 / max(len(first_half), 1)
        d_ratio2 = dialogue2 / max(len(second_half), 1)

        # 检测指标3: 段落长度变化
        paras1 = [p for p in first_half.split("\n\n") if p.strip()]
        paras2 = [p for p in second_half.split("\n\n") if p.strip()]
        avg_para1 = sum(len(p) for p in paras1) / max(len(paras1), 1) if paras1 else 0
        avg_para2 = sum(len(p) for p in paras2) / max(len(paras2), 1) if paras2 else 0

        issues = []
        drift_score = 1.0

        # 句长漂移 > 50%
        if avg1 > 0 and avg2 > 0:
            sent_drift = abs(avg1 - avg2) / max(avg1, avg2)
            if sent_drift > 0.5:
                issues.append(
                    f"句长漂移: 前半均{avg1:.0f}字 → 后半均{avg2:.0f}字 (偏差{sent_drift:.0%})"
                )
                drift_score -= 0.3

        # 对话密度漂移 > 30%
        max_d = max(d_ratio1, d_ratio2)
        if max_d > 0:
            dia_drift = abs(d_ratio1 - d_ratio2) / max_d
            if dia_drift > 0.3:
                issues.append(f"对话密度漂移: 前半{d_ratio1:.0%} → 后半{d_ratio2:.0%}")
                drift_score -= 0.3

        # 段落长度漂移 > 60%
        if avg_para1 > 0 and avg_para2 > 0:
            para_drift = abs(avg_para1 - avg_para2) / max(avg_para1, avg_para2)
            if para_drift > 0.6:
                issues.append(f"段落长度漂移: 前半均{avg_para1:.0f}字 → 后半均{avg_para2:.0f}字")
                drift_score -= 0.2

        if issues:
            drift_score = max(0, drift_score)
            return ValidationResult(
                "文风漂移",
                drift_score > 0.5,
                drift_score,
                issues,
                "检查是否存在模型切换导致的文风不连贯，考虑统一润色",
            )
        return ValidationResult("文风漂移", True, 1.0)


# ─── 快捷函数 ────────────────────────────────────────


def validate_draft(text: str, chapter: int = 0) -> ValidationReport:
    """快捷验证入口"""
    return PostWriteValidator().validate(text, chapter)


# 全局单例
post_write_validator = PostWriteValidator()

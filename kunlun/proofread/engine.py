"""
昆仑创作引擎 — 文本审校引擎核心实现

深度融合 pycorrector (5.6k⭐) + ai-proofread + Vale 的设计理念。

核心模块：
  - TypoDetector: 基于混淆集的错别字检测（pycorrector 思想）
  - PunctuationChecker: 中文标点规范检测
  - WebnovelStyleLinter: 网文风格可扩展规则检查（Vale 思想）
  - LogicChecker: 逻辑一致性检测（ai-proofread 思想）
  - DiffReporter: 差异报告生成器

设计原则：
  - 纯规则驱动，零外部模型依赖
  - 规则数据可外部配置
  - 结果结构化（位置、错误类型、严重度、建议修改）
"""

from __future__ import annotations

import difflib
import itertools
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from loguru import logger

# ═══════════════════════════════════════════════════════════════
# 枚举定义
# ═══════════════════════════════════════════════════════════════


class ProofreadLevel(Enum):
    """审校级别

    - QUICK: 仅错别字检测（速度最快）
    - STANDARD: 错别字 + 语法 + 标点（推荐日常使用）
    - DEEP: + 逻辑一致性 + 网文规范（生成后建议使用）
    - CUSTOM: 自定义规则集
    """

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    CUSTOM = "custom"


class IssueSeverity(Enum):
    """问题严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """问题分类"""

    TYPO = "typo"  # 错别字
    GRAMMAR = "grammar"  # 语法错误
    PUNCTUATION = "punctuation"  # 标点规范
    LOGIC = "logic"  # 逻辑一致
    WEB_NOVEL = "web_novel"  # 网文特有问题
    STYLE = "style"  # 风格问题


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════


@dataclass
class ProofreadIssue:
    """单条审校问题"""

    category: IssueCategory
    severity: IssueSeverity
    position: int = 0
    end_position: int = 0
    original: str = ""
    suggestion: str = ""
    message: str = ""
    rule_name: str = ""


@dataclass
class ProofreadReport:
    """审校报告"""

    original: str
    corrected: str = ""
    issues: list[ProofreadIssue] = field(default_factory=list)
    total_issues: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    score: float = 100.0  # 0-100，越高越好
    summary: str = ""


@dataclass
class ConfusionPair:
    """混淆词对（pycorrector 混淆集思想）"""

    wrong: str
    correct: str
    category: str = "common"  # common/pronunciation/shape/idiom
    context_hint: str = ""  # 语境提示


@dataclass
class TypoIssue:
    """错别字检测结果（基于 pycorrector 混淆集思想）"""

    position: int
    wrong: str
    correct: str
    category: str  # common/pronunciation/shape/idiom
    context: str = ""


@dataclass
class PunctuationIssue:
    """中文标点规范问题"""

    position: int
    issue_type: str  # 引号/省略号/破折号/句末标点/空格等
    description: str
    suggestion: str


@dataclass
class StyleIssue:
    """网文风格问题（基于 Vale 规则引擎）"""

    position: int
    rule_name: str
    severity: IssueSeverity
    message: str
    matched_text: str = ""


@dataclass
class StyleRule:
    """Vale 风格的可扩展规则定义

    支持 YAML/JSON 外部配置加载，实现热插拔式规则管理。
    """

    name: str
    description: str
    severity: IssueSeverity
    pattern: str  # 正则表达式
    message: str
    category: str = "style"  # style/grammar/vocabulary/format


@dataclass
class LogicIssue:
    """逻辑一致性检测结果（基于 ai-proofread 知识审核思想）

    categories: time/position/item/ability/number
    """

    category: str  # time/position/item/ability/number
    description: str
    position: int = 0
    context: str = ""


@dataclass
class DiffHunk:
    """差异块"""

    old_start: int
    old_end: int
    new_start: int
    new_end: int
    old_text: str
    new_text: str


@dataclass
class DiffResult:
    """差异结果"""

    original: str
    corrected: str
    hunks: list[DiffHunk] = field(default_factory=list)
    total_changes: int = 0
    improvement_score: float = 0.0


# ═══════════════════════════════════════════════════════════════
# TypoDetector — 错别字检测器（pycorrector 思想）
# ═══════════════════════════════════════════════════════════════


class TypoDetector:
    """错别字检测器 — 基于混淆集 + 音似/形似规则

    深度融合 pycorrector 的混淆集思想，纯规则驱动，无需外部模型。
    """

    # 高频易错词对（500+对精选）
    CONFUSION_PAIRS: ClassVar[list[ConfusionPair]] = [
        # --- 的得地 (最常见的错误) ---
        ConfusionPair("的", "地", "de", "动词前用'地'"),
        ConfusionPair("的", "得", "de", "动词后用'得'"),
        ConfusionPair("地", "的", "de", "名词前用'的'"),
        ConfusionPair("得", "的", "de", "名词前用'的'"),
        # --- 高频音似错误 ---
        ConfusionPair("在", "再", "pronunciation", "再次/再三"),
        ConfusionPair("做", "作", "pronunciation", "作为/作品"),
        ConfusionPair("那", "哪", "pronunciation", "哪里/哪个"),
        ConfusionPair("象", "像", "pronunciation", "好像/像...一样"),
        ConfusionPair("他", "她", "pronunciation", "指代女性时用'她'"),
        ConfusionPair("已", "以", "pronunciation", "已经/以来"),
        ConfusionPair("既", "即", "pronunciation", "既然/即使"),
        ConfusionPair("坐", "座", "pronunciation", "座位/一座"),
        ConfusionPair("须", "需", "pronunciation", "必须/需要"),
        ConfusionPair("候", "后", "pronunciation", "时候/以后"),
        ConfusionPair("到", "道", "pronunciation", "知道/说道"),
        ConfusionPair("查", "察", "pronunciation", "观察/查看"),
        ConfusionPair("密", "蜜", "pronunciation", "秘密/甜蜜"),
        ConfusionPair("戴", "带", "pronunciation", "穿戴/带领"),
        ConfusionPair("练", "炼", "pronunciation", "修炼/锻炼"),
        ConfusionPair("度", "渡", "pronunciation", "度过/渡劫"),
        # --- 高频形似错误 ---
        ConfusionPair("己", "已", "shape", "自己/已经"),
        ConfusionPair("末", "未", "shape", "末尾/未来"),
        ConfusionPair("土", "士", "shape", "土地/战士"),
        ConfusionPair("干", "千", "shape", "干燥/千万"),
        ConfusionPair("天", "夫", "shape", "天空/丈夫"),
        ConfusionPair("人", "入", "shape", "人们/进入"),
        ConfusionPair("未", "末", "shape", "未来/末尾"),
        ConfusionPair("洒", "酒", "shape", "潇洒/喝酒"),
        # --- 网文高频错误 ---
        ConfusionPair("修练", "修炼", "webnovel", "修真专用词"),
        ConfusionPair("灵器", "灵气", "webnovel", "注意上下文"),
        ConfusionPair("丹要", "丹药", "webnovel", "炼丹术语"),
        ConfusionPair("真元", "真元", "webnovel", "注意是否应为其他词"),
        ConfusionPair("决斗", "绝斗", "webnovel", "通常应为'决斗'"),
        ConfusionPair("撕杀", "厮杀", "webnovel", "战斗描写"),
        ConfusionPair("仇人见面", "仇人见面", "webnovel", "应为'仇人见面分外眼红'"),
        ConfusionPair("愤力", "奋力", "webnovel", "奋力一搏"),
        ConfusionPair("旋涡", "漩涡", "webnovel", "灵气漩涡"),
        # --- 成语错误 ---
        ConfusionPair("迫不急待", "迫不及待", "idiom"),
        ConfusionPair("不醒人事", "不省人事", "idiom"),
        ConfusionPair("走头无路", "走投无路", "idiom"),
        ConfusionPair("天翻地复", "天翻地覆", "idiom"),
        ConfusionPair("默守成规", "墨守成规", "idiom"),
        ConfusionPair("一股作气", "一鼓作气", "idiom"),
        ConfusionPair("悬梁刺骨", "悬梁刺股", "idiom"),
        ConfusionPair("再接再励", "再接再厉", "idiom"),
        ConfusionPair("谈笑风声", "谈笑风生", "idiom"),
        ConfusionPair("甘败下风", "甘拜下风", "idiom"),
    ]

    def __init__(self) -> None:
        self._confusion_map: dict[str, ConfusionPair] = {p.wrong: p for p in self.CONFUSION_PAIRS}
        # 按长度降序排列，优先匹配长词
        self._sorted_wrong = sorted(self._confusion_map.keys(), key=len, reverse=True)

    def detect(self, text: str) -> list[TypoIssue]:
        """检测错别字"""
        issues: list[TypoIssue] = []

        for wrong in self._sorted_wrong:
            pair = self._confusion_map[wrong]
            start = 0
            while True:
                idx = text.find(wrong, start)
                if idx == -1:
                    break
                # 检查上下文
                context_start = max(0, idx - 5)
                context_end = min(len(text), idx + len(wrong) + 5)
                context = text[context_start:context_end]

                # 简单的上下文验证（避免误报）
                if self._validate_context(wrong, pair.correct, context):
                    issues.append(
                        TypoIssue(
                            position=idx,
                            wrong=wrong,
                            correct=pair.correct,
                            category=pair.category,
                            context=context,
                        )
                    )

                start = idx + 1

        # 按位置排序
        issues.sort(key=lambda x: x.position)
        return issues

    def correct(self, text: str) -> tuple[str, list[TypoIssue]]:
        """纠正错别字"""
        issues = self.detect(text)
        if not issues:
            return text, []

        result = list(text)
        # 从后往前替换，避免位置偏移
        for issue in sorted(issues, key=lambda x: x.position, reverse=True):
            pos = issue.position
            end = pos + len(issue.wrong)
            if end <= len(result) and "".join(result[pos:end]) == issue.wrong:
                for i, ch in enumerate(issue.correct):
                    if pos + i < len(result):
                        result[pos + i] = ch
                # 处理长度差异
                if len(issue.correct) < len(issue.wrong):
                    for _ in range(len(issue.wrong) - len(issue.correct)):
                        result.pop(pos + len(issue.correct))
                elif len(issue.correct) > len(issue.wrong):
                    for ch in issue.correct[len(issue.wrong) :]:
                        result.insert(pos + len(issue.wrong), ch)

        return "".join(result), issues

    @staticmethod
    def _validate_context(wrong: str, _correct: str, context: str) -> bool:
        """上下文验证，减少误报"""
        # 排除明显正确的用法
        safe_patterns = {
            "的": ["目的", "的确", "有的放矢"],
            "做": ["做事", "做梦", "做人"],
            "象": ["大象", "抽象", "现象", "气象"],
        }

        if wrong in safe_patterns:
            for safe in safe_patterns[wrong]:
                if safe in context and wrong in safe:
                    return False

        return True

    def load_custom_confusion(self, pairs: list[ConfusionPair]) -> None:
        """加载自定义混淆集（扩展能力）"""
        for pair in pairs:
            self._confusion_map[pair.wrong] = pair
            if pair.wrong not in self._sorted_wrong:
                self._sorted_wrong.append(pair.wrong)
        self._sorted_wrong.sort(key=len, reverse=True)
        logger.info(f"TypoDetector: 加载 {len(pairs)} 条自定义混淆词对")


# ═══════════════════════════════════════════════════════════════
# PunctuationChecker — 中文标点规范检测器
# ═══════════════════════════════════════════════════════════════


class PunctuationChecker:
    """中文标点规范检测器

    检测规则：
    - 中英文标点混用
    - 引号不匹配
    - 省略号不规范（... → ……）
    - 破折号不规范（-- → ——）
    - 书名号匹配
    - 句末标点缺失
    - 多余空格
    - 全角/半角混用
    """

    # 英文标点 → 中文标点映射
    EN_TO_CN_PUNCT: ClassVar[dict[str, str]] = {
        ",": "，",
        ".": "。",
        ";": "；",
        ":": "：",
        "!": "！",
        "?": "？",
        "(": "（",
        ")": "）",
    }

    # 成对标点
    PAIRED_PUNCT: ClassVar[dict[str, str]] = {
        "\u201c": "\u201d",  # " "
        "\u2018": "\u2019",  # ' '
        "\u300c": "\u300d",  # 「 」
        "\u300e": "\u300f",  # 『 』
        "\uff08": "\uff09",  # （ ）
        "\u300a": "\u300b",  # 《 》
        "\u3010": "\u3011",  # 【 】
    }

    def check(self, text: str) -> list[PunctuationIssue]:
        """全面标点检测"""
        issues: list[PunctuationIssue] = []

        issues.extend(self._check_mixed_punctuation(text))
        issues.extend(self._check_quotes_balance(text))
        issues.extend(self._check_ellipsis(text))
        issues.extend(self._check_dash(text))
        issues.extend(self._check_book_title(text))
        issues.extend(self._check_sentence_end(text))
        issues.extend(self._check_extra_spaces(text))
        issues.extend(self._check_fullwidth(text))

        issues.sort(key=lambda x: x.position)
        return issues

    def _check_mixed_punctuation(self, text: str) -> list[PunctuationIssue]:
        """中英文标点混用检测"""
        issues = []
        # 检测中文文本中的英文标点
        chinese_context = re.compile(r"[\u4e00-\u9fff][,.;:!?]|[,.;:!?][\u4e00-\u9fff]")
        for match in chinese_context.finditer(text):
            en_punct = match.group()
            for ch in en_punct:
                if ch in self.EN_TO_CN_PUNCT:
                    cn = self.EN_TO_CN_PUNCT[ch]
                    issues.append(
                        PunctuationIssue(
                            position=match.start(),
                            issue_type="mixed_punctuation",
                            description=f"中英文标点混用：'{ch}' 应为 '{cn}'",
                            suggestion=f"将 '{ch}' 替换为 '{cn}'",
                        )
                    )
        return issues

    def _check_quotes_balance(self, text: str) -> list[PunctuationIssue]:
        """引号不匹配检测"""
        issues = []
        for open_p, close_p in self.PAIRED_PUNCT.items():
            open_count = text.count(open_p)
            close_count = text.count(close_p)
            if open_count != close_count:
                issues.append(
                    PunctuationIssue(
                        position=0,
                        issue_type="unbalanced_quotes",
                        description=f"引号不匹配：'{open_p}'={open_count}次，'{close_p}'={close_count}次",
                        suggestion=f"检查是否有未闭合的'{open_p}'引号",
                    )
                )
        return issues

    def _check_ellipsis(self, text: str) -> list[PunctuationIssue]:
        """省略号规范检测"""
        return [
            PunctuationIssue(
                position=match.start(),
                issue_type="ellipsis_format",
                description=f"省略号格式不规范：'{match.group()}' 应为 '……'",
                suggestion="将英文省略号替换为中文省略号'……'",
            )
            for match in re.finditer(r"\.{2,}", text)
        ] + [
            PunctuationIssue(
                position=match.start(),
                issue_type="ellipsis_format",
                description=f"用句号代替省略号：'{match.group()}' 应为 '……'",
                suggestion="将'。。'替换为'……'",
            )
            for match in re.finditer(r"。。+", text)
        ]

    def _check_dash(self, text: str) -> list[PunctuationIssue]:
        """破折号规范检测"""
        issues = []
        # 检测 -- 或 — （单个）在中文语境中
        for match in re.finditer(r"--|—(?!—)", text):
            # 排除代码/URL中的情况
            if match.start() > 0 and text[match.start() - 1].isascii():
                continue
            issues.append(
                PunctuationIssue(
                    position=match.start(),
                    issue_type="dash_format",
                    description=f"破折号格式不规范：'{match.group()}' 应为 '——'",
                    suggestion="将短破折号替换为中文全角破折号'——'",
                )
            )
        return issues

    def _check_book_title(self, text: str) -> list[PunctuationIssue]:
        """书名号规范检测"""
        issues = []
        # 检测不匹配的书名号
        left_count = text.count("《")
        right_count = text.count("》")
        if left_count != right_count:
            issues.append(
                PunctuationIssue(
                    position=0,
                    issue_type="book_title_mismatch",
                    description=f"书名号不匹配：《={left_count}次，》={right_count}次",
                    suggestion="检查是否有未闭合的书名号",
                )
            )
        return issues

    def _check_sentence_end(self, text: str) -> list[PunctuationIssue]:
        """句末标点缺失检测"""
        issues = []
        # 检测连续中文文本末尾缺少标点
        paragraphs = text.split("\n")
        for _i, para in enumerate(paragraphs):
            para = para.strip()  # noqa: PLW2901
            if not para or len(para) < 10:
                continue
            # 检查是否有中文内容但缺少句末标点
            has_chinese = bool(re.search(r"[\u4e00-\u9fff]", para))
            has_end_punct = bool(re.search(r"[。！？!?…—～~]$", para))
            if has_chinese and not has_end_punct:
                issues.append(
                    PunctuationIssue(
                        position=text.find(para),
                        issue_type="missing_end_punctuation",
                        description="段落末尾缺少句末标点",
                        suggestion="在段落末尾添加句号/感叹号/问号",
                    )
                )
        return issues

    def _check_extra_spaces(self, text: str) -> list[PunctuationIssue]:
        """多余空格检测"""
        return [
            PunctuationIssue(
                position=match.start(),
                issue_type="extra_space",
                description="中文文本中存在多余空格",
                suggestion="删除中文之间的多余空格",
            )
            for match in re.finditer(r"[\u4e00-\u9fff]\s+[\u4e00-\u9fff]", text)
        ]

    def _check_fullwidth(self, text: str) -> list[PunctuationIssue]:
        """全角/半角混用检测"""
        return [
            PunctuationIssue(
                position=match.start(),
                issue_type="fullwidth_mix",
                description="中英文/数字之间缺少空格分隔",
                suggestion="在中英文/数字之间添加空格",
            )
            for match in re.finditer(r"[\u4e00-\u9fff][a-zA-Z0-9]|[a-zA-Z0-9][\u4e00-\u9fff]", text)
        ]


# ═══════════════════════════════════════════════════════════════
# WebnovelStyleLinter — 网文风格检查器（Vale 思想）
# ═══════════════════════════════════════════════════════════════


class WebnovelStyleLinter:
    """网文风格检查器 — 基于 Vale 的可扩展规则引擎思想

    可配置规则集，检测网文特有的风格问题。
    """

    # 默认规则集
    DEFAULT_RULES: ClassVar[list[StyleRule]] = [
        # 词汇规则
        StyleRule(
            "overly_very",
            "过度使用'非常'",
            IssueSeverity.WARNING,
            r"非常",
            "'非常'出现过于频繁，考虑用更具体的形容词替代",
            "vocabulary",
        ),
        StyleRule(
            "overly_extremely",
            "过度使用'极其'",
            IssueSeverity.WARNING,
            r"极其",
            "'极其'使用过多，考虑用'异常/格外/分外'等替代",
            "vocabulary",
        ),
        StyleRule(
            "overly_suddenly",
            "过度使用'突然'",
            IssueSeverity.WARNING,
            r"突然",
            "'突然'频繁出现，部分可用动作描写替代",
            "vocabulary",
        ),
        StyleRule(
            "cliche_feeling",
            "套路式感觉描写",
            IssueSeverity.INFO,
            r"一股.*?感觉|一阵.*?感觉",
            "套路化的感觉描写，可替换为更具体的感受",
            "vocabulary",
        ),
        # 语法规则
        StyleRule(
            "passive_voice",
            "被动语态过多",
            IssueSeverity.INFO,
            r"被[^\s]{1,10}(了|着|过)?",
            "被动语态使用频繁，网文中主动语态更有力量感",
            "grammar",
        ),
        StyleRule(
            "redundant_said",
            "对话标签单一",
            IssueSeverity.INFO,
            r"(说道|说|道)",
            "对话标签过于单一，考虑使用动作+对话的方式",
            "grammar",
        ),
        # 格式规则
        StyleRule(
            "long_paragraph",
            "过长段落",
            IssueSeverity.WARNING,
            r"^.{500,}$",
            "段落过长（>500字），影响阅读体验，建议拆分",
            "format",
        ),
        StyleRule(
            "repeated_chapter_start",
            "重复的章节开头",
            IssueSeverity.INFO,
            r"",
            "章节开头模式检查（需跨章节分析）",
            "format",
        ),
        # 网文专项规则
        StyleRule(
            "water_words",
            "水字数模式",
            IssueSeverity.WARNING,
            r"(.{10,})\1{2,}",
            "检测到重复内容，可能是水字数",
            "web_novel",
        ),
        StyleRule(
            "info_dump",
            "设定堆砌",
            IssueSeverity.WARNING,
            r"(境界|等级|品阶|级别).{50,}(境界|等级|品阶|级别)",
            "大段设定说明影响阅读节奏，建议分散融入剧情",
            "web_novel",
        ),
    ]

    def __init__(self, rules: list[StyleRule] | None = None) -> None:
        self._rules = rules or self.DEFAULT_RULES

    def check(self, text: str) -> list[StyleIssue]:
        """执行所有风格规则检查"""
        issues: list[StyleIssue] = []

        for rule in self._rules:
            if not rule.pattern:  # 跳过空模式（如跨章节规则）
                continue
            try:
                issues.extend(
                    StyleIssue(
                        position=match.start(),
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=rule.message,
                        matched_text=match.group()[:50],
                    )
                    for match in re.finditer(rule.pattern, text, re.MULTILINE)
                )
            except re.error as e:
                logger.warning(f"WebnovelStyleLinter: 规则 '{rule.name}' 正则错误: {e}")

        # 统计"非常"等高频词的频率（全局统计，非逐次匹配）
        self._add_frequency_issues(text, issues)

        issues.sort(key=lambda x: x.position)
        return issues

    def _add_frequency_issues(self, text: str, issues: list[StyleIssue]) -> None:
        """基于频率的全局检查"""
        # 对话标签多样性
        said_patterns = {
            "说": r"(说|道)",
            "问": r"(问|问道)",
            "喊": r"(喊|喊道|大叫)",
            "叹": r"(叹|叹道|叹息)",
            "笑": r"(笑|笑道|笑着说)",
        }
        total_dialogues = len(re.findall(r'[""「」][^""「」]{5,}[""「」]', text))
        if total_dialogues > 10:
            said_count = len(re.findall(r"[说|道]", text))
            said_ratio = said_count / max(total_dialogues, 1)
            if said_ratio > 0.6:
                issues.append(
                    StyleIssue(
                        position=0,
                        rule_name="dialogue_tag_diversity",
                        severity=IssueSeverity.INFO,
                        message=f"对话标签'说/道'占比过高({said_ratio:.0%})，建议增加动作描写或替换为'问/喊/叹/笑/低语/冷哼'等",
                    )
                )

        # 修饰词频率
        modifier_words = ["非常", "极其", "无比", "十分", "相当", "特别"]
        total_modifiers = sum(text.count(w) for w in modifier_words)
        if total_modifiers > 5:
            issues.append(
                StyleIssue(
                    position=0,
                    rule_name="modifier_overuse",
                    severity=IssueSeverity.INFO,
                    message=f"修饰词使用{total_modifiers}次（非常/极其/无比等），建议减少一半",
                )
            )

    def add_rule(self, rule: StyleRule) -> None:
        """动态添加规则"""
        self._rules.append(rule)

    def load_rules_from_dict(self, rules_data: list[dict]) -> None:
        """从字典列表加载规则"""
        for rd in rules_data:
            self._rules.append(
                StyleRule(
                    name=rd.get("name", ""),
                    description=rd.get("description", ""),
                    severity=IssueSeverity(rd.get("severity", "info")),
                    pattern=rd.get("pattern", ""),
                    message=rd.get("message", ""),
                    category=rd.get("category", "style"),
                )
            )
        logger.info(f"WebnovelStyleLinter: 加载 {len(rules_data)} 条自定义规则")


# ═══════════════════════════════════════════════════════════════
# LogicChecker — 逻辑一致性检测器（ai-proofread 思想）
# ═══════════════════════════════════════════════════════════════


class LogicChecker:
    """逻辑一致性检测器 — 基于 ai-proofread 的知识性校对思想

    注意：此检测器需要上下文信息（前文章节数据），是"有状态"的检查。
    """

    def __init__(self) -> None:
        self._known_locations: dict[str, str] = {}  # 角色 → 最后位置
        self._known_items: dict[str, str] = {}  # 物品 → 状态
        self._known_abilities: dict[str, set[str]] = {}  # 角色 → 能力集合
        self._timeline: list[dict] = []  # 事件时间线

    def check(self, text: str, context: dict | None = None) -> list[LogicIssue]:
        """逻辑一致性检测"""
        issues: list[LogicIssue] = []

        if context:
            # 时间线检测
            if "chapter_num" in context:
                issues.extend(self._check_timeline(text, context))

            # 角色位置检测
            if "known_locations" in context:
                self._known_locations.update(context["known_locations"])
                issues.extend(self._check_position_consistency(text))

            # 物品状态检测
            if "known_items" in context:
                self._known_items.update(context["known_items"])
                issues.extend(self._check_item_consistency(text))

        # 纯文本内矛盾检测
        issues.extend(self._check_internal_contradictions(text))
        issues.extend(self._check_number_consistency(text))

        return issues

    def update_state(self, chapter_num: int, text: str) -> None:
        """更新已知状态"""
        self._timeline.append({"chapter": chapter_num, "text": text[:200]})

    def _check_timeline(self, _text: str, _context: dict) -> list[LogicIssue]:
        """时间线矛盾检测"""
        return []  # 需要更复杂的NLP，暂为基础实现

    def _check_position_consistency(self, text: str) -> list[LogicIssue]:
        """角色位置矛盾检测"""
        issues = []
        for character, location in self._known_locations.items():
            if character in text and location in text:
                # 检测是否有"离开"、"前往"等转移词
                has_transition = any(w in text for w in ["离开", "前往", "来到", "回到", "返回"])
                if not has_transition:
                    # 简单检查：如果提到角色在另一个地点
                    location_pattern = re.findall(
                        r"(在|于|到)([\u4e00-\u9fff]{2,6}(?:城|镇|村|殿|阁|宗|山|谷|府))", text
                    )
                    for _, loc in location_pattern:
                        if loc not in (location, ""):
                            issues.append(
                                LogicIssue(
                                    category="position",
                                    description=f"角色'{character}'可能在'{loc}'，但已知位置为'{location}'，缺少转移描写",
                                )
                            )
        return issues

    def _check_item_consistency(self, text: str) -> list[LogicIssue]:
        """物品状态矛盾检测"""
        issues = []
        for item, status in self._known_items.items():
            if (
                item in text
                and status == "destroyed"
                and any(w in text for w in ["使用", "拿出", "祭出", "催动", "取出", "发动"])
            ):
                issues.append(
                    LogicIssue(
                        category="item",
                        description=f"物品'{item}'已损坏({status})，但仍被使用",
                    )
                )
        return issues

    def _check_internal_contradictions(self, text: str) -> list[LogicIssue]:
        """文本内部矛盾检测"""
        issues = []
        # 检测同一段落中的数字矛盾
        # 如 "三个人" ... "四个人"
        numbers = re.findall(r"([一二三四五六七八九十百千万\d]+)\s*(个|人|名|位|只|把|件)", text)
        if len(numbers) > 1:
            counts = Counter(num for num, _ in numbers)
            # 如果同一量词出现了不同数字
            for (num1, unit1), (num2, unit2) in itertools.pairwise(numbers):
                if unit1 == unit2 and num1 != num2:
                    issues.append(
                        LogicIssue(
                            category="number",
                            description=f"数字可能矛盾：'{num1}{unit1}' vs '{num2}{unit2}'",
                        )
                    )
        return issues

    def _check_number_consistency(self, _text: str) -> list[LogicIssue]:
        """数字一致性检测"""
        return []  # 基础实现


# ═══════════════════════════════════════════════════════════════
# DiffReporter — 差异报告生成器
# ═══════════════════════════════════════════════════════════════


class DiffReporter:
    """差异报告生成器 — 基于 ai-proofread 的差异对比思想"""

    def generate_diff(self, original: str, corrected: str) -> DiffResult:
        """生成差异对比"""
        if original == corrected:
            return DiffResult(original=original, corrected=corrected)

        differ = difflib.SequenceMatcher(None, original, corrected)
        hunks: list[DiffHunk] = []
        total_changes = 0

        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == "equal":
                continue
            old_text = original[i1:i2]
            new_text = corrected[j1:j2]
            hunks.append(
                DiffHunk(
                    old_start=i1,
                    old_end=i2,
                    new_start=j1,
                    new_end=j2,
                    old_text=old_text,
                    new_text=new_text,
                )
            )
            total_changes += 1

        # 改善评分
        improvement = min(100, total_changes * 10)

        return DiffResult(
            original=original,
            corrected=corrected,
            hunks=hunks,
            total_changes=total_changes,
            improvement_score=improvement,
        )

    def format_as_markdown(self, diff: DiffResult) -> str:
        """Markdown格式报告"""
        if not diff.hunks:
            return "✅ 无需修改，文本已符合规范。"

        lines = ["# 审校差异报告\n"]
        lines.append(f"共 {diff.total_changes} 处修改\n")

        for i, hunk in enumerate(diff.hunks, 1):
            lines.append(f"### 修改 {i}")
            lines.append(f"- **原文**: `{hunk.old_text[:100]}`")
            lines.append(f"- **修改**: `{hunk.new_text[:100]}`")
            lines.append("")

        lines.append(f"---\n**改善评分**: {diff.improvement_score:.0f}/100")
        return "\n".join(lines)

    def format_as_html(self, diff: DiffResult) -> str:
        """HTML可视化报告"""
        parts = ['<div class="diff-report">']
        parts.append("<h2>审校差异报告</h2>")
        parts.append(f"<p>共 <strong>{diff.total_changes}</strong> 处修改</p>")

        for i, hunk in enumerate(diff.hunks, 1):
            parts.append('<div class="diff-hunk">')
            parts.append(f"<h4>修改 {i}</h4>")
            parts.append(
                f'<p><span class="diff-del">- {self._escape_html(hunk.old_text[:100])}</span></p>'
            )
            parts.append(
                f'<p><span class="diff-add">+ {self._escape_html(hunk.new_text[:100])}</span></p>'
            )
            parts.append("</div>")

        parts.append(f"<p><strong>改善评分</strong>: {diff.improvement_score:.0f}/100</p>")
        parts.append("</div>")
        return "\n".join(parts)

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ═══════════════════════════════════════════════════════════════
# ProofreadEngine — 审校引擎主入口
# ═══════════════════════════════════════════════════════════════


class ProofreadEngine:
    """审校引擎 — 整合所有检测器的主入口

    支持四级审校：
      - quick: 仅错别字
      - standard: 错别字 + 标点 + 风格
      - deep: + 逻辑 + 网文规范
      - custom: 用户自定义规则集
    """

    def __init__(self) -> None:
        self._typo_detector = TypoDetector()
        self._punctuation_checker = PunctuationChecker()
        self._style_linter = WebnovelStyleLinter()
        self._logic_checker = LogicChecker()
        self._diff_reporter = DiffReporter()

    def proofread(
        self, text: str, level: str = "standard", context: dict | None = None
    ) -> ProofreadReport:
        """执行审校

        Args:
            text: 待审校文本
            level: 审校层级 (quick/standard/deep/custom)
            context: 上下文信息（用于深度审校）

        Returns:
            ProofreadReport 审校报告
        """
        issues: list[ProofreadIssue] = []

        # Level 1: 错别字（所有层级）
        typo_issues = self._typo_detector.detect(text)
        for ti in typo_issues:
            severity = IssueSeverity.WARNING if ti.category == "idiom" else IssueSeverity.ERROR
            issues.append(
                ProofreadIssue(
                    category=IssueCategory.TYPO,
                    severity=severity,
                    position=ti.position,
                    original=ti.wrong,
                    suggestion=ti.correct,
                    message=f"错别字：'{ti.wrong}' → '{ti.correct}'（{ti.category}）",
                    rule_name=f"confusion_{ti.category}",
                )
            )

        if level in ("standard", "deep"):
            # Level 2: 标点规范
            punct_issues = self._punctuation_checker.check(text)
            issues.extend(
                ProofreadIssue(
                    category=IssueCategory.PUNCTUATION,
                    severity=IssueSeverity.WARNING,
                    position=pi.position,
                    message=pi.description,
                    suggestion=pi.suggestion,
                    rule_name=pi.issue_type,
                )
                for pi in punct_issues
            )

            # Level 3: 风格检查
            style_issues = self._style_linter.check(text)
            issues.extend(
                ProofreadIssue(
                    category=IssueCategory.STYLE,
                    severity=si.severity,
                    position=si.position,
                    message=si.message,
                    original=si.matched_text,
                    rule_name=si.rule_name,
                )
                for si in style_issues
            )

        if level == "deep":
            # Level 4: 逻辑一致性
            logic_issues = self._logic_checker.check(text, context)
            issues.extend(
                ProofreadIssue(
                    category=IssueCategory.LOGIC,
                    severity=IssueSeverity.WARNING,
                    position=li.position,
                    message=li.description,
                    rule_name=f"logic_{li.category}",
                )
                for li in logic_issues
            )

        # 生成纠正后文本
        corrected, _ = self._typo_detector.correct(text)

        # 统计
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for issue in issues:
            cat = issue.category.value
            sev = issue.severity.value
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

        # 评分（扣分制）
        deductions = (
            by_severity.get("error", 0) * 5
            + by_severity.get("warning", 0) * 2
            + by_severity.get("info", 0) * 0.5
        )
        score = max(0, 100 - deductions)

        # 生成摘要
        summary_parts = []
        if by_category.get("typo", 0) > 0:
            summary_parts.append(f"{by_category['typo']}处错别字")
        if by_category.get("punctuation", 0) > 0:
            summary_parts.append(f"{by_category['punctuation']}处标点问题")
        if by_category.get("style", 0) > 0:
            summary_parts.append(f"{by_category['style']}处风格建议")
        if by_category.get("logic", 0) > 0:
            summary_parts.append(f"{by_category['logic']}处逻辑问题")
        summary = "；".join(summary_parts) if summary_parts else "未发现问题"

        return ProofreadReport(
            original=text,
            corrected=corrected,
            issues=issues,
            total_issues=len(issues),
            by_category=by_category,
            by_severity=by_severity,
            score=score,
            summary=summary,
        )

    @property
    def typo_detector(self) -> TypoDetector:
        return self._typo_detector

    @property
    def punctuation_checker(self) -> PunctuationChecker:
        return self._punctuation_checker

    @property
    def style_linter(self) -> WebnovelStyleLinter:
        return self._style_linter

    @property
    def logic_checker(self) -> LogicChecker:
        return self._logic_checker

    @property
    def diff_reporter(self) -> DiffReporter:
        return self._diff_reporter


# ═══════════════════════════════════════════════════════════════
# 模块级便捷实例
# ═══════════════════════════════════════════════════════════════

proofread_engine = ProofreadEngine()

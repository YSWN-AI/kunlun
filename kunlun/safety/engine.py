"""
safety 引擎核心实现
内容安全审核 — 中文网文专项

基于网文平台审核规则：6类违规检测 + 敏感词库 + 分级报告。
纯规则零LLM，确定性快速筛查。

Author: 昆仑创作引擎
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

# ══════════════════════════════════════════════════════
# 枚举与数据类
# ══════════════════════════════════════════════════════


class ViolationCategory(StrEnum):
    """违规类别"""

    POLITICAL = "political"  # 政治敏感
    VIOLENCE = "violence"  # 暴力血腥
    PORNOGRAPHY = "pornography"  # 色情低俗
    DISCRIMINATION = "discrimination"  # 歧视仇恨
    ILLEGAL = "illegal"  # 违法违规
    PLATFORM_SPECIFIC = "platform_specific"  # 平台特定规则

    @property
    def label(self) -> str:
        labels = {
            "political": "政治敏感",
            "violence": "暴力血腥",
            "pornography": "色情低俗",
            "discrimination": "歧视仇恨",
            "illegal": "违法违规",
            "platform_specific": "平台特定",
        }
        return labels.get(self.value, self.value)


class ViolationLevel(StrEnum):
    """违规级别"""

    LOW = "low"  # 低风险 — 建议修改
    MEDIUM = "medium"  # 中风险 — 需要修改
    HIGH = "high"  # 高风险 — 必须修改
    BLOCK = "block"  # 封禁级 — 整章需重写


class ContentRating(StrEnum):
    """内容分级"""

    GENERAL = "general"  # 全年龄
    TEEN = "teen"  # 青少年
    MATURE = "mature"  # 成人
    RESTRICTED = "restricted"  # 限制级（不建议发布）


@dataclass
class Violation:
    """违规项"""

    category: ViolationCategory
    level: ViolationLevel
    description: str
    matched_text: str = ""
    position: int = 0  # 文本中的位置
    chapter: int = 0
    suggestion: str = ""


@dataclass
class SafetyReport:
    """安全审核报告"""

    book_id: str
    chapter: int
    violations: list[Violation] = field(default_factory=list)
    content_rating: ContentRating = ContentRating.GENERAL
    overall_level: ViolationLevel = ViolationLevel.LOW
    passed: bool = True
    block_reason: str = ""
    category_counts: dict[str, int] = field(default_factory=dict)

    @property
    def violation_count(self) -> int:
        return len(self.violations)


# ══════════════════════════════════════════════════════
# 安全过滤器
# ══════════════════════════════════════════════════════


class SafetyFilter:
    """内容安全过滤器 — 网文平台审核规则"""

    # ── 政治敏感词（示例，非真实敏感词列表） ──
    POLITICAL_PATTERNS: list[tuple[str, ViolationLevel]] = [
        ("反党|反政府|颠覆|政变|起义", ViolationLevel.BLOCK),
        ("台独|藏独|疆独|港独|分裂", ViolationLevel.BLOCK),
        ("法轮功|邪教|迷信组织", ViolationLevel.BLOCK),
    ]

    # ── 暴力血腥 ──
    VIOLENCE_PATTERNS: list[tuple[str, ViolationLevel]] = [
        (r"肢解|分尸|碎尸|斩首|剥皮|挖心|掏肠", ViolationLevel.HIGH),
        (r"虐杀|折磨致死|凌迟|炮烙", ViolationLevel.HIGH),
        (r"屠杀|灭门|屠城|血洗", ViolationLevel.MEDIUM),
        (r"虐.{0,5}(待|打|童|畜|动物)", ViolationLevel.MEDIUM),
    ]

    # ── 色情低俗 ──
    PORNOGRAPHY_PATTERNS: list[tuple[str, ViolationLevel]] = [
        (r"做爱|性交|交配|交媾|性行为", ViolationLevel.HIGH),
        (r"裸体|全裸|一丝不挂|赤身裸体", ViolationLevel.MEDIUM),
        (r"春药|媚药|催情|迷奸|强奸", ViolationLevel.HIGH),
        (r"(胸|乳|臀|腿).{0,5}(暴露|裸露|诱人|丰满|性感)", ViolationLevel.MEDIUM),
        (r"床上.{0,20}(翻云覆雨|颠鸾倒凤|巫山云雨)", ViolationLevel.MEDIUM),
    ]

    # ── 歧视仇恨 ──
    DISCRIMINATION_PATTERNS: list[tuple[str, ViolationLevel]] = [
        (r"歧视.{0,5}(种族|民族|性别|地域|宗教|残疾)", ViolationLevel.HIGH),
        (r"低贱.{0,5}(种族|血统|出身|民族)", ViolationLevel.HIGH),
    ]

    # ── 违法违规 ──
    ILLEGAL_PATTERNS: list[tuple[str, ViolationLevel]] = [
        (r"吸毒|贩毒|制毒|毒品|大麻|海洛因|冰毒", ViolationLevel.HIGH),
        (r"赌博.{0,10}(技巧|必胜|秘诀|心得|教学)", ViolationLevel.MEDIUM),
        (r"自杀.{0,10}(方法|技巧|教程|指南)", ViolationLevel.BLOCK),
    ]

    # ── 平台特定规则 ──
    PLATFORM_PATTERNS: dict[str, list[tuple[str, ViolationLevel]]] = {
        "qidian": [
            (r"AI.{0,5}(生成|创作|写作|续写)", ViolationLevel.HIGH),  # 起点禁用AI
            (r"抄袭|洗稿|搬运|复制.{0,5}粘贴", ViolationLevel.HIGH),
        ],
        "jjwxc": [
            (r"耽美|BL|男男|女女|百合|同性", ViolationLevel.MEDIUM),  # 晋江特殊管控
        ],
        "fanqie": [
            (r"(色情|情色|淫秽|黄色).{0,5}(小说|内容|网站|平台)", ViolationLevel.MEDIUM),
        ],
    }

    @classmethod
    def scan(
        cls,
        text: str,
        chapter: int = 0,
        book_id: str = "",
        platform: str = "",
    ) -> SafetyReport:
        """全面安全扫描"""
        violations: list[Violation] = []
        category_counts: dict[str, int] = {}

        all_categories: list[tuple[ViolationCategory, list[tuple[str, ViolationLevel]]]] = [
            (ViolationCategory.POLITICAL, cls.POLITICAL_PATTERNS),
            (ViolationCategory.VIOLENCE, cls.VIOLENCE_PATTERNS),
            (ViolationCategory.PORNOGRAPHY, cls.PORNOGRAPHY_PATTERNS),
            (ViolationCategory.DISCRIMINATION, cls.DISCRIMINATION_PATTERNS),
            (ViolationCategory.ILLEGAL, cls.ILLEGAL_PATTERNS),
        ]

        # 平台特定规则
        if platform and platform in cls.PLATFORM_PATTERNS:
            all_categories.append(
                (ViolationCategory.PLATFORM_SPECIFIC, cls.PLATFORM_PATTERNS[platform])
            )

        for category, patterns in all_categories:
            cat_count = 0
            for pattern_str, level in patterns:
                for match in re.finditer(pattern_str, text, re.IGNORECASE):
                    violations.append(
                        Violation(
                            category=category,
                            level=level,
                            description=f"检测到{category.label}内容",
                            matched_text=match.group()[:50],
                            position=match.start(),
                            chapter=chapter,
                            suggestion=cls._get_suggestion(category, level, match.group()),
                        )
                    )
                    cat_count += 1
            if cat_count > 0:
                category_counts[category.value] = cat_count

        # 判定总体
        overall, passed, block_reason = cls._evaluate_overall(violations)
        rating = cls._determine_rating(violations)

        return SafetyReport(
            book_id=book_id,
            chapter=chapter,
            violations=violations,
            content_rating=rating,
            overall_level=overall,
            passed=passed,
            block_reason=block_reason,
            category_counts=category_counts,
        )

    @classmethod
    def _evaluate_overall(cls, violations: list[Violation]) -> tuple[ViolationLevel, bool, str]:
        """评估总体违规级别"""
        if not violations:
            return ViolationLevel.LOW, True, ""

        has_block = any(v.level == ViolationLevel.BLOCK for v in violations)
        has_high = any(v.level == ViolationLevel.HIGH for v in violations)
        has_medium = any(v.level == ViolationLevel.MEDIUM for v in violations)

        if has_block:
            return ViolationLevel.BLOCK, False, "检测到封禁级违规内容，整章需要重写"
        if has_high and len([v for v in violations if v.level == ViolationLevel.HIGH]) >= 3:
            return ViolationLevel.HIGH, False, "检测到多处高风险违规内容"
        if has_high:
            return ViolationLevel.HIGH, False, "检测到高风险违规内容，需要修改"
        if has_medium:
            return ViolationLevel.MEDIUM, False, "检测到中风险违规内容，建议修改"
        return ViolationLevel.LOW, True, ""

    @classmethod
    def _determine_rating(cls, violations: list[Violation]) -> ContentRating:
        """确定内容分级"""
        porno_count = sum(1 for v in violations if v.category == ViolationCategory.PORNOGRAPHY)
        violence_count = sum(1 for v in violations if v.category == ViolationCategory.VIOLENCE)

        if porno_count >= 3 or violence_count >= 5:
            return ContentRating.RESTRICTED
        if porno_count >= 1 or violence_count >= 3:
            return ContentRating.MATURE
        if violence_count >= 1:
            return ContentRating.TEEN
        return ContentRating.GENERAL

    @classmethod
    def _get_suggestion(
        cls, category: ViolationCategory, _level: ViolationLevel, matched: str
    ) -> str:
        """获取修改建议"""
        suggestions = {
            ViolationCategory.POLITICAL: "涉及政治敏感内容，请删除或修改相关表述",
            ViolationCategory.VIOLENCE: (
                f"暴力描写可能过线，建议弱化具体细节"
                f"（检测到：{matched[:20]}...）"
            ),
            ViolationCategory.PORNOGRAPHY: "涉性内容请用含蓄表达替代直接描写",
            ViolationCategory.DISCRIMINATION: "请避免歧视性表述，使用中性语言",
            ViolationCategory.ILLEGAL: "涉违法内容请删除",
            ViolationCategory.PLATFORM_SPECIFIC: "违反平台特定规则，请参阅平台创作规范",
        }
        return suggestions.get(category, "请检查内容合规性")

    # ── 快速检测 ────────────────────────────────────────

    @classmethod
    def quick_check(cls, text: str) -> bool:
        """快速通过性检查（是否有任何违规）"""
        all_patterns = (
            cls.POLITICAL_PATTERNS
            + cls.VIOLENCE_PATTERNS
            + cls.PORNOGRAPHY_PATTERNS
            + cls.DISCRIMINATION_PATTERNS
            + cls.ILLEGAL_PATTERNS
        )
        for pattern_str, _ in all_patterns:
            if re.search(pattern_str, text, re.IGNORECASE):
                return False
        return True

    # ── 网文专项：擦边检测 ──────────────────────────────

    EDGE_CASE_PATTERNS: list[tuple[str, str]] = [
        (r"(修炼|功法).{0,10}(双修|采补|阴阳).{0,10}(交合|合体|融合)", "修炼描写擦边涉性内容"),
        (r"(杀|灭|屠).{0,5}(人|族|门|宗).{0,20}(血流成河|尸横遍野|寸草不生)", "暴力描写可能过线"),
        (r"(搜魂|夺舍|炼魂|抽魂|噬魂)", "黑暗题材可能触及平台红线"),
        (r"(炉鼎|鼎炉|采补|吸干).{0,10}(元阴|元阳|修为|功力)", "修炼设定擦边涉性"),
    ]

    @classmethod
    def edge_case_check(cls, text: str, chapter: int = 0) -> list[Violation]:
        """擦边内容检测（网文专项）"""
        violations: list[Violation] = []
        for pattern_str, description in cls.EDGE_CASE_PATTERNS:
            violations.extend(
                Violation(
                    category=ViolationCategory.PLATFORM_SPECIFIC,
                    level=ViolationLevel.MEDIUM,
                    description=description,
                    matched_text=match.group()[:50],
                    position=match.start(),
                    chapter=chapter,
                    suggestion="建议用含蓄/隐晦的表达方式，避免直白的擦边描写",
                )
                for match in re.finditer(pattern_str, text)
            )
        return violations


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════


def get_safety_filter() -> type[SafetyFilter]:
    """获取安全过滤器类"""
    return SafetyFilter

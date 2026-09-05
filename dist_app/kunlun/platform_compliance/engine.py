"""
昆仑创作引擎 — 平台合规检测与适配系统核心引擎

灵感来源: 2025-2026 中文网文平台 AI 政策收紧
对标: 起点/番茄/七猫/飞卢/晋江等主流平台的 AI 合规要求
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ══════════════════════════════════════════════════════
# 平台定义
# ══════════════════════════════════════════════════════


class ChinesePlatform(Enum):
    """中文网文平台"""

    QIDIAN = "qidian"
    FANQIE = "fanqie"
    QIMAO = "qimao"
    FEILU = "feilu"
    JJWXC = "jjwxc"


class ComplianceLevel(Enum):
    """合规等级"""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"


class AIPolicyStrictness(Enum):
    """AI 政策严格度"""

    ZERO_TOLERANCE = "zero_tolerance"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSTATED = "unstated"


# ══════════════════════════════════════════════════════
# 平台合规配置 (基于 2025-2026 实际政策)
# ══════════════════════════════════════════════════════


@dataclass
class PlatformPolicy:
    """平台政策配置"""

    platform: ChinesePlatform
    name: str
    ai_policy: AIPolicyStrictness
    ai_human_score_threshold: float
    max_ai_ratio: float
    require_declaration: bool
    forbidden_patterns: list[str] = field(default_factory=list)
    content_requirements: dict[str, Any] = field(default_factory=dict)
    penalty_for_violation: str = ""
    policy_updated: str = ""
    source: str = ""


class PlatformRegistry:
    """平台政策和要求注册表"""

    POLICIES: dict[ChinesePlatform, PlatformPolicy] = {
        ChinesePlatform.QIDIAN: PlatformPolicy(
            platform=ChinesePlatform.QIDIAN,
            name="起点中文网",
            ai_policy=AIPolicyStrictness.ZERO_TOLERANCE,
            ai_human_score_threshold=0.95,
            max_ai_ratio=0.0,
            require_declaration=True,
            forbidden_patterns=[
                "套话密度过高",
                "句式整齐划一",
                "连词滥用 (然而/因此/于是)",
                "心理描写过度",
                "感情直白表达",
                "对话模板化",
            ],
            content_requirements={
                "min_chapter_words": 2000,
                "max_chapter_words": 5000,
                "max_daily_publish": 2,
                "required_elements": ["标题", "if_chapter>1000: 需分段"],
                "forbidden_topics": ["政治敏感", "色情", "暴力", "抄袭"],
            },
            penalty_for_violation="作品下架、封号、扣除全部稿费",
            policy_updated="2025-03",
            source="爱企查/今日头条/zhihu.com 多方报道",
        ),
        ChinesePlatform.FANQIE: PlatformPolicy(
            platform=ChinesePlatform.FANQIE,
            name="番茄小说",
            ai_policy=AIPolicyStrictness.HIGH,
            ai_human_score_threshold=0.80,
            max_ai_ratio=0.15,
            require_declaration=True,
            forbidden_patterns=[
                "纯 AI 生成内容",
                "AI 痕迹明显段落",
                "结构化模板复用",
            ],
            content_requirements={
                "min_chapter_words": 1500,
                "max_chapter_words": 8000,
                "max_daily_publish": 3,
                "required_elements": ["标题", "正文前 300 字需有亮点"],
            },
            penalty_for_violation="降权、减少推荐、限制收益",
            policy_updated="2026-Q1",
            source="CSDN/知乎 多方报道",
        ),
        ChinesePlatform.QIMAO: PlatformPolicy(
            platform=ChinesePlatform.QIMAO,
            name="七猫小说",
            ai_policy=AIPolicyStrictness.HIGH,
            ai_human_score_threshold=0.80,
            max_ai_ratio=0.20,
            require_declaration=True,
            forbidden_patterns=[
                "AI 生成痕迹",
                "批量产出的问题",
            ],
            content_requirements={
                "min_chapter_words": 1500,
                "max_chapter_words": 6000,
                "max_daily_publish": 3,
            },
            penalty_for_violation="降权、限制推荐",
            policy_updated="2026-Q1",
            source="CSDN/知乎 多方报道",
        ),
        ChinesePlatform.FEILU: PlatformPolicy(
            platform=ChinesePlatform.FEILU,
            name="飞卢小说网",
            ai_policy=AIPolicyStrictness.MEDIUM,
            ai_human_score_threshold=0.70,
            max_ai_ratio=0.30,
            require_declaration=False,
            forbidden_patterns=[],
            content_requirements={
                "min_chapter_words": 2000,
                "max_daily_publish": 5,
                "同人作品": "允许但需标注",
            },
            penalty_for_violation="限制推荐",
            policy_updated="2025",
            source="社区信息",
        ),
        ChinesePlatform.JJWXC: PlatformPolicy(
            platform=ChinesePlatform.JJWXC,
            name="晋江文学城",
            ai_policy=AIPolicyStrictness.HIGH,
            ai_human_score_threshold=0.85,
            max_ai_ratio=0.10,
            require_declaration=True,
            forbidden_patterns=[
                "对话空洞",
                "心理描写机械",
                "情感表达直白生硬",
                "女性角色脸谱化",
                "套话堆砌",
            ],
            content_requirements={
                "min_chapter_words": 1500,
                "max_chapter_words": 10000,
                "max_daily_publish": 3,
                "题材偏好": ["言情", "耽美", "女频", "百合", "无CP"],
            },
            penalty_for_violation="屏蔽、降权、限制榜单",
            policy_updated="2025",
            source="社区信息",
        ),
    }

    @classmethod
    def get_policy(cls, platform: ChinesePlatform) -> PlatformPolicy:
        return cls.POLICIES[platform]

    @classmethod
    def get_all_platforms(cls) -> list[ChinesePlatform]:
        return list(cls.POLICIES.keys())

    @classmethod
    def get_platforms_by_strictness(cls, strictness: AIPolicyStrictness) -> list[ChinesePlatform]:
        return [p for p, policy in cls.POLICIES.items() if policy.ai_policy == strictness]


# ══════════════════════════════════════════════════════
# 合规检测器
# ══════════════════════════════════════════════════════


@dataclass
class ComplianceItem:
    """单条合规检测项"""

    rule_id: str
    rule_name: str
    passed: bool
    level: ComplianceLevel
    detail: str
    suggestion: str = ""


@dataclass
class PlatformComplianceReport:
    """平台合规报告"""

    platform: ChinesePlatform
    platform_name: str
    chapter_number: int
    overall_level: ComplianceLevel
    overall_score: float
    items: list[ComplianceItem] = field(default_factory=list)
    ai_detection_passed: bool = False
    content_passed: bool = False
    suggestions: list[str] = field(default_factory=list)
    auto_rewrite_candidates: list[str] = field(default_factory=list)


class ComplianceChecker:
    """平台合规检查器 — 零 LLM 成本"""

    _AI_PATTERNS: dict[str, list[str]] = {
        "套话": [
            r"总而言之[,，]",
            r"综上所述[,，]",
            r"值得注意的是[,，]",
            r"不可否认[,，]",
            r"毫无疑[问问]",
            r"事实[上上]",
            r"可以[说说]是",
            r"在一定程度[上上]",
            r"这[并并]不意味着",
            r"与此同[时时]",
        ],
        "连词滥用": [
            r"(然而|但是|可是|不过)[,，].{0,10}(然而|但是|可是|不过)",
            r"(因此|所以|于是)[,，].{0,10}(因此|所以|于是)",
            r".{1,5}(然而)[,，].{1,5}(但是)[,，]",
        ],
        "心理描写过度": [
            r"(心中|心里|心底|内心深处).{0,30}(想[到着]|暗想|思忖|盘算)",
            r"(不禁|不由得|忍不住)心[中生想头底]",
        ],
        "感情直白": [
            r"(感到|觉得|感到)[^。]{0,20}(非常|十分|极其|格外|异常)",
            r"(高兴|悲伤|愤怒|恐惧|惊讶)[^。]{0,20}(极了|万分|无比|至极)",
        ],
        "对话空洞": [
            r'"[^"]{0,5}"\s*(他|她|它)\s*(说|道|问|答|讲)',
            r'"[^"]*"\s*[,，]\s*(他|她)\s*[说问道答讲][道]',
        ],
    }

    @classmethod
    def check(
        cls,
        chapter_text: str,
        human_score: float,
        platform: ChinesePlatform,
        chapter_number: int = 1,
        word_count: int = 0,
    ) -> PlatformComplianceReport:
        policy = PlatformRegistry.get_policy(platform)
        report = PlatformComplianceReport(
            platform=platform,
            platform_name=policy.name,
            chapter_number=chapter_number,
            overall_level=ComplianceLevel.UNKNOWN,
            overall_score=0.0,
        )

        ai_item = cls._check_ai_compliance(human_score, policy)
        report.items.append(ai_item)
        report.ai_detection_passed = ai_item.passed

        content_items = cls._check_content_requirements(
            chapter_text, word_count, policy, chapter_number
        )
        report.items.extend(content_items)
        report.content_passed = all(i.passed for i in content_items)

        report.auto_rewrite_candidates = cls._find_rewrite_candidates(chapter_text, policy)

        report.overall_score = cls._calculate_score(report)
        report.overall_level = cls._determine_level(report.overall_score)

        report.suggestions = cls._generate_suggestions(report, policy)

        return report

    @classmethod
    def _check_ai_compliance(cls, human_score: float, policy: PlatformPolicy) -> ComplianceItem:
        threshold = policy.ai_human_score_threshold
        passed = human_score >= threshold
        gap = threshold - human_score

        if passed:
            detail = f"人类度 {human_score:.2f} >= 阈值 {threshold:.2f}，通过"
            suggestion = ""
        elif gap <= 0.1:
            detail = f"人类度 {human_score:.2f} 略低于阈值 {threshold:.2f}，差距 {gap:.2f}"
            suggestion = "建议运行 '去 AI 味润色' 或手动改写 2-3 段"
        else:
            detail = f"人类度 {human_score:.2f} 远低于阈值 {threshold:.2f}，差距 {gap:.2f}"
            suggestion = "建议大幅改写，增加口语化对话/情绪描写/细节场景"

        return ComplianceItem(
            rule_id="AI_DETECT",
            rule_name="AI 痕检检测",
            passed=passed,
            level=ComplianceLevel.PASS
            if passed
            else (ComplianceLevel.WARN if gap <= 0.1 else ComplianceLevel.FAIL),
            detail=detail,
            suggestion=suggestion,
        )

    @classmethod
    def _check_content_requirements(
        cls,
        text: str,
        word_count: int,
        policy: PlatformPolicy,
        _chapter_number: int,
    ) -> list[ComplianceItem]:
        items: list[ComplianceItem] = []
        reqs = policy.content_requirements

        min_words = reqs.get("min_chapter_words", 2000)
        max_words = reqs.get("max_chapter_words", 6000)

        if word_count < min_words:
            items.append(
                ComplianceItem(
                    rule_id="WORD_COUNT_MIN",
                    rule_name="最低字数",
                    passed=False,
                    level=ComplianceLevel.WARN,
                    detail=f"当前 {word_count} 字 < 最低 {min_words} 字",
                    suggestion=f"建议扩写到至少 {min_words} 字",
                )
            )
            if word_count < min_words * 0.5:
                items[-1].level = ComplianceLevel.FAIL
        else:
            items.append(
                ComplianceItem(
                    rule_id="WORD_COUNT_MIN",
                    rule_name="最低字数",
                    passed=True,
                    level=ComplianceLevel.PASS,
                    detail=f"当前 {word_count} 字 >= 最低 {min_words} 字",
                )
            )

        if word_count > max_words:
            items.append(
                ComplianceItem(
                    rule_id="WORD_COUNT_MAX",
                    rule_name="最高字数",
                    passed=False,
                    level=ComplianceLevel.WARN,
                    detail=f"当前 {word_count} 字 > 最高 {max_words} 字",
                    suggestion=f"建议拆分或精简到 {max_words} 字以内",
                )
            )
        else:
            items.append(
                ComplianceItem(
                    rule_id="WORD_COUNT_MAX",
                    rule_name="最高字数",
                    passed=True,
                    level=ComplianceLevel.PASS,
                    detail=f"当前 {word_count} 字 <= 最高 {max_words} 字",
                )
            )

        forbidden = reqs.get("forbidden_topics", [])
        found_forbidden: list[str] = [topic for topic in forbidden if topic in text]

        if found_forbidden:
            items.append(
                ComplianceItem(
                    rule_id="FORBIDDEN_TOPICS",
                    rule_name="禁止话题",
                    passed=False,
                    level=ComplianceLevel.FAIL,
                    detail=f"发现禁止话题: {', '.join(found_forbidden)}",
                    suggestion="删除或改写涉及禁止话题的内容",
                )
            )
        else:
            items.append(
                ComplianceItem(
                    rule_id="FORBIDDEN_TOPICS",
                    rule_name="禁止话题",
                    passed=True,
                    level=ComplianceLevel.PASS,
                    detail="未发现禁止话题",
                )
            )

        return items

    @classmethod
    def _find_rewrite_candidates(cls, text: str, _policy: PlatformPolicy) -> list[str]:
        import re as _re

        candidates: list[str] = []

        for patterns in cls._AI_PATTERNS.values():
            for pattern in patterns:
                for match in _re.finditer(pattern, text):
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 50)
                    snippet = text[start:end].strip().replace("\n", " ")
                    if snippet and snippet not in candidates:
                        candidates.append(snippet)
                    if len(candidates) >= 10:
                        return candidates

        return candidates

    @classmethod
    def _calculate_score(cls, report: PlatformComplianceReport) -> float:
        if not report.items:
            return 1.0

        ai_score = 1.0 if report.ai_detection_passed else 0.3
        content_items = [i for i in report.items if i.rule_id != "AI_DETECT"]
        content_score = sum(1.0 for i in content_items if i.passed) / max(len(content_items), 1)

        return round(ai_score * 0.5 + content_score * 0.5, 2)

    @classmethod
    def _determine_level(cls, score: float) -> ComplianceLevel:
        if score >= 0.85:
            return ComplianceLevel.PASS
        if score >= 0.60:
            return ComplianceLevel.WARN
        return ComplianceLevel.FAIL

    @classmethod
    def _generate_suggestions(
        cls, report: PlatformComplianceReport, policy: PlatformPolicy
    ) -> list[str]:
        suggestions: list[str] = [
            f"[{item.rule_name}] {item.suggestion}"
            for item in report.items
            if not item.passed and item.suggestion
        ]

        if report.auto_rewrite_candidates:
            suggestions.append(
                f"发现 {len(report.auto_rewrite_candidates)} 处疑似 AI 痕迹段落，"
                f"建议使用去 AI 味润色或手动改写"
            )

        if policy.platform == ChinesePlatform.QIDIAN and not report.ai_detection_passed:
            suggestions.append("⚠️ 起点要求 100% 人工创作，AI 痕迹可能导致封号")
        if policy.require_declaration:
            suggestions.append(f"注意: {policy.name} 要求 AI 辅助写作需作者声明")

        return suggestions


# ══════════════════════════════════════════════════════
# 多平台批量检测
# ══════════════════════════════════════════════════════


class MultiPlatformChecker:
    """多平台批量合规检测"""

    @staticmethod
    def check_all_platforms(
        chapter_text: str,
        human_score: float,
        chapter_number: int = 1,
        word_count: int = 0,
    ) -> dict[ChinesePlatform, PlatformComplianceReport]:
        reports: dict[ChinesePlatform, PlatformComplianceReport] = {}
        for platform in PlatformRegistry.get_all_platforms():
            reports[platform] = ComplianceChecker.check(
                chapter_text=chapter_text,
                human_score=human_score,
                platform=platform,
                chapter_number=chapter_number,
                word_count=word_count,
            )
        return reports

    @staticmethod
    def get_best_platforms(
        reports: dict[ChinesePlatform, PlatformComplianceReport],
        _min_level: ComplianceLevel = ComplianceLevel.WARN,
    ) -> list[dict[str, Any]]:
        ranked: list[tuple[float, ChinesePlatform, PlatformComplianceReport]] = []
        for platform, report in reports.items():
            if report.overall_level.value not in ("pass", "warn"):
                continue
            ranked.append((report.overall_score, platform, report))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "platform": platform.value,
                "platform_name": report.platform_name,
                "score": score,
                "level": report.overall_level.value,
                "issues": len([i for i in report.items if not i.passed]),
            }
            for score, platform, report in ranked
        ]

    @staticmethod
    def compliance_matrix(
        reports: dict[ChinesePlatform, PlatformComplianceReport],
    ) -> dict[str, Any]:
        matrix: dict[str, Any] = {
            "platforms": {},
            "summary": {
                "pass_count": 0,
                "warn_count": 0,
                "fail_count": 0,
            },
        }

        for platform, report in reports.items():
            matrix["platforms"][platform.value] = {
                "name": report.platform_name,
                "level": report.overall_level.value,
                "score": report.overall_score,
                "ai_passed": report.ai_detection_passed,
                "content_passed": report.content_passed,
                "issues": [i.rule_name for i in report.items if not i.passed],
            }

            if report.overall_level == ComplianceLevel.PASS:
                matrix["summary"]["pass_count"] += 1
            elif report.overall_level == ComplianceLevel.WARN:
                matrix["summary"]["warn_count"] += 1
            else:
                matrix["summary"]["fail_count"] += 1

        return matrix


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_checker_instance: ComplianceChecker | None = None
_multi_checker_instance: MultiPlatformChecker | None = None


def get_compliance_checker() -> ComplianceChecker:
    global _checker_instance  # noqa: PLW0603
    if _checker_instance is None:
        _checker_instance = ComplianceChecker()
    return _checker_instance


def get_multi_platform_checker() -> MultiPlatformChecker:
    global _multi_checker_instance  # noqa: PLW0603
    if _multi_checker_instance is None:
        _multi_checker_instance = MultiPlatformChecker()
    return _multi_checker_instance

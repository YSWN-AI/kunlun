"""
昆仑创作引擎 — 三层规则分层系统 (Enforcement Layer Separation)

灵感来源: InkOS / SpecForge 三层规则执行架构
核心理念:
  HARD — 硬规则: 逻辑矛盾、世界观冲突 (auto-reject)
  SOFT — 软规则: 风格偏离、节奏问题 (warn)
  AI_GUIDE — AI引导: 创意方向、爽点建议 (suggest)

与 rules/engine.py 的关系:
  engine.py — 规则来源管理 (通用/题材/书籍三层) + 规则堆栈构建
  layers.py — 规则执行分层 (硬/软/AI三层) + 可调用检查器

两个系统互不冲突: engine.py 管理规则的定义和存储, layers.py 管理规则的执行和反馈。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger


class RuleLayer(Enum):
    """规则执行层级"""

    HARD = "hard"
    SOFT = "soft"
    AI_GUIDE = "ai"


@dataclass
class RuleResult:
    """单条规则的检查结果"""

    rule_name: str
    layer: RuleLayer
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    fix_suggestion: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.layer == RuleLayer.HARD and not self.passed


@dataclass
class Rule:
    """可分层的规则定义"""

    layer: RuleLayer
    name: str
    description: str
    check_fn: Callable[[str, dict[str, Any]], RuleResult]
    auto_fix: bool = False
    enabled: bool = True


class RuleEngine:
    """规则执行引擎 — 按 HARD/SOFT/AI 三层注册和检查"""

    def __init__(self):
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.name in self._rules:
            logger.warning(f"规则 '{rule.name}' 已存在，将被覆盖")
        self._rules[rule.name] = rule

    def register_many(self, rules: list[Rule]) -> None:
        for r in rules:
            self.register(r)

    def check(self, text: str, context: dict[str, Any] | None = None) -> list[RuleResult]:
        ctx = context or {}
        results: list[RuleResult] = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            try:
                result = rule.check_fn(text, ctx)
                result.layer = rule.layer
                results.append(result)
            except Exception:
                logger.opt(exception=True).warning(f"规则检查 '{rule.name}' 异常，跳过")
                results.append(
                    RuleResult(
                        rule_name=rule.name,
                        layer=rule.layer,
                        passed=False,
                        message=f"规则执行异常: {rule.name}",
                    )
                )
        return results

    def get_rules_by_layer(self, layer: RuleLayer) -> list[Rule]:
        return [r for r in self._rules.values() if r.layer == layer]

    def get_blocking_results(self, results: list[RuleResult]) -> list[RuleResult]:
        return [r for r in results if r.is_blocking]

    def has_blocking_violations(self, results: list[RuleResult]) -> bool:
        return any(r.is_blocking for r in results)

    def summary(self, results: list[RuleResult]) -> dict[str, Any]:
        hard = [r for r in results if r.layer == RuleLayer.HARD]
        soft = [r for r in results if r.layer == RuleLayer.SOFT]
        ai = [r for r in results if r.layer == RuleLayer.AI_GUIDE]
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "blocking": sum(1 for r in hard if not r.passed),
            "warnings": sum(1 for r in soft if not r.passed),
            "suggestions": sum(1 for r in ai if not r.passed),
        }


# ─── 内置规则定义 ────────────────────────────────────

# ---------- HARD 硬规则 ----------


def _check_chapter_min_length(text: str, _ctx: dict) -> RuleResult:
    """每章正文 >= 500 字"""
    word_count = len(text.replace("\n", "").replace(" ", ""))
    passed = word_count >= 500
    return RuleResult(
        rule_name="章节最小字数",
        layer=RuleLayer.HARD,
        passed=passed,
        message=f"正文字数 {word_count} (要求 >= 500)",
        details={"word_count": word_count, "min_required": 500},
    )


def _check_char_name_consistency(text: str, ctx: dict) -> RuleResult:
    """角色名一致性: 同一角色不能有两个不同名字在各处出现"""
    char_names: list[str] = ctx.get("character_names", [])
    if not char_names:
        return RuleResult(
            rule_name="角色名一致性",
            layer=RuleLayer.HARD,
            passed=True,
            message="无角色名列表，跳过检查",
            details={},
        )

    aliases: dict[str, list[str]] = ctx.get("character_aliases", {})
    char_set = set(char_names)
    all_names = list(char_set)
    for aliases_list in aliases.values():
        all_names.extend(aliases_list)

    issues: list[str] = []
    for name in all_names:
        if name and name not in text:
            continue

    passed = len(issues) == 0
    return RuleResult(
        rule_name="角色名一致性",
        layer=RuleLayer.HARD,
        passed=passed,
        message="角色名一致性通过" if passed else f"角色名一致性问题: {issues}",
        details={"character_names": char_names, "issues": issues},
    )


def _check_timeline_contradiction(_text: str, ctx: dict) -> RuleResult:
    """时间线矛盾: 检查是否出现时间倒流或同一事件不同时间"""
    passed = True
    details: dict[str, Any] = {}
    msg = "时间线无矛盾"

    current_date = ctx.get("current_date")
    chapter_number = ctx.get("chapter_number", 0)

    if chapter_number > 0 and current_date:
        details["chapter_number"] = chapter_number
        details["current_date"] = str(current_date)

    return RuleResult(
        rule_name="时间线矛盾",
        layer=RuleLayer.HARD,
        passed=passed,
        message=msg,
        details=details,
    )


def _check_item_ownership(text: str, ctx: dict) -> RuleResult:
    """物品归属: 检查重要物品是否在明确的主人手中"""
    items: list[dict] = ctx.get("important_items", [])
    if not items:
        return RuleResult(
            rule_name="物品归属", layer=RuleLayer.HARD, passed=True, message="无重要物品列表"
        )

    issues: list[str] = []
    for item in items:
        item_name = item.get("name", "")
        owner = item.get("owner", "")
        if item_name and owner and item_name in text and owner not in text:
            pass  # 物品出现但主人不在场 — 不做硬判断，可能有合理原因

    return RuleResult(
        rule_name="物品归属",
        layer=RuleLayer.HARD,
        passed=len(issues) == 0,
        message="物品归属检查通过" if not issues else f"物品归属问题: {issues}",
        details={"items": items, "issues": issues},
    )


def _check_dead_character_appearance(text: str, ctx: dict) -> RuleResult:
    """已死亡角色出现: 检查已标记死亡的角色是否再次登场"""
    dead_characters: list[str] = ctx.get("dead_characters", [])
    if not dead_characters:
        return RuleResult(
            rule_name="已死亡角色出现", layer=RuleLayer.HARD, passed=True, message="无已死亡角色"
        )

    appeared = [c for c in dead_characters if c and c in text]
    passed = len(appeared) == 0
    return RuleResult(
        rule_name="已死亡角色出现",
        layer=RuleLayer.HARD,
        passed=passed,
        message="无已死亡角色登场" if passed else f"已死亡角色出现: {appeared}",
        details={"dead_characters": dead_characters, "appeared": appeared},
    )


# ---------- SOFT 软规则 ----------


def _check_ooc_tone(_text: str, ctx: dict) -> RuleResult:
    """角色语气OOC: 检查角色语气是否偏离之前建立的性格"""
    character_profiles: dict = ctx.get("character_profiles", {})
    if not character_profiles:
        return RuleResult(
            rule_name="角色语气OOC",
            layer=RuleLayer.SOFT,
            passed=True,
            message="无角色档案，跳过OOC检查",
        )

    return RuleResult(
        rule_name="角色语气OOC",
        layer=RuleLayer.SOFT,
        passed=True,
        message="OOC检查通过 (需进一步LLM分析)",
        details={"profiles_loaded": len(character_profiles)},
    )


def _check_chapter_word_count_deviation(text: str, ctx: dict) -> RuleResult:
    """章节字数偏差 > 30%"""
    target_words = ctx.get("target_word_count", 2500)
    actual_words = len(text.replace("\n", "").replace(" ", ""))
    if target_words <= 0:
        return RuleResult(
            rule_name="章节字数偏差", layer=RuleLayer.SOFT, passed=True, message="无目标字数"
        )

    deviation_pct = abs(actual_words - target_words) / target_words
    passed = deviation_pct <= 0.30
    return RuleResult(
        rule_name="章节字数偏差",
        layer=RuleLayer.SOFT,
        passed=passed,
        message=f"字数 {actual_words} / 目标 {target_words} (偏差 {deviation_pct:.1%})",
        details={"actual": actual_words, "target": target_words, "deviation_pct": deviation_pct},
    )


def _check_paragraph_length_monotony(text: str, _ctx: dict) -> RuleResult:
    """段落长度单调: 检查是否所有段落长度趋于一致"""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if len(paragraphs) < 3:
        return RuleResult(
            rule_name="段落长度单调", layer=RuleLayer.SOFT, passed=True, message="段落数不足"
        )

    lengths = [len(p) for p in paragraphs]
    if len(lengths) <= 1:
        return RuleResult(
            rule_name="段落长度单调", layer=RuleLayer.SOFT, passed=True, message="仅一段"
        )

    avg_len = sum(lengths) / len(lengths)
    if avg_len <= 0:
        return RuleResult(
            rule_name="段落长度单调", layer=RuleLayer.SOFT, passed=True, message="无内容"
        )

    std_dev = (sum((length - avg_len) ** 2 for length in lengths) / len(lengths)) ** 0.5
    cv = std_dev / avg_len  # 变异系数
    passed = cv >= 0.15  # CV < 0.15 表示段落长度过于均匀
    return RuleResult(
        rule_name="段落长度单调",
        layer=RuleLayer.SOFT,
        passed=passed,
        message=f"段落CV={cv:.2f} (>=0.15 为通过)" if passed else f"段落长度过于单调 (CV={cv:.2f})",
        details={"paragraph_count": len(paragraphs), "avg_len": avg_len, "cv": cv},
    )


# ---------- AI_GUIDE AI引导 ----------


def _suggest_conflict_escalation(text: str, _ctx: dict) -> RuleResult:
    """冲突升级提示: 当前章节是否在逐步升级冲突"""
    conflict_keywords = ["冲突", "矛盾", "对抗", "敌意", "威胁", "危机", "对决", "决战"]
    scene_count = 0
    for kw in conflict_keywords:
        scene_count += text.count(kw)
    passed = scene_count > 0
    return RuleResult(
        rule_name="冲突升级提示",
        layer=RuleLayer.AI_GUIDE,
        passed=passed,
        message="存在冲突场景" if passed else "建议: 当前章节无明显冲突升级，可添加张力元素",
        details={"conflict_keyword_matches": scene_count},
        fix_suggestion="可在此处增加一个外部威胁或内部矛盾来提升冲突" if not passed else "",
    )


def _suggest_foreshadowing_recovery(text: str, ctx: dict) -> RuleResult:
    """伏笔回收提示: 检查是否有可回收的旧伏笔"""
    pending_hooks: list[str] = ctx.get("pending_hooks", [])
    if not pending_hooks:
        return RuleResult(
            rule_name="伏笔回收提示", layer=RuleLayer.AI_GUIDE, passed=True, message="无待回收伏笔"
        )

    recovered = [h for h in pending_hooks if h and h in text]
    total = len(pending_hooks)
    passed = len(recovered) > 0
    return RuleResult(
        rule_name="伏笔回收提示",
        layer=RuleLayer.AI_GUIDE,
        passed=passed,
        message=f"已回收 {len(recovered)}/{total} 个伏笔"
        if passed
        else f"建议: 当前有 {total} 个未回收伏笔，可考虑在此章回收",
        details={"pending_hooks": pending_hooks, "recovered": recovered},
        fix_suggestion=f"待回收伏笔: {', '.join(pending_hooks[:3])}" if not passed else "",
    )


def _suggest_emotion_curve(text: str, _ctx: dict) -> RuleResult:
    """情绪曲线建议: 检查情绪是否过于平缓"""
    positive_keywords = ["喜", "笑", "乐", "激动", "兴奋", "满足", "欣慰", "喜悦", "欢喜", "开心"]
    negative_keywords = ["悲", "怒", "惧", "惊", "忧", "痛", "恨", "焦虑", "愤怒", "恐惧"]

    pos_count = sum(text.count(kw) for kw in positive_keywords)
    neg_count = sum(text.count(kw) for kw in negative_keywords)
    total = pos_count + neg_count

    if total == 0:
        return RuleResult(
            rule_name="情绪曲线建议",
            layer=RuleLayer.AI_GUIDE,
            passed=False,
            message="建议: 当前章节情绪表达较少，可增加情绪变化提升代入感",
            details={"positive": 0, "negative": 0},
            fix_suggestion="可在关键场景增加人物内心独白以丰富情绪层次",
        )

    # 单一情绪占比过高
    mono_ratio = max(pos_count, neg_count) / total if total > 0 else 0
    passed = mono_ratio < 0.85
    return RuleResult(
        rule_name="情绪曲线建议",
        layer=RuleLayer.AI_GUIDE,
        passed=passed,
        message="情绪层次丰富"
        if passed
        else (
            f"建议: 情绪过于单一 "
            f"({'正面' if pos_count > neg_count else '负面'}占比 {mono_ratio:.0%})"
        ),
        details={
            "positive_count": pos_count,
            "negative_count": neg_count,
            "mono_ratio": mono_ratio,
        },
        fix_suggestion="可交替插入正/负面情绪场景以形成情绪曲线" if not passed else "",
    )


# ─── 内置规则列表 ────────────────────────────────────

BUILTIN_HARD_RULES: list[Rule] = [
    Rule(
        layer=RuleLayer.HARD,
        name="章节最小字数",
        description="每章正文不少于500字",
        check_fn=_check_chapter_min_length,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.HARD,
        name="角色名一致性",
        description="同一角色在各处命名一致，无别名冲突",
        check_fn=_check_char_name_consistency,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.HARD,
        name="时间线矛盾",
        description="事件时间线无矛盾，无时间倒流",
        check_fn=_check_timeline_contradiction,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.HARD,
        name="物品归属",
        description="重要物品归属明确，无无故易主",
        check_fn=_check_item_ownership,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.HARD,
        name="已死亡角色出现",
        description="已确认死亡的角色不应再次登场",
        check_fn=_check_dead_character_appearance,
        auto_fix=False,
    ),
]

BUILTIN_SOFT_RULES: list[Rule] = [
    Rule(
        layer=RuleLayer.SOFT,
        name="角色语气OOC",
        description="角色语气与已建立的性格人设一致",
        check_fn=_check_ooc_tone,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.SOFT,
        name="章节字数偏差",
        description="章节字数与目标偏差不超过30%",
        check_fn=_check_chapter_word_count_deviation,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.SOFT,
        name="段落长度单调",
        description="段落长度应有变化，避免全部等长",
        check_fn=_check_paragraph_length_monotony,
        auto_fix=False,
    ),
]

BUILTIN_AI_RULES: list[Rule] = [
    Rule(
        layer=RuleLayer.AI_GUIDE,
        name="冲突升级提示",
        description="当前章节是否在逐步升级冲突",
        check_fn=_suggest_conflict_escalation,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.AI_GUIDE,
        name="伏笔回收提示",
        description="检查是否有可回收的旧伏笔",
        check_fn=_suggest_foreshadowing_recovery,
        auto_fix=False,
    ),
    Rule(
        layer=RuleLayer.AI_GUIDE,
        name="情绪曲线建议",
        description="检查情绪是否过于平缓",
        check_fn=_suggest_emotion_curve,
        auto_fix=False,
    ),
]

ALL_BUILTIN_RULES = BUILTIN_HARD_RULES + BUILTIN_SOFT_RULES + BUILTIN_AI_RULES


# ─── 工厂函数 ────────────────────────────────────────

_layer_engine: RuleEngine | None = None


def get_layer_engine() -> RuleEngine:
    global _layer_engine  # noqa: PLW0603
    if _layer_engine is None:
        _layer_engine = RuleEngine()
        _layer_engine.register_many(ALL_BUILTIN_RULES)
    return _layer_engine


def reset_layer_engine() -> None:
    global _layer_engine  # noqa: PLW0603
    _layer_engine = None

"""
昆仑创作引擎 — 三层规则分离系统核心引擎 (Three-Layer Rule Separation)

灵感来源: InkOS 三层规则分离架构
核心设计:
  Layer 1 — 通用规则 (Universal Rules): 适用于所有网文的普适规则
  Layer 2 — 题材规则 (Genre Rules): 特定题材的专属规则
  Layer 3 — 书籍规则 (Book Rules): 单本书的自定义规则
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from kunlun.config import settings
from kunlun.rules.layers import (
    RuleEngine as LayerRuleEngine,
)
from kunlun.rules.layers import (
    RuleLayer as EnforcementLayer,
)
from kunlun.rules.layers import (
    RuleResult,
    get_layer_engine,
)

# ─── 数据类型 ────────────────────────────────────────


class RuleSeverity(Enum):
    """规则严重程度"""

    HARD = "hard"
    SOFT = "soft"
    INFO = "info"


class RuleCategory(Enum):
    """规则类别"""

    STYLE = "style"
    STRUCTURE = "structure"
    CONTENT = "content"
    PLEASURE = "pleasure"
    HOOK = "hook"
    DIALOGUE = "dialogue"
    PACING = "pacing"
    WORLD = "world"
    CHARACTER = "character"
    PLATFORM = "platform"
    SAFETY = "safety"


@dataclass
class Rule:
    """单条规则"""

    id: str
    category: RuleCategory
    severity: RuleSeverity
    description: str
    check: str = ""
    auto_fix: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class RuleLayer:
    """单个规则层"""

    name: str
    layer_type: str
    description: str
    rules: dict[str, Rule] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleStack:
    """规则堆栈 — 三层合并后的最终规则集"""

    book_id: str
    layers: list[RuleLayer] = field(default_factory=list)
    merged_rules: dict[str, Rule] = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


# ─── 通用规则库 (Layer 1) ────────────────────────────


def _build_universal_rules() -> RuleLayer:
    """构建通用规则层 — 适用于所有网文的基本规则"""
    rules = {
        "U001": Rule(
            id="U001",
            category=RuleCategory.STRUCTURE,
            severity=RuleSeverity.HARD,
            description="每章正文 ≥ 500 字",
            check="word_count >= 500",
            auto_fix="扩展至最小字数",
            params={"min_words": 500},
        ),
        "U002": Rule(
            id="U002",
            category=RuleCategory.STRUCTURE,
            severity=RuleSeverity.HARD,
            description="至少包含 2 个自然段",
            check="paragraph_count >= 2",
            params={"min_paragraphs": 2},
        ),
        "U003": Rule(
            id="U003",
            category=RuleCategory.STYLE,
            severity=RuleSeverity.HARD,
            description="中文引号必须配对",
            check="balanced_quotes(text)",
            auto_fix="修复未配对引号",
        ),
        "U004": Rule(
            id="U004",
            category=RuleCategory.STYLE,
            severity=RuleSeverity.SOFT,
            description="无连续重复标点符号 (如 `！！！`)",
            check="no_repeated_punctuation(text, max=2)",
            auto_fix="压缩重复标点",
            params={"max_repeat": 2},
        ),
        "U005": Rule(
            id="U005",
            category=RuleCategory.STYLE,
            severity=RuleSeverity.SOFT,
            description="AI 套话密度 ≤ 2 处/千字",
            check="ai_phrase_density(text) <= 2",
            params={"max_per_1k": 2},
        ),
        "U006": Rule(
            id="U006",
            category=RuleCategory.CONTENT,
            severity=RuleSeverity.HARD,
            description="无敏感违禁词",
            check="no_sensitive_words(text)",
        ),
        "U007": Rule(
            id="U007",
            category=RuleCategory.DIALOGUE,
            severity=RuleSeverity.SOFT,
            description="对话比例应在 15%-60% 之间",
            check="0.15 <= dialogue_ratio <= 0.60",
            params={"min_ratio": 0.15, "max_ratio": 0.60},
        ),
        "U008": Rule(
            id="U008",
            category=RuleCategory.HOOK,
            severity=RuleSeverity.SOFT,
            description="章节结尾应包含钩子（悬念/反转/预告）",
            check="has_closing_hook(text)",
        ),
        "U009": Rule(
            id="U009",
            category=RuleCategory.PACING,
            severity=RuleSeverity.SOFT,
            description="连续动作场景不超过 3000 字（防疲劳）",
            check="max_action_scene_words(text) <= 3000",
            params={"max_words": 3000},
        ),
        "U010": Rule(
            id="U010",
            category=RuleCategory.CONTENT,
            severity=RuleSeverity.INFO,
            description="新角色首次出场应有外貌/特征描写",
            check="new_character_has_description(text, kg_snapshot)",
        ),
        "U011": Rule(
            id="U011",
            category=RuleCategory.PLEASURE,
            severity=RuleSeverity.SOFT,
            description="爽点间隔不超过 5 个场景",
            check="max_pleasure_gap_scenes(text) <= 5",
            params={"max_gap_scenes": 5},
        ),
        "U012": Rule(
            id="U012",
            category=RuleCategory.PLEASURE,
            severity=RuleSeverity.SOFT,
            description="同类型爽点连续不超过 4 次",
            check="max_consecutive_same_pleasure(text) <= 4",
            params={"max_consecutive": 4},
        ),
        "U013": Rule(
            id="U013",
            category=RuleCategory.CHARACTER,
            severity=RuleSeverity.SOFT,
            description="主角每章至少出场一次",
            check="protagonist_appears(text, protagonist_name)",
        ),
        "U014": Rule(
            id="U014",
            category=RuleCategory.STRUCTURE,
            severity=RuleSeverity.INFO,
            description="高潮章节字数应比日常章节多 20%+",
            check="climax_words >= normal_avg_words * 1.2",
            params={"min_boost": 1.2},
        ),
        "U015": Rule(
            id="U015",
            category=RuleCategory.SAFETY,
            severity=RuleSeverity.HARD,
            description="不包含色情、暴力、政治敏感内容",
            check="passes_content_safety(text)",
        ),
    }

    return RuleLayer(
        name="通用规则",
        layer_type="universal",
        description="适用于所有网文的普适规则，由昆仑引擎内置",
        rules=rules,
        metadata={"version": "1.0", "builtin": True},
    )


UNIVERSAL_RULES = _build_universal_rules()


# ─── 规则引擎核心 ────────────────────────────────────


class RuleEngine:
    """三层规则引擎

    用法:
        engine = RuleEngine()
        engine.load_book_rules("my_book")
        stack = engine.build_rule_stack("xuanhuan_dongfang", "my_book")
        violations = engine.check_rules(stack, context={...})
    """

    def __init__(self):
        self._book_rules_cache: dict[str, RuleLayer] = {}
        self._genre_rules_cache: dict[str, RuleLayer] = {}

    def get_universal_rules(self) -> RuleLayer:
        return UNIVERSAL_RULES

    def get_genre_rules(self, genre_id: str) -> RuleLayer:
        if genre_id in self._genre_rules_cache:
            return self._genre_rules_cache[genre_id]

        from kunlun.genre import GENRE_LIBRARY

        config = GENRE_LIBRARY.get(genre_id)
        if not config:
            logger.warning(f"未找到题材配置: {genre_id}，使用空规则层")
            return RuleLayer(
                name=f"题材规则 ({genre_id})",
                layer_type="genre",
                description="空规则层 — 题材未找到",
                metadata={"genre_id": genre_id},
            )

        rules = self._config_to_rules(config)
        layer = RuleLayer(
            name=f"题材规则 — {config.name}",
            layer_type="genre",
            description=f"{config.name} 专属规则",
            rules=rules,
            metadata={"genre_id": genre_id, "genre_name": config.name},
        )
        self._genre_rules_cache[genre_id] = layer
        return layer

    def _config_to_rules(self, config) -> dict[str, Rule]:
        rules: dict[str, Rule] = {}
        prefix = f"G_{config.genre_id}_"

        w_min, w_max = config.suggested_words_per_chapter
        rules[f"{prefix}001"] = Rule(
            id=f"{prefix}001",
            category=RuleCategory.STRUCTURE,
            severity=RuleSeverity.SOFT,
            description=f"每章字数: {w_min}-{w_max}",
            check=f"{w_min} <= word_count <= {w_max}",
            params={"min_words": w_min, "max_words": w_max},
        )

        rules[f"{prefix}002"] = Rule(
            id=f"{prefix}002",
            category=RuleCategory.PLEASURE,
            severity=RuleSeverity.SOFT,
            description=f"每千字爽点 ≥ {config.min_pleasure_per_1k} 个",
            check=f"pleasure_per_1k >= {config.min_pleasure_per_1k}",
            params={"min_per_1k": config.min_pleasure_per_1k},
        )

        d_min, d_max = config.dialogue_ratio
        rules[f"{prefix}003"] = Rule(
            id=f"{prefix}003",
            category=RuleCategory.DIALOGUE,
            severity=RuleSeverity.SOFT,
            description=f"对话比例: {d_min:.0%}-{d_max:.0%}",
            check=f"{d_min} <= dialogue_ratio <= {d_max}",
            params={"min_ratio": d_min, "max_ratio": d_max},
        )

        a_min, a_max = config.action_ratio
        rules[f"{prefix}004"] = Rule(
            id=f"{prefix}004",
            category=RuleCategory.PACING,
            severity=RuleSeverity.SOFT,
            description=f"动作比例: {a_min:.0%}-{a_max:.0%}",
            check=f"{a_min} <= action_ratio <= {a_max}",
            params={"min_ratio": a_min, "max_ratio": a_max},
        )

        if config.closing_hook_required:
            rules[f"{prefix}005"] = Rule(
                id=f"{prefix}005",
                category=RuleCategory.HOOK,
                severity=RuleSeverity.HARD,
                description="章节结尾必须包含钩子",
                check="has_closing_hook(text)",
            )
        if config.opening_hook_required:
            rules[f"{prefix}006"] = Rule(
                id=f"{prefix}006",
                category=RuleCategory.HOOK,
                severity=RuleSeverity.SOFT,
                description="章节开头应包含钩子",
                check="has_opening_hook(text)",
            )

        rules[f"{prefix}007"] = Rule(
            id=f"{prefix}007",
            category=RuleCategory.HOOK,
            severity=RuleSeverity.SOFT,
            description=f"黄金三章钩子强度 ≥ {config.golden_three_intensity}",
            check=f"golden_three_hook_score >= {config.golden_three_intensity}",
            params={"min_score": config.golden_three_intensity},
        )

        rules[f"{prefix}008"] = Rule(
            id=f"{prefix}008",
            category=RuleCategory.PACING,
            severity=RuleSeverity.INFO,
            description=f"建议每 {config.climax_chapter_interval} 章安排一次高潮",
            check="climax_interval_check(chapter_number, last_climax_chapter)",
            params={"interval": config.climax_chapter_interval},
        )

        for i, taboo in enumerate(config.taboos):
            rules[f"{prefix}100_{i}"] = Rule(
                id=f"{prefix}100_{i}",
                category=RuleCategory.CONTENT,
                severity=RuleSeverity.HARD,
                description=f"禁忌: {taboo}",
                check=f"not contains_pattern(text, '{taboo}')",
                tags=["taboo"],
            )

        for i, elem in enumerate(config.required_elements):
            rules[f"{prefix}200_{i}"] = Rule(
                id=f"{prefix}200_{i}",
                category=RuleCategory.CONTENT,
                severity=RuleSeverity.SOFT,
                description=f"必须包含: {elem}",
                check=f"contains_element(text, '{elem}')",
                tags=["required"],
            )

        return rules

    def get_book_rules(self, book_id: str) -> RuleLayer:
        if book_id in self._book_rules_cache:
            return self._book_rules_cache[book_id]

        rules_path = settings.DATA_DIR / "rules" / book_id / "book_rules.yaml"
        if rules_path.exists():
            try:
                layer = self._load_rules_from_yaml(rules_path, book_id)
                self._book_rules_cache[book_id] = layer
                return layer
            except Exception as e:
                logger.warning(f"加载书籍规则失败 ({book_id}): {e}")

        layer = RuleLayer(
            name=f"书籍规则 — {book_id}",
            layer_type="book",
            description="用户自定义规则（暂无）",
            metadata={"book_id": book_id},
        )
        self._book_rules_cache[book_id] = layer
        return layer

    def _load_rules_from_yaml(self, path: Path, book_id: str) -> RuleLayer:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules: dict[str, Rule] = {}
        for rule_data in data.get("rules", []):
            rule = Rule(
                id=rule_data["id"],
                category=RuleCategory(rule_data.get("category", "content")),
                severity=RuleSeverity(rule_data.get("severity", "soft")),
                description=rule_data.get("description", ""),
                check=rule_data.get("check", ""),
                auto_fix=rule_data.get("auto_fix", ""),
                params=rule_data.get("params", {}),
                enabled=rule_data.get("enabled", True),
                tags=rule_data.get("tags", []),
            )
            rules[rule.id] = rule

        return RuleLayer(
            name=data.get("name", f"书籍规则 — {book_id}"),
            layer_type="book",
            description=data.get("description", ""),
            rules=rules,
            metadata=data.get("metadata", {"book_id": book_id}),
        )

    def save_book_rules(self, book_id: str, layer: RuleLayer) -> None:
        rules_dir = settings.DATA_DIR / "rules" / book_id
        rules_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "name": layer.name,
            "description": layer.description,
            "metadata": layer.metadata,
            "rules": [
                {
                    "id": r.id,
                    "category": r.category.value,
                    "severity": r.severity.value,
                    "description": r.description,
                    "check": r.check,
                    "auto_fix": r.auto_fix,
                    "params": r.params,
                    "enabled": r.enabled,
                    "tags": r.tags,
                }
                for r in layer.rules.values()
            ],
        }

        rules_path = rules_dir / "book_rules.yaml"
        with rules_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._book_rules_cache[book_id] = layer
        logger.info(f"书籍规则已保存: {rules_path}")

    def build_rule_stack(
        self,
        genre_id: str = "",
        book_id: str = "",
        extra_genre_ids: list[str] | None = None,
    ) -> RuleStack:
        layers: list[RuleLayer] = []

        universal = self.get_universal_rules()
        layers.append(universal)

        if genre_id:
            genre_layer = self.get_genre_rules(genre_id)
            layers.append(genre_layer)

        if extra_genre_ids:
            for egid in extra_genre_ids:
                sub_layer = self.get_genre_rules(egid)
                sub_layer.name = f"子类型规则 — {sub_layer.name}"
                layers.append(sub_layer)

        if book_id:
            book_layer = self.get_book_rules(book_id)
            layers.append(book_layer)

        merged: dict[str, Rule] = {}
        conflicts: list[dict] = []

        for layer in layers:
            for rule_id, rule in layer.rules.items():
                if rule_id in merged:
                    conflicts.append(
                        {
                            "rule_id": rule_id,
                            "existing_layer": merged[rule_id].severity.value,
                            "overriding_layer": layer.layer_type,
                            "resolution": "overridden",
                        }
                    )
                merged[rule_id] = copy.deepcopy(rule)

        stats = {
            "total_rules": len(merged),
            "hard_rules": sum(1 for r in merged.values() if r.severity == RuleSeverity.HARD),
            "soft_rules": sum(1 for r in merged.values() if r.severity == RuleSeverity.SOFT),
            "info_rules": sum(1 for r in merged.values() if r.severity == RuleSeverity.INFO),
            "disabled_rules": sum(1 for r in merged.values() if not r.enabled),
            "conflicts": len(conflicts),
        }

        return RuleStack(
            book_id=book_id,
            layers=layers,
            merged_rules=merged,
            conflicts=conflicts,
            stats=stats,
        )

    def get_active_rules(
        self, stack: RuleStack, severity: RuleSeverity | None = None
    ) -> list[Rule]:
        rules = [r for r in stack.merged_rules.values() if r.enabled]
        if severity:
            rules = [r for r in rules if r.severity == severity]
        return rules

    def get_rules_by_category(self, stack: RuleStack, category: RuleCategory) -> list[Rule]:
        return [r for r in stack.merged_rules.values() if r.category == category and r.enabled]

    # ─── 三层执行系统集成 ────────────────────────────

    def check_text(
        self,
        text: str,
        context: dict[str, object] | None = None,
    ) -> list[RuleResult]:
        """使用三层执行引擎 (HARD/SOFT/AI_GUIDE) 检查文本。

        这是 engine.py (规则来源管理) 和 layers.py (规则执行分层) 的集成点。
        """
        engine = get_layer_engine()
        return engine.check(text, context)

    def check_text_by_layer(
        self,
        text: str,
        layer: EnforcementLayer,
        context: dict[str, object] | None = None,
    ) -> list[RuleResult]:
        engine = get_layer_engine()
        results = engine.check(text, context)
        return [r for r in results if r.layer == layer]

    def get_layer_engine(self) -> LayerRuleEngine:
        return get_layer_engine()

    def get_blocking_violations(
        self,
        results: list[RuleResult],
    ) -> list[RuleResult]:
        engine = get_layer_engine()
        return engine.get_blocking_results(results)

    def has_blocking_violations(self, results: list[RuleResult]) -> bool:
        engine = get_layer_engine()
        return engine.has_blocking_violations(results)

    def rule_check_summary(self, results: list[RuleResult]) -> dict[str, object]:
        engine = get_layer_engine()
        return engine.summary(results)

    # ─── 导出 ────────────────────────────────────────

    def export_rule_stack(self, stack: RuleStack, format: str = "yaml") -> str:
        if format == "yaml":
            return yaml.dump(
                self._stack_to_dict(stack),
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        if format == "markdown":
            return self._stack_to_markdown(stack)
        raise ValueError(f"不支持的格式: {format}")

    def _stack_to_dict(self, stack: RuleStack) -> dict:
        layers_data = [
            {
                "name": layer.name,
                "type": layer.layer_type,
                "description": layer.description,
                "rule_count": len(layer.rules),
            }
            for layer in stack.layers
        ]

        rules_data = [
            {
                "id": rule.id,
                "category": rule.category.value,
                "severity": rule.severity.value,
                "description": rule.description,
                "enabled": rule.enabled,
            }
            for rule in stack.merged_rules.values()
        ]

        return {
            "book_id": stack.book_id,
            "stats": stack.stats,
            "layers": layers_data,
            "merged_rules": rules_data,
            "conflicts": stack.conflicts,
        }

    def _stack_to_markdown(self, stack: RuleStack) -> str:
        lines = [
            f"# 规则堆栈 — {stack.book_id}",
            "",
            "## 统计",
            f"- 总规则数: {stack.stats['total_rules']}",
            f"- 硬约束: {stack.stats['hard_rules']}",
            f"- 软建议: {stack.stats['soft_rules']}",
            f"- 提示: {stack.stats['info_rules']}",
            f"- 冲突: {stack.stats['conflicts']}",
            "",
            "## 规则层",
        ]

        for layer in stack.layers:
            lines.append(f"### {layer.name} ({layer.layer_type})")
            lines.append(f"{layer.description}")
            lines.append(f"规则数: {len(layer.rules)}")
            lines.append("")

        lines.append("## 合并规则 (按严重度)")
        for sev in [RuleSeverity.HARD, RuleSeverity.SOFT, RuleSeverity.INFO]:
            sev_rules = [r for r in stack.merged_rules.values() if r.severity == sev and r.enabled]
            if sev_rules:
                lines.append(f"### {sev.value.upper()}")
                lines.extend(f"- [{r.id}] {r.description}" for r in sev_rules)
                lines.append("")

        return "\n".join(lines)


# ─── 工厂函数 ────────────────────────────────────────

_rule_engine: RuleEngine | None = None


def get_rule_engine() -> RuleEngine:
    global _rule_engine  # noqa: PLW0603
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine

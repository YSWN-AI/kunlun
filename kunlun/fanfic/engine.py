"""
昆仑创作引擎 — 同人创作模式

支持基于已有IP/正典的二次创作，区别于原创的专属功能:
  1. 正典导入 — 导入原作的角色/事件/设定/时间线
  2. 同人审计维度 — OOC检测 / 正典一致性 / 同人创新度
  3. 正典知识库 — 基于原作构建可检索的知识图谱
  4. 同人规则层 — 在原作规则之上叠加同人创作约束
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from loguru import logger

from kunlun.config import settings

# ─── 枚举 ──────────────────────────────────────────


class FanficMode(Enum):
    """同人创作模式"""

    STRICT_CANON = "strict_canon"  # 严格遵循原作 — 不偏离原作设定
    CANON_DIVERGENT = "canon_divergent"  # 正典分歧 — 在某点分歧后展开
    AU_ALTERNATE = "au_alternate"  # AU架空 — 保留角色，改变世界观
    CROSSOVER = "crossover"  # 跨界联动 — 多个作品交叉
    PREQUEL = "prequel"  # 前传
    SEQUEL = "sequel"  # 续写
    GAP_FILLER = "gap_filler"  # 补白 — 填补原作空白
    WHAT_IF = "what_if"  # 如果路线 — 改变关键抉择


class OOCSeverity(Enum):
    """OOC严重度"""

    NONE = "none"  # 不OOC
    MILD = "mild"  # 轻微 — 角色反应略有偏差
    MODERATE = "moderate"  # 中等 — 角色行为模式偏离
    SEVERE = "severe"  # 严重 — 角色核心特质改变
    COMPLETE = "complete"  # 完全OOC — 只是同名的另一个人


# ─── 数据模型 ────────────────────────────────────────


@dataclass
class CanonCharacter:
    """正典角色"""

    name: str
    aliases: list[str] = field(default_factory=list)
    core_traits: list[str] = field(default_factory=list)
    speech_patterns: list[str] = field(default_factory=list)
    key_relationships: dict[str, str] = field(default_factory=dict)
    abilities: list[str] = field(default_factory=list)
    backstory: str = ""
    arc: str = ""
    prohibitions: list[str] = field(default_factory=list)


@dataclass
class CanonSetting:
    """正典设定"""

    world_name: str
    time_period: str = ""
    locations: dict[str, str] = field(default_factory=dict)
    power_system: str = ""
    social_structure: str = ""
    key_events: list[dict] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)


@dataclass
class CanonImport:
    """正典导入包"""

    source_name: str
    source_type: str = ""
    characters: list[CanonCharacter] = field(default_factory=list)
    settings: list[CanonSetting] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    divergence_point: str = ""


@dataclass
class OOCReport:
    """OOC检测报告"""

    character_name: str
    severity: OOCSeverity
    violations: list[str] = field(default_factory=list)
    canonical_trait: str = ""
    current_behavior: str = ""
    suggestion: str = ""


# ─── 正典导入器 ──────────────────────────────────────


class CanonImporter:
    """正典导入器 — 从各种来源导入原作信息"""

    @classmethod
    def from_markdown(cls, filepath: Path) -> CanonImport:
        text = filepath.read_text(encoding="utf-8")
        return cls._parse_markdown(text, filepath.stem)

    @classmethod
    def from_json(cls, filepath: Path) -> CanonImport:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return cls._parse_json(data)

    @classmethod
    def from_yaml(cls, filepath: Path) -> CanonImport:
        try:
            import yaml

            with filepath.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls._parse_json(data)
        except ImportError:
            logger.error("YAML 支持需要 pyyaml")
            return CanonImport(source_name=filepath.stem)

    @classmethod
    def empty(cls, name: str) -> CanonImport:
        return CanonImport(source_name=name)

    @classmethod
    def _parse_markdown(cls, text: str, name: str) -> CanonImport:
        imp = CanonImport(source_name=name)
        current_section = ""

        for line in text.split("\n"):
            line = line.strip()  # noqa: PLW2901
            if not line:
                continue

            if line.startswith("## 角色"):
                current_section = "character"
                continue
            if line.startswith("## 设定") or line.startswith("## 世界观"):
                current_section = "setting"
                continue
            if line.startswith("## 时间线"):
                current_section = "timeline"
                continue
            if line.startswith("## 分歧点"):
                imp.divergence_point = line.replace("## 分歧点", "").strip()
                current_section = ""
                continue
            if line.startswith("# "):
                current_section = ""
                continue

            if current_section == "character" and line.startswith("- "):
                cls._parse_character_line(line[2:], imp)
            elif current_section == "timeline" and line.startswith("- "):
                imp.timeline.append({"event": line[2:].strip()})

        return imp

    @classmethod
    def _parse_character_line(cls, line: str, imp: CanonImport) -> None:
        parts = [p.strip() for p in line.split("|")]
        if not parts:
            return

        char = CanonCharacter(name=parts[0])
        if len(parts) > 1:
            char.core_traits = [t.strip() for t in parts[1].split(",")]
        if len(parts) > 2:
            for rel in parts[2].split(","):
                if "=" in rel:
                    k, v = rel.split("=", 1)
                    char.key_relationships[k.strip()] = v.strip()

        imp.characters.append(char)

    @classmethod
    def _parse_json(cls, data: dict) -> CanonImport:
        imp = CanonImport(
            source_name=data.get("source_name", ""),
            source_type=data.get("source_type", ""),
            divergence_point=data.get("divergence_point", ""),
            timeline=data.get("timeline", []),
        )
        for cd in data.get("characters", []):
            imp.characters.append(
                CanonCharacter(
                    name=cd.get("name", ""),
                    aliases=cd.get("aliases", []),
                    core_traits=cd.get("core_traits", []),
                    speech_patterns=cd.get("speech_patterns", []),
                    key_relationships=cd.get("key_relationships", {}),
                    abilities=cd.get("abilities", []),
                    backstory=cd.get("backstory", ""),
                    arc=cd.get("arc", ""),
                    prohibitions=cd.get("prohibitions", []),
                )
            )
        for sd in data.get("settings", []):
            imp.settings.append(
                CanonSetting(
                    world_name=sd.get("world_name", ""),
                    time_period=sd.get("time_period", ""),
                    locations=sd.get("locations", {}),
                    power_system=sd.get("power_system", ""),
                    social_structure=sd.get("social_structure", ""),
                    key_events=sd.get("key_events", []),
                    rules=sd.get("rules", []),
                )
            )
        return imp


# ─── OOC 检测器 ──────────────────────────────────────


class OOCDetector:
    """OOC检测器 — 检测同人创作中角色是否偏离原作

    检测维度:
      1. 核心价值观违背 — 角色做出了在原作中绝不可能做的事
      2. 性格特征偏离 — 性格表现与原作描述矛盾
      3. 说话方式改变 — 口癖/语气词/称呼方式改变
      4. 关系错位 — 与其他角色的关系描述与原作矛盾
      5. 能力矛盾 — 展现的能力超出/低于原作设定
    """

    @classmethod
    def check(
        cls, text: str, char: CanonCharacter, mode: FanficMode = FanficMode.STRICT_CANON
    ) -> OOCReport:
        violations: list[str] = []
        severity = OOCSeverity.NONE

        for prohibition in char.prohibitions:
            if re.search(prohibition, text):
                violations.append(f"禁止行为: {prohibition}")
                severity = OOCSeverity.SEVERE

        for trait in char.core_traits:
            opposite = cls._get_opposite_trait(trait)
            if opposite and re.search(opposite, text):
                violations.append(f"性格偏离: '{trait}' → 表现出相反特质")
                if severity.value < OOCSeverity.MODERATE.value:
                    severity = OOCSeverity.MODERATE

        for pattern in char.speech_patterns:
            if re.search(pattern, text):
                break
            violations.append(f"说话方式改变: 缺少特征 '{pattern}'")

        for name_alias in char.aliases:
            if name_alias in text:
                break
        else:
            if char.name not in text:
                pass

        if (
            mode in (FanficMode.AU_ALTERNATE, FanficMode.WHAT_IF)
            and severity == OOCSeverity.MODERATE
        ):
            severity = OOCSeverity.MILD

        return OOCReport(
            character_name=char.name,
            severity=severity,
            violations=violations,
            canonical_trait=", ".join(char.core_traits[:3]),
            current_behavior=violations[0] if violations else "一致",
            suggestion=cls._get_suggestion(mode, severity, violations),
        )

    @classmethod
    def _get_opposite_trait(cls, trait: str) -> str | None:
        opposites = {
            "勇敢": "害怕|退缩|逃避",
            "善良": "残忍|冷酷|无情",
            "冷静": "冲动|暴躁|失控",
            "忠诚": "背叛|出卖|反水",
            "正直": "阴险|狡诈|卑鄙",
            "温柔": "粗暴|凶狠|严厉",
            "乐观": "绝望|悲观|消极",
            "聪明": "愚蠢|迟钝|无知",
        }
        return opposites.get(trait)

    @classmethod
    def _get_suggestion(cls, mode: FanficMode, severity: OOCSeverity, violations: list[str]) -> str:
        if severity == OOCSeverity.NONE:
            return "角色塑造与原作一致"
        if severity == OOCSeverity.MILD:
            return "轻微偏差，在同人创作可接受范围内"
        if mode == FanficMode.AU_ALTERNATE:
            return f"AU模式允许偏离，但需在故事中解释: {violations[0] if violations else ''}"
        return f"建议回顾原作中该角色的行为模式，修正: {', '.join(violations[:3])}"


# ─── 同人知识库构建 ──────────────────────────────────


class FanficKnowledgeBase:
    """同人知识库 — 基于正典构建可检索知识"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self._canon: CanonImport | None = None
        self._data_dir: Path | None = None

        if book_id:
            self._data_dir = settings.DATA_DIR / "fanfic" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def import_canon(self, canon: CanonImport) -> None:
        self._canon = canon
        self._save()

    @property
    def canon(self) -> CanonImport | None:
        return self._canon

    def get_character(self, name: str) -> CanonCharacter | None:
        if not self._canon:
            return None
        for c in self._canon.characters:
            if c.name == name or name in c.aliases:
                return c
        return None

    def list_characters(self) -> list[str]:
        if not self._canon:
            return []
        return [c.name for c in self._canon.characters]

    def build_prompt_context(self, mode: FanficMode) -> str:
        if not self._canon:
            return ""

        lines = [
            f"【同人创作】原作: {self._canon.source_name}",
            f"【创作模式】{mode.value}",
        ]

        if self._canon.divergence_point:
            lines.append(f"【分歧点】{self._canon.divergence_point}")

        if self._canon.characters:
            lines.append("【正典角色】")
            for c in self._canon.characters[:10]:
                traits = ", ".join(c.core_traits[:5])
                lines.append(f"  - {c.name}: {traits}")

        if self._canon.settings:
            for s in self._canon.settings[:3]:
                lines.append(f"【世界观】{s.world_name}")
                if s.rules:
                    lines.extend(f"  - {r}" for r in s.rules[:5])

        if self._canon.timeline:
            lines.append("【原时间线】")
            lines.extend(f"  - {e.get('event', str(e))}" for e in self._canon.timeline[:10])

        lines.append("【OOC约束】")
        if mode == FanficMode.STRICT_CANON:
            lines.append("  严格遵循原作角色性格，不得偏离核心特征")
        elif mode == FanficMode.AU_ALTERNATE:
            lines.append("  保留角色核心性格，世界观和设定可以重新诠释")
        elif mode == FanficMode.WHAT_IF:
            lines.append("  在关键抉择点处改变，后续发展的角色变化需合乎逻辑")

        return "\n".join(lines)

    def _save(self) -> None:
        if not self._data_dir or not self._canon:
            return
        path = self._data_dir / "canon.json"
        data = {
            "source_name": self._canon.source_name,
            "source_type": self._canon.source_type,
            "divergence_point": self._canon.divergence_point,
            "characters": [
                {
                    "name": c.name,
                    "aliases": c.aliases,
                    "core_traits": c.core_traits,
                    "speech_patterns": c.speech_patterns,
                    "key_relationships": c.key_relationships,
                    "abilities": c.abilities,
                    "prohibitions": c.prohibitions,
                }
                for c in self._canon.characters
            ],
            "timeline": self._canon.timeline,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._data_dir:
            return
        path = self._data_dir / "canon.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._canon = CanonImporter._parse_json(data)
            except Exception:
                logger.debug(f"正典数据解析失败: {path}")


# ─── 工厂函数 ────────────────────────────────────────

_kbs: dict[str, FanficKnowledgeBase] = {}


def get_fanfic_kb(book_id: str) -> FanficKnowledgeBase:
    if book_id not in _kbs:
        _kbs[book_id] = FanficKnowledgeBase(book_id)
    return _kbs[book_id]

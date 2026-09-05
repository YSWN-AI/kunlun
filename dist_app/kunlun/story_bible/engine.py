"""
昆仑创作引擎 — Story Bible 统一管理模块核心引擎

灵感来源: Sudowrite Story Bible + NovelCrafter Codex
对标: 网文写作中世界观/角色/规则/意图的集中管理与结构化查询
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 数据类型
# ══════════════════════════════════════════════════════


class BibleSection(Enum):
    """Story Bible 四大分区"""

    AUTHOR_INTENT = "author_intent"
    CURRENT_FOCUS = "current_focus"
    BOOK_RULES = "book_rules"
    STORY_BIBLE = "story_bible"


class WorkflowStage(Enum):
    """Sudowrite 式创作管线阶段"""

    IDEA = "idea"
    OUTLINE = "outline"
    BEATS = "beats"
    DRAFT = "draft"
    REVISE = "revise"


@dataclass
class BibleEntry:
    """Bible 中的单个结构化条目"""

    key: str
    section: BibleSection
    entry_type: str
    raw_line: str
    parsed_fields: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    chapter_relevance: dict[int, float] = field(default_factory=dict)
    created_at: float = 0.0


@dataclass
class WorkflowPlan:
    """Sudowrite 式创作计划"""

    book_id: str
    stage: WorkflowStage
    idea: str = ""
    outline_summary: list[str] = field(default_factory=list)
    chapter_beats: dict[int, list[str]] = field(default_factory=dict)
    total_chapters_planned: int = 0
    genre: str = ""
    target_word_count: int = 5000


@dataclass
class CodexQueryResult:
    """Codex 式查询结果"""

    query: str
    matched_entries: list[BibleEntry] = field(default_factory=list)
    related_sections: list[BibleSection] = field(default_factory=list)
    kg_entities: list[dict] = field(default_factory=list)
    summary: str = ""


@dataclass
class ChapterBibleChange:
    """章节对 Bible 的变更记录"""

    chapter: int
    section: BibleSection
    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    summary: str = ""


# ══════════════════════════════════════════════════════
# Markdown 解析器 — 零 LLM, 纯正则
# ══════════════════════════════════════════════════════

_MD_HEADER = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_MD_LIST_ITEM = re.compile(r"^[\-\*\+]\s+(.+)$", re.MULTILINE)
_MD_NUMBERED = re.compile(r"^\d+[\.\)、]\s+(.+)$", re.MULTILINE)
_MD_FIELD = re.compile(r"^\*\*([^*]+)\*\*\s*[:：]\s*(.+)$")
_MD_TAG = re.compile(r"#(\w+)")
_ENTITY_KEY = re.compile(r"^\[([^\]]+)\]\s*[:：]\s*(.+)")


class BibleParser:
    """Markdown Bible → 结构化条目 解析器"""

    @staticmethod
    def parse_section(text: str, section: BibleSection) -> list[BibleEntry]:
        entries: list[BibleEntry] = []
        if not text.strip():
            return entries

        lines = text.split("\n")
        current_header: str = ""
        current_subheader: str = ""

        for line in lines:
            line = line.strip()  # noqa: PLW2901
            if not line:
                continue

            h_match = _MD_HEADER.match(line)
            if h_match:
                level = len(h_match.group(1))
                title = h_match.group(2)
                if level == 1:
                    current_header = title
                    current_subheader = ""
                elif level == 2:
                    current_subheader = title
                continue

            em_match = _ENTITY_KEY.match(line)
            if em_match:
                eid, desc = em_match.group(1), em_match.group(2)
                tags = _MD_TAG.findall(desc)
                etype = eid.split("_")[0] if "_" in eid else "entity"
                entries.append(
                    BibleEntry(
                        key=eid,
                        section=section,
                        entry_type=etype,
                        raw_line=line,
                        parsed_fields={
                            "header": current_header,
                            "subheader": current_subheader,
                            "description": desc,
                        },
                        tags=tags,
                        created_at=time.time(),
                    )
                )
                continue

            f_match = _MD_FIELD.match(line)
            if f_match:
                key, val = f_match.group(1), f_match.group(2)
                key_slug = key.strip().lower().replace(" ", "_")
                entries.append(
                    BibleEntry(
                        key=key_slug,
                        section=section,
                        entry_type="field",
                        raw_line=line,
                        parsed_fields={
                            "header": current_header,
                            "subheader": current_subheader,
                            "label": key.strip(),
                            "value": val.strip(),
                        },
                        created_at=time.time(),
                    )
                )
                continue

            li_match = _MD_LIST_ITEM.match(line) or _MD_NUMBERED.match(line)
            if li_match:
                content = li_match.group(1)
                tags = _MD_TAG.findall(content)
                etype = (
                    "rule"
                    if (
                        "必须" in content
                        or "不能" in content
                        or "禁止" in content
                        or "应当" in content
                    )
                    else "note"
                )
                entries.append(
                    BibleEntry(
                        key=BibleParser._make_key(current_header + current_subheader + content)[
                            :60
                        ],
                        section=section,
                        entry_type=etype,
                        raw_line=line,
                        parsed_fields={
                            "header": current_header,
                            "subheader": current_subheader,
                            "content": content,
                        },
                        tags=tags,
                        created_at=time.time(),
                    )
                )
                continue

            entries.append(
                BibleEntry(
                    key=BibleParser._make_key(line)[:50],
                    section=section,
                    entry_type="paragraph",
                    raw_line=line,
                    parsed_fields={
                        "header": current_header,
                        "subheader": current_subheader,
                        "content": line,
                    },
                    created_at=time.time(),
                )
            )

        return entries

    @staticmethod
    def _make_key(text: str) -> str:
        return re.sub(r"\s+", "_", text.strip())[:60]


# ══════════════════════════════════════════════════════
# Story Bible 主引擎
# ══════════════════════════════════════════════════════


class StoryBible:
    """Story Bible 统一管理器"""

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.story_dir = settings.DATA_DIR / "story" / book_id
        self.bible_cache_dir = settings.DATA_DIR / "story_bible" / book_id
        self.bible_cache_dir.mkdir(parents=True, exist_ok=True)

        self._entries: dict[BibleSection, list[BibleEntry]] = {}
        self._last_parse_time: float = 0
        self._section_files: dict[BibleSection, Path] = {}

        self._init_section_files()

    def _init_section_files(self):
        self._section_files = {
            BibleSection.AUTHOR_INTENT: self.story_dir / "author_intent.md",
            BibleSection.CURRENT_FOCUS: self.story_dir / "current_focus.md",
            BibleSection.BOOK_RULES: self.story_dir / "book_rules.md",
            BibleSection.STORY_BIBLE: self.story_dir / "story_bible.md",
        }

    def _read_section_file(self, section: BibleSection) -> str:
        path = self._section_files.get(section)
        if path and path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _write_section_file(self, section: BibleSection, content: str):
        path = self._section_files.get(section)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def parse_all(self, force: bool = False) -> dict[BibleSection, list[BibleEntry]]:
        cache_path = self.bible_cache_dir / "parsed_entries.json"
        mtimes = {
            s: self._section_files[s].stat().st_mtime if self._section_files[s].exists() else 0
            for s in BibleSection
        }

        if not force and cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
                if cache.get("mtime", 0) >= max(mtimes.values()):
                    self._last_parse_time = cache.get("parsed_at", 0)
                    return self._load_from_cache(cache)
            except Exception:
                logger.debug("Story Bible 缓存加载失败，将重新解析")

        self._entries = {}
        for section in BibleSection:
            text = self._read_section_file(section)
            self._entries[section] = BibleParser.parse_section(text, section)

        self._save_cache(mtimes)
        self._last_parse_time = time.time()
        return self._entries

    def _load_from_cache(self, cache: dict) -> dict[BibleSection, list[BibleEntry]]:
        self._entries = {}
        for section in BibleSection:
            entries_data = cache.get("entries", {}).get(section.value, [])
            self._entries[section] = [BibleEntry(**e) for e in entries_data]
        return self._entries

    def _save_cache(self, mtimes: dict):
        cache_path = self.bible_cache_dir / "parsed_entries.json"
        data = {
            "parsed_at": time.time(),
            "mtime": max(mtimes.values()),
            "entries": {
                s.value: [
                    {
                        "key": e.key,
                        "section": e.section.value,
                        "entry_type": e.entry_type,
                        "raw_line": e.raw_line,
                        "parsed_fields": e.parsed_fields,
                        "tags": e.tags,
                        "created_at": e.created_at,
                    }
                    for e in entries
                ]
                if entries
                else []
                for s, entries in self._entries.items()
            },
        }
        cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_overview(self) -> dict:
        self.parse_all()
        overview: dict[str, Any] = {
            "book_id": self.book_id,
            "sections": {},
            "stats": {"total_entries": 0, "total_rules": 0, "total_entities": 0},
        }

        for section in BibleSection:
            entries = self._entries.get(section, [])
            overview["sections"][section.value] = {
                "entry_count": len(entries),
                "types": len({e.entry_type for e in entries}),
                "headers": list(
                    {
                        e.parsed_fields.get("header", "")
                        for e in entries
                        if e.parsed_fields.get("header")
                    }
                ),
                "tags": list({tag for e in entries for tag in e.tags}),
                "preview": self._read_section_file(section)[:500],
            }
            overview["stats"]["total_entries"] += len(entries)
            overview["stats"]["total_rules"] += sum(1 for e in entries if e.entry_type == "rule")
            overview["stats"]["total_entities"] += sum(
                1
                for e in entries
                if e.entry_type in ("character", "location", "power_system", "event")
            )

        return overview

    def codex_query(self, query: str, top_k: int = 10) -> CodexQueryResult:
        self.parse_all()
        result = CodexQueryResult(query=query)

        query_terms = set(query.strip().lower().split())
        scored: list[tuple[float, BibleEntry]] = []

        for section in BibleSection:
            for entry in self._entries.get(section, []):
                text = (
                    entry.key + " " + entry.raw_line + " " + " ".join(entry.parsed_fields.values())
                ).lower()
                text_terms = set(text.split())

                overlap = len(query_terms & text_terms)
                union = len(query_terms | text_terms)
                score = overlap / max(union, 1)

                tag_match = sum(1 for t in entry.tags if any(qt in t.lower() for qt in query_terms))
                score += tag_match * 0.3

                header = entry.parsed_fields.get("header", "").lower()
                if any(qt in header for qt in query_terms):
                    score += 0.5

                if score > 0.05:
                    scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        result.matched_entries = [e for _, e in scored[:top_k]]
        result.related_sections = list({e.section for e in result.matched_entries})

        if result.matched_entries:
            lines = []
            for e in result.matched_entries[:5]:
                content = (
                    e.parsed_fields.get("content")
                    or e.parsed_fields.get("description")
                    or e.parsed_fields.get("value")
                    or e.raw_line
                )
                lines.append(f"- [{e.section.value}] {content}")
            result.summary = "\n".join(lines)

        return result

    def get_chapter_context(self, chapter: int) -> dict[str, Any]:
        self.parse_all()
        context: dict[str, Any] = {
            "chapter": chapter,
            "book_rules_active": [],
            "relevant_entities": [],
            "active_plot_threads": [],
            "story_bible_relevant": [],
            "author_intent_context": "",
        }

        for section in BibleSection:
            entries = self._entries.get(section, [])
            for e in entries:
                min_ch = e.parsed_fields.get("from_chapter", "")
                max_ch = e.parsed_fields.get("to_chapter", "")
                if min_ch or max_ch:
                    if min_ch and int(min_ch) > chapter:
                        continue
                    if max_ch and int(max_ch) < chapter:
                        continue
                    context["relevant_entities"].append(
                        {
                            "section": section.value,
                            "key": e.key,
                            "type": e.entry_type,
                            "content": e.parsed_fields.get("content")
                            or e.parsed_fields.get("description")
                            or e.raw_line,
                        }
                    )

        context["active_rule_count"] = len(context["book_rules_active"])
        context["relevant_entity_count"] = len(context["relevant_entities"])
        context["overall_bible_summary"] = self._generate_bible_summary(200)

        return context

    def _generate_bible_summary(self, max_len: int = 300) -> str:
        parts = []
        for section in [BibleSection.STORY_BIBLE, BibleSection.BOOK_RULES]:
            entries = self._entries.get(section, [])
            key_entries = [e for e in entries if e.entry_type in ("field", "rule")][:5]
            for e in key_entries:
                content = e.parsed_fields.get("value") or e.parsed_fields.get("content") or ""
                if content:
                    parts.append(f"- {e.parsed_fields.get('label', '')}: {content}")

        summary = "\n".join(parts)
        if len(summary) > max_len:
            summary = summary[:max_len] + "..."
        return summary

    def create_workflow_plan(
        self, idea: str, genre: str = "", target_chapters: int = 100
    ) -> WorkflowPlan:
        return WorkflowPlan(
            book_id=self.book_id,
            stage=WorkflowStage.IDEA,
            idea=idea,
            total_chapters_planned=target_chapters,
            genre=genre,
        )

    def save_workflow_plan(self, plan: WorkflowPlan):
        path = self.bible_cache_dir / "workflow_plan.json"
        data = {
            "book_id": plan.book_id,
            "stage": plan.stage.value,
            "idea": plan.idea,
            "outline_summary": plan.outline_summary,
            "chapter_beats": {str(k): v for k, v in plan.chapter_beats.items()},
            "total_chapters_planned": plan.total_chapters_planned,
            "genre": plan.genre,
            "target_word_count": plan.target_word_count,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_workflow_plan(self) -> WorkflowPlan | None:
        path = self.bible_cache_dir / "workflow_plan.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorkflowPlan(
            book_id=data["book_id"],
            stage=WorkflowStage(data["stage"]),
            idea=data["idea"],
            outline_summary=data.get("outline_summary", []),
            chapter_beats={int(k): v for k, v in data.get("chapter_beats", {}).items()},
            total_chapters_planned=data.get("total_chapters_planned", 0),
            genre=data.get("genre", ""),
            target_word_count=data.get("target_word_count", 5000),
        )

    def advance_workflow_stage(self, plan: WorkflowPlan, new_stage: WorkflowStage):
        plan.stage = new_stage
        self.save_workflow_plan(plan)

    TEMPLATES: dict[str, str] = {
        "xuanhuan_dongfang": """# 东方玄幻 Story Bible

## 力量体系
**修炼境界**: [realm_power]: (待定义 — 如练气/筑基/金丹/元婴/化神)
**功法来源**: [source_power]: (待定义)
**境界突破条件**: [breakthrough]: (待定义)

## 世界观
**世界构成**: [world_structure]: (待定义 — 如三界/九州/万族)
**势力分布**: [factions]: (待定义)
**历史事件**: [history]: (待定义)

## 核心设定
**金手指**: [golden_finger]: (待定义)
**核心冲突**: [core_conflict]: (待定义)
**修炼资源**: [resources]: (待定义)
""",
        "xianxia_xiuzhen": """# 仙侠修真 Story Bible

## 修炼体系
**修炼境界**: [realm_power]: (待定义 — 如练气/筑基/金丹/元婴/化神/炼虚/合体/大乘/渡劫)
**飞升条件**: [ascension]: (待定义)
**天劫机制**: [tribulation]: (待定义)

## 世界观
**世界层次**: [world_layers]: (待定义 — 如凡界/灵界/仙界)
**宗门体系**: [sects]: (待定义)
**灵脉分布**: [spirit_veins]: (待定义)

## 核心设定
**主线任务**: [main_quest]: (待定义)
**道友体系**: [companions]: (待定义)
**仇敌体系**: [enemies]: (待定义)
""",
    }

    def initialize_bible_from_template(
        self, template_key: str, custom_values: dict[str, str] | None = None
    ) -> str:
        template = self.TEMPLATES.get(template_key, self.TEMPLATES["xuanhuan_dongfang"])
        values = custom_values or {}
        for key, val in values.items():
            template = template.replace("(待定义)", val, 1) if key in template else template

        self._write_section_file(BibleSection.STORY_BIBLE, template)
        return template

    def export_codex_json(self) -> dict[str, Any]:
        self.parse_all()
        export: dict[str, Any] = {
            "book_id": self.book_id,
            "generated_at": time.time(),
            "entries": {},
        }

        for section in BibleSection:
            entries = self._entries.get(section, [])
            export["entries"][section.value] = [
                {
                    "key": e.key,
                    "type": e.entry_type,
                    "content": e.parsed_fields.get("content")
                    or e.parsed_fields.get("description")
                    or e.raw_line,
                    "tags": e.tags,
                    "header": e.parsed_fields.get("header", ""),
                    "subheader": e.parsed_fields.get("subheader", ""),
                }
                for e in entries
                if e.entry_type != "paragraph"
            ]

        return export

    def export_for_context_injection(self, max_entries: int = 20) -> str:
        self.parse_all()
        lines: list[str] = []
        priority_order = [
            BibleSection.BOOK_RULES,
            BibleSection.STORY_BIBLE,
            BibleSection.CURRENT_FOCUS,
            BibleSection.AUTHOR_INTENT,
        ]

        for section in priority_order:
            entries = self._entries.get(section, [])
            relevant = [e for e in entries if e.entry_type in ("field", "rule", "entity")]
            for e in relevant[: max_entries // len(priority_order) + 1]:
                label = e.parsed_fields.get("label", "")
                value = (
                    e.parsed_fields.get("value")
                    or e.parsed_fields.get("content")
                    or e.parsed_fields.get("description", "")
                )
                if value:
                    lines.append(
                        f"[{section.value}] {label}: {value}"
                        if label
                        else f"[{section.value}] {value}"
                    )

        return "\n".join(lines[:max_entries])


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_bibles: dict[str, StoryBible] = {}


def get_story_bible(book_id: str) -> StoryBible:
    if book_id not in _bibles:
        _bibles[book_id] = StoryBible(book_id)
    return _bibles[book_id]

"""
文件联动同步器 — 确保控制文件、真相文件、技能文件的自动读取和联动更新

解决的核心问题:
  1. 控制文档 (author_intent/current_focus/book_rules/story_bible) 每章前自动重读
  2. 真相文件 (7个JSON) 每章后自动写入 + 每章前自动注入上下文
  3. 风格指纹 (fingerprint.json) 自动加载并注入Writer
  4. 学习补丁 (learned_patches.md) 自动注入Writer prompt
  5. 运行时产物 (chapter-*.intent.md/context.json) 前后章关联
  6. 进化画像 (profile.json) 自动注入偏好提示

数据流:
  控制文档 ──read──> Editor ──inject──> Architect prompt
  真相文件 ──read──> Auditor33 ──validate──> 草稿
  风格指纹 ──read──> StyleInjector ──inject──> Writer/Stylist prompt
  学习补丁 ──read──> SkillsLoader ──inject──> Writer prompt
  运行时产物 ──write──> chapter-N/ ──read──> chapter-N+1
  进化画像 ──read──> EvolutionTracker ──inject──> preference hints
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from loguru import logger

from kunlun.config import settings


@dataclass
class PipelineContext:
    """每次管线运行前组装的全量上下文"""

    book_id: str
    chapter: int
    # 控制文档（每章前自动重读，确保最新）
    author_intent: str = ""
    current_focus: str = ""
    book_rules: str = ""
    story_bible: str = ""
    # 真相文件摘要（自动注入Architect/Auditor）
    truth_summary: str = ""
    consistency_warnings: list[str] = field(default_factory=list)
    # 风格指纹（自动注入Writer/Stylist）
    style_prompt: str = ""
    style_loaded: bool = False
    # 学习补丁（Reflector产出，自动注入Writer）
    learned_rules: str = ""
    # 上一章运行时产物（前后章关联）
    prev_intent: str = ""
    prev_context: dict = field(default_factory=dict)
    # 进化画像（自动注入偏好提示）
    evolution_tips: str = ""
    # 组装后的完整注入文本
    assembled_context: str = ""


class FileSyncManager:
    """
    文件联动同步器

    职责: 在每个管线步骤前后，自动读取/写入相关文件，确保
    所有Agent看到的始终是最新的文件状态。
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.story_dir = settings.DATA_DIR / "story" / book_id
        self.runtime_dir = self.story_dir / "runtime"
        self.truth_dir = settings.DATA_DIR / "truth" / book_id
        self.style_dir = settings.DATA_DIR / "style" / book_id
        self.learn_dir = settings.DATA_DIR / "learn"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.story_dir, self.runtime_dir, self.truth_dir, self.style_dir, self.learn_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ═══ 1. 控制文档：每章前自动重读 ═══

    def _read_if_exists(self, path: Path) -> str:
        """安全读取文件，不存在返回空字符串"""
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"[FileSync] 读取失败 {path}: {e}")
        return ""

    def _write_if_changed(self, path: Path, content: str):
        """写入文件（自动创建父目录）"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning(f"[FileSync] 写入失败 {path}: {e}")

    def refresh_control_docs(self) -> dict:
        """每章前自动重读所有控制文档（确保作者在Web UI修改后立即生效）"""
        docs = {
            "author_intent": self._read_if_exists(self.story_dir / "author_intent.md"),
            "current_focus": self._read_if_exists(self.story_dir / "current_focus.md"),
            "book_rules": self._read_if_exists(self.story_dir / "book_rules.md"),
            "story_bible": self._read_if_exists(self.story_dir / "story_bible.md"),
        }
        logger.debug(f"[FileSync] 控制文档已刷新: {[k for k, v in docs.items() if v]}")
        return docs

    def get_author_intent(self) -> str:
        return self._read_if_exists(self.story_dir / "author_intent.md")

    def get_current_focus(self) -> str:
        return self._read_if_exists(self.story_dir / "current_focus.md")

    def update_current_focus(self, new_focus: str):
        """更新当前焦点（作者在Web UI修改后调用）"""
        self._write_if_changed(self.story_dir / "current_focus.md", new_focus)
        logger.info("[FileSync] current_focus.md 已更新")

    def update_author_intent(self, new_intent: str):
        self._write_if_changed(self.story_dir / "author_intent.md", new_intent)

    # ═══ 2. 真相文件：每章后自动写入 + 每章前自动注入 ═══

    def get_truth_summary(self) -> tuple[str, list[str]]:
        """读取真相文件，生成供Architect/Auditor使用的摘要"""
        from kunlun.truth import get_truth_manager

        tm = get_truth_manager(self.book_id)
        report = cast(Any, tm).get_consistency_report()

        warnings = []
        hooks_data = tm.get("pending_hooks")
        overdue = hooks_data.get("overdue", [])
        if overdue:
            warnings.append(f"⚠️ {len(overdue)}个伏笔逾期")

        subplots = tm.get("subplot_board")
        stag = subplots.get("stagnation_warnings", [])
        if stag:
            warnings.append(f"⚠️ 支线停滞: {stag}")

        return report, warnings

    def update_truth_after_chapter(self, chapter: int, draft: str, blueprint: dict):
        """每章完成后自动更新所有真相文件"""
        from kunlun.truth import get_truth_manager

        tm = get_truth_manager(self.book_id)

        # 章节摘要
        scenes = blueprint.get("scenes", []) or []
        characters = []
        for s in scenes:
            characters.extend(s.get("characters_involved", []))
        hooks = blueprint.get("foreshadowing", {}).get("to_plant", [])
        cast(Any, tm).add_chapter_summary(chapter, draft[:300], list(set(characters)), [], hooks)

        # 角色状态更新
        for scene in scenes:
            for char in scene.get("characters_involved", []):
                cast(Any, tm).update_character_state(
                    char,
                    chapter,
                    location=scene.get("location", ""),
                    emotion=scene.get("emotion", "neutral"),
                )
                cast(Any, tm).update_emotional_arc(
                    char, chapter, scene.get("emotion", "neutral"), 0.5, scene.get("title", "")
                )

        # 伏笔管理
        fp = blueprint.get("foreshadowing", {})
        for hook in fp.get("to_plant", []):
            cast(Any, tm).register_hook(hook, chapter, chapter + 10, "medium", hook)
        for hook in fp.get("to_reveal", []):
            tm.reveal_hook(hook, chapter)

        # 逾期检查
        overdue = tm.check_overdue_hooks(chapter)
        if overdue:
            logger.warning(f"[FileSync] {len(overdue)}个伏笔逾期: {[h['name'] for h in overdue]}")

        logger.info(f"[FileSync] 真相文件已更新 (ch{chapter})")

    # ═══ 3. 风格指纹：自动加载 + 自动注入 ═══

    def get_style_context(self) -> tuple[str, bool]:
        """读取风格指纹，生成Writer/Stylist注入文本"""
        try:
            from kunlun.style.fingerprint import style_analyzer, style_injector

            fp = style_analyzer.load_fingerprint(self.book_id)
            if fp:
                style_prompt = style_injector.build_style_prompt(fp)
                return style_prompt, True
        except Exception as e:
            logger.debug(f"[FileSync] 风格指纹未加载: {e}")
        return "", False

    def save_style_fingerprint(self, fp):
        """保存风格指纹"""
        from kunlun.style.fingerprint import style_analyzer

        style_analyzer.save_fingerprint(fp, self.book_id)

    # ═══ 4. 学习补丁：自动加载 + 自动注入 ═══

    def get_learned_rules(self) -> str:
        """读取Reflector产出的学习补丁"""
        patch_file = settings.SKILLS_DIR / "learned_patches.md"
        content = self._read_if_exists(patch_file)
        if not content:
            return ""

        # 提取最近10条规则（避免token膨胀）
        import re

        rules = re.findall(r"\*\*规则\*\*:\s*`([^`]+)`\s*→\s*(.+)", content)
        if not rules:
            return ""

        recent = rules[-10:]  # 最新10条
        lines = ["## 已学习写作规则 (Reflector)\n"]
        for pat, sug in recent:
            lines.append(f"- `{pat}` → {sug}")
        return "\n".join(lines)

    # ═══ 5. 运行时产物：上一章上下文注入下一章 ═══

    def save_runtime_artifacts(
        self, chapter: int, intent: dict, blueprint: dict, audit: dict, draft_preview: str = ""
    ):
        """保存本章运行时产物"""
        # intent.md — 给人阅读
        intent_md = f"# 第{chapter}章 创作意图\n\n"
        if isinstance(intent, dict):
            intent_md += (
                "## 必须包含\n" + "\n".join(f"- {x}" for x in intent.get("must_keep", [])) + "\n\n"
            )
            intent_md += (
                "## 必须避免\n" + "\n".join(f"- {x}" for x in intent.get("must_avoid", [])) + "\n\n"
            )
            intent_md += f"## 目标情绪: {intent.get('emotion_target', '')}\n"
        self._write_if_changed(self.runtime_dir / f"chapter-{chapter:04d}.intent.md", intent_md)

        # context.json — 给系统读取
        context = {
            "chapter": chapter,
            "blueprint_summary": {k: blueprint.get(k, "") for k in ["arc_stage", "scenes_count"]},
            "audit_passed": audit.get("passed", False),
            "audit_score": audit.get("overall_score", 0),
            "draft_preview": draft_preview[:200],
            "timestamp": time.time(),
        }
        self._write_if_changed(
            self.runtime_dir / f"chapter-{chapter:04d}.context.json",
            json.dumps(context, ensure_ascii=False, indent=2),
        )

    def get_prev_chapter_context(self, chapter: int) -> dict:
        """读取上一章的运行时产物"""
        prev = chapter - 1
        if prev < 1:
            return {}

        ctx_file = self.runtime_dir / f"chapter-{prev:04d}.context.json"
        if ctx_file.exists():
            try:
                return json.loads(ctx_file.read_text(encoding="utf-8"))
            except Exception:
                logger.debug(f"上下文文件读取失败: chapter-{prev:04d}.context.json")

        intent_file = self.runtime_dir / f"chapter-{prev:04d}.intent.md"
        intent_text = self._read_if_exists(intent_file)
        return {"chapter": prev, "intent_md": intent_text}

    # ═══ 6. 进化画像：自动注入 ═══

    def get_evolution_context(self) -> str:
        """读取进化画像，生成偏好提示"""
        profile_path = self.learn_dir / f"{self.book_id}_profile.json"
        if not profile_path.exists():
            return ""

        try:
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            lines = ["## 作者写作画像\n"]
            if "total_chapters" in data:
                lines.append(
                    f"- 已写: {data.get('total_chapters', 0)}章, {data.get('total_words', 0)}字"
                )
            if "avg_audit_score" in data:
                lines.append(f"- 平均质量分: {data.get('avg_audit_score', 0):.1f}")
            if "improvement_rate" in data:
                rate = data.get("improvement_rate", 0)
                if rate != 0:
                    lines.append(f"- 近期进步率: {rate:+.1%}")
            if "avg_chapter_length" in data:
                lines.append(f"- 偏好章长: {data.get('avg_chapter_length', 0):.0f}字")
            return "\n".join(lines)
        except Exception:
            return ""

    # ═══ 主接口：每章前组装全量上下文 ═══

    def assemble_pipeline_context(self, chapter: int) -> PipelineContext:
        """每章开始前调用：组装所有文件的最新状态为一个上下文对象"""
        ctx = PipelineContext(book_id=self.book_id, chapter=chapter)

        # 1. 控制文档
        docs = self.refresh_control_docs()
        ctx.author_intent = docs.get("author_intent", "")
        ctx.current_focus = docs.get("current_focus", "")
        ctx.book_rules = docs.get("book_rules", "")
        ctx.story_bible = docs.get("story_bible", "")

        # 2. 真相文件
        ctx.truth_summary, ctx.consistency_warnings = self.get_truth_summary()

        # 3. 风格指纹
        ctx.style_prompt, ctx.style_loaded = self.get_style_context()

        # 4. 学习补丁
        ctx.learned_rules = self.get_learned_rules()

        # 5. 上一章运行时产物
        prev_ctx = self.get_prev_chapter_context(chapter)
        ctx.prev_intent = prev_ctx.get("intent_md", "")
        ctx.prev_context = prev_ctx

        # 6. 进化画像
        ctx.evolution_tips = self.get_evolution_context()

        # 7. 组装完整注入文本
        parts = []
        if ctx.author_intent:
            parts.append(f"## 作者长期意图\n{ctx.author_intent[:800]}")
        if ctx.current_focus:
            parts.append(f"## 当前关注点\n{ctx.current_focus[:500]}")
        if ctx.truth_summary and "通过" not in ctx.truth_summary:
            parts.append(ctx.truth_summary)
        if ctx.consistency_warnings:
            parts.append("\n".join(ctx.consistency_warnings))
        if ctx.style_prompt:
            parts.append(ctx.style_prompt)
        if ctx.learned_rules:
            parts.append(ctx.learned_rules)
        if ctx.evolution_tips:
            parts.append(ctx.evolution_tips)
        ctx.assembled_context = "\n\n".join(parts)

        return ctx

    # 每章完成后：自动更新所有文件

    def sync_after_chapter(
        self, chapter: int, draft: str, blueprint: dict, audit_result: dict, chapter_intent=None
    ):
        """每章完成后调用：自动更新所有联动文件"""
        # 1. 真相文件
        self.update_truth_after_chapter(chapter, draft, blueprint)

        # 2. 运行时产物
        intent_dict = (
            chapter_intent.__dict__
            if hasattr(chapter_intent, "__dict__")
            else (chapter_intent or {})
        )
        self.save_runtime_artifacts(chapter, intent_dict, blueprint, audit_result, draft[:200])

        # 3. 进化追踪
        from kunlun.learn.evolve import get_evolution_tracker

        tracker = get_evolution_tracker(self.book_id)
        tracker.record_chapter(
            chapter,
            len(draft),
            audit_result.get("overall_score", 85),
            audit_result.get("fatal_count", 0),
            0,
        )

        # 4. 如果有风格指纹，确保持久化
        if self.style_dir.exists():
            logger.debug("[FileSync] 风格指纹目录已就绪")

        logger.info(f"[FileSync] 第{chapter}章后文件同步完成 (真相+运行时+进化)")


# 全局实例管理
_syncers: dict[str, FileSyncManager] = {}


def get_syncer(book_id: str) -> FileSyncManager:
    if book_id not in _syncers:
        _syncers[book_id] = FileSyncManager(book_id)
    return _syncers[book_id]

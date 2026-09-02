"""
昆仑创作引擎 — 自动文件同步触发器

核心原则：用户任何操作都应该自动更新所有相关文件。
不依赖主动调用，通过 API 中间件和事件注册保证每次用户操作后自动同步。

触发链路：
  用户操作 → API端点 → AutoSync.after_action(action_type, data)
    ├─ → 控制文档保存 (author_intent.md / current_focus.md / book_rules.md)
    ├─ → 知识图谱更新 (角色/物品/地点/关系)
    ├─ → 真相文件更新 (7个JSON)
    ├─ → 偏好学习持久化 (learner.save())
    ├─ → 风格指纹保存 (fingerprint.json)
    ├─ → 写作仪表盘更新 (dashboard_state.json)
    ├─ → 运行时产物保存 (chapter-N.*)
    └─ → Token用量记录 (usage/*.jsonl)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from loguru import logger

from kunlun.config import settings


class AutoSync:
    """
    自动同步触发器

    注册方式:
        AutoSync.after_action("chapter_generated", my_handler)

    使用方式（在API端点末尾调用）:
        await AutoSync.trigger("chapter_generated", {
            "book_id": "...", "chapter": 1, "draft": "..."
        })
    """

    _handlers: dict[str, list[Callable]] = {}  # action_type → [handler, ...]

    @classmethod
    def register(cls, action_type: str, handler: Callable):
        """注册一个操作后的自动同步处理器"""
        if action_type not in cls._handlers:
            cls._handlers[action_type] = []
        cls._handlers[action_type].append(handler)
        logger.debug(f"[AutoSync] 注册: {action_type} → {handler.__name__}")

    @classmethod
    async def trigger(cls, action_type: str, data: dict | None = None):
        """
        触发指定操作类型的所有同步处理器。

        应放在每个会修改数据的 API 端点末尾调用。
        """
        handlers = cls._handlers.get(action_type, [])
        if not handlers:
            return

        data = data or {}
        book_id = data.get("book_id", "default")
        logger.debug(f"[AutoSync] 触发: {action_type} (book_id={book_id})")

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(action_type, data)
                else:
                    handler(action_type, data)
            except Exception as e:
                logger.warning(f"[AutoSync] 处理失败 {handler.__name__}: {e}")

    @classmethod
    def trigger_sync(cls, action_type: str, data: dict | None = None):
        """同步版本触发（用于非异步上下文）"""
        handlers = cls._handlers.get(action_type, [])
        data = data or {}
        for handler in handlers:
            try:
                handler(action_type, data)
            except Exception as e:
                logger.warning(f"[AutoSync] 同步处理失败 {handler.__name__}: {e}")


# ═══════════════════════════════════════════════════════════════
# 内置同步处理器
# ═══════════════════════════════════════════════════════════════


def _sync_control_docs(_action_type: str, data: dict):
    """控制文档自动保存"""
    book_id = data.get("book_id", "default")
    story_dir = settings.DATA_DIR / "story" / book_id
    story_dir.mkdir(parents=True, exist_ok=True)

    mappings = {
        "author_intent": ("author_intent.md", "author_intent"),
        "current_focus": ("current_focus.md", "current_focus"),
        "book_rules": ("book_rules.md", "book_rules"),
        "story_bible": ("story_bible.md", "story_bible"),
    }
    for filename, data_key in mappings.values():
        content = data.get(data_key, "")
        if content:
            (story_dir / filename).write_text(str(content), encoding="utf-8")
            logger.debug(f"[AutoSync] 控制文档已保存: {filename}")


def _sync_learner(_action_type: str, data: dict):
    """偏好学习自动持久化"""
    book_id = data.get("book_id", "default")
    try:
        from kunlun.learn import get_learner

        learner = get_learner(book_id)
        learner.save()
        logger.debug(f"[AutoSync] 偏好已持久化 (book_id={book_id})")
    except Exception as e:
        logger.warning(f"[AutoSync] 偏好持久化失败: {e}")


def _sync_truth(_action_type: str, data: dict):
    """真相文件自动更新"""
    book_id = data.get("book_id", "default")
    chapter = data.get("chapter", 0)
    draft = data.get("draft", "")
    blueprint = data.get("blueprint", {})
    if not draft or not chapter:
        return
    try:
        from kunlun.filesync import get_syncer

        syncer = get_syncer(book_id)
        syncer.update_truth_after_chapter(chapter, draft, blueprint)
    except Exception as e:
        logger.warning(f"[AutoSync] 真相文件更新失败: {e}")


def _sync_dashboard(_action_type: str, data: dict):
    """写作仪表盘自动更新"""
    book_id = data.get("book_id", "default")
    chapter = data.get("chapter", 0)
    draft = data.get("draft", "")
    try:
        from kunlun.dashboard import get_dashboard

        db = get_dashboard(book_id)
        # DashboardEngine 为只读引擎，通过快照记录当前仪表盘状态
        db.take_snapshot()
        logger.debug(f"[AutoSync] 仪表盘快照已记录 (chapter={chapter}, draft_len={len(draft)})")
    except Exception as e:
        logger.warning(f"[AutoSync] 仪表盘更新失败: {e}")


def _sync_retention(_action_type: str, data: dict):
    """读者留存预测自动保存"""
    book_id = data.get("book_id", "default")
    if "retention_features" in data:
        try:
            from kunlun.retention import get_retention_predictor

            pred = get_retention_predictor(book_id)
            feat = data["retention_features"]
            # 使用正文进行完整的追读力分析（真实API: analyze）
            text = feat.get("text", "") or feat.get("draft", "") or ""
            if text:
                feat_chapter = int(feat.get("chapter", 0))
                pred.analyze(
                    text=text,
                    chapter_number=feat_chapter,
                    is_first_three=feat_chapter <= 3,
                )
            logger.debug(f"[AutoSync] 留存预测已保存 (book={book_id})")
        except Exception as e:
            logger.warning(f"[AutoSync] 留存预测保存失败: {e}")


def _sync_pleasure(_action_type: str, data: dict):
    """爽点数据自动持久化"""
    book_id = data.get("book_id", "default")
    chapter = data.get("chapter", 0)
    draft = data.get("draft", "")
    if not draft:
        return
    try:
        from kunlun.pleasure import get_pleasure_engine

        engine = get_pleasure_engine(book_id)
        engine.detect_events(chapter, draft)
    except Exception as e:
        logger.warning(f"[AutoSync] 爽点引擎更新失败: {e}")


def _sync_runtime_artifacts(_action_type: str, data: dict):
    """运行时产物自动保存"""
    book_id = data.get("book_id", "default")
    chapter = data.get("chapter", 0)
    blueprint = data.get("blueprint", {})
    audit_result = data.get("audit_result", {})
    try:
        from kunlun.filesync import get_syncer

        syncer = get_syncer(book_id)
        syncer.save_runtime_artifacts(
            chapter,
            data.get("intent", {}),
            blueprint,
            audit_result,
            (data.get("draft") or "")[:200],
        )
    except Exception as e:
        logger.warning(f"[AutoSync] 运行时产物保存失败: {e}")


# ═══════════════════════════════════════════════════════════════
# 注册所有自动同步处理器
# ═══════════════════════════════════════════════════════════════


def _register_default_handlers():
    """注册默认的自动同步处理器"""

    # 章节生成完成后：更新所有相关文件
    AutoSync.register("chapter_generated", _sync_truth)
    AutoSync.register("chapter_generated", _sync_learner)
    AutoSync.register("chapter_generated", _sync_dashboard)
    AutoSync.register("chapter_generated", _sync_pleasure)
    AutoSync.register("chapter_generated", _sync_runtime_artifacts)

    # 控制文档修改后：保存到文件
    AutoSync.register("control_doc_updated", _sync_control_docs)

    # 反馈/偏好更新后：持久化
    AutoSync.register("feedback_given", _sync_learner)
    AutoSync.register("preferences_updated", _sync_learner)

    # 导出操作后：更新仪表盘
    AutoSync.register("chapter_exported", _sync_dashboard)

    # 留存数据更新后：自动保存
    AutoSync.register("retention_updated", _sync_retention)

    # 创作完成后的全量同步
    AutoSync.register("chapter_published", _sync_truth)
    AutoSync.register("chapter_published", _sync_dashboard)
    AutoSync.register("chapter_published", _sync_runtime_artifacts)

    logger.info(
        f"[AutoSync] 已注册 {sum(len(v) for v in AutoSync._handlers.values())} 个同步处理器"
    )


# 模块加载时自动注册
_register_default_handlers()

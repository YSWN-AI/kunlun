"""
昆仑创作引擎 — 核心扩展集成

将插件系统、TTS、图像生成等新模块集成到现有管线中。
在管线关键节点自动触发插件钩子事件。

用法:
    在应用启动时调用 setup_extensions() 即可注册所有集成。
"""

from __future__ import annotations

import logging
from pathlib import Path

from kunlun.plugins import PluginEvent, PluginHook, plugin_manager

logger = logging.getLogger(__name__)


# ── 管线钩子集成 ──────────────────────────────────


async def emit_pipeline_start(book_id: str, data: dict | None = None) -> None:
    """管线启动时触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PIPELINE_START,
            book_id=book_id,
            data=data or {},
        )
    )


async def emit_pipeline_end(book_id: str, data: dict | None = None) -> None:
    """管线完成时触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PIPELINE_END,
            book_id=book_id,
            data=data or {},
        )
    )


async def emit_chapter_generated(
    book_id: str,
    chapter_num: int,
    title: str,
    content: str,
) -> None:
    """章节生成后触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.CHAPTER_GENERATED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "title": title,
                "content_length": len(content),
            },
        )
    )


async def emit_chapter_revised(
    book_id: str,
    chapter_num: int,
    revision_notes: str = "",
) -> None:
    """章节修订后触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.CHAPTER_REVISED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "revision_notes": revision_notes,
            },
        )
    )


async def emit_audit_complete(
    book_id: str,
    chapter_num: int,
    score: float,
    issues: list[dict] | None = None,
) -> None:
    """审计完成时触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.AUDIT_COMPLETE,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "score": score,
                "issues": issues or [],
            },
        )
    )


async def emit_audit_gate_failed(
    book_id: str,
    chapter_num: int,
    gate_name: str,
    reason: str,
) -> None:
    """审计门禁失败时触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.AUDIT_GATE_FAILED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "gate": gate_name,
                "reason": reason,
            },
        )
    )


async def emit_character_created(
    book_id: str,
    character_name: str,
    data: dict | None = None,
) -> None:
    """创建角色时触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.CHARACTER_CREATED,
            book_id=book_id,
            data={
                "character_name": character_name,
                **(data or {}),
            },
        )
    )


async def emit_style_analyzed(
    book_id: str,
    style_profile: dict | None = None,
) -> None:
    """风格分析完成时触发插件事件"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.STYLE_ANALYZED,
            book_id=book_id,
            data=style_profile or {},
        )
    )


# ── Phase 2: 协作事件 ─────────────────────────────


async def emit_collab_session_created(
    book_id: str,
    session_id: str,
    owner_id: str,
) -> None:
    """协作会话创建时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COLLAB_SESSION_CREATED,
            book_id=book_id,
            data={"session_id": session_id, "owner_id": owner_id},
        )
    )


async def emit_collab_user_joined(
    book_id: str,
    session_id: str,
    user_id: str,
) -> None:
    """用户加入协作时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COLLAB_USER_JOINED,
            book_id=book_id,
            data={"session_id": session_id, "user_id": user_id},
        )
    )


async def emit_collab_user_left(
    book_id: str,
    session_id: str,
    user_id: str,
) -> None:
    """用户离开协作时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COLLAB_USER_LEFT,
            book_id=book_id,
            data={"session_id": session_id, "user_id": user_id},
        )
    )


async def emit_collab_comment_added(
    book_id: str,
    session_id: str,
    author_id: str,
    content: str,
) -> None:
    """协作评论添加时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COLLAB_COMMENT_ADDED,
            book_id=book_id,
            data={
                "session_id": session_id,
                "author_id": author_id,
                "content": content[:100],
            },
        )
    )


# ── Phase 2: 发布事件 ─────────────────────────────


async def emit_publish_started(
    book_id: str,
    chapter_num: int,
    platforms: list[str],
) -> None:
    """发布开始触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PUBLISH_STARTED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "platforms": platforms,
            },
        )
    )


async def emit_publish_completed(
    book_id: str,
    chapter_num: int,
    platforms: list[str],
    results: list[dict],
) -> None:
    """发布完成触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PUBLISH_COMPLETED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "platforms": platforms,
                "results": results,
            },
        )
    )


async def emit_publish_failed(
    book_id: str,
    chapter_num: int,
    platform: str,
    error: str,
) -> None:
    """发布失败触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PUBLISH_FAILED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "platform": platform,
                "error": error,
            },
        )
    )


async def emit_publish_scheduled(
    book_id: str,
    chapter_num: int,
    platforms: list[str],
    publish_at: float,
) -> None:
    """定时发布计划创建时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PUBLISH_SCHEDULED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "platforms": platforms,
                "publish_at": publish_at,
            },
        )
    )


# ── Phase 2: 社区事件 ─────────────────────────────


async def emit_community_review_added(
    book_id: str,
    author_id: str,
    rating: int,
) -> None:
    """社区评论添加时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COMMUNITY_REVIEW_ADDED,
            book_id=book_id,
            data={"author_id": author_id, "rating": rating},
        )
    )


async def emit_community_rating_added(
    book_id: str,
    user_id: str,
    overall: int,
) -> None:
    """社区评分添加时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COMMUNITY_RATING_ADDED,
            book_id=book_id,
            data={"user_id": user_id, "overall": overall},
        )
    )


async def emit_community_tip_received(
    book_id: str,
    from_user: str,
    to_user: str,
    amount: int,
) -> None:
    """收到打赏时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COMMUNITY_TIP_RECEIVED,
            book_id=book_id,
            data={
                "from_user": from_user,
                "to_user": to_user,
                "amount": amount,
            },
        )
    )


async def emit_community_boost_received(
    book_id: str,
    chapter_num: int,
    from_user: str,
    amount: int,
) -> None:
    """收到催更票时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.COMMUNITY_BOOST_RECEIVED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "from_user": from_user,
                "amount": amount,
            },
        )
    )


# ── Phase 3: 变现事件 ─────────────────────────────


async def emit_monetize_subscription_created(
    user_id: str,
    plan_id: str,
    tier: str,
) -> None:
    """订阅创建时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MONETIZE_SUBSCRIPTION_CREATED,
            book_id=user_id,
            data={"plan_id": plan_id, "tier": tier},
        )
    )


async def emit_monetize_subscription_cancelled(user_id: str) -> None:
    """订阅取消时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MONETIZE_SUBSCRIPTION_CANCELLED,
            book_id=user_id,
            data={},
        )
    )


async def emit_monetize_tip_sent(
    book_id: str,
    from_user: str,
    to_user: str,
    amount: int,
) -> None:
    """打赏发送时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MONETIZE_TIP_SENT,
            book_id=book_id,
            data={
                "from_user": from_user,
                "to_user": to_user,
                "amount": amount,
            },
        )
    )


async def emit_monetize_chapter_unlocked(
    book_id: str,
    chapter_num: int,
    price: int,
    user_id: str,
) -> None:
    """付费章节解锁时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MONETIZE_CHAPTER_UNLOCKED,
            book_id=book_id,
            data={
                "chapter_num": chapter_num,
                "price": price,
                "user_id": user_id,
            },
        )
    )


async def emit_monetize_withdrawal_requested(
    user_id: str,
    amount: float,
    method: str,
) -> None:
    """提现申请时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MONETIZE_WITHDRAWAL_REQUESTED,
            book_id=user_id,
            data={"amount": amount, "method": method},
        )
    )


# ── Phase 3: 市场事件 ─────────────────────────────


async def emit_marketplace_template_installed(
    template_id: str,
    user_id: str,
    template_name: str,
) -> None:
    """模板安装时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MARKETPLACE_TEMPLATE_INSTALLED,
            book_id=template_id,
            data={"user_id": user_id, "template_name": template_name},
        )
    )


async def emit_marketplace_template_published(
    template_id: str,
    author_id: str,
    name: str,
    category: str,
) -> None:
    """模板发布时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MARKETPLACE_TEMPLATE_PUBLISHED,
            book_id=template_id,
            data={
                "author_id": author_id,
                "name": name,
                "category": category,
            },
        )
    )


async def emit_marketplace_template_rated(
    template_id: str,
    rating: float,
    user_id: str,
) -> None:
    """模板评分时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.MARKETPLACE_TEMPLATE_RATED,
            book_id=template_id,
            data={"rating": rating, "user_id": user_id},
        )
    )


# ── Phase 3: 插件商店事件 ─────────────────────────


async def emit_plugin_store_installed(
    plugin_id: str,
    user_id: str,
    plugin_name: str,
) -> None:
    """插件安装时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PLUGIN_STORE_INSTALLED,
            book_id=plugin_id,
            data={"user_id": user_id, "plugin_name": plugin_name},
        )
    )


async def emit_plugin_store_published(
    plugin_id: str,
    author_id: str,
    name: str,
    category: str,
) -> None:
    """插件发布时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PLUGIN_STORE_PUBLISHED,
            book_id=plugin_id,
            data={
                "author_id": author_id,
                "name": name,
                "category": category,
            },
        )
    )


async def emit_plugin_store_rated(
    plugin_id: str,
    rating: float,
    user_id: str,
) -> None:
    """插件评分时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.PLUGIN_STORE_RATED,
            book_id=plugin_id,
            data={"rating": rating, "user_id": user_id},
        )
    )


# ── Phase 3: 微调事件 ─────────────────────────────


async def emit_finetune_training_started(
    adapter_name: str,
    base_model: str,
    adapter_type: str,
) -> None:
    """微调训练开始时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.FINETUNE_TRAINING_STARTED,
            book_id=adapter_name,
            data={
                "base_model": base_model,
                "adapter_type": adapter_type,
            },
        )
    )


async def emit_finetune_training_completed(
    adapter_name: str,
    trained_steps: int,
    loss: float,
) -> None:
    """微调训练完成时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.FINETUNE_TRAINING_COMPLETED,
            book_id=adapter_name,
            data={
                "trained_steps": trained_steps,
                "loss": loss,
            },
        )
    )


async def emit_finetune_adapter_activated(
    adapter_name: str,
    base_model: str,
) -> None:
    """适配器激活时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.FINETUNE_ADAPTER_ACTIVATED,
            book_id=adapter_name,
            data={"base_model": base_model},
        )
    )


# ── Phase 3: 分析事件 ─────────────────────────────


async def emit_analytics_report_generated(
    book_id: str,
    fmt: str,
    user_id: str = "",
) -> None:
    """分析报告生成时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.ANALYTICS_REPORT_GENERATED,
            book_id=book_id,
            data={"format": fmt, "user_id": user_id},
        )
    )


async def emit_analytics_data_exported(
    book_id: str,
    fmt: str,
    record_count: int = 0,
) -> None:
    """数据导出时触发"""
    await plugin_manager.emit(
        PluginEvent(
            hook=PluginHook.ANALYTICS_DATA_EXPORTED,
            book_id=book_id,
            data={"format": fmt, "record_count": record_count},
        )
    )


# ── 应用启动与关闭 ────────────────────────────────


async def setup_extensions() -> None:
    """初始化所有扩展模块

    应在应用启动时调用（main.py 中）。
    """
    logger.info("Setting up extensions...")

    # 启动插件系统
    await plugin_manager.startup()

    # 自动加载内置插件
    _load_builtin_plugins()

    logger.info("Extensions setup complete")


async def teardown_extensions() -> None:
    """清理所有扩展模块

    应在应用关闭时调用。
    """
    logger.info("Tearing down extensions...")
    await plugin_manager.shutdown()
    logger.info("Extensions teardown complete")


def _load_builtin_plugins() -> None:
    """加载内置插件"""
    plugins_dir = Path(__file__).parent.parent / "plugins"
    if plugins_dir.is_dir():
        count = plugin_manager.load_from_dir(plugins_dir)
        if count > 0:
            logger.info("Loaded %d builtin plugins", count)

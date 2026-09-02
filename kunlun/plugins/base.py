"""
插件基类定义
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PluginHook(StrEnum):
    """插件可挂载的钩子事件"""

    # 管线事件
    PIPELINE_START = "pipeline:start"
    PIPELINE_END = "pipeline:end"
    PIPELINE_STEP_START = "pipeline:step:start"
    PIPELINE_STEP_END = "pipeline:step:end"

    # 章节事件
    CHAPTER_GENERATED = "chapter:generated"
    CHAPTER_REVISED = "chapter:revised"
    CHAPTER_PUBLISHED = "chapter:published"

    # 审计事件
    AUDIT_START = "audit:start"
    AUDIT_COMPLETE = "audit:complete"
    AUDIT_GATE_FAILED = "audit:gate:failed"

    # 世界建筑事件
    WORLD_LOCATION_ADDED = "world:location:added"
    WORLD_FACTION_ADDED = "world:faction:added"
    WORLD_TIMELINE_ADDED = "world:timeline:added"

    # 角色事件
    CHARACTER_CREATED = "character:created"
    CHARACTER_UPDATED = "character:updated"

    # 风格事件
    STYLE_ANALYZED = "style:analyzed"

    # 协作事件 (Phase 2)
    COLLAB_SESSION_CREATED = "collab:session:created"
    COLLAB_USER_JOINED = "collab:user:joined"
    COLLAB_USER_LEFT = "collab:user:left"
    COLLAB_COMMENT_ADDED = "collab:comment:added"
    COLLAB_COMMENT_RESOLVED = "collab:comment:resolved"

    # 发布事件 (Phase 2)
    PUBLISH_STARTED = "publish:started"
    PUBLISH_COMPLETED = "publish:completed"
    PUBLISH_FAILED = "publish:failed"
    PUBLISH_SCHEDULED = "publish:scheduled"

    # 社区事件 (Phase 2)
    COMMUNITY_REVIEW_ADDED = "community:review:added"
    COMMUNITY_RATING_ADDED = "community:rating:added"
    COMMUNITY_TIP_RECEIVED = "community:tip:received"
    COMMUNITY_BOOST_RECEIVED = "community:boost:received"

    # 变现事件 (Phase 3)
    MONETIZE_SUBSCRIPTION_CREATED = "monetize:subscription:created"
    MONETIZE_SUBSCRIPTION_CANCELLED = "monetize:subscription:cancelled"
    MONETIZE_TIP_SENT = "monetize:tip:sent"
    MONETIZE_CHAPTER_UNLOCKED = "monetize:chapter:unlocked"
    MONETIZE_WITHDRAWAL_REQUESTED = "monetize:withdrawal:requested"

    # 市场事件 (Phase 3)
    MARKETPLACE_TEMPLATE_INSTALLED = "marketplace:template:installed"
    MARKETPLACE_TEMPLATE_PUBLISHED = "marketplace:template:published"
    MARKETPLACE_TEMPLATE_RATED = "marketplace:template:rated"

    # 插件商店事件 (Phase 3)
    PLUGIN_STORE_INSTALLED = "plugin_store:installed"
    PLUGIN_STORE_PUBLISHED = "plugin_store:published"
    PLUGIN_STORE_RATED = "plugin_store:rated"

    # 微调事件 (Phase 3)
    FINETUNE_TRAINING_STARTED = "finetune:training:started"
    FINETUNE_TRAINING_COMPLETED = "finetune:training:completed"
    FINETUNE_ADAPTER_ACTIVATED = "finetune:adapter:activated"

    # 分析事件 (Phase 3)
    ANALYTICS_REPORT_GENERATED = "analytics:report:generated"
    ANALYTICS_DATA_EXPORTED = "analytics:data:exported"

    # 系统事件
    SYSTEM_STARTUP = "system:startup"
    SYSTEM_SHUTDOWN = "system:shutdown"


@dataclass
class PluginEvent:
    """插件事件数据"""

    hook: PluginHook
    book_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """插件基类 — 所有第三方插件必须继承此类

    属性:
        name: 插件唯一标识
        version: 语义化版本号
        description: 插件描述
        author: 作者
        hooks: 插件监听的钩子事件列表

    方法:
        on_event(event): 统一事件处理入口
        on_*(): 具体钩子处理方法（按需覆盖）
    """

    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    hooks: list[PluginHook] = []

    def __repr__(self) -> str:
        return f"<Plugin {self.name} v{self.version}>"

    # ── 统一事件入口 ──────────────────────────────

    async def on_event(self, event: PluginEvent) -> None:
        """根据 event.hook 分发到对应的处理方法"""
        handler_map = {
            PluginHook.PIPELINE_START: self.on_pipeline_start,
            PluginHook.PIPELINE_END: self.on_pipeline_end,
            PluginHook.PIPELINE_STEP_START: self.on_pipeline_step_start,
            PluginHook.PIPELINE_STEP_END: self.on_pipeline_step_end,
            PluginHook.CHAPTER_GENERATED: self.on_chapter_generated,
            PluginHook.CHAPTER_REVISED: self.on_chapter_revised,
            PluginHook.CHAPTER_PUBLISHED: self.on_chapter_published,
            PluginHook.AUDIT_START: self.on_audit_start,
            PluginHook.AUDIT_COMPLETE: self.on_audit_complete,
            PluginHook.AUDIT_GATE_FAILED: self.on_audit_gate_failed,
            PluginHook.WORLD_LOCATION_ADDED: self.on_world_location_added,
            PluginHook.WORLD_FACTION_ADDED: self.on_world_faction_added,
            PluginHook.WORLD_TIMELINE_ADDED: self.on_world_timeline_added,
            PluginHook.CHARACTER_CREATED: self.on_character_created,
            PluginHook.CHARACTER_UPDATED: self.on_character_updated,
            PluginHook.STYLE_ANALYZED: self.on_style_analyzed,
            PluginHook.COLLAB_SESSION_CREATED: self.on_collab_session_created,
            PluginHook.COLLAB_USER_JOINED: self.on_collab_user_joined,
            PluginHook.COLLAB_USER_LEFT: self.on_collab_user_left,
            PluginHook.COLLAB_COMMENT_ADDED: self.on_collab_comment_added,
            PluginHook.COLLAB_COMMENT_RESOLVED: self.on_collab_comment_resolved,
            PluginHook.PUBLISH_STARTED: self.on_publish_started,
            PluginHook.PUBLISH_COMPLETED: self.on_publish_completed,
            PluginHook.PUBLISH_FAILED: self.on_publish_failed,
            PluginHook.PUBLISH_SCHEDULED: self.on_publish_scheduled,
            PluginHook.COMMUNITY_REVIEW_ADDED: self.on_community_review_added,
            PluginHook.COMMUNITY_RATING_ADDED: self.on_community_rating_added,
            PluginHook.COMMUNITY_TIP_RECEIVED: self.on_community_tip_received,
            PluginHook.COMMUNITY_BOOST_RECEIVED: self.on_community_boost_received,
            PluginHook.MONETIZE_SUBSCRIPTION_CREATED: self.on_monetize_subscription_created,
            PluginHook.MONETIZE_SUBSCRIPTION_CANCELLED: self.on_monetize_subscription_cancelled,
            PluginHook.MONETIZE_TIP_SENT: self.on_monetize_tip_sent,
            PluginHook.MONETIZE_CHAPTER_UNLOCKED: self.on_monetize_chapter_unlocked,
            PluginHook.MONETIZE_WITHDRAWAL_REQUESTED: self.on_monetize_withdrawal_requested,
            PluginHook.MARKETPLACE_TEMPLATE_INSTALLED: self.on_marketplace_template_installed,
            PluginHook.MARKETPLACE_TEMPLATE_PUBLISHED: self.on_marketplace_template_published,
            PluginHook.MARKETPLACE_TEMPLATE_RATED: self.on_marketplace_template_rated,
            PluginHook.PLUGIN_STORE_INSTALLED: self.on_plugin_store_installed,
            PluginHook.PLUGIN_STORE_PUBLISHED: self.on_plugin_store_published,
            PluginHook.PLUGIN_STORE_RATED: self.on_plugin_store_rated,
            PluginHook.FINETUNE_TRAINING_STARTED: self.on_finetune_training_started,
            PluginHook.FINETUNE_TRAINING_COMPLETED: self.on_finetune_training_completed,
            PluginHook.FINETUNE_ADAPTER_ACTIVATED: self.on_finetune_adapter_activated,
            PluginHook.ANALYTICS_REPORT_GENERATED: self.on_analytics_report_generated,
            PluginHook.ANALYTICS_DATA_EXPORTED: self.on_analytics_data_exported,
            PluginHook.SYSTEM_STARTUP: self.on_system_startup,
            PluginHook.SYSTEM_SHUTDOWN: self.on_system_shutdown,
        }
        handler = handler_map.get(event.hook)
        if handler:
            await handler(event)

    # ── 管线事件 ──────────────────────────────────

    async def on_pipeline_start(self, event: PluginEvent) -> None:
        """管线启动时触发"""

    async def on_pipeline_end(self, event: PluginEvent) -> None:
        """管线完成时触发"""

    async def on_pipeline_step_start(self, event: PluginEvent) -> None:
        """管线步骤开始时触发"""

    async def on_pipeline_step_end(self, event: PluginEvent) -> None:
        """管线步骤结束时触发"""

    # ── 章节事件 ──────────────────────────────────

    async def on_chapter_generated(self, event: PluginEvent) -> None:
        """章节生成后触发"""

    async def on_chapter_revised(self, event: PluginEvent) -> None:
        """章节修订后触发"""

    async def on_chapter_published(self, event: PluginEvent) -> None:
        """章节发布后触发"""

    # ── 审计事件 ──────────────────────────────────

    async def on_audit_start(self, event: PluginEvent) -> None:
        """审计开始时触发"""

    async def on_audit_complete(self, event: PluginEvent) -> None:
        """审计完成时触发"""

    async def on_audit_gate_failed(self, event: PluginEvent) -> None:
        """审计门禁失败时触发"""

    # ── 世界建筑事件 ────────────────────────────────

    async def on_world_location_added(self, event: PluginEvent) -> None:
        """添加地点时触发"""

    async def on_world_faction_added(self, event: PluginEvent) -> None:
        """添加阵营时触发"""

    async def on_world_timeline_added(self, event: PluginEvent) -> None:
        """添加时间线事件时触发"""

    # ── 角色事件 ──────────────────────────────────

    async def on_character_created(self, event: PluginEvent) -> None:
        """创建角色时触发"""

    async def on_character_updated(self, event: PluginEvent) -> None:
        """更新角色时触发"""

    # ── 风格事件 ──────────────────────────────────

    async def on_style_analyzed(self, event: PluginEvent) -> None:
        """风格分析完成后触发"""

    # ── 协作事件 (Phase 2) ────────────────────────

    async def on_collab_session_created(self, event: PluginEvent) -> None:
        """协作会话创建时触发"""

    async def on_collab_user_joined(self, event: PluginEvent) -> None:
        """用户加入协作时触发"""

    async def on_collab_user_left(self, event: PluginEvent) -> None:
        """用户离开协作时触发"""

    async def on_collab_comment_added(self, event: PluginEvent) -> None:
        """协作评论添加时触发"""

    async def on_collab_comment_resolved(self, event: PluginEvent) -> None:
        """协作评论解决时触发"""

    # ── 发布事件 (Phase 2) ────────────────────────

    async def on_publish_started(self, event: PluginEvent) -> None:
        """发布开始时触发"""

    async def on_publish_completed(self, event: PluginEvent) -> None:
        """发布完成时触发"""

    async def on_publish_failed(self, event: PluginEvent) -> None:
        """发布失败时触发"""

    async def on_publish_scheduled(self, event: PluginEvent) -> None:
        """定时发布计划创建时触发"""

    # ── 社区事件 (Phase 2) ────────────────────────

    async def on_community_review_added(self, event: PluginEvent) -> None:
        """社区评论添加时触发"""

    async def on_community_rating_added(self, event: PluginEvent) -> None:
        """社区评分添加时触发"""

    async def on_community_tip_received(self, event: PluginEvent) -> None:
        """收到打赏时触发"""

    async def on_community_boost_received(self, event: PluginEvent) -> None:
        """收到催更票时触发"""

    # ── 变现事件 (Phase 3) ────────────────────────

    async def on_monetize_subscription_created(self, event: PluginEvent) -> None:
        """订阅创建时触发"""

    async def on_monetize_subscription_cancelled(self, event: PluginEvent) -> None:
        """订阅取消时触发"""

    async def on_monetize_tip_sent(self, event: PluginEvent) -> None:
        """打赏发送时触发"""

    async def on_monetize_chapter_unlocked(self, event: PluginEvent) -> None:
        """付费章节解锁时触发"""

    async def on_monetize_withdrawal_requested(self, event: PluginEvent) -> None:
        """提现申请时触发"""

    # ── 市场事件 (Phase 3) ────────────────────────

    async def on_marketplace_template_installed(self, event: PluginEvent) -> None:
        """模板安装时触发"""

    async def on_marketplace_template_published(self, event: PluginEvent) -> None:
        """模板发布时触发"""

    async def on_marketplace_template_rated(self, event: PluginEvent) -> None:
        """模板评分时触发"""

    # ── 插件商店事件 (Phase 3) ────────────────────

    async def on_plugin_store_installed(self, event: PluginEvent) -> None:
        """插件安装时触发"""

    async def on_plugin_store_published(self, event: PluginEvent) -> None:
        """插件发布时触发"""

    async def on_plugin_store_rated(self, event: PluginEvent) -> None:
        """插件评分时触发"""

    # ── 微调事件 (Phase 3) ────────────────────────

    async def on_finetune_training_started(self, event: PluginEvent) -> None:
        """微调训练开始时触发"""

    async def on_finetune_training_completed(self, event: PluginEvent) -> None:
        """微调训练完成时触发"""

    async def on_finetune_adapter_activated(self, event: PluginEvent) -> None:
        """适配器激活时触发"""

    # ── 分析事件 (Phase 3) ────────────────────────

    async def on_analytics_report_generated(self, event: PluginEvent) -> None:
        """分析报告生成时触发"""

    async def on_analytics_data_exported(self, event: PluginEvent) -> None:
        """数据导出时触发"""

    # ── 系统事件 ──────────────────────────────────

    async def on_system_startup(self, event: PluginEvent) -> None:
        """系统启动时触发"""

    async def on_system_shutdown(self, event: PluginEvent) -> None:
        """系统关闭时触发"""

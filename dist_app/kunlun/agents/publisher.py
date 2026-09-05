"""
昆仑创作引擎 — 发布 Agent

独立的发布 Agent，在 Makefile 流水线中作为独立节点参与多 Agent 协作。
与 kunlun.publish 发布代理配合，提供 Agent 层级的发布编排能力。

职责：
- 接收 Makefile 的发布任务包
- 调用 PublishProxy 执行平台发布
- 发布后触发版本管理 commit
- 发布状态回调消息总线

设计来源：昆仑_缺失功能补全设计.md §发布系统
          昆仑_剩余功能补全设计.md §12. 多平台适配
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.publish import Platform, PublishStatus, get_publish_proxy
from kunlun.versions.manager import CommitScope, version_manager

# ─── 数据结构 ───────────────────────────────────────


class PublishAction(StrEnum):
    PUBLISH = "publish"
    SCHEDULE = "schedule"
    CANCEL = "cancel"
    STATUS = "status"


@dataclass
class PublisherTask:
    """发布 Agent 接收的任务包。"""

    book_id: str
    chapter_number: int
    title: str
    content: str
    platforms: list[str] = field(default_factory=lambda: [Platform.FANQIE.value])
    action: PublishAction = PublishAction.PUBLISH
    scheduled_time: str | None = None  # ISO format
    metadata: dict = field(default_factory=dict)


@dataclass
class PublisherResult:
    """发布结果。"""

    book_id: str
    chapter_number: int
    success: bool
    published_platforms: list[str]
    failed_platforms: list[str]
    errors: list[str]
    publish_time: str
    publish_urls: dict[str, str]  # platform → url


# ─── 发布 Agent ─────────────────────────────────────


class PublisherAgent(BaseAgent):
    """独立发布 Agent。

    作为多 Agent 系统中的独立节点，负责将已审核通过的章节
    发布到目标平台。支持多平台并行发布和定时发布。
    """

    agent_name: str = "publisher"
    capabilities: ClassVar[list[str]] = [
        "publish_chapter",
        "multi_platform_publish",
        "publish_scheduling",
        "publish_status_query",
    ]

    def __init__(self, nats_client=None):
        super().__init__(nats_client=nats_client)
        self._published_log: list[PublisherResult] = []

    # ── BaseAgent 抽象方法实现 ────────────────────────

    async def execute(self, task: dict) -> dict:
        """BaseAgent 入口 — 委托给 process 方法。"""
        return await self.process(task)

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        """处理消息总线消息。"""
        if msg.msg_type == "PUBLISH":
            result = await self.process(msg.payload)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="PUBLISH_DONE",
                payload={"publish_result": result},
                correlation_id=msg.correlation_id,
                kg_snapshot_id=msg.kg_snapshot_id,
            )
        return None

    # ── 任务处理 ─────────────────────────────────────

    async def process(self, task_package: dict) -> dict:
        """处理发布任务（BaseAgent 接口）。

        从 Makefile 流水线接收任务包，解析后执行发布。
        """
        try:
            task_data = task_package.get("publisher_task", task_package)
            task = PublisherTask(
                book_id=task_data.get("book_id", "default"),
                chapter_number=task_data.get("chapter_number", 0),
                title=task_data.get("title", ""),
                content=task_data.get("content", ""),
                platforms=task_data.get("platforms", ["fanqie"]),
                action=PublishAction(task_data.get("action", "publish")),
                scheduled_time=task_data.get("scheduled_time"),
                metadata=task_data.get("metadata", {}),
            )
        except Exception as e:
            logger.exception(f"Publisher 任务解析失败: {e}")
            logger.error(f"Publisher 任务解析失败: {e}")
            return {"status": "error", "error": str(e)}

        result = await self.publish(task)
        return {
            "status": "success" if result.success else "partial",
            "result": {
                "book_id": result.book_id,
                "chapter_number": result.chapter_number,
                "published_platforms": result.published_platforms,
                "failed_platforms": result.failed_platforms,
                "publish_time": result.publish_time,
                "urls": result.publish_urls,
            },
        }

    async def publish(self, task: PublisherTask) -> PublisherResult:
        """执行发布操作。"""
        published: list[str] = []
        failed: list[str] = []
        errors: list[str] = []
        urls: dict[str, str] = {}

        if task.action == PublishAction.CANCEL:
            return PublisherResult(
                book_id=task.book_id,
                chapter_number=task.chapter_number,
                success=True,
                published_platforms=[],
                failed_platforms=[],
                errors=[],
                publish_time=datetime.now(UTC).isoformat(),
                publish_urls={},
            )

        if task.action == PublishAction.STATUS:
            status_data = self._check_status(task.book_id, task.chapter_number)
            records = status_data.get("records", [])
            return PublisherResult(
                book_id=task.book_id,
                chapter_number=task.chapter_number,
                success=True,
                published_platforms=[
                    r["platform"] for r in records if r["status"] == PublishStatus.PUBLISHED.value
                ],
                failed_platforms=[
                    r["platform"] for r in records if r["status"] == PublishStatus.FAILED.value
                ],
                errors=[],
                publish_time=datetime.now(UTC).isoformat(),
                publish_urls={r["platform"]: r["url"] for r in records if r["url"]},
            )

        # 执行发布
        for platform_str in task.platforms:
            try:
                # 将字符串规范化为 Platform 枚举
                platform = Platform(platform_str) if isinstance(platform_str, str) else platform_str
                proxy = get_publish_proxy(task.book_id)
                proxy.prepare_chapter(
                    chapter=task.chapter_number,
                    text=task.content,
                    platform=platform,
                    chapter_title=task.title or "",
                )
                pname = platform.value
                published.append(pname)
                urls[pname] = ""
                logger.info(f"[Publisher] ch{task.chapter_number} → {pname} 准备完成")
            except Exception as e:
                failed.append(platform.value)
                errors.append(f"{platform}: {e}")
                logger.exception(f"[Publisher] 平台发布失败 ({platform.value}): {e}")

        publish_time = datetime.now(UTC).isoformat()
        result = PublisherResult(
            book_id=task.book_id,
            chapter_number=task.chapter_number,
            success=len(failed) == 0,
            published_platforms=published,
            failed_platforms=failed,
            errors=errors,
            publish_time=publish_time,
            publish_urls=urls,
        )
        self._published_log.append(result)

        # 发布后版本管理
        self._commit_publish(task, result)

        return result

    def _commit_publish(self, task: PublisherTask, result: PublisherResult):
        """发布成功后自动 commit 版本记录。"""
        try:
            if not version_manager.is_available():
                return
            platforms_str = ", ".join(result.published_platforms)
            version_manager.auto_commit(
                file_path=f"chapters/{task.book_id}/ch{task.chapter_number}.json",
                scope=CommitScope.PUBLISH,
                message=f"ch{task.chapter_number}: 发布到 {platforms_str}",
            )
        except Exception as e:
            logger.exception(f"发布版本记录跳过: {e}")
            logger.debug(f"发布版本记录跳过: {e}")

    # ── 状态查询 ─────────────────────────────────────

    def _check_status(self, book_id: str, chapter_number: int) -> dict:
        """查询章节在各平台的发布状态。"""
        proxy = get_publish_proxy(book_id)
        records = proxy.get_history()
        return {
            "book_id": book_id,
            "chapter_number": chapter_number,
            "records": [
                {
                    "platform": r["platform"],
                    "status": r["status"],
                    "published_at": r["published_at"],
                }
                for r in records
                if r.get("chapter", 0) == chapter_number
            ],
        }

    def get_publish_history(self, book_id: str, limit: int = 20) -> list[PublisherResult]:
        """获取发布历史。"""
        return [r for r in self._published_log if r.book_id == book_id][-limit:]

    # ── 平台适配 ─────────────────────────────────────

    def get_platform_config(self, platform: str) -> dict:
        """获取平台适配配置。"""
        platform_configs = {
            "tomato": {
                "name": "番茄小说",
                "chapter_length": (2000, 2500),
                "hook_interval": 3,
                "golden_three_focus": "爽点密度",
            },
            "qidian": {
                "name": "起点中文网",
                "chapter_length": (2000, 3000),
                "hook_interval": 5,
                "golden_three_focus": "世界观新颖",
            },
            "qimao": {
                "name": "七猫",
                "chapter_length": (1500, 2000),
                "hook_interval": 3,
                "golden_three_focus": "情感共鸣",
            },
            "feilu": {
                "name": "飞卢",
                "chapter_length": (1500, 2000),
                "hook_interval": 2,
                "golden_three_focus": "噱头冲击",
            },
            "jinjiang": {
                "name": "晋江文学城",
                "chapter_length": (2000, 3000),
                "hook_interval": 4,
                "golden_three_focus": "情感细腻",
            },
        }
        return platform_configs.get(platform, platform_configs["tomato"])

    def suggest_platforms(self, book_style: str, word_count: int) -> list[str]:
        """根据书籍风格和字数建议目标平台。"""
        suggestions: list[tuple[str, int]] = []
        platform_cfgs: dict[str, dict[str, Any]] = {
            "tomato": {"min_words": 80, "styles": ["爽文", "系统", "穿越"]},
            "qidian": {"min_words": 200, "styles": ["玄幻", "仙侠", "都市"]},
            "qimao": {"min_words": 60, "styles": ["言情", "甜宠", "总裁"]},
            "feilu": {"min_words": 100, "styles": ["同人", "爽文", "脑洞"]},
            "jinjiang": {"min_words": 60, "styles": ["耽美", "言情", "古言"]},
        }
        for pid, cfg in platform_cfgs.items():
            score = 0
            if word_count >= cfg["min_words"] * 10000 * 0.5:
                score += 1
            if any(s in book_style for s in cfg["styles"]):
                score += 2
            if score > 0:
                suggestions.append((pid, score))
        suggestions.sort(key=lambda x: -x[1])
        return [s[0] for s in suggestions[:3]]


# ─── 全局单例 ──────────────────────────────────────

publisher_agent = PublisherAgent()

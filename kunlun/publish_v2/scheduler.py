"""
发布调度器 — 定时发布与队列管理

支持:
- 定时发布 (cron-like scheduling)
- 发布队列管理
- 发布历史记录
- 批量发布

用法:
    scheduler = PublishScheduler()
    scheduler.schedule(
        book_id="book_001",
        chapter_num=42,
        platforms=["qidian", "fanqie"],
        publish_at=time.time() + 86400,  # 明天发布
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ScheduleStatus(StrEnum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    PARTIAL = "partial"  # 部分成功
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PublishSchedule:
    """发布计划"""

    schedule_id: str
    book_id: str
    chapter_num: int
    chapter_title: str = ""
    platforms: list[str] = field(default_factory=list)
    status: ScheduleStatus = ScheduleStatus.PENDING
    publish_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    executed_at: float = 0.0
    results: dict[str, str] = field(default_factory=dict)  # platform_id -> status
    error: str = ""

    @property
    def is_due(self) -> bool:
        return time.time() >= self.publish_at

    @property
    def is_immediate(self) -> bool:
        return self.publish_at == 0.0


class PublishScheduler:
    """发布调度器

    管理发布计划，支持定时和立即发布。

    用法:
        scheduler = PublishScheduler(engine)
        scheduler.schedule("book_001", 42, ["qidian"], publish_at=...)
        await scheduler.run_pending()  # 执行所有到期任务
    """

    def __init__(self, engine=None):
        self._engine = engine
        self._schedules: dict[str, PublishSchedule] = {}
        self._history: list[PublishSchedule] = []
        self._max_history: int = 500

    def schedule(
        self,
        book_id: str,
        chapter_num: int,
        platforms: list[str],
        chapter_title: str = "",
        publish_at: float = 0.0,
    ) -> str:
        """创建发布计划，返回 schedule_id"""
        import uuid

        schedule_id = str(uuid.uuid4())[:12]

        self._schedules[schedule_id] = PublishSchedule(
            schedule_id=schedule_id,
            book_id=book_id,
            chapter_num=chapter_num,
            chapter_title=chapter_title,
            platforms=platforms,
            publish_at=publish_at,
        )

        logger.info(
            "发布计划创建: %s (book=%s, ch=%d, platforms=%s, at=%s)",
            schedule_id,
            book_id,
            chapter_num,
            platforms,
            "立即"
            if publish_at == 0.0
            else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(publish_at)),
        )
        return schedule_id

    def cancel(self, schedule_id: str) -> bool:
        """取消发布计划"""
        sched = self._schedules.get(schedule_id)
        if not sched or sched.status != ScheduleStatus.PENDING:
            return False
        sched.status = ScheduleStatus.CANCELLED
        self._archive(sched)
        return True

    def get_schedule(self, schedule_id: str) -> PublishSchedule | None:
        return self._schedules.get(schedule_id)

    def list_pending(self, book_id: str = "") -> list[PublishSchedule]:
        """列出待执行的计划"""
        pending = [s for s in self._schedules.values() if s.status == ScheduleStatus.PENDING]
        if book_id:
            pending = [s for s in pending if s.book_id == book_id]
        return sorted(pending, key=lambda s: s.publish_at or float("inf"))

    def list_due(self) -> list[PublishSchedule]:
        """列出所有到期/应立即执行的计划"""
        return [s for s in self.list_pending() if s.is_due or s.is_immediate]

    async def run_pending(self) -> list[PublishSchedule]:
        """执行所有待处理的发布计划"""
        due = self.list_due()
        if not due:
            return []

        logger.info("Executing %d pending publish schedules", len(due))

        tasks = [self._execute_schedule(s) for s in due]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        completed: list[PublishSchedule] = []
        for sched, result in zip(due, results, strict=False):
            if isinstance(result, Exception):
                sched.status = ScheduleStatus.FAILED
                sched.error = str(result)
                logger.warning("Schedule %s failed: %s", sched.schedule_id, result)
            completed.append(sched)

        return completed

    async def _execute_schedule(self, sched: PublishSchedule) -> None:
        """执行单个发布计划"""
        sched.status = ScheduleStatus.PUBLISHING

        if not self._engine:
            sched.status = ScheduleStatus.FAILED
            sched.error = "发布引擎未初始化"
            self._archive(sched)
            return

        results = await self._engine.publish_chapter(
            book_id=sched.book_id,
            chapter_num=sched.chapter_num,
            platforms=sched.platforms,
        )

        for r in results:
            sched.results[r.platform_id] = r.status.value

        successes = sum(1 for r in results if r.success)
        if successes == len(results):
            sched.status = ScheduleStatus.COMPLETED
        elif successes > 0:
            sched.status = ScheduleStatus.PARTIAL
        else:
            sched.status = ScheduleStatus.FAILED

        sched.executed_at = time.time()
        self._archive(sched)

    def _archive(self, sched: PublishSchedule) -> None:
        """归档已完成的计划"""
        self._schedules.pop(sched.schedule_id, None)
        self._history.append(sched)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(
        self,
        book_id: str = "",
        limit: int = 50,
    ) -> list[PublishSchedule]:
        history = self._history
        if book_id:
            history = [h for h in history if h.book_id == book_id]
        return list(reversed(history))[:limit]

    def get_stats(self) -> dict[str, Any]:
        return {
            "pending": len(self.list_pending()),
            "history": len(self._history),
            "completed_today": sum(
                1
                for h in self._history
                if h.status == ScheduleStatus.COMPLETED and time.time() - h.executed_at < 86400
            ),
        }

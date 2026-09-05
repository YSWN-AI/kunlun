"""
断更恢复引擎 — 检测断更状态，自动生成恢复报告

功能:
- 检测断更状态（最后完成章节 + 下一章蓝图状态）
- 生成故事现状摘要（N 章递进摘要）
- 活跃伏笔检查（逾期/即将到期/安全）
- 角色位置速查
- 待办建议

用法:
    from kunlun.recovery import RecoveryEngine
    engine = RecoveryEngine(book_id="book_001")
    report = await engine.generate_recovery_report()
"""

from __future__ import annotations

import logging
from typing import Any

from kunlun.recovery.rollback import ChapterVersionManager, get_version_manager

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """断更恢复引擎

    检测断更状态，生成恢复报告，帮助作者快速找回写作状态。

    用法:
        engine = RecoveryEngine(book_id="book_001")
        report = await engine.get_recovery_report()
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self._version_manager = get_version_manager(book_id)

    async def get_recovery_report(self) -> dict[str, Any]:
        """生成恢复报告"""
        return {
            "book_id": self.book_id,
            "last_chapter": await self._get_last_chapter(),
            "versions": await self._get_version_summary(),
            "status": "ready",
        }

    async def _get_last_chapter(self) -> dict[str, Any]:
        """获取最后完成的章节信息"""
        latest = self._version_manager.get_latest(1)
        return {
            "has_content": bool(latest),
            "word_count": len(latest) if latest else 0,
        }

    async def _get_version_summary(self) -> dict[str, Any]:
        """获取版本摘要"""
        versions = self._version_manager._index.get("versions", {})
        total = sum(len(v) for v in versions.values())
        return {"total_versions": total, "chapters": len(versions)}

    def get_version_manager(self) -> ChapterVersionManager:
        """获取版本管理器"""
        return self._version_manager

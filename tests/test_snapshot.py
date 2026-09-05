"""
测试: KG Snapshot 快照管理器
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from kunlun.kg.snapshot import KGSnapshot, SnapshotManager

pytestmark = pytest.mark.integration

class TestKGSnapshot:
    """快照数据结构"""

    def test_create_empty_snapshot(self):
        snap = KGSnapshot(
            snapshot_id="test_001",
            book_id="test_book",
            chapter=1,
        )
        assert snap.snapshot_id == "test_001"
        assert snap.book_id == "test_book"
        assert snap.chapter == 1
        assert snap.entity_count == 0
        assert len(snap.characters) == 0

    def test_to_summary_empty(self):
        snap = KGSnapshot(snapshot_id="s1", book_id="b1", chapter=1)
        summary = snap.to_summary()
        assert "KG 快照" in summary
        assert "第 1 章" in summary

    def test_to_summary_with_characters(self):
        snap = KGSnapshot(snapshot_id="s1", book_id="b1", chapter=5)
        snap.characters = [
            {"e": {"name": "张三", "traits": "勇敢, 聪明"}},
            {"e": {"name": "李四", "traits": "狡诈, 多疑"}},
        ]
        snap.foreshadowing_planted = [
            {"e": {"name": "龙王身份", "priority": "high", "expectedRevealChapter": 10}},
        ]
        summary = snap.to_summary()
        assert "张三" in summary
        assert "李四" in summary
        assert "龙王身份" in summary
        assert "high" in summary

    def test_to_summary_with_overdue(self):
        snap = KGSnapshot(snapshot_id="s1", book_id="b1", chapter=12)
        snap.foreshadowing_overdue = [
            {"e": {"name": "遗失的玉佩", "expectedRevealChapter": 8}},
        ]
        snap.foreshadowing_planted = [
            {"e": {"name": "暗杀计划", "priority": "medium", "expectedRevealChapter": 15}},
        ]
        summary = snap.to_summary()
        assert "逾期" in summary
        assert "遗失的玉佩" in summary

    def test_to_context_dict(self):
        snap = KGSnapshot(snapshot_id="s1", book_id="b1", chapter=3)
        snap.characters = [{"e": {"name": "A"}}]
        snap.entity_count = 1
        ctx = snap.to_context_dict()
        assert ctx["snapshot_id"] == "s1"
        assert ctx["chapter"] == 3
        assert ctx["character_count"] == 1


class TestSnapshotManager:
    """快照管理器"""

    @pytest.fixture
    def temp_dir(self, monkeypatch):
        tmp = tempfile.mkdtemp()
        from kunlun.config import settings

        monkeypatch.setattr(settings, "DATA_DIR", Path(tmp))
        mgr = SnapshotManager()
        yield mgr
        shutil.rmtree(tmp)

    def test_create_snapshot(self, temp_dir):
        snap = temp_dir.create_snapshot("test_book", 1)
        assert snap is not None
        assert snap.book_id == "test_book"
        assert snap.chapter == 1
        assert len(snap.snapshot_id) > 0

    def test_get_latest(self, temp_dir):
        _ = temp_dir.create_snapshot("test_book", 1)
        _ = temp_dir.create_snapshot("test_book", 2)
        latest = temp_dir.get_latest("test_book")
        assert latest is not None
        assert latest.chapter == 2

    def test_get_snapshot_by_id(self, temp_dir):
        snap = temp_dir.create_snapshot("test_book", 3)
        retrieved = temp_dir.get_snapshot(snap.snapshot_id)
        assert retrieved is not None
        assert retrieved.snapshot_id == snap.snapshot_id
        assert retrieved.chapter == 3

    def test_get_nonexistent(self, temp_dir):
        assert temp_dir.get_snapshot("nonexistent") is None
        assert temp_dir.get_latest("no_book") is None

    def test_multiple_books(self, temp_dir):
        temp_dir.create_snapshot("book_a", 1)
        temp_dir.create_snapshot("book_b", 5)
        latest_a = temp_dir.get_latest("book_a")
        latest_b = temp_dir.get_latest("book_b")
        assert latest_a.chapter == 1
        assert latest_b.chapter == 5

    def test_persistence(self, temp_dir):
        snap = temp_dir.create_snapshot("persist_test", 10)
        # 创建新 manager 模拟重启
        mgr2 = SnapshotManager()
        retrieved = mgr2.get_snapshot(snap.snapshot_id)
        assert retrieved is not None
        assert retrieved.book_id == "persist_test"
        assert retrieved.chapter == 10

"""质量趋势追踪器测试"""

import pytest

from kunlun.quality.tracker import QualityTracker

pytestmark = pytest.mark.integration


class TestQualityTracker:
    def setup_method(self):
        import uuid

        self.tracker = QualityTracker(f"test_{uuid.uuid4().hex[:8]}")

    def test_record(self):
        m = self.tracker.record(1, overall_score=0.85, ai_score=0.9)
        assert m.chapter == 1
        assert m.overall_score == 0.85

    def test_get(self):
        self.tracker.record(1, overall_score=0.8)
        m = self.tracker.get(1)
        assert m is not None
        assert m.overall_score == 0.8

    def test_get_latest(self):
        self.tracker.record(1, overall_score=0.7)
        self.tracker.record(2, overall_score=0.9)
        latest = self.tracker.get_latest()
        assert latest.chapter == 2
        assert latest.overall_score == 0.9

    def test_get_all(self):
        self.tracker.record(2, overall_score=0.7)
        self.tracker.record(1, overall_score=0.8)
        all_m = self.tracker.get_all()
        assert len(all_m) == 2
        assert all_m[0].chapter == 1  # 按章节排序

    def test_trend_insufficient(self):
        trend = self.tracker.get_trend()
        assert trend.direction == "insufficient_data"

    def test_trend_improving(self):
        self.tracker.record(1, overall_score=0.5)
        self.tracker.record(2, overall_score=0.7)
        self.tracker.record(3, overall_score=0.9)
        trend = self.tracker.get_trend()
        assert trend.direction in ("improving", "stable")

    def test_trend_declining(self):
        self.tracker.record(1, overall_score=0.9)
        self.tracker.record(2, overall_score=0.7)
        self.tracker.record(3, overall_score=0.5)
        trend = self.tracker.get_trend()
        assert trend.direction in ("declining", "stable")

    def test_get_summary(self):
        self.tracker.record(1, overall_score=0.8, ai_score=0.9, word_count=2000)
        self.tracker.record(2, overall_score=0.7, ai_score=0.8, word_count=2500)
        summary = self.tracker.get_summary()
        assert summary["total_chapters"] == 2
        assert summary["latest_chapter"] == 2
        assert len(summary["chapters"]) == 2

    def test_persistence(self):
        """跨实例持久化"""
        t1 = QualityTracker("persist_test")
        t1.record(1, overall_score=0.85)
        t1.record(2, overall_score=0.90)

        t2 = QualityTracker("persist_test")
        assert t2.get(1).overall_score == 0.85
        assert t2.get(2).overall_score == 0.90
        assert t2.get_latest().chapter == 2

    def test_traffic_rating_tracking(self):
        self.tracker.record(1, overall_score=0.8, traffic_rating="A")
        self.tracker.record(2, overall_score=0.7, traffic_rating="B")
        summary = self.tracker.get_summary()
        ratings = [c["traffic_rating"] for c in summary["chapters"]]
        assert "A" in ratings
        assert "B" in ratings

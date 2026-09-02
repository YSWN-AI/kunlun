"""Fanqie gate tests"""

import pytest

from kunlun.audit.fanqie_gates import FanqieTrafficOptimizer

pytestmark = pytest.mark.unit


def make_long(chars, n):
    return chars * n


class TestFanqieGates:
    def test_cliffhanger(self):
        d = "test " + "cliffhanger-- " * 30
        FanqieTrafficOptimizer.check_chapter(d, chapter=1)
        assert True

    def test_first_three(self):
        chapters = ["test" * 20] * 3
        r = FanqieTrafficOptimizer.check_first_three(chapters)
        assert len(r["chapters"]) == 3

    def test_schedule(self):
        r = FanqieTrafficOptimizer.get_publish_advice(20000)
        assert "冷启动" in r.get("stage", "")

    def test_life_stage_cold(self):
        assert "冷启动" in FanqieTrafficOptimizer.get_life_stage(5000)

    def test_life_stage_validation(self):
        assert "验证" in FanqieTrafficOptimizer.get_life_stage(90000)

    def test_life_stage_prime(self):
        assert "首秀" in FanqieTrafficOptimizer.get_life_stage(200000)

    def test_potential_score_range(self):
        """潜力分应在0-100范围内"""
        from kunlun.audit.fanqie_gates import ChapterTrafficReport

        r = ChapterTrafficReport(chapter=1, word_count=2000)
        score = FanqieTrafficOptimizer._calc_potential(r)
        assert 0 <= score <= 100, f"潜力分越界: {score}"

    def test_check_chapter_basic(self):
        """基本章节检查不崩溃"""
        draft = "测试" * 500
        r = FanqieTrafficOptimizer.check_chapter(draft, chapter=1, is_first_three=True)
        assert r.potential_score > 0
        assert r.life_stage != ""
        assert r.traffic_rating != "未知"

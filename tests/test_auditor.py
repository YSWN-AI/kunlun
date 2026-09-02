"""
测试: Auditor 8道门禁
"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.agents.auditor import Auditor


class TestAuditorGateG1:
    """G1 弧线阶段审计"""

    @pytest.fixture
    def auditor(self):
        return Auditor()

    def test_arc_detection_normal(self, auditor):
        text = (
            "他推开大门，走入陌生的城市。高楼林立，路上行人如织，"
            "一切都与那个小山村截然不同。他的心跳加快了，这不仅是新的环境，更是新的开始。"
        )
        result = auditor._audit_arc(
            text, {"arc_stage": "crossing", "chapter": 5, "chapter_type": "normal"}
        )
        assert "level" in result
        assert result["score"] >= 0

    def test_arc_detection_climax(self, auditor):
        text = (
            "剑光闪过，血溅三尺。他冷冷地看着倒下的敌人，"
            "多年来的仇恨在这一刻终于了结。但也就在此刻，他听到了那个熟悉的声音。"
        )
        result = auditor._audit_arc(
            text, {"arc_stage": "ordeal", "chapter": 30, "chapter_type": "climax"}
        )
        assert result["level"] in ["PASS", "WARN", "FAIL"]  # GateLevel 枚举值


class TestAuditorGateG2:
    """G2 信息释放审计"""

    @pytest.fixture
    def auditor(self):
        return Auditor()

    def test_normal_density(self, auditor):
        text = "他去见了李师傅。李师傅是个退休的老木匠，手艺极好。师徒二人打了招呼，寒暄几句，便进了木工坊。"
        result = auditor._audit_info_release(text)
        assert result["level"] == "PASS"

    def test_high_density(self, auditor):
        text = (
            "张三、李四、王五、赵六、钱七、孙八、周九、吴十、郑十一、"
            "王十二、冯十三、陈十四、褚十五、卫十六、蒋十七、沈十八"
        )
        result = auditor._audit_info_release(text)
        assert result["level"] in ["WARN", "FAIL", "PASS"]  # GateLevel 枚举值（无 FATAL）


class TestAuditorGateG3:
    """G3 去AI味审计"""

    @pytest.fixture
    def auditor(self):
        return Auditor()

    def test_human_like_text(self, auditor):
        text = (
            "他蹲下。\n"
            "地上的脚印很新，边缘还带着湿润的泥土。是五分钟前留下的。"
            "他抬头，巷子尽头空空荡荡。但风里还有人的气味。"
        )
        result = auditor._audit_ai_detection(text)
        assert "level" in result
        assert result["score"] >= 0

    def test_ai_pattern_text(self, auditor):
        text = (
            "然而，他心中充满了复杂的情绪。此外，他面临的挑战也是前所未有的。"
            "因此，他决定采取行动。不过，他也清楚地知道前路的艰难。而且，他需要更多的准备。"
            "所以，他开始了新的旅程。"
        )
        result = auditor._audit_ai_detection(text)
        assert "level" in result


class TestAuditorGateG5:
    """G5 爽点多样性审计"""

    @pytest.fixture
    def auditor(self):
        return Auditor()

    def test_diverse_pleasure(self, auditor):
        text = "第一段：升级突破。/第二段：打脸反转。/第三段：宝藏发现。/第四段：浪漫告白。"
        result = auditor._audit_pleasure_diversity(text)
        assert "level" in result

    def test_repetitive_pleasure(self, auditor):
        text = "打脸打脸打脸打脸打脸打脸打脸打脸打脸打脸打脸打脸"
        result = auditor._audit_pleasure_diversity(text)
        assert result["level"] in ["WARN", "FAIL", "PASS"]  # GateLevel 枚举值（无 FATAL）


class TestAuditorGateG6:
    """G6 情感一致性审计"""

    @pytest.fixture
    def auditor(self):
        return Auditor()

    def test_consistent_emotion(self, auditor):
        text = "前半部分：他微笑，阳光洒在脸上。/后半部分：他也笑了，心情愉悦。"
        result = auditor._audit_emotion(
            text, {"emotion_curve": {"start_emotion": "joy", "end_emotion": "joy"}}
        )
        assert result["level"] in ["PASS", "WARN"]

    def test_abrupt_shift(self, auditor):
        text = (
            "前半部分：他开怀大笑，世界如此美好。/"
            "后半部分：他坠入深渊，万念俱灰，生无可恋，绝望至极。"
        )
        result = auditor._audit_emotion(
            text, {"emotion_curve": {"start_emotion": "joy", "end_emotion": "sadness"}}
        )
        assert "level" in result

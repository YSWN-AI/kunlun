"""
测试蝴蝶效应检测器 (Ripple Detector)
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration

from kunlun.ripple.detector import (
    RippleDetector,
    RippleImpact,
    RippleReport,
    ripple_detector,
)


class TestRippleDetector:
    def test_init(self):
        detector = RippleDetector()
        assert detector is not None

    def test_detect_with_no_kg(self):
        detector = RippleDetector()
        report = detector.detect("char_001", "角色等级从筑基提升到元婴")
        assert isinstance(report, RippleReport)
        assert report.changed_entity_uid == "char_001"
        assert report.change_description == "角色等级从筑基提升到元婴"
        assert report.total_affected == 0

    @patch("kunlun.ripple.detector.kg_client")
    def test_detect_with_related_entities(self, mock_kg):
        mock_kg.query_cypher.side_effect = [
            [{"type": "Character", "name": "张三"}],
            [
                {"uid": "loc_001", "type": "Location", "name": "青云山", "relation": "LOCATED_AT"},
                {"uid": "item_001", "type": "Item", "name": "青玄剑", "relation": "POSSESSES"},
            ],
        ]
        detector = RippleDetector()
        report = detector.detect("char_001", "角色改名")
        assert report.changed_entity_type == "Character"
        assert report.total_affected == 2
        assert len(report.impacts) == 2

    @patch("kunlun.ripple.detector.kg_client")
    def test_generate_markdown_report(self, mock_kg):
        mock_kg.query_cypher.side_effect = [
            [{"type": "Character", "name": "主角"}],
            [
                {
                    "uid": "org_001",
                    "type": "Organization",
                    "name": "青云宗",
                    "relation": "MEMBER_OF",
                },
            ],
        ]
        detector = RippleDetector()
        report = detector.detect("char_001", "离开宗门")
        md = detector.generate_markdown_report(report)
        assert "蝴蝶效应检测报告" in md
        assert "char_001" in md
        assert "青云宗" in md


class TestRippleImpact:
    def test_ripple_impact_fields(self):
        impact = RippleImpact(
            entity_uid="loc_001",
            entity_type="Location",
            entity_name="青云山",
            impact_description="位置信息需要同步更新",
            severity="LOW",
            suggestion="请检查青云山",
        )
        assert impact.severity == "LOW"
        assert impact.entity_type == "Location"

    def test_ripple_impact_defaults(self):
        impact = RippleImpact(
            entity_uid="e1",
            entity_type="Character",
            entity_name="测试",
            impact_description="测试影响",
            severity="MEDIUM",
        )
        assert impact.suggestion == ""


class TestRippleReport:
    def test_ripple_report_defaults(self):
        report = RippleReport(
            changed_entity_uid="e1",
            changed_entity_type="Character",
            change_description="测试变更",
        )
        assert report.impacts == []
        assert report.total_affected == 0

    def test_ripple_report_with_impacts(self):
        impact = RippleImpact(
            entity_uid="e2",
            entity_type="Location",
            entity_name="测试地",
            impact_description="测试",
            severity="HIGH",
        )
        report = RippleReport(
            changed_entity_uid="e1",
            changed_entity_type="Character",
            change_description="变更",
            impacts=[impact],
            total_affected=1,
        )
        assert len(report.impacts) == 1


class TestSingleton:
    def test_ripple_detector_singleton_exists(self):
        assert ripple_detector is not None
        assert isinstance(ripple_detector, RippleDetector)

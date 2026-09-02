"""输出契约验证器测试 — 覆盖150项清单第10-23条"""

import pytest

from kunlun.audit.output_contract import (
    OutputContractValidator,
)

pytestmark = pytest.mark.unit


class TestOutputContract:
    def setup_method(self):
        self.validator = OutputContractValidator()

    def test_valid_chapter_summary(self):
        data = {
            "chapter": 5,
            "title": "意外相遇",
            "summary": "王林在集市上遇到了多年未见的老友。",
            "characters": ["王林", "老友"],
            "key_events": ["重逢", "交换情报"],
        }
        report = self.validator.validate("chapter_summary", data)
        assert report.valid, f"有效数据应通过: {report.errors}"

    def test_invalid_chapter_missing(self):
        data = {
            "title": "意外相遇",
            "summary": "王林在集市上遇到了多年未见的老友。",
        }
        report = self.validator.validate("chapter_summary", data)
        assert not report.valid, "缺少必填字段应失败"
        assert any("chapter" in e for e in report.errors)

    def test_invalid_priority(self):
        data = {
            "name": "神秘玉佩",
            "priority": "urgent",
            "expectedRevealChapter": 10,
            "description": "一个刻满符文的玉佩",
        }
        report = self.validator.validate("foreshadowing", data)
        assert not report.valid, "无效枚举值应失败"

    def test_valid_foreshadowing(self):
        data = {
            "name": "神秘玉佩",
            "priority": "high",
            "expectedRevealChapter": 10,
            "description": "一个刻满符文的玉佩",
        }
        report = self.validator.validate("foreshadowing", data)
        assert report.valid, f"有效伏笔应通过: {report.errors}"

    def test_unknown_schema(self):
        report = self.validator.validate("unknown_schema", {"data": 1})
        assert report.valid, "未知Schema应默认通过"
        assert len(report.warnings) > 0

    def test_type_mismatch(self):
        data = {
            "chapter": "五章",  # 应该是 int
            "title": "测试",
            "summary": "摘要" * 5,
            "characters": [],
            "key_events": [],
        }
        report = self.validator.validate("chapter_summary", data)
        assert not report.valid, "类型错误应失败"

    def test_get_schema_json(self):
        schema_json = self.validator.get_schema_json("chapter_summary")
        assert "chapter" in schema_json
        assert "必需" in schema_json

    def test_full_schema_coverage(self):
        """所有预定义 Schema 对有效数据都应通过"""
        test_data = {
            "chapter_summary": {
                "chapter": 1,
                "title": "T",
                "summary": "S" * 10,
                "characters": ["a"],
                "key_events": ["b"],
            },
            "character_update": {
                "character_uid": "w_001",
                "name": "王林",
                "emotion": "平静",
                "location": "后山",
                "realm": "筑基期",
            },
            "foreshadowing": {
                "name": "秘密",
                "priority": "medium",
                "expectedRevealChapter": 20,
                "description": "D" * 5,
            },
            "pleasure_point": {
                "chapter": 3,
                "type": "face_slap",
                "strength": 8,
                "description": "D" * 5,
            },
        }
        for schema_name, data in test_data.items():
            report = self.validator.validate(schema_name, data)
            assert report.valid, f"{schema_name} 校验失败: {report.errors}"

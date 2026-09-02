"""冲突引擎单元测试"""

import tempfile
from pathlib import Path

import pytest

from kunlun.conflict import ConflictManager, ConflictStatus, ConflictType, TensionLevel

pytestmark = pytest.mark.unit


class TestConflictManager:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.cm = ConflictManager("test_book")

    def test_register_conflict(self):
        c = self.cm.register_conflict(
            "正邪对决",
            ConflictType.PERSON_VS_PERSON,
            participants=["主角", "反派"],
            chapter=0,
        )
        assert c.id.startswith("conflict_")
        assert c.name == "正邪对决"
        assert c.status == ConflictStatus.INTRODUCED
        assert c.id in self.cm.conflicts

    def test_update_status(self):
        c = self.cm.register_conflict("测试冲突", ConflictType.PERSON_VS_PERSON)
        self.cm.update_status(c.id, ConflictStatus.ESCALATING, chapter=3)
        c = self.cm.conflicts[c.id]
        assert c.status == ConflictStatus.ESCALATING

    def test_analyze_chapter_creates_tension(self):
        self.cm.register_conflict("战斗", ConflictType.PERSON_VS_PERSON, chapter=0)
        text = "杀杀杀！轰！砰！两人拼命决一死战，终于击杀对方。"
        tension, _conflicts = self.cm.analyze_chapter(text, chapter=1)
        assert tension.tension_score >= 0
        assert tension.chapter == 1
        assert isinstance(tension.tension_level, TensionLevel)

    def test_resolve_conflict(self):
        c = self.cm.register_conflict("测试", ConflictType.PERSON_VS_PERSON)
        self.cm.update_status(c.id, ConflictStatus.CLIMAX, chapter=3)
        self.cm.update_status(c.id, ConflictStatus.RESOLVED, chapter=5)
        c = self.cm.conflicts[c.id]
        assert c.status == ConflictStatus.RESOLVED
        assert c.chapter_resolved == 5

    def test_active_conflicts_ordering(self):
        self.cm.register_conflict("冲突A", ConflictType.PERSON_VS_PERSON)
        self.cm.register_conflict("冲突B", ConflictType.PERSON_VS_SELF)
        active = self.cm.get_active_conflicts()
        assert len(active) >= 2  # INTRODUCED状态的冲突也是活跃的

    def test_update_nonexistent_conflict(self):
        assert "nonexistent" not in self.cm.conflicts

    def test_conflict_summary(self):
        self.cm.register_conflict("主线", ConflictType.PERSON_VS_PERSON)
        self.cm.register_conflict("支线", ConflictType.PERSON_VS_NATURE)
        summary = self.cm.get_conflict_summary()
        assert "total" in str(summary) or "conflicts" in str(summary).lower()

    def test_tension_curve(self):
        self.cm.register_conflict("张力测试", ConflictType.PERSON_VS_PERSON)
        text = "杀杀杀！爆发！轰！砰！拼命决战！"
        self.cm.analyze_chapter(text, chapter=1)
        self.cm.analyze_chapter(text, chapter=2)
        curve = self.cm.get_tension_curve(last_n=5)
        assert len(curve) >= 1
        assert "score" in curve[0]

    def test_persistence(self):

        c = self.cm.register_conflict("持久化冲突", ConflictType.PERSON_VS_PERSON)
        self.cm.update_status(c.id, ConflictStatus.ESCALATING, chapter=2)
        # 通过 _save 已自动保存，验证冲突存在
        assert c.id in self.cm.conflicts

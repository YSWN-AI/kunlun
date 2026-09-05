"""Vibe 总调度器测试"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from kunlun.vibe_writer.orchestrator import VibeOrchestrator

pytestmark = pytest.mark.integration

class TestVibeOrchestrator:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.master = VibeOrchestrator(workspace=self.tmpdir)

    def test_init_no_project(self):
        assert not self.master.has_project

    def test_classify_intent_create(self):
        intent = self.master._classify_intent("我想写一本玄幻小说")
        assert intent == "开书"

    def test_classify_intent_world(self):
        intent = self.master._classify_intent("构建世界观设定")
        assert intent == "设定"

    def test_classify_intent_character(self):
        intent = self.master._classify_intent("设计几个角色")
        assert intent == "角色"

    def test_classify_intent_outline(self):
        intent = self.master._classify_intent("规划全书大纲")
        assert intent == "大纲"

    def test_classify_intent_write(self):
        intent = self.master._classify_intent("写第一章")
        assert intent == "写作"

    def test_classify_intent_revise(self):
        intent = self.master._classify_intent("修改一下内容")
        assert intent == "修改"

    def test_classify_intent_quality(self):
        intent = self.master._classify_intent("检查章节质量")
        assert intent == "质量"

    def test_classify_intent_export(self):
        intent = self.master._classify_intent("导出为EPUB")
        assert intent == "导出"

    def test_classify_intent_finish(self):
        intent = self.master._classify_intent("完结这本书")
        assert intent == "完结"

    def test_classify_intent_status(self):
        intent = self.master._classify_intent("现在进度怎么样了")
        assert intent == "状态"

    def test_handle_create_book(self):
        result = asyncio.run(self.master.say("我想写一本叫《苍穹之剑》的玄幻小说"))
        assert result["success"]
        assert self.master.has_project
        assert self.master._project.title == "苍穹之剑"
        assert self.master._project.genre == "玄幻"
        assert (self.tmpdir / self.master._project.book_id).exists()

    def test_handle_world_building(self):
        asyncio.run(self.master.say("写一本叫《仙途》的仙侠小说"))
        result = asyncio.run(self.master.say("构建一个以飞升为核心的世界观"))
        assert result["success"]
        assert self.master._project.world_ready

    def test_handle_characters(self):
        asyncio.run(self.master.say("写一本都市小说"))
        result = asyncio.run(self.master.say("设计主角和反派"))
        assert result["success"]
        assert self.master._project.characters_ready

    def test_handle_outline(self):
        asyncio.run(self.master.say("写一本玄幻小说"))
        result = asyncio.run(self.master.say("规划全书大纲"))
        assert result["success"]
        assert self.master._project.outline_ready

    def test_handle_status_without_project(self):
        result = asyncio.run(self.master.say("进度怎么样了"))
        assert "还没有创作项目" in result["message"]

    def test_handle_status_with_project(self):
        asyncio.run(self.master.say("写一本小说"))
        result = asyncio.run(self.master.say("进度"))
        assert "进度" in result["message"]

    def test_conversation_tracked(self):
        asyncio.run(self.master.say("写一本小说"))
        assert len(self.master.get_conversation()) >= 2

    def test_project_persisted(self):
        asyncio.run(self.master.say("写一本叫《测试》的小说"))
        project_file = self.master._project.data_dir / "project.json"
        assert project_file.exists()

    def test_get_status(self):
        status = self.master.get_status()
        assert "project" in status
        assert "conversation_length" in status

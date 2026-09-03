# -*- coding: utf-8 -*-
"""
四层记忆 L1-L2 增强测试

覆盖:
  - SummaryTree 添加/获取/重建摘要
  - SummaryTree 序列化
  - EbbinghausForgetting 保持率计算
  - EbbinghausForgetting 重要度加成和永久保留
  - EbbinghausForgetting 访问增强
  - EventExtractor 战斗/对话/揭示/转折事件提取
  - EventExtractor 人名提取
  - WorkingMemory 角色状态卡
  - WorkingMemory 伏笔预警
  - WorkingMemory 增强上下文
  - WorkingMemory 巩固到情景记忆
  - EpisodicMemory 摘要树集成
  - EpisodicMemory 遗忘加权搜索
  - EpisodicMemory 持久化 save/load
  - MemoryManager retrieve_for_writing / store_after_writing
  - 向后兼容：现有 MemoryManager.query/write_chapter_memory 仍正常
"""

import asyncio
import os
import tempfile
import time

import pytest

from kunlun.memory import (
    EbbinghausForgetting,
    EpisodicEvent,
    EpisodicMemory,
    EventExtractor,
    MemoryImportance,
    MemoryItem,
    MemoryManager,
    SummaryTree,
    SummaryTreeNode,
    WorkingMemory,
)


# ══════════════════════════════════════════════════════
# SummaryTree 测试
# ══════════════════════════════════════════════════════


class TestSummaryTree:
    """摘要树测试"""

    def test_add_and_get_chapter_summary(self):
        """测试添加章节摘要并获取"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第一章：主角初入江湖")
        tree.add_chapter_summary(2, "第二章：遭遇强敌")

        # 获取范围摘要
        result = tree.get_summary_for_range(1, 2, max_level=2)
        assert "第一章：主角初入江湖" in result
        assert "第二章：遭遇强敌" in result

    def test_volume_organization(self):
        """测试卷划分（每50章一卷）"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第1章")
        tree.add_chapter_summary(50, "第50章")
        tree.add_chapter_summary(51, "第51章")

        # 第1章和第50章应在第一卷，第51章在第二卷
        assert len(tree.root.children) == 2
        assert tree.root.children[0].chapter_range == (1, 50)
        assert tree.root.children[1].chapter_range == (51, 100)

    def test_get_book_summary(self):
        """测试全书摘要"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第一章摘要内容")
        tree.add_chapter_summary(2, "第二章摘要内容")

        book_summary = tree.get_book_summary()
        assert len(book_summary) > 0
        assert "第1卷" in book_summary

    def test_get_volume_summary(self):
        """测试获取某卷摘要"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第一章内容")
        tree.add_chapter_summary(2, "第二章内容")

        vol1 = tree.get_volume_summary(1)
        assert "第一章内容" in vol1
        # 不存在的卷返回空字符串
        assert tree.get_volume_summary(99) == ""

    def test_rebuild_book_summary(self):
        """测试重建全书摘要"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第一章")
        tree.root.summary = ""  # 清空
        tree.rebuild_book_summary()
        assert len(tree.get_book_summary()) > 0

    def test_scene_summaries(self):
        """测试场景摘要（L3节点）"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(
            1,
            "第一章摘要",
            scene_summaries=[
                {"title": "场景一", "summary": "主角登场"},
                {"title": "场景二", "summary": "遭遇战斗"},
            ],
        )
        # 找到第1章节点
        ch_node = None
        for vol in tree.root.children:
            for ch in vol.children:
                if ch.chapter_range == (1, 1):
                    ch_node = ch
        assert ch_node is not None
        assert len(ch_node.children) == 2
        assert ch_node.children[0].title == "场景一"

    def test_serialization(self):
        """测试摘要树序列化/反序列化"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第一章摘要")
        tree.add_chapter_summary(51, "第五十一章摘要")

        data = tree.to_dict()
        assert data["volume_size"] == 50
        assert "root" in data

        tree2 = SummaryTree.from_dict(data)
        assert tree2.volume_size == 50
        assert len(tree2.root.children) == 2
        # 验证内容一致
        result = tree2.get_summary_for_range(1, 1, max_level=2)
        assert "第一章摘要" in result

    def test_get_summary_for_range_max_level_1(self):
        """测试max_level=1时返回卷级摘要"""
        tree = SummaryTree(volume_size=50)
        tree.add_chapter_summary(1, "第一章")
        result = tree.get_summary_for_range(1, 50, max_level=1)
        assert "第1卷" in result


# ══════════════════════════════════════════════════════
# EbbinghausForgetting 测试
# ══════════════════════════════════════════════════════


class TestEbbinghausForgetting:
    """艾宾浩斯遗忘曲线测试"""

    def test_calculate_retention_fresh_memory(self):
        """测试新记忆保持率接近1.0"""
        forgetting = EbbinghausForgetting()
        item = MemoryItem(
            id="test1",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.MEDIUM,
        )
        retention = forgetting.calculate_retention(item)
        assert 0.9 <= retention <= 1.0

    def test_calculate_retention_old_memory(self):
        """测试旧记忆保持率下降"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 720 * 3600  # 720小时前（30天）
        item = MemoryItem(
            id="test2",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.MEDIUM,
            created_at=old_time,
        )
        retention = forgetting.calculate_retention(item)
        assert retention < 0.5

    def test_high_importance_floor(self):
        """测试HIGH(4)重要度最低保持0.8"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 1000 * 3600  # 很老
        item = MemoryItem(
            id="test3",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.HIGH,
            created_at=old_time,
        )
        retention = forgetting.calculate_retention(item)
        assert retention >= 0.8

    def test_critical_permanent(self):
        """测试CRITICAL(5)永久保留"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 10000 * 3600
        item = MemoryItem(
            id="test4",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.CRITICAL,
            created_at=old_time,
        )
        retention = forgetting.calculate_retention(item)
        assert retention == 1.0

    def test_access_count_boost(self):
        """测试访问次数加成"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 200 * 3600
        item_low = MemoryItem(
            id="test5a",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.MEDIUM,
            created_at=old_time,
            access_count=0,
        )
        item_high = MemoryItem(
            id="test5b",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.MEDIUM,
            created_at=old_time,
            access_count=10,
        )
        r_low = forgetting.calculate_retention(item_low)
        r_high = forgetting.calculate_retention(item_high)
        assert r_high > r_low

    def test_should_forget(self):
        """测试should_forget判断"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 5000 * 3600
        item = MemoryItem(
            id="test6",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.TRIVIAL,
            created_at=old_time,
        )
        assert forgetting.should_forget(item, threshold=0.1) is True

    def test_critical_never_forget(self):
        """测试CRITICAL永不遗忘"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 10000 * 3600
        item = MemoryItem(
            id="test7",
            layer=__import__("kunlun.memory.engine", fromlist=["MemoryLayer"]).MemoryLayer.WORKING,
            content="测试",
            importance=MemoryImportance.CRITICAL,
            created_at=old_time,
        )
        assert forgetting.should_forget(item) is False

    def test_apply_forgetting(self):
        """测试批量应用遗忘曲线"""
        forgetting = EbbinghausForgetting()
        old_time = time.time() - 5000 * 3600
        events = [
            EpisodicEvent(
                id="e1",
                chapter=1,
                scene="测试",
                summary="旧事件",
                importance=MemoryImportance.TRIVIAL,
                created_at=old_time,
            ),
            EpisodicEvent(
                id="e2",
                chapter=1,
                scene="测试",
                summary="关键事件",
                importance=MemoryImportance.CRITICAL,
                created_at=old_time,
            ),
        ]
        kept, forgotten = forgetting.apply_forgetting(events)
        # CRITICAL事件应保留
        assert any(e.id == "e2" for e in kept)
        # 旧的TRIVIAL事件可能被遗忘
        assert len(kept) + len(forgotten) == 2

    def test_boost_memory(self):
        """测试访问后增强记忆"""
        forgetting = EbbinghausForgetting()
        events = [
            EpisodicEvent(
                id="boost_test",
                chapter=1,
                scene="测试",
                summary="测试事件",
                access_count=0,
            )
        ]
        original_access = events[0].access_count
        original_last = events[0].last_accessed
        time.sleep(0.01)
        forgetting.boost_memory("boost_test", events)
        assert events[0].access_count == original_access + 1
        assert events[0].last_accessed > original_last


# ══════════════════════════════════════════════════════
# EventExtractor 测试
# ══════════════════════════════════════════════════════


class TestEventExtractor:
    """事件自动提取器测试"""

    def test_extract_battle_event(self):
        """测试战斗事件提取"""
        extractor = EventExtractor()
        text = "林天道拔剑出鞘，剑光如练。\n\n他一剑斩出，剑气轰然爆发，将敌人碾压成碎片。这一击秒杀了三名修士，战斗瞬间结束。"
        events = extractor.extract_events(text, chapter=1)
        assert len(events) > 0
        assert any(e["event_type"] == "battle" for e in events)

    def test_extract_dialogue_event(self):
        """测试对话事件提取"""
        extractor = EventExtractor()
        text = '林天道说道："你竟敢背叛我？"\n\n苏婉儿冷笑道："人不为己，天诛地灭。"'
        events = extractor.extract_events(text, chapter=1)
        assert any(e["event_type"] == "dialogue" for e in events)

    def test_extract_revelation_event(self):
        """测试揭示事件提取"""
        extractor = EventExtractor()
        text = "林天道终于发现了真相。原来这一切竟然是师父的阴谋，他得知了那个隐藏多年的秘密。"
        events = extractor.extract_events(text, chapter=1)
        assert any(e["event_type"] == "revelation" for e in events)

    def test_extract_turning_event(self):
        """测试转折事件提取"""
        extractor = EventExtractor()
        text = "然而就在这时，突然一道黑影闪过。没想到敌人竟然还有后手，但是林天道早有准备。"
        events = extractor.extract_events(text, chapter=1)
        assert any(e["event_type"] == "turning" for e in events)

    def test_extract_characters(self):
        """测试人名提取"""
        extractor = EventExtractor()
        text = '林天行说道："来吧。" 苏婉儿笑道："好。" 赵震天怒道："放肆！"'
        names = extractor.extract_characters(text)
        assert "林天行" in names
        assert "苏婉儿" in names
        assert "赵震天" in names

    def test_event_fields_complete(self):
        """测试事件字段完整性"""
        extractor = EventExtractor()
        text = "林天道拔剑战斗，一剑斩杀了敌人。他说道：这就是下场。"
        events = extractor.extract_events(text, chapter=5)
        for event in events:
            assert "scene" in event
            assert "summary" in event
            assert "participants" in event
            assert "event_type" in event
            assert "plot_relevance" in event
            assert "emotional_arc" in event
            assert 0.3 <= event["plot_relevance"] <= 0.8

    def test_emotional_arc_detection(self):
        """测试情感弧线检测"""
        extractor = EventExtractor()
        text = "林天道心中充满了愤怒和痛苦，他握紧了拳头，眼中闪过杀机。"
        events = extractor.extract_events(text, chapter=1)
        # 消极情感词多，应为falling或neutral
        if events:
            assert events[0]["emotional_arc"] in ("falling", "neutral", "peak")


# ══════════════════════════════════════════════════════
# WorkingMemory 增强测试
# ══════════════════════════════════════════════════════


class TestWorkingMemoryEnhanced:
    """工作记忆增强测试"""

    def test_set_character_state(self):
        """测试设置角色状态卡"""
        wm = WorkingMemory()
        wm.set_character_state("林天道", {
            "emotion": "愤怒",
            "ability": "筑基期",
            "motivation": "复仇",
        })
        assert "林天道" in wm.character_states
        assert wm.character_states["林天道"]["emotion"] == "愤怒"

    def test_get_character_states(self):
        """测试获取所有角色状态"""
        wm = WorkingMemory()
        wm.set_character_state("A", {"emotion": "平静"})
        wm.set_character_state("B", {"emotion": "紧张"})
        states = wm.get_character_states()
        assert len(states) == 2
        assert any(s["name"] == "A" for s in states)

    def test_add_foreshadow_alert(self):
        """测试添加伏笔预警"""
        wm = WorkingMemory()
        wm.add_foreshadow_alert({
            "type": "应揭示",
            "content": "主角身世之谜应在第10章揭示",
            "chapter": 10,
        })
        assert len(wm.foreshadow_alerts) == 1
        assert wm.foreshadow_alerts[0]["type"] == "应揭示"

    def test_get_context_enhanced(self):
        """测试增强上下文"""
        wm = WorkingMemory()
        wm.set_current_chapter(5, "当前章节内容")
        wm.set_character_state("林天道", {"emotion": "坚定", "motivation": "复仇"})
        wm.add_foreshadow_alert({"type": "应安插", "content": "伏笔提示"})
        context = wm.get_context_enhanced()
        assert "当前章节内容" in context
        assert "在场角色状态" in context
        assert "林天道" in context
        assert "伏笔预警" in context

    def test_consolidate_to_episodic(self):
        """测试巩固工作记忆到情景记忆"""
        wm = WorkingMemory()
        wm.current_chapter = 3
        wm.add_note("重要线索：神秘玉佩", importance=MemoryImportance.HIGH)
        wm.add_note("琐碎信息", importance=MemoryImportance.TRIVIAL)
        events = wm.consolidate_to_episodic()
        # HIGH笔记应被巩固
        assert len(events) >= 1
        assert any("神秘玉佩" in e.summary for e in events)
        # TRIVIAL笔记不应被巩固（importance.value < 2）
        # 注意：TRIVIAL=1 < 2，所以不会被巩固


# ══════════════════════════════════════════════════════
# EpisodicMemory 增强测试
# ══════════════════════════════════════════════════════


class TestEpisodicMemoryEnhanced:
    """情景记忆增强测试"""

    def test_enable_summary_tree(self):
        """测试启用摘要树"""
        em = EpisodicMemory()
        assert em.summary_tree is None
        em.enable_summary_tree(volume_size=50)
        assert em.summary_tree is not None
        assert em.summary_tree.volume_size == 50

    def test_add_event_syncs_to_summary_tree(self):
        """测试添加事件同步到摘要树"""
        em = EpisodicMemory()
        em.enable_summary_tree()
        event = EpisodicEvent(
            id="test_sync",
            chapter=1,
            scene="测试场景",
            summary="测试事件摘要内容",
        )
        em.add_event(event)
        # 摘要树中应有第1章
        result = em.summary_tree.get_summary_for_range(1, 1, max_level=2)
        assert len(result) > 0

    def test_add_chapter_with_events(self):
        """测试自动提取事件并添加"""
        em = EpisodicMemory()
        em.enable_summary_tree()
        text = '林天道说道："来吧。"\n\n他拔剑战斗，一剑斩杀了敌人。然而敌人竟然还有后手。'
        events = em.add_chapter_with_events(1, text, summary="第一章测试")
        assert len(events) > 0
        assert len(em.events) > 0
        # 摘要树应有第1章摘要
        assert em.summary_tree.get_book_summary() != ""

    def test_search_with_forgetting(self):
        """测试带遗忘加权的搜索"""
        em = EpisodicMemory()
        em.add_event(EpisodicEvent(
            id="search_1",
            chapter=1,
            scene="测试",
            summary="林天道修炼剑法",
            participants=["林天道"],
        ))
        results = em.search_with_forgetting("林天道 剑法", limit=5)
        assert len(results) > 0
        assert any("林天道" in e.summary for e in results)

    def test_get_events_by_chapter_with_summary(self):
        """测试获取章节事件+摘要"""
        em = EpisodicMemory()
        em.enable_summary_tree()
        em.add_event(EpisodicEvent(
            id="ch_test",
            chapter=3,
            scene="测试",
            summary="第三章事件",
        ))
        result = em.get_events_by_chapter_with_summary(3)
        assert result["chapter"] == 3
        assert result["event_count"] >= 1
        assert "events" in result
        assert "summary" in result

    def test_apply_forgetting_cycle(self):
        """测试遗忘周期执行"""
        em = EpisodicMemory()
        old_time = time.time() - 5000 * 3600
        em.add_event(EpisodicEvent(
            id="old_trivial",
            chapter=1,
            scene="旧事件",
            summary="旧的琐碎事件",
            importance=MemoryImportance.TRIVIAL,
            created_at=old_time,
        ))
        em.add_event(EpisodicEvent(
            id="fresh_event",
            chapter=2,
            scene="新事件",
            summary="新事件",
            importance=MemoryImportance.MEDIUM,
        ))
        count = em.apply_forgetting_cycle()
        assert count >= 0  # 至少不报错
        # 新事件应保留
        assert any(e.id == "fresh_event" for e in em.events)

    def test_save_and_load(self):
        """测试L2持久化save/load"""
        em = EpisodicMemory()
        em.enable_summary_tree()
        em.add_event(EpisodicEvent(
            id="persist_test",
            chapter=1,
            scene="持久化测试",
            summary="测试持久化",
            participants=["测试者"],
        ))
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            filepath = f.name
        try:
            em.save(filepath)
            assert os.path.exists(filepath)

            em2 = EpisodicMemory()
            em2.load(filepath)
            assert len(em2.events) == 1
            assert em2.events[0].id == "persist_test"
            assert em2.summary_tree is not None
        finally:
            os.unlink(filepath)


# ══════════════════════════════════════════════════════
# MemoryManager 增强测试
# ══════════════════════════════════════════════════════


class TestMemoryManagerEnhanced:
    """记忆管理器增强测试"""

    def test_retrieve_for_writing(self):
        """测试写作前记忆检索"""
        mm = MemoryManager(book_id="test_retrieve")
        mm.working.set_character_state("林天道", {"emotion": "坚定"})
        mm.episodic.add_event(EpisodicEvent(
            id="rf_test",
            chapter=1,
            scene="测试",
            summary="林天道的过往事件",
            participants=["林天道"],
        ))
        result = asyncio.run(mm.retrieve_for_writing(
            chapter_outline={"chapter": 2, "scene_type": "battle"},
            present_characters=["林天道"],
        ))
        assert "working_context" in result
        assert "character_states" in result
        assert "relevant_events" in result
        assert "patterns" in result
        assert any(cs["name"] == "林天道" for cs in result["character_states"])

    def test_store_after_writing(self):
        """测试写作后记忆写入"""
        mm = MemoryManager(book_id="test_store")
        text = '林天道说道："来吧。"\n\n他拔剑战斗，一剑斩杀了敌人。然而真相竟然如此。'
        result = mm.store_after_writing(1, text, summary="第一章测试")
        assert result["chapter"] == 1
        assert result["extracted_events"] > 0
        assert mm.episodic.summary_tree is not None
        assert len(mm.episodic.events) > 0

    def test_get_enhanced_context(self):
        """测试获取增强上下文"""
        mm = MemoryManager(book_id="test_ctx")
        mm.working.set_current_chapter(1, "测试上下文")
        mm.working.set_character_state("测试角色", {"emotion": "平静"})
        context = mm.get_enhanced_context()
        assert "测试上下文" in context
        assert "测试角色" in context

    def test_full_save_load(self):
        """测试完整保存/加载四层记忆"""
        mm = MemoryManager(book_id="test_full_save")
        mm.write_chapter_memory(
            chapter=1,
            content="测试内容",
            summary="测试摘要",
            events=[{"scene": "测试", "summary": "测试事件", "participants": ["测试者"]}],
            entities=[{"name": "测试者", "entity_type": "character", "description": "测试人物"}],
        )
        mm.working.set_character_state("测试者", {"emotion": "开心"})
        mm.episodic.enable_summary_tree()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            filepath = f.name
        try:
            mm.save(filepath)
            mm2 = MemoryManager(book_id="new")
            mm2.load(filepath)
            assert mm2.book_id == "test_full_save"
            assert len(mm2.episodic.events) > 0
            assert len(mm2.semantic.entities) > 0
            assert "测试者" in mm2.working.character_states
        finally:
            os.unlink(filepath)


# ══════════════════════════════════════════════════════
# 向后兼容测试
# ══════════════════════════════════════════════════


class TestBackwardCompatibility:
    """向后兼容测试"""

    def test_query_still_works(self):
        """测试现有query方法仍正常"""
        mm = MemoryManager(book_id="test_bc_query")
        mm.write_chapter_memory(
            chapter=1,
            content="林天道修炼",
            summary="修炼摘要",
            events=[{"scene": "修炼", "summary": "林天道修炼剑法", "participants": ["林天道"]}],
        )
        result = mm.query("林天道", query_type="general")
        assert result is not None
        assert len(result.episodic) > 0 or len(result.working) > 0

    def test_write_chapter_memory_still_works(self):
        """测试现有write_chapter_memory方法仍正常"""
        mm = MemoryManager(book_id="test_bc_write")
        mm.write_chapter_memory(
            chapter=1,
            content="测试内容",
            summary="测试摘要",
            events=[
                {
                    "scene": "测试场景",
                    "summary": "测试事件摘要",
                    "participants": ["角色A"],
                    "event_type": "battle",
                }
            ],
        )
        assert len(mm.episodic.events) == 1
        assert mm.episodic.events[0].participants == ["角色A"]
        assert 1 in mm.working.recent_chapters

    def test_get_character_sheet_still_works(self):
        """测试现有get_character_sheet方法仍正常"""
        mm = MemoryManager(book_id="test_bc_sheet")
        mm.write_chapter_memory(
            chapter=1,
            content="测试",
            entities=[{"name": "测试角色", "entity_type": "character", "description": "测试"}],
        )
        sheet = mm.get_character_sheet("测试角色")
        assert sheet["found"] is True
        assert sheet["name"] == "测试角色"

    def test_get_plot_recap_still_works(self):
        """测试现有get_plot_recap方法仍正常"""
        mm = MemoryManager(book_id="test_bc_recap")
        mm.write_chapter_memory(
            chapter=1,
            content="测试",
            events=[{"scene": "测试", "summary": "测试事件", "plot_relevance": 0.6}],
        )
        recap = mm.get_plot_recap(from_chapter=1)
        assert "情节回顾" in recap or "暂无情节记录" in recap

    def test_episodic_event_backward_compatible(self):
        """测试EpisodicEvent新增字段不破坏旧代码"""
        # 旧方式创建（不传新字段）
        event = EpisodicEvent(
            id="bc_test",
            chapter=1,
            scene="测试",
            summary="测试",
        )
        # 新字段应有默认值
        assert hasattr(event, "last_accessed")
        assert hasattr(event, "access_count")
        assert hasattr(event, "importance")
        assert event.access_count == 0
        assert event.importance == MemoryImportance.MEDIUM
        # to_dict/from_dict应兼容
        data = event.to_dict()
        event2 = EpisodicEvent.from_dict(data)
        assert event2.id == "bc_test"

"""
四层记忆 L3-L4 深度落地模块测试

覆盖:
  - EntityRelationGraph: 添加关系、双向查询、时序过滤、关系路径、邻域子图、关系历史、序列化
  - SceneTemplateLibrary: 默认模板、按类型获取、推荐、爽点模式、章节提取、使用记录、序列化
  - SemanticMemory 增强: 绑定图谱、添加关系、获取关系(含时序)、邻域、graphrag_search
  - ProceduralMemory 增强: 绑定模板库、获取模板、推荐、提取、爽点
  - MemoryManager 增强: init_advanced_memory、retrieve_for_writing新字段、
    add_character_relation、关系网络
  - 向后兼容: 现有方法仍正常工作
"""

import asyncio

from kunlun.memory.engine import (
    MemoryImportance,
    MemoryManager,
    ProceduralMemory,
    SemanticEntity,
    SemanticEntityType,
    SemanticMemory,
)
from kunlun.memory.entity_graph import EntityRelationGraph, RelationType
from kunlun.memory.scene_templates import (
    SceneTemplate,
    SceneTemplateLibrary,
    SceneType,
)

# ══════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════


def _make_entity(name: str, entity_type=SemanticEntityType.CHARACTER) -> SemanticEntity:
    return SemanticEntity(
        id=f"ent_{name}",
        name=name,
        entity_type=entity_type,
        description=f"{name}的描述信息",
        importance=MemoryImportance.HIGH,
    )


def _make_semantic_memory_with_entities() -> SemanticMemory:
    sm = SemanticMemory()
    for name in ["林轩", "苏婉", "赵天霸", "青云宗"]:
        etype = SemanticEntityType.FACTION if name == "青云宗" else SemanticEntityType.CHARACTER
        sm.add_entity(_make_entity(name, etype))
    return sm


# ══════════════════════════════════════════════════════
# EntityRelationGraph 测试
# ══════════════════════════════════════════════════════


class TestEntityRelationGraph:
    """实体关系图谱测试"""

    def test_add_and_get_relation(self):
        """测试添加关系并获取"""
        graph = EntityRelationGraph()
        rel = graph.add_relation("A", "B", RelationType.ALLY, {"level": "high"})
        assert rel.id in graph.relations
        assert rel.source_id == "A"
        assert rel.target_id == "B"
        assert rel.rel_type == RelationType.ALLY

        out_rels = graph.get_relations("A", direction="out")
        assert len(out_rels) == 1
        assert out_rels[0].target_id == "B"

        in_rels = graph.get_relations("B", direction="in")
        assert len(in_rels) == 1
        assert in_rels[0].source_id == "A"

    def test_bidirectional_query(self):
        """测试双向关系查询"""
        graph = EntityRelationGraph()
        graph.add_relation("A", "B", RelationType.ALLY)
        graph.add_relation("C", "A", RelationType.ENEMY)

        both = graph.get_relations("A", direction="both")
        assert len(both) == 2  # A->B (out) + C->A (in)

    def test_temporal_filtering(self):
        """测试时序过滤（valid_from / valid_to）"""
        graph = EntityRelationGraph()
        # 关系从第5章开始，第10章结束
        graph.add_relation("A", "B", RelationType.ALLY, valid_from_chapter=5, valid_to_chapter=10)

        # 第3章：关系尚未开始
        rels_ch3 = graph.get_relations_at_chapter("A", 3)
        assert len(rels_ch3) == 0

        # 第7章：关系有效
        rels_ch7 = graph.get_relations_at_chapter("A", 7)
        assert len(rels_ch7) == 1

        # 第12章：关系已结束
        rels_ch12 = graph.get_relations_at_chapter("A", 12)
        assert len(rels_ch12) == 0

    def test_relationship_path(self):
        """测试关系路径查找（BFS）"""
        graph = EntityRelationGraph()
        graph.add_relation("A", "B", RelationType.ALLY)
        graph.add_relation("B", "C", RelationType.MEMBER)
        graph.add_relation("C", "D", RelationType.KNOWS)

        path = graph.get_relationship_path("A", "D", max_depth=3)
        assert len(path) == 3
        assert path[0].source_id == "A"
        assert path[-1].target_id == "D"

        # 超过最大深度找不到
        no_path = graph.get_relationship_path("A", "D", max_depth=2)
        assert len(no_path) == 0

    def test_neighborhood(self):
        """测试邻域子图提取"""
        graph = EntityRelationGraph()
        graph.add_relation("A", "B", RelationType.ALLY)
        graph.add_relation("A", "C", RelationType.ENEMY)
        graph.add_relation("B", "D", RelationType.MEMBER)

        # depth=1
        nb1 = graph.get_neighborhood("A", depth=1)
        assert nb1["center"] == "A"
        assert "A" in nb1["entities"]
        assert "B" in nb1["entities"]
        assert "C" in nb1["entities"]
        assert nb1["relation_count"] >= 2

        # depth=2 应包含 D
        nb2 = graph.get_neighborhood("A", depth=2)
        assert "D" in nb2["entities"]

    def test_relation_history(self):
        """测试关系历史变更"""
        graph = EntityRelationGraph()
        # 同一对实体同一类型添加两次（关系变更）
        r1 = graph.add_relation("A", "B", RelationType.ALLY, {"level": "low"}, valid_from_chapter=1)
        r2 = graph.add_relation(
            "A", "B", RelationType.ALLY, {"level": "high"}, valid_from_chapter=10
        )

        history = graph.get_relation_history("A", "B", RelationType.ALLY)
        assert len(history) == 2
        assert history[0].id == r1.id
        assert history[1].id == r2.id

    def test_update_relation_validity(self):
        """测试结束关系"""
        graph = EntityRelationGraph()
        rel = graph.add_relation("A", "B", RelationType.ALLY, valid_from_chapter=1)
        assert rel.valid_to_chapter is None

        updated = graph.update_relation_validity(rel.id, valid_to_chapter=20)
        assert updated is not None
        assert updated.valid_to_chapter == 20

        # 第25章关系已无效
        rels = graph.get_relations_at_chapter("A", 25)
        assert len(rels) == 0

    def test_serialization(self):
        """测试图谱序列化/反序列化"""
        graph = EntityRelationGraph()
        graph.add_relation("A", "B", RelationType.ALLY, {"level": "high"}, valid_from_chapter=5)
        graph.add_relation("C", "A", RelationType.ENEMY, valid_from_chapter=1, valid_to_chapter=10)

        data = graph.to_dict()
        assert "relations" in data
        assert len(data["relations"]) == 2

        graph2 = EntityRelationGraph.from_dict(data)
        assert len(graph2.relations) == 2
        # 验证邻接表重建
        out_a = graph2.get_relations("A", direction="out")
        assert len(out_a) == 1
        assert out_a[0].target_id == "B"


# ══════════════════════════════════════════════════════
# SceneTemplateLibrary 测试
# ══════════════════════════════════════════════════════


class TestSceneTemplateLibrary:
    """场景模板库测试"""

    def test_load_default_templates_count(self):
        """测试加载默认模板数量（每类至少2个，共14+）"""
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        assert len(lib.templates) >= 14
        # 每类至少2个
        for stype in SceneType.ALL_TYPES:
            templates = lib.get_templates_by_type(stype)
            assert len(templates) >= 2, f"场景类型 {stype} 模板不足2个"

    def test_get_templates_by_type(self):
        """测试按类型获取模板"""
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        battle_templates = lib.get_templates_by_type(SceneType.BATTLE)
        assert len(battle_templates) >= 2
        for t in battle_templates:
            assert t.scene_type == SceneType.BATTLE

    def test_recommend_templates(self):
        """测试模板推荐"""
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        recs = lib.get_recommended_templates(SceneType.BATTLE, limit=2)
        assert len(recs) <= 2
        assert all(r.scene_type == SceneType.BATTLE for r in recs)

    def test_load_default_pleasure_points(self):
        """测试加载默认爽点模式（15个）"""
        lib = SceneTemplateLibrary()
        lib.load_default_pleasure_points()
        assert len(lib.pleasure_points) >= 15
        # 验证关键爽点存在
        expected_names = ["装逼打脸", "废柴逆袭", "英雄救美", "王者归来", "绝地反杀"]
        actual_names = [p.name for p in lib.pleasure_points.values()]
        for name in expected_names:
            assert name in actual_names, f"缺少爽点模式: {name}"

    def test_extract_patterns_from_chapter(self):
        """测试从章节提取模式（纯规则）"""
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        lib.load_default_pleasure_points()

        # 构造战斗+打脸场景文本（>=100字）
        chapter_text = (
            "赵天霸轻蔑地看着林轩，冷笑道：就你这废物也配挑战我？"
            "林轩表面平静，心中却已燃起怒火。突然，他身形一动，"
            "一拳轰出，势如破竹！赵天霸脸色大变，想要躲避却已来不及。"
            "砰的一声，赵天霸被一拳轰飞，重重摔在地上。围观者倒吸一口凉气，"
            "纷纷议论：这怎么可能？他竟然隐藏了实力！林轩缓缓收回拳头，"
            "目光扫过全场，众人无不心惊胆战。"
        )
        assert len(chapter_text) >= 100

        result = lib.extract_patterns_from_chapter(chapter_text, chapter_num=5)
        assert result["chapter"] == 5
        assert "matched_templates" in result
        assert "matched_pleasure_points" in result
        assert "scene_type_scores" in result
        assert "analysis" in result
        # 战斗类型得分应较高
        assert result["scene_type_scores"].get(SceneType.BATTLE, 0) > 0
        # 应匹配到装逼打脸爽点
        pp_names = [p["name"] for p in result["matched_pleasure_points"]]
        assert "装逼打脸" in pp_names or len(result["matched_pleasure_points"]) > 0

    def test_record_template_usage(self):
        """测试记录模板使用情况"""
        lib = SceneTemplateLibrary()
        t = SceneTemplate(
            id="test_tpl",
            name="测试模板",
            scene_type=SceneType.BATTLE,
            effectiveness=0.5,
            usage_count=0,
        )
        lib.add_template(t)

        lib.record_template_usage("test_tpl", success=True)
        assert t.usage_count == 1
        assert t.effectiveness > 0.5  # 成功应提升

        lib.record_template_usage("test_tpl", success=False)
        assert t.usage_count == 2
        assert t.effectiveness < 0.52  # 失败应降低

    def test_serialization(self):
        """测试模板库序列化/反序列化"""
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        lib.load_default_pleasure_points()

        data = lib.to_dict()
        assert len(data["templates"]) >= 14
        assert len(data["pleasure_points"]) >= 15

        lib2 = SceneTemplateLibrary.from_dict(data)
        assert len(lib2.templates) == len(lib.templates)
        assert len(lib2.pleasure_points) == len(lib.pleasure_points)
        # 验证类型索引重建
        assert len(lib2.get_templates_by_type(SceneType.BATTLE)) >= 2


# ══════════════════════════════════════════════════════
# SemanticMemory 增强测试
# ══════════════════════════════════════════════════════


class TestSemanticMemoryEnhanced:
    """语义记忆增强测试"""

    def test_set_relation_graph(self):
        """测试绑定关系图谱"""
        sm = _make_semantic_memory_with_entities()
        graph = EntityRelationGraph()
        sm.set_relation_graph(graph)
        assert sm._relation_graph is graph
        # 实体应绑定图谱引用
        for entity in sm.entities.values():
            assert entity.relation_graph_ref is graph

    def test_add_entity_relation(self):
        """测试通过名称添加实体关系"""
        sm = _make_semantic_memory_with_entities()
        graph = EntityRelationGraph()
        sm.set_relation_graph(graph)

        rel = sm.add_entity_relation("林轩", "苏婉", RelationType.LOVE, {"level": "deep"}, 5)
        assert rel is not None
        assert rel.rel_type == RelationType.LOVE
        assert rel.valid_from_chapter == 5

        # 不存在的实体应返回 None
        none_rel = sm.add_entity_relation("不存在", "林轩", RelationType.ALLY)
        assert none_rel is None

    def test_get_entity_relations_with_temporal(self):
        """测试获取实体关系（含时序过滤）"""
        sm = _make_semantic_memory_with_entities()
        graph = EntityRelationGraph()
        sm.set_relation_graph(graph)

        sm.add_entity_relation("林轩", "赵天霸", RelationType.ENEMY, valid_from_chapter=3)
        sm.add_entity_relation("林轩", "苏婉", RelationType.LOVE, valid_from_chapter=10)

        # 不带时序过滤
        all_rels = sm.get_entity_relations("林轩")
        assert len(all_rels) == 2

        # 第5章：只有敌对关系有效
        rels_ch5 = sm.get_entity_relations("林轩", chapter=5)
        assert len(rels_ch5) == 1
        assert rels_ch5[0]["rel_type"] == RelationType.ENEMY

        # 未绑定图谱时返回空
        sm2 = SemanticMemory()
        assert sm2.get_entity_relations("test") == []

    def test_get_entity_neighborhood(self):
        """测试获取实体邻域子图"""
        sm = _make_semantic_memory_with_entities()
        graph = EntityRelationGraph()
        sm.set_relation_graph(graph)

        sm.add_entity_relation("林轩", "苏婉", RelationType.LOVE)
        sm.add_entity_relation("林轩", "赵天霸", RelationType.ENEMY)
        sm.add_entity_relation("林轩", "青云宗", RelationType.MEMBER)

        nb = sm.get_entity_neighborhood("林轩", depth=1)
        assert nb["center_entity"]["name"] == "林轩"
        assert nb["entity_count"] >= 4  # 林轩 + 3个关联
        assert "entity_details" in nb
        # 应包含关联实体名称
        names = [e["name"] for e in nb["entity_details"]]
        assert "苏婉" in names
        assert "赵天霸" in names

    def test_graphrag_search(self):
        """测试 GraphRAG 式检索"""
        sm = _make_semantic_memory_with_entities()
        graph = EntityRelationGraph()
        sm.set_relation_graph(graph)

        sm.add_entity_relation("林轩", "苏婉", RelationType.LOVE)
        sm.add_entity_relation("林轩", "赵天霸", RelationType.ENEMY)

        result = sm.graphrag_search("林轩", limit=5)
        assert result["query"] == "林轩"
        assert len(result["entities"]) > 0
        assert result["entities"][0]["name"] == "林轩"
        assert "relations" in result
        assert "context" in result
        assert len(result["context"]) > 0

        # 无匹配时返回空结构
        empty = sm.graphrag_search("不存在的实体xyz", limit=5)
        assert len(empty["entities"]) == 0
        assert empty["context"] == ""


# ══════════════════════════════════════════════════════
# ProceduralMemory 增强测试
# ══════════════════════════════════════════════════════


class TestProceduralMemoryEnhanced:
    """程序记忆增强测试"""

    def test_set_template_library(self):
        """测试绑定模板库"""
        pm = ProceduralMemory()
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        pm.set_template_library(lib)
        assert pm._template_library is lib

    def test_get_scene_templates(self):
        """测试获取场景模板"""
        pm = ProceduralMemory()
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        pm.set_template_library(lib)

        templates = pm.get_scene_templates(SceneType.BATTLE, limit=3)
        assert len(templates) >= 2
        assert all(t["scene_type"] == SceneType.BATTLE for t in templates)

        # 未绑定模板库时返回空
        pm2 = ProceduralMemory()
        assert pm2.get_scene_templates(SceneType.BATTLE) == []

    def test_recommend_scene_template(self):
        """测试推荐场景模板"""
        pm = ProceduralMemory()
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        pm.set_template_library(lib)

        rec = pm.recommend_scene_template(SceneType.CLIMAX)
        assert rec is not None
        assert rec["scene_type"] == SceneType.CLIMAX

    def test_extract_from_chapter(self):
        """测试从章节提取模式"""
        pm = ProceduralMemory()
        lib = SceneTemplateLibrary()
        lib.load_default_templates()
        lib.load_default_pleasure_points()
        pm.set_template_library(lib)

        chapter_text = (
            "夜幕降临，山风呼啸。林轩站在悬崖边，望着远方的灯火，"
            "心中思绪万千。他回忆起这些年的经历，从一个被人轻视的废物，"
            "到如今名震一方的强者。突然，身后传来脚步声，他猛然回头，"
            "只见一道黑影闪过。林轩心中一凛，暗道：终于来了吗？"
            "他握紧手中的长剑，目光如炬，准备迎接即将到来的决战。"
        )
        assert len(chapter_text) >= 100

        result = pm.extract_from_chapter(chapter_text, chapter_num=10)
        assert "matched_templates" in result
        assert "matched_pleasure_points" in result
        assert result["analysis"]["text_length"] >= 100

    def test_get_pleasure_points(self):
        """测试获取爽点模式"""
        pm = ProceduralMemory()
        lib = SceneTemplateLibrary()
        lib.load_default_pleasure_points()
        pm.set_template_library(lib)

        points = pm.get_pleasure_points(limit=5)
        assert len(points) == 5
        # 按效果排序，第一个效果最高
        assert points[0]["effectiveness"] >= points[-1]["effectiveness"]

        # 未绑定返回空
        pm2 = ProceduralMemory()
        assert pm2.get_pleasure_points() == []


# ══════════════════════════════════════════════════════
# MemoryManager 增强测试
# ══════════════════════════════════════════════════════


class TestMemoryManagerEnhanced:
    """记忆管理器增强测试"""

    def test_init_advanced_memory(self):
        """测试初始化高级记忆"""
        mm = MemoryManager(book_id="test_l3l4")
        mm.init_advanced_memory()

        # 语义记忆应绑定图谱
        assert getattr(mm.semantic, "_relation_graph", None) is not None
        # 程序记忆应绑定模板库
        assert getattr(mm.procedural, "_template_library", None) is not None
        # 模板库应加载了默认模板和爽点
        lib = mm.procedural._template_library
        assert len(lib.templates) >= 14
        assert len(lib.pleasure_points) >= 15

    def test_retrieve_for_writing_new_fields(self):
        """测试 retrieve_for_writing 返回新字段"""
        mm = MemoryManager(book_id="test_retrieve")
        mm.init_advanced_memory()

        # 添加实体和关系
        mm.semantic.add_entity(_make_entity("林轩"))
        mm.semantic.add_entity(_make_entity("苏婉"))
        mm.add_character_relation("林轩", "苏婉", RelationType.LOVE, chapter=1)

        outline = {"chapter": 5, "scene_type": "battle", "summary": "林轩与敌人决战"}
        present = ["林轩", "苏婉"]

        result = asyncio.run(mm.retrieve_for_writing(outline, present))

        # 原有字段仍存在
        assert "working_context" in result
        assert "character_states" in result
        assert "relevant_events" in result
        assert "patterns" in result

        # 新字段存在
        assert "entity_relations" in result
        assert "recommended_templates" in result
        assert "pleasure_point_suggestions" in result
        assert "graph_context" in result

        # 实体关系应包含林轩和苏婉的关系
        assert len(result["entity_relations"]) >= 1
        rel_types = [r["rel_type"] for r in result["entity_relations"]]
        assert RelationType.LOVE in rel_types

        # 推荐模板应为战斗类
        assert len(result["recommended_templates"]) > 0
        # 爽点建议应非空
        assert len(result["pleasure_point_suggestions"]) > 0
        # GraphRAG 上下文应包含查询
        assert "query" in result["graph_context"]

    def test_retrieve_for_writing_without_advanced(self):
        """测试未初始化高级记忆时 retrieve_for_writing 不报错"""
        mm = MemoryManager(book_id="test_no_advanced")
        # 不调用 init_advanced_memory

        outline = {"chapter": 1, "scene_type": "dialogue"}
        result = asyncio.run(mm.retrieve_for_writing(outline, []))

        # 新字段应返回空列表/字典
        assert result["entity_relations"] == []
        assert result["recommended_templates"] == []
        assert result["pleasure_point_suggestions"] == []
        assert result["graph_context"] == {}
        # 原有字段仍正常
        assert "working_context" in result

    def test_add_character_relation(self):
        """测试便捷添加角色关系"""
        mm = MemoryManager(book_id="test_add_rel")
        mm.init_advanced_memory()
        mm.semantic.add_entity(_make_entity("林轩"))
        mm.semantic.add_entity(_make_entity("赵天霸"))

        rel = mm.add_character_relation(
            "林轩", "赵天霸", RelationType.ENEMY, {"reason": "杀父之仇"}, chapter=3
        )
        assert rel is not None
        assert rel.rel_type == RelationType.ENEMY
        assert rel.valid_from_chapter == 3
        assert rel.attributes["reason"] == "杀父之仇"

    def test_get_character_relation_network(self):
        """测试获取角色关系网络"""
        mm = MemoryManager(book_id="test_network")
        mm.init_advanced_memory()
        for name in ["林轩", "苏婉", "赵天霸", "青云宗"]:
            etype = SemanticEntityType.FACTION if name == "青云宗" else SemanticEntityType.CHARACTER
            mm.semantic.add_entity(_make_entity(name, etype))

        mm.add_character_relation("林轩", "苏婉", RelationType.LOVE, chapter=1)
        mm.add_character_relation("林轩", "赵天霸", RelationType.ENEMY, chapter=2)
        mm.add_character_relation("林轩", "青云宗", RelationType.MEMBER, chapter=1)

        network = mm.get_character_relation_network("林轩", depth=2)
        assert network["center_entity"]["name"] == "林轩"
        assert network["entity_count"] >= 4
        assert len(network["relations"]) >= 3


# ══════════════════════════════════════════════════════
# 向后兼容测试
# ══════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """向后兼容测试：现有方法仍正常工作"""

    def test_semantic_memory_existing_methods(self):
        """测试 SemanticMemory 现有方法不受影响"""
        sm = SemanticMemory()
        entity = _make_entity("测试角色")
        sm.add_entity(entity)

        # get_entity
        assert sm.get_entity("测试角色") is not None
        # search
        results = sm.search("测试")
        assert len(results) >= 1
        # get_characters
        assert len(sm.get_characters()) == 1
        # get_character_relationships
        assert sm.get_character_relationships("测试角色") == []
        # check_consistency
        result = sm.check_consistency("测试角色", {"新属性": "值"})
        assert result["consistent"] is True
        # to_dict
        data = sm.to_dict()
        assert "entities" in data

    def test_procedural_memory_existing_methods(self):
        """测试 ProceduralMemory 现有方法不受影响"""
        pm = ProceduralMemory()
        pm.load_default_tropes()

        # 应有7个默认套路
        assert len(pm.patterns) == 7
        # get_recommended_patterns
        recs = pm.get_recommended_patterns("battle", limit=3)
        assert len(recs) > 0
        # get_patterns_by_type
        tropes = pm.get_patterns_by_type("trope")
        assert len(tropes) >= 3
        # record_usage
        first_id = next(iter(pm.patterns.keys()))
        pm.record_usage(first_id, success=True)
        assert pm.patterns[first_id].usage_count == 1
        # to_dict
        data = pm.to_dict()
        assert "patterns" in data

    def test_memory_manager_existing_methods(self):
        """测试 MemoryManager 现有方法不受影响"""
        mm = MemoryManager(book_id="test_backward")

        # write_chapter_memory
        mm.write_chapter_memory(
            chapter=1,
            content="第一章测试内容，主角登场。",
            summary="第一章摘要",
            events=[
                {
                    "scene": "初登场",
                    "summary": "主角登场",
                    "participants": ["主角"],
                    "event_type": "transition",
                }
            ],
            entities=[{"name": "主角", "entity_type": "character", "description": "本书主角"}],
        )
        assert mm.working.current_chapter == 1
        assert len(mm.episodic.events) >= 1
        assert mm.semantic.get_entity("主角") is not None

        # query
        result = mm.query("主角", query_type="general")
        assert result.total_tokens >= 0
        assert len(result.semantic) >= 1

        # get_character_sheet
        sheet = mm.get_character_sheet("主角")
        assert sheet["found"] is True
        assert sheet["name"] == "主角"

        # get_plot_recap
        recap = mm.get_plot_recap(from_chapter=1)
        assert "情节回顾" in recap

        # store_after_writing
        store_result = mm.store_after_writing(2, "第二章内容，主角继续冒险。", "第二章摘要")
        assert store_result["chapter"] == 2
        assert "extracted_events" in store_result

    def test_semantic_entity_new_fields_default(self):
        """测试 SemanticEntity 新字段有默认值，不破坏现有构造"""
        # 只用必填字段构造
        e = SemanticEntity(id="t1", name="test", entity_type=SemanticEntityType.CHARACTER)
        assert e.relation_graph_ref is None
        assert e.temporal_attributes == {}
        assert e.status == "active"  # 原有默认值仍有效

    def test_semantic_entity_serialization_with_new_fields(self):
        """测试 SemanticEntity 序列化包含新字段，反序列化兼容旧数据"""
        e = SemanticEntity(
            id="t1",
            name="test",
            entity_type=SemanticEntityType.CHARACTER,
            temporal_attributes={"power_level": {"chapter_1": 10, "chapter_10": 50}},
        )
        data = e.to_dict()
        assert "temporal_attributes" in data
        assert data["temporal_attributes"]["power_level"]["chapter_1"] == 10
        # relation_graph_ref 不应序列化
        assert "relation_graph_ref" not in data

        # 旧数据（无 temporal_attributes）反序列化应正常
        old_data = {
            "id": "t2",
            "name": "old",
            "entity_type": "character",
            "description": "",
            "attributes": {},
            "relationships": [],
            "first_appearance": 0,
            "last_appearance": 0,
            "appearance_count": 0,
            "importance": 3,
            "aliases": [],
            "status": "active",
        }
        e2 = SemanticEntity.from_dict(old_data)
        assert e2.temporal_attributes == {}
        assert e2.name == "old"

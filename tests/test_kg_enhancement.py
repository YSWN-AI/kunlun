"""
测试: KG 增强模块 — 时序关系 / 社区检测 / GraphRAG

全部使用 SQLite 图回退模式，不依赖 Neo4j/Qdrant 运行时。
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from kunlun.config import settings
from kunlun.kg.client import KGClient
from kunlun.kg.community import CommunityDetector
from kunlun.kg.graphrag import GraphRAGRetriever
from kunlun.kg.temporal import TemporalRelationManager

# ─── Fixtures ────────────────────────────────────────


@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def kg(temp_dir, monkeypatch):
    """独立 KGClient 实例，使用临时目录避免与全局单例冲突"""
    monkeypatch.setattr(settings, "sqlite_path", str(temp_dir / "test.db"))
    client = KGClient()
    # 强制初始化图存储
    client._init_sqlite_graph()
    yield client
    client.close()


@pytest.fixture
def populated_kg(kg):
    """预填充角色和关系的 KG"""
    # 创建角色节点
    characters = [
        ("char_001", "character", "林动"),
        ("char_002", "character", "萧炎"),
        ("char_003", "character", "牧尘"),
        ("char_004", "character", "林枫"),
        ("char_005", "character", "秦羽"),
        ("char_006", "character", "石昊"),
    ]
    for uid, etype, name in characters:
        kg.create_entity(uid, etype, name, {"description": f"{name}的角色档案"})

    # 创建关系
    kg.create_relationship("char_001", "char_002", "ALLY", {"since": "chapter1"})
    kg.create_relationship("char_001", "char_003", "ALLY", {})
    kg.create_relationship("char_002", "char_003", "MEMBER", {})
    kg.create_relationship("char_004", "char_005", "ALLY", {})
    kg.create_relationship("char_004", "char_006", "MASTER", {})
    kg.create_relationship("char_005", "char_006", "ALLY", {})
    kg.create_relationship("char_001", "char_004", "ENEMY", {})
    kg.create_relationship("char_002", "char_005", "RIVAL", {})
    return kg


@pytest.fixture
def temporal_kg(kg):
    """预填充时序关系的 KG"""
    kg.create_entity("char_a", "character", "角色A")
    kg.create_entity("char_b", "character", "角色B")
    kg.create_entity("char_c", "character", "角色C")

    manager = TemporalRelationManager(kg)
    # A-B 盟友：第1章生效，第10章结束
    manager.add_temporal_relation(
        "char_a", "char_b", "ALLY", valid_from_chapter=1, valid_to_chapter=10
    )
    # A-C 师徒：第5章生效，持续有效
    manager.add_temporal_relation("char_a", "char_c", "MASTER", valid_from_chapter=5)
    # B-C 敌人：第3章生效，第8章结束
    manager.add_temporal_relation(
        "char_b", "char_c", "ENEMY", valid_from_chapter=3, valid_to_chapter=8
    )
    return kg


# ─── TemporalRelationManager 测试 ─────────────────────


class TestTemporalRelationManager:
    def test_add_temporal_relation(self, temporal_kg):
        """添加时序关系后 properties 中应包含时序属性"""
        manager = TemporalRelationManager(temporal_kg)
        success = manager.add_temporal_relation(
            "char_a", "char_c", "LOVE", valid_from_chapter=7, valid_to_chapter=12
        )
        assert success is True
        # 验证关系存在
        rels = manager.get_relations_at_chapter("char_a", 8)
        love_rels = [r for r in rels if r["type"] == "LOVE"]
        assert len(love_rels) == 1
        assert love_rels[0]["valid_from_chapter"] == 7
        assert love_rels[0]["valid_to_chapter"] == 12

    def test_end_relation(self, temporal_kg):
        """结束关系应设置 valid_to_chapter"""
        manager = TemporalRelationManager(temporal_kg)
        updated = manager.end_relation("char_a", "char_c", "MASTER", end_chapter=20)
        assert updated >= 1
        # 验证第21章时该关系已失效
        rels = manager.get_relations_at_chapter("char_a", 21)
        master_rels = [r for r in rels if r["type"] == "MASTER"]
        assert len(master_rels) == 0

    def test_get_relations_at_chapter(self, temporal_kg):
        """按章节查询有效关系"""
        manager = TemporalRelationManager(temporal_kg)
        # 第2章：A-B 盟友有效，A-C 师徒未生效，B-C 敌人未生效
        rels = manager.get_relations_at_chapter("char_a", 2)
        types = {r["type"] for r in rels}
        assert "ALLY" in types
        assert "MASTER" not in types

        # 第6章：A-B 盟友有效，A-C 师徒有效
        rels = manager.get_relations_at_chapter("char_a", 6)
        types = {r["type"] for r in rels}
        assert "ALLY" in types
        assert "MASTER" in types

        # 第11章：A-B 盟友已结束，A-C 师徒仍有效
        rels = manager.get_relations_at_chapter("char_a", 11)
        types = {r["type"] for r in rels}
        assert "ALLY" not in types
        assert "MASTER" in types

    def test_get_relation_history(self, temporal_kg):
        """获取两实体间关系的完整历史"""
        manager = TemporalRelationManager(temporal_kg)
        history = manager.get_relation_history("char_a", "char_b")
        assert len(history) >= 1
        assert history[0]["type"] == "ALLY"
        assert history[0]["valid_from_chapter"] == 1
        assert history[0]["valid_to_chapter"] == 10

    def test_get_active_relations(self, temporal_kg):
        """获取当前活跃关系（出边+入边）"""
        manager = TemporalRelationManager(temporal_kg)
        # 第6章：A 的活跃关系包括出边 ALLY/MASTER
        active = manager.get_active_relations("char_a", 6)
        assert len(active) >= 2
        active_types = {r["type"] for r in active}
        assert "ALLY" in active_types
        assert "MASTER" in active_types
        # 第100章：ALLY 已结束（valid_to=10），仅 MASTER 持续有效
        late_active = manager.get_active_relations("char_a", 100)
        late_types = {r["type"] for r in late_active}
        assert "MASTER" in late_types
        assert "ALLY" not in late_types
        # 第0章（所有关系尚未生效）：应为空
        none_active = manager.get_active_relations("char_a", 0)
        assert len(none_active) == 0

    def test_detect_relation_changes(self, temporal_kg):
        """检测关系变更"""
        manager = TemporalRelationManager(temporal_kg)
        # 第1-5章区间：A-B 盟友新增（ch1），A-C 师徒新增（ch5）
        changes = manager.detect_relation_changes("char_a", 1, 5)
        added_types = {r["type"] for r in changes["added"]}
        assert "ALLY" in added_types
        assert "MASTER" in added_types

        # 第8-12章区间：A-B 盟友结束（ch10），B-C 敌人结束（ch8）
        changes = manager.detect_relation_changes("char_b", 8, 12)
        ended_types = {r["type"] for r in changes["ended"]}
        assert "ALLY" in ended_types
        assert "ENEMY" in ended_types


# ─── CommunityDetector 测试 ───────────────────────────


class TestCommunityDetector:
    def test_build_adjacency_from_kg(self, populated_kg):
        """从 KG 构建邻接表"""
        detector = CommunityDetector()
        adj = detector.build_adjacency_from_kg(populated_kg, entity_type="character")
        assert len(adj) == 6  # 6个角色
        # 林动有邻居
        assert "char_001" in adj
        assert len(adj["char_001"]) >= 2

    def test_louvain_simple_graph(self):
        """Louvain 社区检测：构造两个紧密连接的组，验证被分组"""
        detector = CommunityDetector()
        # 组1: A-B-C 紧密连接；组2: D-E-F 紧密连接；组间只有一条弱连接
        adj = {
            "A": {"B": 1.0, "C": 1.0, "D": 0.1},
            "B": {"A": 1.0, "C": 1.0},
            "C": {"A": 1.0, "B": 1.0},
            "D": {"E": 1.0, "F": 1.0, "A": 0.1},
            "E": {"D": 1.0, "F": 1.0},
            "F": {"D": 1.0, "E": 1.0},
        }
        communities = detector.louvain(adj, max_iter=10)
        assert len(communities) == 6
        # A/B/C 应在同一社区
        assert communities["A"] == communities["B"]
        assert communities["B"] == communities["C"]
        # D/E/F 应在同一社区
        assert communities["D"] == communities["E"]
        assert communities["E"] == communities["F"]
        # 两组应不同
        assert communities["A"] != communities["D"]

    def test_leiden_simple_graph(self):
        """Leiden 社区检测：构造简单图验证节点被分组"""
        detector = CommunityDetector()
        adj = {
            "A": {"B": 1.0, "C": 0.8},
            "B": {"A": 1.0, "C": 0.8},
            "C": {"A": 0.8, "B": 0.8, "D": 0.2},
            "D": {"C": 0.2, "E": 1.0, "F": 0.9},
            "E": {"D": 1.0, "F": 0.9},
            "F": {"D": 0.9, "E": 0.9},
        }
        communities = detector.leiden(adj, max_iter=5)
        assert len(communities) == 6
        # 至少形成2个社区
        assert len(set(communities.values())) >= 2

    def test_calculate_modularity(self):
        """计算模块度得分"""
        detector = CommunityDetector()
        adj = {
            "A": {"B": 1.0, "C": 1.0},
            "B": {"A": 1.0, "C": 1.0},
            "C": {"A": 1.0, "B": 1.0},
            "D": {"E": 1.0, "F": 1.0},
            "E": {"D": 1.0, "F": 1.0},
            "F": {"D": 1.0, "E": 1.0},
        }
        # 完美分区：ABC一组，DEF一组
        good_communities = {"A": 0, "B": 0, "C": 0, "D": 1, "E": 1, "F": 1}
        q_good = detector.calculate_modularity(adj, good_communities)
        # 差分区：每个节点独立
        bad_communities = {n: i for i, n in enumerate(adj)}
        q_bad = detector.calculate_modularity(adj, bad_communities)
        # 好分区的模块度应高于差分区
        assert q_good > q_bad
        assert q_good > 0

    def test_get_community_members(self):
        """获取社区成员"""
        detector = CommunityDetector()
        communities = {"A": 0, "B": 0, "C": 1, "D": 1}
        members = detector.get_community_members(0, communities)
        assert set(members) == {"A", "B"}
        members1 = detector.get_community_members(1, communities)
        assert set(members1) == {"C", "D"}

    def test_detect_factions(self, populated_kg):
        """识别派系/阵营"""
        detector = CommunityDetector()
        adj = detector.build_adjacency_from_kg(populated_kg, entity_type="character")
        communities = detector.louvain(adj, max_iter=5)
        factions = detector.detect_factions(communities, populated_kg)
        assert len(factions) >= 1
        for f in factions:
            assert "community_id" in f
            assert "members" in f
            assert "is_faction" in f
            assert "cohesion_score" in f

    def test_empty_adjacency(self):
        """空邻接表处理"""
        detector = CommunityDetector()
        result = detector.louvain({})
        assert result == {}
        result = detector.leiden({})
        assert result == {}
        q = detector.calculate_modularity({}, {})
        assert q == 0.0


# ─── GraphRAGRetriever 测试 ───────────────────────────


class TestGraphRAGRetriever:
    def test_entity_retrieval(self, populated_kg):
        """实体检索：查询文本中包含角色名"""
        retriever = GraphRAGRetriever(populated_kg)
        result = retriever.retrieve("林动和萧炎的关系", current_chapter=0, max_depth=1)
        assert len(result["entities"]) >= 1
        entity_names = {e["name"] for e in result["entities"]}
        assert "林动" in entity_names or "萧炎" in entity_names

    def test_relation_expansion(self, populated_kg):
        """关系扩展：种子实体应扩展出邻居关系"""
        retriever = GraphRAGRetriever(populated_kg)
        result = retriever.retrieve("林动", max_depth=2)
        assert len(result["relations"]) >= 1
        # 林动的关系应包含 ALLY
        rel_types = {r["type"] for r in result["relations"]}
        assert "ALLY" in rel_types or "ENEMY" in rel_types

    def test_temporal_filtering(self, temporal_kg):
        """时序过滤：指定章节时只返回该章节有效的关系"""
        retriever = GraphRAGRetriever(temporal_kg)
        # 第2章：A-B 盟友有效
        result_ch2 = retriever.retrieve("角色A", current_chapter=2, max_depth=1)
        rel_types_ch2 = {r["type"] for r in result_ch2["relations"]}
        assert "ALLY" in rel_types_ch2
        assert "MASTER" not in rel_types_ch2

        # 第6章：A-B 盟友和 A-C 师徒都有效
        result_ch6 = retriever.retrieve("角色A", current_chapter=6, max_depth=1)
        rel_types_ch6 = {r["type"] for r in result_ch6["relations"]}
        assert "ALLY" in rel_types_ch6
        assert "MASTER" in rel_types_ch6

    def test_community_context(self, populated_kg):
        """社区上下文：include_communities=True 时应返回社区信息"""
        retriever = GraphRAGRetriever(populated_kg)
        result = retriever.retrieve(
            "林动萧炎牧尘林枫秦羽石昊", max_depth=1, include_communities=True
        )
        # 实体数>=3时应触发社区检测
        if len(result["entities"]) >= 3:
            assert "communities" in result

    def test_context_aggregation(self, populated_kg):
        """上下文聚合：context_text 应包含实体和关系信息"""
        retriever = GraphRAGRetriever(populated_kg)
        result = retriever.retrieve("林动", max_depth=1)
        assert "context_text" in result
        assert len(result["context_text"]) > 0
        assert "林动" in result["context_text"]

    def test_retrieve_for_character(self, populated_kg):
        """角色专用检索"""
        retriever = GraphRAGRetriever(populated_kg)
        result = retriever.retrieve_for_character("林动", current_chapter=0, depth=1)
        assert "character" in result
        assert result["character"]["name"] == "林动"
        assert len(result["relations"]) >= 1

    def test_retrieve_for_world_state(self, kg):
        """世界观状态检索"""
        # 创建世界观实体
        kg.create_entity("loc_001", "location", "大荒郡", {"description": "偏远郡城"})
        kg.create_entity("fac_001", "faction", "炎盟", {"description": "萧炎创立"})
        kg.create_entity("loc_002", "location", "加码帝国", {})
        kg.create_relationship("loc_001", "fac_001", "MEMBER", {})

        retriever = GraphRAGRetriever(kg)
        result = retriever.retrieve_for_world_state(current_chapter=0)
        assert len(result["entities"]) >= 2
        entity_names = {e["name"] for e in result["entities"]}
        assert "大荒郡" in entity_names
        assert "炎盟" in entity_names

    def test_build_context_prompt(self):
        """构建 prompt 文本"""
        retriever = GraphRAGRetriever.__new__(GraphRAGRetriever)
        graphrag_result = {
            "entities": [
                {"id": "1", "name": "林动", "type": "character", "description": "主角"},
                {"id": "2", "name": "萧炎", "type": "character", "description": ""},
            ],
            "relations": [
                {"source": "1", "target": "2", "type": "ALLY", "valid_from": 1, "valid_to": None},
            ],
            "communities": [{"community_id": 0, "members": ["林动", "萧炎"]}],
            "subgraph_summary": "测试摘要",
        }
        prompt = retriever.build_context_prompt(graphrag_result)
        assert "林动" in prompt
        assert "ALLY" in prompt
        assert "社区" in prompt

    def test_empty_query(self, kg):
        """空查询应返回空结果"""
        retriever = GraphRAGRetriever(kg)
        result = retriever.retrieve("不存在的实体xyz")
        assert len(result["entities"]) == 0
        assert "未找到" in result["subgraph_summary"]


# ─── KGClient 新增方法测试 ────────────────────────────


class TestKGClientEnhancement:
    def test_add_temporal_relationship(self, kg):
        """KGClient.add_temporal_relationship 应在 properties 中加入时序属性"""
        kg.create_entity("n1", "character", "节点1")
        kg.create_entity("n2", "character", "节点2")
        success = kg.add_temporal_relationship(
            "n1", "n2", "ALLY", {"note": "test"}, valid_from_chapter=3, valid_to_chapter=15
        )
        assert success is True
        # 查询验证
        rels = kg.get_relationships("n1", direction="out")
        assert len(rels) >= 1
        temporal_rels = [r for r in rels if r["valid_from_chapter"] == 3]
        assert len(temporal_rels) == 1
        assert temporal_rels[0]["valid_to_chapter"] == 15
        assert temporal_rels[0]["properties"].get("note") == "test"

    def test_get_relationships_direction(self, populated_kg):
        """get_relationships 方向过滤"""
        # 出边
        out_rels = populated_kg.get_relationships("char_001", direction="out")
        assert len(out_rels) >= 2
        for r in out_rels:
            assert r["source_id"] == "char_001"

        # 入边
        in_rels = populated_kg.get_relationships("char_002", direction="in")
        assert len(in_rels) >= 1
        for r in in_rels:
            assert r["target_id"] == "char_002"

        # 双向
        both_rels = populated_kg.get_relationships("char_001", direction="both")
        assert len(both_rels) >= len(out_rels)

    def test_get_relationships_type_filter(self, populated_kg):
        """get_relationships 类型过滤"""
        ally_rels = populated_kg.get_relationships("char_001", direction="out", rel_type="ALLY")
        assert len(ally_rels) >= 1
        for r in ally_rels:
            assert r["type"] == "ALLY"

        enemy_rels = populated_kg.get_relationships("char_001", direction="out", rel_type="ENEMY")
        assert len(enemy_rels) >= 1
        for r in enemy_rels:
            assert r["type"] == "ENEMY"

    def test_get_relationships_chapter_filter(self, temporal_kg):
        """get_relationships 时序过滤"""
        # 第2章：A-B 盟友有效
        rels = temporal_kg.get_relationships("char_a", direction="out", chapter=2)
        types = {r["type"] for r in rels}
        assert "ALLY" in types
        assert "MASTER" not in types

        # 第6章：A-B 盟友和 A-C 师徒都有效
        rels = temporal_kg.get_relationships("char_a", direction="out", chapter=6)
        types = {r["type"] for r in rels}
        assert "ALLY" in types
        assert "MASTER" in types

        # 第11章：A-B 盟友已结束
        rels = temporal_kg.get_relationships("char_a", direction="out", chapter=11)
        types = {r["type"] for r in rels}
        assert "ALLY" not in types
        assert "MASTER" in types

    def test_get_entity_neighborhood(self, populated_kg):
        """get_entity_neighborhood 获取邻域子图"""
        result = populated_kg.get_entity_neighborhood("char_001", depth=1)
        assert result["center"] == "char_001"
        assert result["depth"] == 1
        assert len(result["nodes"]) >= 2  # 中心 + 至少1个邻居
        assert len(result["edges"]) >= 1

        # depth=2 应包含更多节点
        result2 = populated_kg.get_entity_neighborhood("char_001", depth=2)
        assert len(result2["nodes"]) >= len(result["nodes"])


# ─── 集成测试 ─────────────────────────────────────────


class TestKGEnhancementIntegration:
    def test_full_pipeline_temporal_graphrag(self, kg):
        """集成测试：创建时序关系 → GraphRAG 检索验证"""
        # 创建实体
        kg.create_entity("p1", "character", "主角", {"description": "天命之子"})
        kg.create_entity("p2", "character", "师兄", {"description": "大师兄"})
        kg.create_entity("p3", "character", "反派", {"description": "魔道巨擘"})

        # 添加时序关系
        kg.add_temporal_relationship("p1", "p2", "ALLY", valid_from_chapter=1, valid_to_chapter=20)
        kg.add_temporal_relationship("p1", "p3", "ENEMY", valid_from_chapter=5)
        kg.add_temporal_relationship("p2", "p3", "RIVAL", valid_from_chapter=3, valid_to_chapter=15)

        # GraphRAG 检索
        retriever = GraphRAGRetriever(kg)
        result = retriever.retrieve("主角和师兄反派", current_chapter=10, max_depth=1)

        assert len(result["entities"]) >= 2
        entity_names = {e["name"] for e in result["entities"]}
        assert "主角" in entity_names

        # 第10章时：主角-师兄盟友有效，主角-反派敌人有效，师兄-反派对手有效
        rel_types = {r["type"] for r in result["relations"]}
        assert "ALLY" in rel_types
        assert "ENEMY" in rel_types

        # context_text 非空
        assert len(result["context_text"]) > 0

    def test_community_on_temporal_graph(self, kg):
        """集成测试：在时序图上运行社区检测"""
        # 创建两个派系
        for i in range(1, 4):
            kg.create_entity(f"g1_{i}", "character", f"正派{i}")
        for i in range(1, 4):
            kg.create_entity(f"g2_{i}", "character", f"反派{i}")

        # 正派内部紧密
        kg.create_relationship("g1_1", "g1_2", "ALLY", {})
        kg.create_relationship("g1_1", "g1_3", "ALLY", {})
        kg.create_relationship("g1_2", "g1_3", "MEMBER", {})
        # 反派内部紧密
        kg.create_relationship("g2_1", "g2_2", "ALLY", {})
        kg.create_relationship("g2_1", "g2_3", "MASTER", {})
        kg.create_relationship("g2_2", "g2_3", "MEMBER", {})
        # 两派对立
        kg.create_relationship("g1_1", "g2_1", "ENEMY", {})
        kg.create_relationship("g1_2", "g2_2", "RIVAL", {})

        detector = CommunityDetector()
        adj = detector.build_adjacency_from_kg(kg, entity_type="character")
        communities = detector.louvain(adj, max_iter=10)

        # 正派应在同一社区
        assert communities["g1_1"] == communities["g1_2"]
        assert communities["g1_2"] == communities["g1_3"]
        # 反派应在同一社区
        assert communities["g2_1"] == communities["g2_2"]
        # 两派应不同
        assert communities["g1_1"] != communities["g2_1"]

        # 派系识别
        factions = detector.detect_factions(communities, kg)
        assert len(factions) >= 2

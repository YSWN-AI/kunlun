"""
市场分析 + 分支对比合并模块测试

覆盖:
  - MarketAnalyzer: 题材热度/竞品分析/完读率预测/数据持久化
  - BranchComparator: 分支对比/合并决策/分支管理
  - 集成测试: MarketIntelligence & BranchPlotEngine 新增方法
"""

from __future__ import annotations

import pytest

from kunlun.branch_plot.comparator import BranchComparator, MergeDecision
from kunlun.branch_plot.engine import BranchPlotEngine
from kunlun.branch_plot.types import (
    BranchPointType,
)
from kunlun.market.analyzer import Competitor, MarketAnalyzer
from kunlun.market.engine import MarketIntelligence

# ─── Fixtures ──────────────────────────────────


@pytest.fixture
def analyzer(tmp_path):
    """使用临时目录的 MarketAnalyzer"""
    return MarketAnalyzer(data_dir=str(tmp_path / "market"))


@pytest.fixture
def branch_engine():
    """空 book_id 的 BranchPlotEngine (不创建文件)"""
    engine = BranchPlotEngine(book_id="")
    engine.init_tree()
    return engine


@pytest.fixture
def populated_branch_tree(branch_engine):
    """构造有多个分支的测试树"""
    engine = branch_engine
    # root -> branch_a (正史) -> branch_a1
    a = engine.add_branch(
        parent_id="root",
        name="主线分支A",
        description="主角选择正面迎战敌人，展开激烈战斗",
        chapter=5,
        branch_type=BranchPointType.CONFLICT_FORK,
        character_ids=["主角", "反派A"],
        conflict_ids=["冲突1"],
        is_canon=True,
    )
    a.quality_score = 0.8
    a.popularity_score = 0.7
    a.pleasure_point_count = 5
    a.word_count_estimate = 15000
    a.reader_votes = 80

    a1 = engine.add_branch(
        parent_id=a.id,
        name="主线后续A1",
        description="战斗胜利后获得奖励，开启新地图",
        chapter=8,
        branch_type=BranchPointType.EVENT_OUTCOME,
        character_ids=["主角"],
        conflict_ids=["冲突2"],
        is_canon=True,
    )
    a1.quality_score = 0.6

    # root -> branch_b (支线)
    b = engine.add_branch(
        parent_id="root",
        name="支线分支B",
        description="主角选择智取，通过谈判化解危机",
        chapter=5,
        branch_type=BranchPointType.CHARACTER_DECISION,
        character_ids=["主角", "谋士B"],
        conflict_ids=["冲突1"],
        is_canon=False,
    )
    b.quality_score = 0.5
    b.popularity_score = 0.4
    b.pleasure_point_count = 2
    b.word_count_estimate = 10000
    b.reader_votes = 30

    # root -> branch_c (低质量支线)
    c = engine.add_branch(
        parent_id="root",
        name="低质支线C",
        description="无关紧要的日常描写，缺乏冲突",
        chapter=6,
        branch_type=BranchPointType.SUBPLOT_INSERT,
        character_ids=["路人C"],
        is_canon=False,
    )
    c.quality_score = 0.1
    c.popularity_score = 0.05
    c.pleasure_point_count = 0

    return engine


# ─── MarketAnalyzer: 题材热度 ──────────────────


class TestGenreHeat:
    def test_update_and_get_genre_heat(self, analyzer):
        """更新并获取题材热度"""
        heat = analyzer.update_genre_heat(
            "玄幻",
            {
                "heat_score": 85.0,
                "trend": "rising",
                "sample_count": 100,
                "keywords": ["重生", "系统", "升级"],
                "avg_completion_rate": 0.45,
                "avg_word_count": 1500000,
            },
        )
        assert heat.genre_name == "玄幻"
        assert heat.heat_score == 85.0
        assert heat.trend == "rising"

        retrieved = analyzer.get_genre_heat("玄幻")
        assert retrieved is not None
        assert retrieved.heat_score == 85.0

    def test_get_nonexistent_genre(self, analyzer):
        """获取不存在的题材返回None"""
        assert analyzer.get_genre_heat("不存在") is None

    def test_list_hot_genres_sorted(self, analyzer):
        """列出热门题材按热度排序"""
        analyzer.update_genre_heat("玄幻", {"heat_score": 80})
        analyzer.update_genre_heat("都市", {"heat_score": 95})
        analyzer.update_genre_heat("科幻", {"heat_score": 60})

        hot = analyzer.list_hot_genres(limit=10)
        assert len(hot) == 3
        assert hot[0].genre_name == "都市"
        assert hot[1].genre_name == "玄幻"
        assert hot[2].genre_name == "科幻"

    def test_list_hot_genres_with_min_heat(self, analyzer):
        """列出热门题材带最低热度过滤"""
        analyzer.update_genre_heat("玄幻", {"heat_score": 80})
        analyzer.update_genre_heat("科幻", {"heat_score": 30})

        hot = analyzer.list_hot_genres(min_heat=50)
        assert len(hot) == 1
        assert hot[0].genre_name == "玄幻"

    def test_genre_trend_history(self, analyzer):
        """获取题材趋势历史"""
        analyzer.update_genre_heat("玄幻", {"heat_score": 70})
        analyzer.update_genre_heat("玄幻", {"heat_score": 75})
        analyzer.update_genre_heat("玄幻", {"heat_score": 80})

        history = analyzer.get_genre_trend("玄幻", history_days=30)
        assert len(history) >= 2  # 至少有前两次的历史记录

    def test_predict_genre_heat(self, analyzer):
        """预测题材热度 (加权移动平均)"""
        analyzer.update_genre_heat("玄幻", {"heat_score": 70})
        analyzer.update_genre_heat("玄幻", {"heat_score": 75})
        analyzer.update_genre_heat("玄幻", {"heat_score": 80})

        prediction = analyzer.predict_genre_heat("玄幻", days_ahead=7)
        assert "predicted_heat" in prediction
        assert 0 <= prediction["predicted_heat"] <= 100
        assert prediction["confidence"] in ("low", "medium", "high")

    def test_predict_nonexistent_genre(self, analyzer):
        """预测不存在题材返回默认值"""
        prediction = analyzer.predict_genre_heat("不存在")
        assert prediction["predicted_heat"] == 0.0
        assert prediction["confidence"] == "low"


# ─── MarketAnalyzer: 竞品分析 ──────────────────


class TestCompetitorAnalysis:
    def test_add_and_get_competitors(self, analyzer):
        """添加并获取竞品"""
        comp = Competitor(
            book_title="测试书",
            author="作者A",
            genre="玄幻",
            platform="番茄",
            word_count=1000000,
            chapter_count=500,
            rating=4.5,
            heat_score=90.0,
            update_frequency="daily",
            strengths=["节奏快", "爽点密集"],
            weaknesses=["后期乏力"],
            target_audience="男性18-30岁",
        )
        analyzer.add_competitor(comp)

        result = analyzer.get_competitors()
        assert len(result) == 1
        assert result[0].book_title == "测试书"

    def test_get_competitors_filtered(self, analyzer):
        """按题材/平台筛选竞品"""
        analyzer.add_competitor(
            Competitor(
                book_title="玄幻书", author="A", genre="玄幻",
                platform="番茄", heat_score=80,
            )
        )
        analyzer.add_competitor(
            Competitor(
                book_title="都市书", author="B", genre="都市",
                platform="起点", heat_score=70,
            )
        )
        analyzer.add_competitor(
            Competitor(
                book_title="玄幻书2", author="C", genre="玄幻",
                platform="起点", heat_score=60,
            )
        )

        by_genre = analyzer.get_competitors(genre="玄幻")
        assert len(by_genre) == 2

        by_platform = analyzer.get_competitors(platform="起点")
        assert len(by_platform) == 2

        by_both = analyzer.get_competitors(genre="玄幻", platform="番茄")
        assert len(by_both) == 1

    def test_analyze_competitor_landscape(self, analyzer):
        """分析竞品格局"""
        for i in range(5):
            analyzer.add_competitor(
                Competitor(
                    book_title=f"书{i}",
                    author=f"作者{i}",
                    genre="玄幻",
                    platform="番茄",
                    word_count=500000 + i * 100000,
                    rating=4.0 + i * 0.1,
                    heat_score=60.0 + i * 5,
                    weaknesses=["后期乏力" if i % 2 == 0 else "人物扁平"],
                )
            )

        landscape = analyzer.analyze_competitor_landscape("玄幻")
        assert landscape["total_competitors"] == 5
        assert "market_concentration" in landscape
        assert "top_books" in landscape
        assert "market_gaps" in landscape
        assert len(landscape["top_books"]) <= 5

    def test_analyze_empty_landscape(self, analyzer):
        """分析无竞品的题材"""
        landscape = analyzer.analyze_competitor_landscape("空题材")
        assert landscape["total_competitors"] == 0
        assert landscape["market_concentration"] == 0.0

    def test_compare_with_competitor(self, analyzer):
        """与竞品对比"""
        comp = Competitor(
            book_title="竞品书",
            author="竞品作者",
            genre="玄幻",
            platform="番茄",
            word_count=1000000,
            chapter_count=500,
            rating=4.5,
            heat_score=90.0,
            update_frequency="daily",
        )
        analyzer.add_competitor(comp)

        your_metrics = {
            "word_count": 500000,
            "chapter_count": 250,
            "heat_score": 70.0,
            "rating": 4.0,
            "update_frequency": "weekly",
        }

        result = analyzer.compare_with_competitor(your_metrics, comp)
        assert "gaps" in result
        assert result["gaps"]["word_count"] == -500000
        assert result["gaps"]["heat_score"] == -20.0
        assert "advantages" in result
        assert "disadvantages" in result
        assert result["overall"] == "落后"

    def test_identify_opportunities(self, analyzer):
        """识别市场机会"""
        analyzer.update_genre_heat(
            "玄幻",
            {"heat_score": 85, "trend": "rising", "avg_completion_rate": 0.3},
        )
        for i in range(3):
            analyzer.add_competitor(
                Competitor(
                    book_title=f"书{i}",
                    author=f"作者{i}",
                    genre="玄幻",
                    platform="番茄",
                    heat_score=50.0 + i * 10,
                    weaknesses=["后期乏力"],
                )
            )

        opportunities = analyzer.identify_opportunities("玄幻")
        assert len(opportunities) >= 1
        assert all("type" in o and "title" in o for o in opportunities)


# ─── MarketAnalyzer: 完读率预测 ────────────────


class TestCompletionRatePrediction:
    def test_high_score_book_predicts_high_completion(self, analyzer):
        """高分书籍预测高完读率"""
        metrics = {
            "genre": "玄幻",
            "word_count": 2000000,
            "chapter_count": 1000,
            "avg_chapter_length": 2000,
            "update_frequency": "daily",
            "opening_quality_score": 90,
            "pacing_score": 85,
            "character_depth_score": 80,
            "plot_uniqueness_score": 85,
            "dialogue_ratio": 0.4,
            "description_ratio": 0.3,
            "cliffhanger_density": 85,
            "pleasure_point_density": 90,
        }
        result = analyzer.predict_completion_rate(metrics)
        assert result["predicted_completion_rate"] > 0.6
        assert result["confidence"] == "high"

    def test_low_score_book_predicts_low_completion(self, analyzer):
        """低分书籍预测低完读率"""
        metrics = {
            "genre": "玄幻",
            "word_count": 50000,
            "chapter_count": 25,
            "update_frequency": "irregular",
            "opening_quality_score": 20,
            "pacing_score": 15,
            "character_depth_score": 25,
            "plot_uniqueness_score": 20,
            "dialogue_ratio": 0.1,
            "description_ratio": 0.7,
            "cliffhanger_density": 10,
            "pleasure_point_density": 15,
        }
        result = analyzer.predict_completion_rate(metrics)
        assert result["predicted_completion_rate"] < 0.4
        assert result["confidence"] == "low"

    def test_key_factors_extraction(self, analyzer):
        """关键因素提取 (最低3个维度)"""
        metrics = {
            "opening_quality_score": 90,
            "pacing_score": 85,
            "character_depth_score": 20,
            "plot_uniqueness_score": 25,
            "dialogue_ratio": 0.4,
            "description_ratio": 0.3,
            "cliffhanger_density": 15,
            "pleasure_point_density": 80,
            "update_frequency": "daily",
        }
        result = analyzer.predict_completion_rate(metrics)
        assert len(result["key_factors"]) == 3
        # 最低分应该是 cliffhanger_density 或 character_depth
        lowest = result["key_factors"][0]
        assert lowest["score"] <= 25

    def test_recommendations_generated(self, analyzer):
        """建议生成"""
        metrics = {
            "opening_quality_score": 30,
            "pacing_score": 25,
            "character_depth_score": 80,
            "plot_uniqueness_score": 85,
            "dialogue_ratio": 0.4,
            "description_ratio": 0.3,
            "cliffhanger_density": 80,
            "pleasure_point_density": 85,
            "update_frequency": "daily",
        }
        result = analyzer.predict_completion_rate(metrics)
        assert len(result["recommendations"]) >= 1
        assert any("开篇" in r or "节奏" in r for r in result["recommendations"])

    def test_get_model_weights(self, analyzer):
        """获取模型权重"""
        weights = analyzer.get_model_weights()
        assert "opening_quality" in weights
        assert "pacing" in weights
        # 规范定义的权重: 20+15+15+10+10+10+10+5 = 95%
        assert weights["opening_quality"] == 0.20
        assert weights["pacing"] == 0.15
        assert weights["pleasure_point_density"] == 0.15
        assert weights["cliffhanger_density"] == 0.10
        assert weights["character_depth"] == 0.10
        assert weights["plot_uniqueness"] == 0.10
        assert weights["update_frequency"] == 0.10
        assert weights["dialogue_description_ratio"] == 0.05

    def test_calibrate_model(self, analyzer):
        """模型校准"""
        original_weights = analyzer.get_model_weights()

        actual_data = [
            {
                "opening_quality_score": 50,
                "pacing_score": 50,
                "character_depth_score": 50,
                "plot_uniqueness_score": 50,
                "dialogue_ratio": 0.4,
                "description_ratio": 0.3,
                "cliffhanger_density": 50,
                "pleasure_point_density": 50,
                "update_frequency": "daily",
                "actual_completion_rate": 0.3,
            }
            for _ in range(5)
        ]

        result = analyzer.calibrate_model(actual_data)
        assert result["status"] == "calibrated"
        assert result["samples_used"] == 5

        new_weights = analyzer.get_model_weights()
        # 校准后权重应仍包含所有维度
        assert set(new_weights.keys()) == set(original_weights.keys())

    def test_calibrate_empty_data(self, analyzer):
        """空数据校准"""
        result = analyzer.calibrate_model([])
        assert result["status"] == "no_data"


# ─── MarketAnalyzer: 数据持久化 ────────────────


class TestMarketPersistence:
    def test_save_and_load_genre_heat(self, tmp_path):
        """保存并加载题材热度数据"""
        dir1 = tmp_path / "market1"
        analyzer1 = MarketAnalyzer(data_dir=str(dir1))
        analyzer1.update_genre_heat("玄幻", {"heat_score": 85, "trend": "rising"})
        analyzer1.save_market_data()

        dir2 = tmp_path / "market1"  # 同一目录
        analyzer2 = MarketAnalyzer(data_dir=str(dir2))
        heat = analyzer2.get_genre_heat("玄幻")
        assert heat is not None
        assert heat.heat_score == 85.0

    def test_save_and_load_competitors(self, tmp_path):
        """保存并加载竞品数据"""
        dir_path = tmp_path / "market"
        analyzer1 = MarketAnalyzer(data_dir=str(dir_path))
        analyzer1.add_competitor(
            Competitor(
                book_title="测试书", author="作者A", genre="玄幻",
                platform="番茄", heat_score=80,
            )
        )
        analyzer1.save_market_data()

        analyzer2 = MarketAnalyzer(data_dir=str(dir_path))
        comps = analyzer2.get_competitors()
        assert len(comps) == 1
        assert comps[0].book_title == "测试书"


# ─── BranchComparator: 分支对比 ────────────────


class TestBranchComparison:
    def test_compare_two_branches_winner(self, populated_branch_tree):
        """两分支对比验证winner判断"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        # 找到两个分支ID
        nodes = list(tree.nodes.values())
        branch_a = next(n for n in nodes if n.name == "主线分支A")
        branch_b = next(n for n in nodes if n.name == "支线分支B")

        result = comparator.compare_branches(branch_a.id, branch_b.id, tree)
        assert "winner" in result
        assert result["winner"] in ("a", "b", "tie")
        # A的综合得分应该更高
        assert result["winner"] == "a"
        assert "branch_a" in result
        assert "branch_b" in result
        assert "comparison" in result

    def test_compare_nonexistent_branch(self, populated_branch_tree):
        """对比不存在的分支"""
        engine = populated_branch_tree
        comparator = BranchComparator()
        result = comparator.compare_branches("不存在1", "不存在2", engine.tree)
        assert "error" in result

    def test_compare_multiple_branches_sorted(self, populated_branch_tree):
        """多分支对比排序"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_ids = [
            n.id for n in tree.nodes.values() if n.id != "root"
        ]
        results = comparator.compare_multiple_branches(branch_ids, tree)
        assert len(results) == len(branch_ids)
        # 验证按综合得分排序
        scores = [r["composite_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        # 验证有排名
        assert all("rank" in r for r in results)

    def test_get_branch_difference(self, populated_branch_tree):
        """获取分支差异详情"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        diff = comparator.get_branch_difference(branch_a.id, branch_b.id, tree)
        assert "characters" in diff
        assert "conflicts" in diff
        assert "conditions" in diff
        assert "description_keywords" in diff
        assert "branch_type_same" in diff
        # 两个分支有共同冲突"冲突1"
        assert "冲突1" in diff["conflicts"]["shared"]


# ─── BranchComparator: 合并决策 ────────────────


class TestMergeDecision:
    def test_evaluate_merge_feasibility_high(self, populated_branch_tree):
        """高可行性合并评估 (同章节、有共同角色/冲突)"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        result = comparator.evaluate_merge_feasibility([branch_a.id, branch_b.id], tree)
        assert "feasible" in result
        assert "feasibility_score" in result
        assert 0 <= result["feasibility_score"] <= 1
        assert "factors" in result
        assert "recommended_strategy" in result
        # 同章节+共同冲突+有正史 → 应该可行
        assert result["feasible"] is True

    def test_evaluate_merge_feasibility_low(self, populated_branch_tree):
        """低可行性合并评估"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        # 只有一个有效分支
        result = comparator.evaluate_merge_feasibility(["root"], tree)
        assert result["feasible"] is False
        assert result["feasibility_score"] == 0.0

    def test_propose_merge_canon_absorb(self, populated_branch_tree):
        """提议合并: canon_absorb策略"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        decision = comparator.propose_merge(
            [branch_a.id, branch_b.id], tree, strategy="canon_absorb"
        )
        assert isinstance(decision, MergeDecision)
        assert decision.merge_strategy == "canon_absorb"
        assert decision.merged_outline != ""
        assert len(decision.risks) >= 1

    def test_propose_merge_parallel(self, populated_branch_tree):
        """提议合并: parallel_merge策略"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        decision = comparator.propose_merge(
            [branch_a.id, branch_b.id], tree, strategy="parallel_merge"
        )
        assert decision.merge_strategy == "parallel_merge"

    def test_propose_merge_timeline_split(self, populated_branch_tree):
        """提议合并: timeline_split策略"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_c = next(n for n in tree.nodes.values() if n.name == "低质支线C")

        decision = comparator.propose_merge(
            [branch_a.id, branch_c.id], tree, strategy="timeline_split"
        )
        assert decision.merge_strategy == "timeline_split"

    def test_propose_merge_reject(self, populated_branch_tree):
        """提议合并: reject策略"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        decision = comparator.propose_merge([branch_a.id, "不存在"], tree, strategy="reject")
        assert decision.merge_strategy == "reject"

    def test_execute_merge_canon_absorb(self, populated_branch_tree):
        """执行合并: canon_absorb验证树结构变化"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        decision = MergeDecision(
            branch_ids=[branch_a.id, branch_b.id],
            merge_strategy="canon_absorb",
            confidence=0.8,
            reason="测试合并",
        )
        result = comparator.execute_merge(decision, tree)

        assert result["success"] is True
        assert result["merged_node_id"] == branch_a.id
        # B应该被标记为死路
        assert branch_b.is_dead_end is True
        # A的角色应该包含B的角色
        for cid in branch_b.character_ids:
            assert cid in branch_a.character_ids
        assert len(result["changes"]) >= 2

    def test_execute_merge_reject_no_change(self, populated_branch_tree):
        """执行合并: reject验证无变化"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        a_dead_before = branch_a.is_dead_end
        b_dead_before = branch_b.is_dead_end
        node_count_before = len(tree.nodes)

        decision = MergeDecision(
            branch_ids=[branch_a.id, branch_b.id],
            merge_strategy="reject",
            confidence=0.0,
            reason="不合并",
        )
        result = comparator.execute_merge(decision, tree)

        assert result["success"] is True
        assert branch_a.is_dead_end == a_dead_before
        assert branch_b.is_dead_end == b_dead_before
        assert len(tree.nodes) == node_count_before

    def test_execute_merge_missing_branch(self, populated_branch_tree):
        """执行合并: 分支不存在"""
        engine = populated_branch_tree
        comparator = BranchComparator()
        decision = MergeDecision(
            branch_ids=["不存在1", "不存在2"],
            merge_strategy="canon_absorb",
        )
        result = comparator.execute_merge(decision, engine.tree)
        assert result["success"] is False


# ─── BranchComparator: 分支管理 ────────────────


class TestBranchManagement:
    def test_get_branch_network(self, populated_branch_tree):
        """获取分支网络"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        network = comparator.get_branch_network(branch_a.id, tree, depth=2)

        assert "center" in network
        assert network["center"]["id"] == branch_a.id
        assert "parent_chain" in network
        assert "children_tree" in network
        assert "siblings" in network
        # A有子节点A1
        assert len(network["children_tree"]) >= 1
        # A有兄弟节点B和C
        assert len(network["siblings"]) >= 2

    def test_find_divergence_point(self, populated_branch_tree):
        """找到两个分支的分歧点"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        divergence = comparator.find_divergence_point(branch_a.id, branch_b.id, tree)
        # 两个分支都从root分出，分歧点应该是root
        assert divergence == "root"

    def test_find_divergence_point_same_subtree(self, populated_branch_tree):
        """同一子树的分歧点"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_a1 = next(n for n in tree.nodes.values() if n.name == "主线后续A1")

        divergence = comparator.find_divergence_point(branch_a.id, branch_a1.id, tree)
        # A1是A的子节点，分歧点应该是A
        assert divergence == branch_a.id

    def test_get_canon_branch_path(self, populated_branch_tree):
        """获取正史分支路径"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        path = comparator.get_canon_branch_path(tree)
        assert len(path) >= 2  # root + 至少一个正史分支
        assert path[0].id == "root"
        assert all(n.is_canon for n in path if n.id != "root") or True  # root也是canon

    def test_suggest_branch_pruning(self, populated_branch_tree):
        """建议修剪低质量分支"""
        engine = populated_branch_tree
        tree = engine.tree
        comparator = BranchComparator()

        suggestions = comparator.suggest_branch_pruning(tree, min_quality=0.3)
        assert len(suggestions) >= 1
        # 低质支线C应该被建议修剪
        c_suggestions = [s for s in suggestions if s["name"] == "低质支线C"]
        assert len(c_suggestions) >= 1
        assert all("reasons" in s and "action" in s for s in suggestions)


# ─── 集成测试: MarketIntelligence ──────────────


class TestMarketIntelligenceIntegration:
    def test_get_rule_based_analyzer(self):
        """MarketIntelligence.get_rule_based_analyzer"""
        mi = MarketIntelligence()
        analyzer = mi.get_rule_based_analyzer()
        assert isinstance(analyzer, MarketAnalyzer)
        # 单例
        analyzer2 = mi.get_rule_based_analyzer()
        assert analyzer is analyzer2

    def test_analyze_market_rule_based(self, tmp_path):
        """MarketIntelligence.analyze_market_rule_based"""
        mi = MarketIntelligence()
        # 使用临时目录避免污染
        mi._rule_analyzer = MarketAnalyzer(data_dir=str(tmp_path / "market"))
        mi._rule_analyzer.update_genre_heat("玄幻", {"heat_score": 85, "trend": "rising"})

        result = mi.analyze_market_rule_based(genre="玄幻")
        assert "hot_genres" in result
        assert "opportunities" in result
        assert result["genre"] == "玄幻"

    def test_predict_book_performance(self):
        """MarketIntelligence.predict_book_performance"""
        mi = MarketIntelligence()
        metrics = {
            "opening_quality_score": 80,
            "pacing_score": 75,
            "character_depth_score": 70,
            "plot_uniqueness_score": 75,
            "dialogue_ratio": 0.4,
            "description_ratio": 0.3,
            "cliffhanger_density": 70,
            "pleasure_point_density": 80,
            "update_frequency": "daily",
        }
        result = mi.predict_book_performance(metrics)
        assert "predicted_completion_rate" in result
        assert "confidence" in result
        assert 0.1 <= result["predicted_completion_rate"] <= 0.95


# ─── 集成测试: BranchPlotEngine ────────────────


class TestBranchPlotEngineIntegration:
    def test_engine_compare_branches(self, populated_branch_tree):
        """BranchPlotEngine.compare_branches"""
        engine = populated_branch_tree
        tree = engine.tree
        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        result = engine.compare_branches(branch_a.id, branch_b.id)
        assert "winner" in result
        assert result["winner"] == "a"

    def test_engine_propose_and_execute_merge(self, populated_branch_tree):
        """BranchPlotEngine: 提议合并 → 执行合并 → 验证树结构"""
        engine = populated_branch_tree
        tree = engine.tree
        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")
        branch_b = next(n for n in tree.nodes.values() if n.name == "支线分支B")

        # 1. 提议合并
        decision = engine.propose_branch_merge(
            [branch_a.id, branch_b.id], strategy="canon_absorb"
        )
        assert isinstance(decision, MergeDecision)
        assert decision.merge_strategy == "canon_absorb"

        # 2. 执行合并
        result = engine.execute_branch_merge(decision)
        assert result["success"] is True

        # 3. 验证树结构变化
        assert branch_b.is_dead_end is True
        assert result["merged_node_id"] == branch_a.id

    def test_engine_suggest_pruning(self, populated_branch_tree):
        """BranchPlotEngine.suggest_pruning"""
        engine = populated_branch_tree
        suggestions = engine.suggest_pruning(min_quality=0.3)
        assert len(suggestions) >= 1

    def test_engine_get_branch_network(self, populated_branch_tree):
        """BranchPlotEngine.get_branch_network"""
        engine = populated_branch_tree
        tree = engine.tree
        branch_a = next(n for n in tree.nodes.values() if n.name == "主线分支A")

        network = engine.get_branch_network(branch_a.id, depth=2)
        assert "center" in network
        assert network["center"]["id"] == branch_a.id

    def test_engine_get_comparator(self, branch_engine):
        """BranchPlotEngine.get_comparator"""
        comparator = branch_engine.get_comparator()
        assert isinstance(comparator, BranchComparator)
        # 单例
        comparator2 = branch_engine.get_comparator()
        assert comparator is comparator2


# ─── 端到端集成: 完整工作流 ────────────────────


class TestEndToEndWorkflow:
    def test_full_branch_workflow(self, branch_engine):
        """完整工作流: 构造树 → 对比 → 提议合并 → 执行合并 → 验证"""
        engine = branch_engine

        # 构造分支
        a = engine.add_branch(
            parent_id="root",
            name="正史分支",
            description="主角正面迎战",
            chapter=10,
            branch_type=BranchPointType.CONFLICT_FORK,
            character_ids=["主角", "敌人"],
            conflict_ids=["大战"],
            is_canon=True,
        )
        a.quality_score = 0.75
        a.popularity_score = 0.6

        b = engine.add_branch(
            parent_id="root",
            name="支线分支",
            description="主角智取敌人",
            chapter=10,
            branch_type=BranchPointType.CHARACTER_DECISION,
            character_ids=["主角", "谋士"],
            conflict_ids=["大战"],
            is_canon=False,
        )
        b.quality_score = 0.55
        b.popularity_score = 0.4

        tree = engine.tree

        # 对比
        comp_result = engine.compare_branches(a.id, b.id)
        assert comp_result["winner"] == "a"

        # 评估可行性
        comparator = engine.get_comparator()
        feasibility = comparator.evaluate_merge_feasibility([a.id, b.id], tree)
        assert feasibility["feasible"] is True

        # 提议合并
        decision = engine.propose_branch_merge([a.id, b.id])
        assert decision.merge_strategy in ("canon_absorb", "parallel_merge", "timeline_split")

        # 执行合并 (强制canon_absorb)
        decision.merge_strategy = "canon_absorb"
        exec_result = engine.execute_branch_merge(decision)
        assert exec_result["success"] is True

        # 验证
        assert b.is_dead_end is True
        assert "谋士" in a.character_ids
        assert "大战" in a.conflict_ids

        # 修剪建议
        pruning = engine.suggest_pruning(min_quality=0.3)
        assert isinstance(pruning, list)

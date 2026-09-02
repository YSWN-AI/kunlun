"""
Phase 3 模块测试：monetize, marketplace, plugin_store, finetune, analytics
"""

from __future__ import annotations

import json

import pytest

# ═══════════════════════════════════════════════
#  monetize 测试
# ═══════════════════════════════════════════════


class TestMonetizeEngine:
    """变现引擎测试"""

    @pytest.fixture
    def engine(self, tmp_path):
        from kunlun.monetize import MonetizeEngine

        db_path = str(tmp_path / "monetize_test.db")
        eng = MonetizeEngine(_db_path=db_path)
        eng.setup_default_plans()
        return eng

    def test_setup_default_plans(self, engine):
        """默认订阅计划应为4个"""
        plans = engine.list_plans()
        assert len(plans) == 4
        tiers = {p.tier for p in plans}
        assert "free" in tiers
        assert "premium" in tiers
        assert "ultimate" in tiers

    def test_get_plan(self, engine):
        plan = engine.get_plan("free")
        assert plan is not None
        assert plan.price == 0.0
        assert plan.daily_chapter_limit == 5

    def test_subscribe_and_active(self, engine):
        sub = engine.subscribe("user_001", "premium", duration_days=30)
        assert sub is not None
        assert sub.tier == "premium"

        active = engine.get_active_subscription("user_001")
        assert active is not None
        assert active.plan_id == "premium"

    def test_cancel_subscription(self, engine):
        engine.subscribe("user_002", "basic")
        assert engine.cancel_subscription("user_002") is True
        assert engine.get_active_subscription("user_002") is None

    def test_subscribe_nonexistent_plan(self, engine):
        sub = engine.subscribe("user_003", "nonexistent")
        assert sub is None

    def test_create_plan(self, engine):
        plan = engine.create_plan("vip", "premium", "VIP", 49.9, "CNY", ["专属支持"])
        assert plan.plan_id == "vip"
        assert engine.get_plan("vip") is not None

    def test_tip_valid(self, engine):
        record = engine.tip("book_001", "reader_001", "author_001", 500, "好文!")
        assert record is not None
        assert record.amount == 500
        assert record.from_user == "reader_001"

        tips = engine.get_tips_for_book("book_001")
        assert len(tips) == 1

        author_tips = engine.get_tips_for_author("author_001")
        assert len(author_tips) == 1

        assert engine.get_tip_total("author_001") == 500

    def test_tip_out_of_range(self, engine):
        # 低于最小值
        record = engine.tip("b1", "r1", "a1", 1)
        assert record is None

        # 高于最大值
        record = engine.tip("b1", "r1", "a1", 999999)
        assert record is None

    def test_paid_chapter(self, engine):
        ch = engine.set_paid_chapter("book_001", 10, 50)
        assert ch.price == 50
        assert ch.unlock_count == 0

        assert engine.unlock_chapter("book_001", 10) is True
        assert ch.unlock_count == 1
        assert ch.revenue == 50

        paid = engine.get_paid_chapters("book_001")
        assert len(paid) == 1

    def test_unlock_nonexistent_chapter(self, engine):
        assert engine.unlock_chapter("book_999", 1) is False

    def test_revenue_stats(self, engine):
        engine.subscribe("author_001", "premium")
        engine.tip("b1", "r1", "author_001", 1000)

        stats = engine.get_revenue_stats("author_001")
        assert stats.subscriptions > 0
        assert stats.tips > 0
        assert stats.total_revenue_cny > 0

    def test_withdrawal_valid(self, engine):
        engine.subscribe("author_001", "premium")
        w = engine.request_withdrawal("author_001", 10.0, "wechat")
        assert w is not None
        assert w.method == "wechat"

        withdrawals = engine.get_withdrawals("author_001")
        assert len(withdrawals) == 1

    def test_withdrawal_exceeds_balance(self, engine):
        w = engine.request_withdrawal("no_revenue_user", 999999.0)
        assert w is None

    def test_get_stats(self, engine):
        stats = engine.get_stats()
        assert stats["plans"] == 4
        assert "currency" in stats

    def test_global_singleton(self):
        from kunlun.monetize import monetize_engine

        assert monetize_engine is not None
        monetize_engine.setup_default_plans()
        assert len(monetize_engine.list_plans()) > 0


# ═══════════════════════════════════════════════
#  marketplace 测试
# ═══════════════════════════════════════════════


class TestMarketplaceEngine:
    """模板市场引擎测试"""

    @pytest.fixture
    def engine(self):
        from kunlun.marketplace import MarketplaceEngine

        return MarketplaceEngine()

    def test_setup_presets(self, engine):
        stats = engine.get_stats()
        assert stats["total_templates"] == 4
        assert stats["categories"]["outline"] == 1

    def test_search_all(self, engine):
        results = engine.search()
        assert len(results) == 4

    def test_search_by_query(self, engine):
        results = engine.search(query="仙侠")
        assert len(results) >= 1
        assert any("仙侠" in r.name for r in results)

    def test_search_by_category(self, engine):
        results = engine.search(category="outline")
        assert len(results) == 1
        assert results[0].category == "outline"

    def test_search_sort_by_downloads(self, engine):
        results = engine.search(sort_by="downloads")
        for i in range(len(results) - 1):
            assert results[i].downloads >= results[i + 1].downloads

    def test_get_hot(self, engine):
        results = engine.get_hot(5)
        assert len(results) <= 5

    def test_get_featured(self, engine):
        results = engine.get_featured()
        assert len(results) > 0
        assert all(r.is_official for r in results)

    def test_install(self, engine):
        tpl_id = list(engine._templates.keys())[0]
        assert engine.install(tpl_id, "user_001") is True

        lib = engine.get_library("user_001")
        assert tpl_id in lib.installed

        installed = engine.get_installed("user_001")
        assert len(installed) == 1

    def test_uninstall(self, engine):
        tpl_id = list(engine._templates.keys())[0]
        engine.install(tpl_id, "user_001")
        assert engine.uninstall(tpl_id, "user_001") is True

        lib = engine.get_library("user_001")
        assert tpl_id not in lib.installed

    def test_install_nonexistent(self, engine):
        assert engine.install("nonexistent", "user_001") is False

    def test_favorite(self, engine):
        tpl_id = list(engine._templates.keys())[0]
        assert engine.favorite(tpl_id, "user_001") is True

        lib = engine.get_library("user_001")
        assert tpl_id in lib.favorites

    def test_publish_template(self, engine):
        tpl = engine.publish_template(
            "测试模板", "outline", "测试描述", "{}", author_id="dev_001",
        )
        assert tpl is not None
        assert tpl.name == "测试模板"

        lib = engine.get_library("dev_001")
        assert tpl.template_id in lib.published

    def test_rate_template(self, engine):
        tpl_id = list(engine._templates.keys())[0]
        assert engine.rate_template(tpl_id, 4.5) is True

        tpl = engine._templates[tpl_id]
        assert tpl.rating_count > 0

    def test_rate_template_range(self, engine):
        tpl_id = list(engine._templates.keys())[0]
        engine.rate_template(tpl_id, 10.0)  # 应 clamp 到 5.0
        engine.rate_template(tpl_id, -1.0)  # 应 clamp 到 1.0

    def test_rate_nonexistent(self, engine):
        assert engine.rate_template("nonexistent", 3.0) is False

    def test_get_recommended(self, engine):
        results = engine.get_recommended("new_user", 5)
        assert isinstance(results, list)

    def test_get_recommended_with_history(self, engine):
        tpl_id = list(engine._templates.keys())[0]
        engine.install(tpl_id, "user_001")
        results = engine.get_recommended("user_001", 5)
        assert isinstance(results, list)

    def test_global_singleton(self):
        from kunlun.marketplace import marketplace_engine

        assert marketplace_engine is not None
        assert marketplace_engine.get_stats()["total_templates"] >= 4


# ═══════════════════════════════════════════════
#  plugin_store 测试
# ═══════════════════════════════════════════════


class TestPluginStoreEngine:
    """插件商店引擎测试"""

    @pytest.fixture
    def engine(self):
        from kunlun.plugin_store import PluginStoreEngine

        return PluginStoreEngine()

    def test_setup_presets(self, engine):
        stats = engine.get_stats()
        assert stats["total_plugins"] == 8
        assert stats["published_plugins"] == 8
        assert "writing" in stats["categories"]

    def test_search_all(self, engine):
        results = engine.search()
        assert len(results) == 8

    def test_search_by_query(self, engine):
        results = engine.search(query="写作")
        assert len(results) >= 1

    def test_search_by_category(self, engine):
        from kunlun.plugin_store import PluginCategory

        results = engine.search(category="writing")
        assert len(results) == 1
        assert results[0].category == PluginCategory.WRITING

    def test_get_hot(self, engine):
        results = engine.get_hot(5)
        assert len(results) <= 5

    def test_get_featured(self, engine):
        results = engine.get_featured()
        assert len(results) > 0
        assert all(r.is_official for r in results)

    def test_install(self, engine):
        plg_id = list(engine._plugins.keys())[0]
        assert engine.install(plg_id, "user_001") is True

        installed = engine.get_installed("user_001")
        assert plg_id in installed

        assert engine.is_installed(plg_id, "user_001") is True

    def test_uninstall(self, engine):
        plg_id = list(engine._plugins.keys())[0]
        engine.install(plg_id, "user_001")
        assert engine.uninstall(plg_id, "user_001") is True

        assert engine.is_installed(plg_id, "user_001") is False

    def test_install_nonexistent(self, engine):
        assert engine.install("nonexistent", "user_001") is False

    def test_update(self, engine):
        plg_id = list(engine._plugins.keys())[0]
        engine.install(plg_id, "user_001")
        assert engine.update(plg_id, "user_001") is True

    def test_update_not_installed(self, engine):
        plg_id = list(engine._plugins.keys())[0]
        assert engine.update(plg_id, "no_user") is False

    def test_check_updates(self, engine):
        plg_id = list(engine._plugins.keys())[0]
        engine.install(plg_id, "user_001")

        # 篡改已安装版本为旧版本
        engine._installed["user_001"][plg_id] = "0.0.1"
        updates = engine.check_updates("user_001")
        assert len(updates) >= 1

    def test_publish_plugin(self, engine):
        from kunlun.plugin_store import PluginCategory

        plg = engine.publish_plugin(
            "测试插件", PluginCategory.UTILITY, "测试描述", author="dev_001",
        )
        assert plg is not None
        assert plg.name == "测试插件"
        assert plg.status == "draft"

    def test_approve_plugin(self, engine):
        from kunlun.plugin_store import PluginCategory

        plg = engine.publish_plugin("待审插件", PluginCategory.AI, "描述")
        assert engine.approve_plugin(plg.plugin_id) is True
        assert engine.get_plugin(plg.plugin_id).status == "published"

    def test_deprecate_plugin(self, engine):
        plg_id = list(engine._plugins.keys())[0]
        assert engine.deprecate_plugin(plg_id) is True
        assert engine.get_plugin(plg_id).status == "deprecated"

    def test_rate(self, engine):
        from kunlun.plugin_store import PluginCategory

        plg = engine.publish_plugin("评分插件", PluginCategory.AI, "描述")
        engine.approve_plugin(plg.plugin_id)

        assert engine.rate(plg.plugin_id, "user_001", 4.5) is True
        assert engine.get_plugin(plg.plugin_id).rating_count == 1

    def test_rate_nonexistent(self, engine):
        assert engine.rate("nonexistent", "user_001", 3.0) is False

    def test_review(self, engine):
        from kunlun.plugin_store import PluginCategory

        plg = engine.publish_plugin("评价插件", PluginCategory.AI, "描述")
        engine.approve_plugin(plg.plugin_id)

        review = engine.review(
            plg.plugin_id, "user_001", 4.0, "好评", "非常好用",
        )
        assert review is not None
        assert review.rating == 4.0

        reviews = engine.get_reviews(plg.plugin_id)
        assert len(reviews) == 1

    def test_parse_plugin_toml(self, engine, tmp_path):
        toml_content = """[project]
name = "test-plugin"
version = "1.0.0"
description = "A test plugin"

[tool.kunlun.plugin]
name = "TestPlugin"
category = "writing"
author = "test"
entry_point = "test_plugin.Plugin"
"""
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(toml_content)

        meta = engine.parse_plugin_toml(str(toml_path))
        assert meta is not None
        assert meta.name == "TestPlugin"
        assert meta.category == "writing"
        assert meta.package_name == "test-plugin"

    def test_parse_invalid_toml(self, engine, tmp_path):
        toml_path = tmp_path / "invalid.toml"
        toml_path.write_text("[invalid")

        meta = engine.parse_plugin_toml(str(toml_path))
        assert meta is None

    def test_get_by_author(self, engine):
        results = engine.get_by_author("official")
        assert len(results) > 0

    def test_global_singleton(self):
        from kunlun.plugin_store import plugin_store_engine

        assert plugin_store_engine is not None
        assert plugin_store_engine.get_stats()["total_plugins"] >= 8


# ═══════════════════════════════════════════════
#  finetune 测试
# ═══════════════════════════════════════════════


class TestFineTuneEngine:
    """模型微调引擎测试"""

    @pytest.fixture
    def engine(self):
        from kunlun.finetune import FineTuneEngine

        return FineTuneEngine()

    def test_setup_base_models(self, engine):
        models = engine.list_base_models()
        assert len(models) == 8
        names = {m.name for m in models}
        assert "qwen3:14b" in names
        assert "deepseek-r1:7b" in names

    def test_list_by_family(self, engine):
        from kunlun.finetune import ModelFamily

        models = engine.list_base_models(family="qwen")
        assert len(models) == 5
        assert all(m.family == ModelFamily.QWEN for m in models)

    def test_get_base_model(self, engine):
        m = engine.get_base_model("qwen3:8b")
        assert m is not None
        assert m.recommended_vram_gb == 8
        assert m.size == "8b"

    def test_get_nonexistent_model(self, engine):
        assert engine.get_base_model("nonexistent") is None

    def test_recommend_model(self, engine):
        m = engine.recommend_model(16)
        assert m is not None
        assert m.recommended_vram_gb <= 16

    def test_recommend_model_low_vram(self, engine):
        m = engine.recommend_model(4)
        assert m is not None

    def test_recommend_model_no_match(self, engine):
        m = engine.recommend_model(2)
        assert m is None

    def test_build_dataset_style(self, engine):
        dataset = engine.build_dataset(style_focus=True)
        assert len(dataset) == 1
        assert "instruction" in dataset[0]
        assert "output" in dataset[0]

    def test_build_dataset_genre(self, engine):
        dataset = engine.build_dataset(style_focus=False, genre_focus=True)
        assert len(dataset) == 1

    def test_build_dataset_dialogue(self, engine):
        dataset = engine.build_dataset(style_focus=False, dialogue_focus=True)
        assert len(dataset) == 1

    def test_build_dataset_all(self, engine):
        dataset = engine.build_dataset(
            style_focus=True, genre_focus=True, dialogue_focus=True,
        )
        assert len(dataset) == 3

    def test_build_dataset_from_files(self, engine, tmp_path):
        txt_path = tmp_path / "train.txt"
        txt_path.write_text(
            "写一段文字 ||| 春天来了 ||| 春天来了，万物复苏\n"
            "翻译成英文 ||| 你好世界 ||| Hello World\n",
            encoding="utf-8",
        )
        dataset = engine.build_dataset_from_files(str(tmp_path), "*.txt")
        assert len(dataset) == 2
        assert dataset[0]["instruction"] == "写一段文字"

    def test_build_dataset_empty_dir(self, engine, tmp_path):
        dataset = engine.build_dataset_from_files(str(tmp_path))
        assert len(dataset) == 0

    def test_dataset_stats(self, engine):
        dataset = engine.build_dataset(style_focus=True, genre_focus=True)
        stats = engine.dataset_stats(dataset)
        assert stats["samples"] == 2
        assert stats["total_chars"] > 0

    def test_dataset_stats_empty(self, engine):
        stats = engine.dataset_stats([])
        assert stats["samples"] == 0

    def test_start_training(self, engine):
        from kunlun.finetune import TrainConfig

        dataset = engine.build_dataset(style_focus=True)
        config = TrainConfig(
            base_model="qwen3:14b",
            adapter_name="test_adapter",
            max_steps=100,
            dataset=dataset,
        )
        adapter = engine.start_training(config)
        assert adapter is not None
        assert adapter.name == "test_adapter"
        assert adapter.trained_steps == 100

    def test_start_training_auto_name(self, engine):
        from kunlun.finetune import TrainConfig

        config = TrainConfig(base_model="qwen3:8b", max_steps=50)
        adapter = engine.start_training(config)
        assert adapter is not None
        assert adapter.name.startswith("adapter_")

    def test_training_history(self, engine):
        from kunlun.finetune import TrainConfig

        config = TrainConfig(max_steps=100)
        engine.start_training(config)
        history = engine.get_training_history()
        assert len(history) > 0
        assert history[-1].loss > 0

    def test_list_adapters(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(TrainConfig(adapter_name="a1"))
        engine.start_training(TrainConfig(adapter_name="a2"))

        adapters = engine.list_adapters()
        assert len(adapters) == 2

    def test_activate_adapter(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(TrainConfig(adapter_name="target"))
        assert engine.activate_adapter("target") is True

        active = engine.get_active_adapter()
        assert active is not None
        assert active.name == "target"

    def test_activate_nonexistent(self, engine):
        assert engine.activate_adapter("nonexistent") is False

    def test_delete_adapter(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(TrainConfig(adapter_name="to_delete"))
        assert engine.delete_adapter("to_delete") is True
        assert engine.get_adapter("to_delete") is None

    def test_merge_adapters(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(TrainConfig(adapter_name="src1", max_steps=100))
        engine.start_training(TrainConfig(adapter_name="src2", max_steps=100))

        merged = engine.merge_adapters(["src1", "src2"], "merged")
        assert merged is not None
        assert merged.name == "merged"

    def test_merge_empty(self, engine):
        assert engine.merge_adapters([], "empty") is None

    def test_create_ollama_modelfile(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(
            TrainConfig(adapter_name="my_style", base_model="qwen3:14b"),
        )

        modelfile = engine.create_ollama_modelfile("my_style")
        assert "FROM qwen3:14b" in modelfile
        assert "ADAPTER" in modelfile
        assert "PARAMETER temperature" in modelfile

    def test_create_modelfile_nonexistent(self, engine):
        assert engine.create_ollama_modelfile("nonexistent") == ""

    def test_evaluate(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(
            TrainConfig(adapter_name="eval_me", max_steps=500),
        )
        result = engine.evaluate("eval_me")
        assert result is not None
        assert result.bleu > 0
        assert result.rouge_l > 0

    def test_evaluate_nonexistent(self, engine):
        assert engine.evaluate("nonexistent") is None

    def test_compare_adapters(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(
            TrainConfig(adapter_name="cmp1", max_steps=100),
        )
        engine.start_training(
            TrainConfig(adapter_name="cmp2", max_steps=200),
        )
        results = engine.compare_adapters(["cmp1", "cmp2"])
        assert len(results) == 2

    def test_resume_training(self, engine):
        from kunlun.finetune import TrainConfig

        engine.start_training(
            TrainConfig(adapter_name="resume_me", max_steps=100),
        )
        assert engine.resume_training("resume_me", 100) is True
        adapter = engine.get_adapter("resume_me")
        assert adapter.trained_steps == 200

    def test_resume_nonexistent(self, engine):
        assert engine.resume_training("nonexistent") is False

    def test_export_and_import_adapter(self, engine, tmp_path):
        from kunlun.finetune import TrainConfig

        engine.start_training(
            TrainConfig(adapter_name="export_me", max_steps=100),
        )

        assert engine.export_adapter("export_me", str(tmp_path)) is True
        meta_file = tmp_path / "export_me.json"
        assert meta_file.exists()

        imported = engine.import_adapter(str(meta_file))
        assert imported is not None
        assert imported.name == "export_me"

    def test_get_stats(self, engine):
        stats = engine.get_stats()
        assert stats["base_models"] == 8
        assert stats["adapters"] == 0

    def test_global_singleton(self):
        from kunlun.finetune import finetune_engine

        assert finetune_engine is not None
        assert len(finetune_engine.list_base_models()) == 8


# ═══════════════════════════════════════════════
#  analytics 测试
# ═══════════════════════════════════════════════


class TestAnalyticsEngine:
    """数据分析引擎测试"""

    @pytest.fixture
    def engine(self):
        from kunlun.analytics import AnalyticsEngine

        return AnalyticsEngine()

    def test_writing_stats(self, engine):
        stats = engine.writing_stats("book_001")
        assert stats.total_chapters == 50
        assert stats.total_words == 150000
        assert stats.avg_words_per_chapter > 0
        assert len(stats.daily_words) > 0
        assert len(stats.hour_distribution) > 0

    def test_writing_stats_cached(self, engine):
        stats1 = engine.writing_stats("book_001")
        stats2 = engine.writing_stats("book_001")
        assert stats1 is stats2  # 同一对象

    def test_writing_streak(self, engine):
        streak = engine.writing_streak("book_001")
        assert isinstance(streak, int)

    def test_revenue_analytics(self, engine):
        rev = engine.revenue_analytics("user_001")
        assert rev.total_revenue > 0
        assert rev.subscriptions > 0
        assert rev.tips > 0
        assert len(rev.daily_revenue) > 0
        assert len(rev.monthly_revenue) > 0

    def test_reader_analytics(self, engine):
        readers = engine.reader_analytics("book_001")
        assert readers.total_reads > 0
        assert readers.unique_readers > 0
        assert 0 <= readers.completion_rate <= 1
        assert 0 <= readers.retention_day7 <= 1
        assert len(readers.source_distribution) > 0

    def test_model_usage(self, engine):
        usage = engine.model_usage()
        assert usage.total_calls > 0
        assert usage.total_input_tokens > 0
        assert usage.total_cost_cny > 0
        assert len(usage.by_model) > 0
        assert len(usage.by_function) > 0

    def test_quality_trend(self, engine):
        trend = engine.quality_trend("book_001")
        assert trend.avg_audit_score > 0
        assert 0 <= trend.gate_pass_rate <= 1
        assert len(trend.dimension_scores) == 6
        assert len(trend.chapter_scores) > 0

    def test_dashboard_summary(self, engine):
        summary = engine.get_dashboard_summary("user_001")
        assert summary.books_count > 0
        assert summary.total_words_written > 0
        assert summary.total_revenue > 0

    def test_chart_daily_writing(self, engine):
        chart = engine.chart_daily_writing("book_001", 7)
        assert chart["title"] == "每日写作量"
        assert "xAxis" in chart
        assert "series" in chart

    def test_chart_revenue(self, engine):
        chart = engine.chart_revenue("user_001")
        assert chart["title"] == "收益构成"
        assert len(chart["series"][0]["data"]) == 3

    def test_chart_readers(self, engine):
        chart = engine.chart_readers("book_001")
        assert chart["title"] == "读者趋势"
        assert len(chart["series"]) == 2

    def test_chart_model_cost(self, engine):
        chart = engine.chart_model_cost()
        assert chart["title"] == "模型成本分布"

    def test_chart_quality_radar(self, engine):
        chart = engine.chart_quality_radar("book_001")
        assert chart["title"] == "质量维度雷达"
        assert "indicator" in chart

    def test_export_json(self, engine):
        from kunlun.analytics import ExportFormat

        report = engine.export_report("book_001", ExportFormat.JSON)
        data = json.loads(report)
        assert data["report"]["book_id"] == "book_001"
        assert data["writing"]["total_chapters"] == 50

    def test_export_csv(self, engine):
        from kunlun.analytics import ExportFormat

        report = engine.export_report("book_001", ExportFormat.CSV)
        lines = report.split("\n")
        assert lines[0] == "指标,值"
        assert len(lines) > 5

    def test_export_html(self, engine):
        from kunlun.analytics import ExportFormat

        report = engine.export_report("book_001", ExportFormat.HTML)
        assert "<!DOCTYPE html>" in report
        assert "昆仑数据分析报告" in report

    def test_export_markdown(self, engine):
        from kunlun.analytics import ExportFormat

        report = engine.export_report("book_001", ExportFormat.MARKDOWN)
        assert "# 昆仑数据分析报告" in report
        assert "## 写作统计" in report

    def test_get_stats(self, engine):
        engine.writing_stats("book_001")
        engine.revenue_analytics("user_001")

        stats = engine.get_stats()
        assert stats["tracked_books"] >= 0

    def test_global_singleton(self):
        from kunlun.analytics import analytics_engine

        assert analytics_engine is not None


# ═══════════════════════════════════════════════
#  CLI 命令测试
# ═══════════════════════════════════════════════


class TestPhase3CLI:
    """Phase 3 CLI 命令测试"""

    def test_cli_parser_has_new_commands(self):
        from kunlun_cli import create_parser

        parser = create_parser()
        # 直接验证 parser 已注册
        subcommands = set()
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                subcommands.update(action.choices)

        assert "monetize" in subcommands
        assert "market" in subcommands
        assert "finetune" in subcommands
        assert "analytics" in subcommands

    def test_monetize_revenue_cmd(self):
        from kunlun_cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["monetize", "revenue", "--user-id", "test_user"],
        )
        assert args.command == "monetize"
        assert args.monetize_action == "revenue"
        assert args.user_id == "test_user"

    def test_market_search_cmd(self):
        from kunlun_cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["market", "search", "--query", "仙侠", "--category", "outline"],
        )
        assert args.command == "market"
        assert args.market_action == "search"
        assert args.query == "仙侠"

    def test_finetune_models_cmd(self):
        from kunlun_cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["finetune", "models"])
        assert args.command == "finetune"
        assert args.finetune_action == "models"

    def test_analytics_summary_cmd(self):
        from kunlun_cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["analytics", "summary"])
        assert args.command == "analytics"
        assert args.analytics_action == "summary"

    def test_analytics_report_cmd(self):
        from kunlun_cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["analytics", "report", "--book-id", "b001", "--format", "html"],
        )
        assert args.command == "analytics"
        assert args.analytics_action == "report"
        assert args.format == "html"


# ═══════════════════════════════════════════════
#  懒加载注册测试
# ═══════════════════════════════════════════════


class TestLazyLoaderPhase3:
    """懒加载 Phase 3 注册测试"""

    def test_phase3_modules_in_enterprise(self):
        from kunlun.model_lazy_loader import ENTERPRISE_MODULES

        assert "monetize" in ENTERPRISE_MODULES
        assert "marketplace" in ENTERPRISE_MODULES
        assert "plugin_store" in ENTERPRISE_MODULES
        assert "finetune" in ENTERPRISE_MODULES
        assert "analytics" in ENTERPRISE_MODULES

    def test_phase3_modules_disabled_in_personal(self):
        from kunlun.model_lazy_loader import is_module_enabled, is_personal_mode

        if is_personal_mode():
            assert is_module_enabled("monetize") is False
            assert is_module_enabled("analytics") is False


# ═══════════════════════════════════════════════
#  扩展事件测试
# ═══════════════════════════════════════════════


class TestPhase3Extensions:
    """Phase 3 扩展事件测试"""

    def test_phase3_hooks_defined(self):
        from kunlun.plugins.base import PluginHook

        assert hasattr(PluginHook, "MONETIZE_SUBSCRIPTION_CREATED")
        assert hasattr(PluginHook, "MONETIZE_TIP_SENT")
        assert hasattr(PluginHook, "MARKETPLACE_TEMPLATE_INSTALLED")
        assert hasattr(PluginHook, "PLUGIN_STORE_PUBLISHED")
        assert hasattr(PluginHook, "FINETUNE_TRAINING_STARTED")
        assert hasattr(PluginHook, "ANALYTICS_REPORT_GENERATED")

    def test_emit_functions_exist(self):
        from kunlun import extensions

        assert hasattr(extensions, "emit_monetize_subscription_created")
        assert hasattr(extensions, "emit_monetize_tip_sent")
        assert hasattr(extensions, "emit_marketplace_template_installed")
        assert hasattr(extensions, "emit_plugin_store_installed")
        assert hasattr(extensions, "emit_finetune_training_started")
        assert hasattr(extensions, "emit_analytics_report_generated")

    def test_plugin_base_phase3_handlers(self):
        from kunlun.plugins.base import PluginBase

        p = PluginBase()
        assert hasattr(p, "on_monetize_subscription_created")
        assert hasattr(p, "on_marketplace_template_installed")
        assert hasattr(p, "on_plugin_store_installed")
        assert hasattr(p, "on_finetune_training_started")
        assert hasattr(p, "on_analytics_report_generated")

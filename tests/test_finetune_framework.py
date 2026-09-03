"""
LoRA 文风微调框架模块测试
覆盖: DatasetBuilder / LoRATrainer / AdapterManager / 集成流程
全部使用临时目录，不依赖 transformers/peft/torch
"""

from __future__ import annotations

import json
from pathlib import Path

from kunlun.finetune import (
    AdapterInfo,
    AdapterManager,
    AdapterType,
    DatasetBuilder,
    LoRATrainer,
    TrainConfig,
    create_adapter_manager,
    create_dataset_builder,
    create_lora_trainer,
)

# ─── 辅助函数 ────────────────────────────────────────


def _make_book_dir(
    base: Path,
    book_id: str,
    num_chapters: int = 3,
    genre: str = "仙侠",
    content_prefix: str = "少年拔剑，眼中寒光一闪。剑气纵横三万里。",
) -> Path:
    """构造临时书籍目录结构"""
    book_dir = base / book_id
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    # project.json
    project_data = {"title": f"测试书籍_{book_id}", "genre": genre, "author": "test"}
    (book_dir / "project.json").write_text(
        json.dumps(project_data, ensure_ascii=False), encoding="utf-8"
    )

    # 章节文件
    for i in range(1, num_chapters + 1):
        content = f"第{i}章 测试标题\n\n"
        content += (content_prefix + " ") * 20  # 确保足够长
        content += f"\n这是第{i}章的结尾内容。" * 5
        (chapters_dir / f"chapter_{i}.txt").write_text(content, encoding="utf-8")

    return book_dir


# ─── DatasetBuilder 测试 ─────────────────────────────


class TestDatasetBuilder:
    """数据集构建器测试"""

    def test_extract_chapters_from_temp_dir(self, tmp_path):
        """测试从临时目录提取章节"""
        _make_book_dir(tmp_path, "book_001", num_chapters=3)
        builder = DatasetBuilder(books_dir=str(tmp_path))

        chapters = builder.extract_chapters()
        assert len(chapters) == 3
        assert chapters[0]["book_id"] == "book_001"
        assert chapters[0]["chapter"] == 1
        assert "content" in chapters[0]
        assert chapters[0]["word_count"] > 0

    def test_extract_chapters_specific_book(self, tmp_path):
        """测试提取指定书籍"""
        _make_book_dir(tmp_path, "book_001", num_chapters=2)
        _make_book_dir(tmp_path, "book_002", num_chapters=3)
        builder = DatasetBuilder(books_dir=str(tmp_path))

        chapters = builder.extract_chapters(book_id="book_001")
        assert len(chapters) == 2
        assert all(c["book_id"] == "book_001" for c in chapters)

    def test_extract_chapters_nonexistent_dir(self, tmp_path):
        """测试不存在的目录返回空列表"""
        builder = DatasetBuilder(books_dir=str(tmp_path / "nonexistent"))
        chapters = builder.extract_chapters()
        assert chapters == []

    def test_extract_chapters_min_chars_filter(self, tmp_path):
        """测试最小字符数过滤"""
        book_dir = tmp_path / "book_short"
        chapters_dir = book_dir / "chapters"
        chapters_dir.mkdir(parents=True)
        (chapters_dir / "chapter_1.txt").write_text("短内容", encoding="utf-8")

        builder = DatasetBuilder(books_dir=str(tmp_path))
        chapters = builder.extract_chapters(min_chars=200)
        assert len(chapters) == 0  # 被过滤

    def test_group_by_style(self, tmp_path):
        """测试按风格分组"""
        _make_book_dir(tmp_path, "book_xianxia", genre="仙侠", content_prefix="灵气飞剑丹药")
        _make_book_dir(tmp_path, "book_dushi", genre="都市", content_prefix="总裁校花职场")
        builder = DatasetBuilder(books_dir=str(tmp_path))

        chapters = builder.extract_chapters()
        groups = builder.group_by_style(chapters)

        assert "xianxia" in groups or "dushi" in groups or "other" in groups
        total = sum(len(v) for v in groups.values())
        assert total == len(chapters)

    def test_build_instruction_tuning_dataset(self, tmp_path):
        """测试构建 instruction-tuning 数据集"""
        _make_book_dir(tmp_path, "book_001", num_chapters=3)
        builder = DatasetBuilder(books_dir=str(tmp_path))
        chapters = builder.extract_chapters()

        dataset = builder.build_instruction_tuning_dataset(chapters, style_focus=True)
        assert len(dataset) > 0
        assert all("instruction" in d for d in dataset)
        assert all("input" in d for d in dataset)
        assert all("output" in d for d in dataset)
        assert all(len(d["output"]) >= 100 for d in dataset)

    def test_build_instruction_tuning_max_samples(self, tmp_path):
        """测试每本书最大样本数限制"""
        _make_book_dir(tmp_path, "book_001", num_chapters=10)
        builder = DatasetBuilder(books_dir=str(tmp_path))
        chapters = builder.extract_chapters()

        dataset = builder.build_instruction_tuning_dataset(
            chapters, max_samples_per_book=2
        )
        assert len(dataset) <= 2

    def test_build_continuation_dataset(self, tmp_path):
        """测试构建续写数据集"""
        _make_book_dir(tmp_path, "book_001", num_chapters=2)
        builder = DatasetBuilder(books_dir=str(tmp_path))
        chapters = builder.extract_chapters()

        dataset = builder.build_continuation_dataset(chapters, context_ratio=0.3)
        assert len(dataset) > 0
        assert all("context" in d for d in dataset)
        assert all("continuation" in d for d in dataset)
        assert all("book_id" in d for d in dataset)

    def test_save_and_load_jsonl(self, tmp_path):
        """测试 JSONL 保存和加载"""
        dataset = [
            {"instruction": "测试1", "input": "输入1", "output": "输出1"},
            {"instruction": "测试2", "input": "输入2", "output": "输出2"},
        ]
        builder = DatasetBuilder(output_dir=str(tmp_path))
        filepath = str(tmp_path / "test.jsonl")

        saved_path = builder.save_dataset(dataset, filepath, format="jsonl")
        assert Path(saved_path).exists()

        loaded = builder.load_dataset(saved_path)
        assert len(loaded) == 2
        assert loaded[0]["instruction"] == "测试1"

        # 验证是 JSONL 格式（每行一个 JSON）
        content = Path(saved_path).read_text(encoding="utf-8")
        lines = [l for l in content.strip().split("\n") if l]
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # 每行可独立解析

    def test_save_and_load_json(self, tmp_path):
        """测试 JSON 格式保存和加载"""
        dataset = [{"instruction": "测试", "input": "输入", "output": "输出"}]
        builder = DatasetBuilder(output_dir=str(tmp_path))
        filepath = str(tmp_path / "test.json")

        saved_path = builder.save_dataset(dataset, filepath, format="json")
        loaded = builder.load_dataset(saved_path)
        assert len(loaded) == 1

    def test_dataset_stats(self, tmp_path):
        """测试数据集统计"""
        _make_book_dir(tmp_path, "book_001", num_chapters=2)
        builder = DatasetBuilder(books_dir=str(tmp_path))
        chapters = builder.extract_chapters()
        dataset = builder.build_instruction_tuning_dataset(chapters)

        stats = builder.dataset_stats(dataset)
        assert stats["samples"] == len(dataset)
        assert stats["total_chars"] > 0
        assert "avg_input_chars" in stats
        assert "avg_output_chars" in stats
        assert "style_distribution" in stats

    def test_dataset_stats_empty(self):
        """测试空数据集统计"""
        builder = DatasetBuilder()
        stats = builder.dataset_stats([])
        assert stats["samples"] == 0

    def test_analyze_style_from_text(self):
        """测试文本风格分析"""
        builder = DatasetBuilder()
        text = (
            "月华如水，洒在青石小径上。竹影婆娑，随风轻摇。"
            '"你终于来了。"她轻声说道，眼中带着一丝期待。'
            "远处传来几声蛙鸣，和着溪水的潺潺声。"
        )
        result = builder.analyze_style_from_text(text)

        assert "avg_sentence_length" in result
        assert "dialogue_ratio" in result
        assert "description_ratio" in result
        assert "vocabulary_richness" in result
        assert "pace_indicator" in result
        assert result["char_count"] > 0
        assert result["sentence_count"] > 0
        assert 0 <= result["dialogue_ratio"] <= 1
        assert 0 <= result["description_ratio"] <= 1

    def test_analyze_style_empty_text(self):
        """测试空文本风格分析"""
        builder = DatasetBuilder()
        result = builder.analyze_style_from_text("")
        assert result["char_count"] == 0
        assert result["avg_sentence_length"] == 0


# ─── LoRATrainer 测试 ────────────────────────────────


class TestLoRATrainer:
    """LoRA 训练器测试"""

    def _make_config(self, tmp_path: Path) -> TrainConfig:
        return TrainConfig(
            base_model="qwen3:8b",
            adapter_name="test_adapter",
            adapter_type=AdapterType.STYLE,
            rank=16,
            alpha=32,
            dropout=0.05,
            num_epochs=2,
            batch_size=4,
            gradient_accumulation=2,
            learning_rate=2e-4,
            max_steps=100,
            warmup_steps=10,
            save_steps=50,
            output_dir=str(tmp_path / "adapters"),
            max_seq_length=2048,
        )

    def test_init(self, tmp_path):
        """测试初始化"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        assert trainer.config == config
        assert trainer._script_path is None

    def test_setup_environment(self, tmp_path):
        """测试环境检查"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        env = trainer.setup_environment()

        assert "python_version" in env
        assert "libraries" in env
        assert "available" in env
        assert "gpu_available" in env
        assert "transformers" in env["libraries"]
        assert "peft" in env["libraries"]
        assert "torch" in env["libraries"]

    def test_build_training_script_contains_components(self, tmp_path):
        """测试生成的训练脚本包含关键组件"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        script = trainer.build_training_script()

        assert "LoraConfig" in script
        assert "TrainingArguments" in script
        assert "Trainer" in script
        assert "BitsAndBytesConfig" in script
        assert "AutoModelForCausalLM" in script
        assert "AutoTokenizer" in script
        assert "DataCollatorForLanguageModeling" in script
        assert "save_pretrained" in script
        assert "paged_adamw_8bit" in script
        assert "CAUSAL_LM" in script

    def test_build_training_script_config_values(self, tmp_path):
        """测试脚本中包含配置值"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        script = trainer.build_training_script()

        assert "qwen3:8b" in script
        assert "r=16" in script
        assert "lora_alpha=32" in script
        assert "num_train_epochs=2" in script
        assert "learning_rate=0.0002" in script

    def test_validate_script_syntax(self, tmp_path):
        """测试脚本语法验证（ast.parse 通过）"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        assert trainer.validate_script_syntax() is True

    def test_dry_run(self, tmp_path):
        """测试 dry_run 模拟训练"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        result = trainer.dry_run()

        assert result["status"] == "dry_run_success"
        assert result["config_valid"] is True
        assert result["script_syntax_valid"] is True
        assert result["estimated_trainable_params"] > 0
        assert "script_path" in result
        assert Path(result["script_path"]).exists()
        assert "output_dir" in result

    def test_dry_run_invalid_config(self, tmp_path):
        """测试无效配置的 dry_run"""
        config = TrainConfig(base_model="", adapter_name="bad", output_dir=str(tmp_path))
        trainer = LoRATrainer(config)
        result = trainer.dry_run()
        assert result["status"] != "dry_run_success"
        assert result["config_valid"] is False

    def test_estimate_trainable_params(self, tmp_path):
        """测试可训练参数量估算"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)
        params = trainer.estimate_trainable_params()

        assert params > 0
        # rank=16, hidden_dim≈4096, 4 target_modules → 2*16*4096*4 = 524288
        assert params == 2 * 16 * 4096 * 4

    def test_estimate_trainable_params_large_model(self, tmp_path):
        """测试大模型参数量估算"""
        config = TrainConfig(
            base_model="qwen3:72b", rank=32, output_dir=str(tmp_path)
        )
        trainer = LoRATrainer(config)
        params = trainer.estimate_trainable_params()
        # 72b → hidden_dim=8192, rank=32, 4 targets → 2*32*8192*4
        assert params == 2 * 32 * 8192 * 4

    def test_get_training_script_path(self, tmp_path):
        """测试获取脚本路径"""
        config = self._make_config(tmp_path)
        trainer = LoRATrainer(config)

        # dry_run 前返回默认路径
        path = trainer.get_training_script_path()
        assert "test_adapter" in path
        assert path.endswith("train_lora.py")

        # dry_run 后返回实际路径
        trainer.dry_run()
        path2 = trainer.get_training_script_path()
        assert Path(path2).exists()


# ─── AdapterManager 测试 ─────────────────────────────


class TestAdapterManager:
    """适配器管理器测试"""

    def test_register_adapter(self, tmp_path):
        """测试注册适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        info = mgr.register_adapter(
            name="test_style",
            base_model="qwen3:8b",
            adapter_type=AdapterType.STYLE,
            description="测试文风适配器",
            tags=["仙侠", "文风"],
        )

        assert isinstance(info, AdapterInfo)
        assert info.name == "test_style"
        assert info.base_model == "qwen3:8b"
        assert info.adapter_type == AdapterType.STYLE

        # 验证目录和文件创建
        adapter_dir = tmp_path / "adapters" / "test_style"
        assert adapter_dir.exists()
        assert (adapter_dir / "metadata.json").exists()
        assert (adapter_dir / "adapter_config.json").exists()

    def test_load_adapter(self, tmp_path):
        """测试加载适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("test_load", "qwen3:8b", AdapterType.STYLE)

        loaded = mgr.load_adapter("test_load")
        assert loaded is not None
        assert loaded.name == "test_load"
        assert loaded.base_model == "qwen3:8b"

    def test_load_nonexistent_adapter(self, tmp_path):
        """测试加载不存在的适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        assert mgr.load_adapter("nonexistent") is None

    def test_list_adapters(self, tmp_path):
        """测试列出适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("adapter1", "qwen3:8b", AdapterType.STYLE)
        mgr.register_adapter("adapter2", "qwen3:14b", AdapterType.GENRE)
        mgr.register_adapter("adapter3", "qwen3:8b", AdapterType.DIALOGUE)

        all_adapters = mgr.list_adapters()
        assert len(all_adapters) == 3

        # 按类型过滤
        style_adapters = mgr.list_adapters(adapter_type=AdapterType.STYLE)
        assert len(style_adapters) == 1
        assert style_adapters[0].name == "adapter1"

    def test_activate_and_deactivate(self, tmp_path):
        """测试激活和取消激活"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("active_test", "qwen3:8b", AdapterType.STYLE)

        # 激活
        assert mgr.activate_adapter("active_test") is True
        active = mgr.get_active_adapter()
        assert active is not None
        assert active.name == "active_test"
        assert active.is_active is True

        # 取消激活
        mgr.deactivate_adapter()
        assert mgr.get_active_adapter() is None

    def test_activate_nonexistent(self, tmp_path):
        """测试激活不存在的适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        assert mgr.activate_adapter("nonexistent") is False

    def test_delete_adapter(self, tmp_path):
        """测试删除适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("to_delete", "qwen3:8b", AdapterType.STYLE)

        assert mgr.delete_adapter("to_delete") is True
        assert mgr.load_adapter("to_delete") is None
        assert not (tmp_path / "adapters" / "to_delete").exists()

    def test_delete_active_adapter(self, tmp_path):
        """测试删除激活状态的适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("active_to_delete", "qwen3:8b", AdapterType.STYLE)
        mgr.activate_adapter("active_to_delete")

        assert mgr.delete_adapter("active_to_delete") is True
        assert mgr.get_active_adapter() is None

    def test_merge_adapters(self, tmp_path):
        """测试合并适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("style_a", "qwen3:8b", AdapterType.STYLE, tags=["仙侠"])
        mgr.register_adapter("style_b", "qwen3:8b", AdapterType.STYLE, tags=["都市"])

        merged = mgr.merge_adapters(
            adapter_names=["style_a", "style_b"],
            merged_name="merged_style",
            weights=[0.6, 0.4],
        )

        assert merged is not None
        assert merged.name == "merged_style"
        assert "仙侠" in merged.tags
        assert "都市" in merged.tags
        assert "Merged from" in merged.description

        # 验证合并适配器已持久化
        assert mgr.load_adapter("merged_style") is not None

    def test_merge_adapters_equal_weights(self, tmp_path):
        """测试等权合并"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("a1", "qwen3:8b", AdapterType.STYLE)
        mgr.register_adapter("a2", "qwen3:8b", AdapterType.STYLE)

        merged = mgr.merge_adapters(["a1", "a2"], "merged_eq")
        assert merged is not None

    def test_merge_nonexistent_adapter(self, tmp_path):
        """测试合并不存在的适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("exists", "qwen3:8b", AdapterType.STYLE)

        result = mgr.merge_adapters(["exists", "nonexistent"], "bad_merge")
        assert result is None

    def test_export_and_import_adapter(self, tmp_path):
        """测试导出和导入适配器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("export_test", "qwen3:8b", AdapterType.STYLE)

        # 导出
        export_dir = tmp_path / "exports"
        exported_path = mgr.export_adapter("export_test", str(export_dir))
        assert exported_path != ""
        assert Path(exported_path).exists()

        # 导入（重命名）
        mgr2 = AdapterManager(adapters_dir=str(tmp_path / "adapters2"))
        imported = mgr2.import_adapter(exported_path, name="imported_test")
        assert imported is not None
        assert imported.name == "imported_test"
        assert imported.base_model == "qwen3:8b"

    def test_update_adapter_metadata(self, tmp_path):
        """测试更新元数据"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("update_test", "qwen3:8b", AdapterType.STYLE)

        result = mgr.update_adapter_metadata(
            "update_test",
            description="更新后的描述",
            trained_steps=500,
            training_loss=1.5,
            tags=["新标签"],
        )
        assert result is True

        loaded = mgr.load_adapter("update_test")
        assert loaded.description == "更新后的描述"
        assert loaded.trained_steps == 500
        assert loaded.training_loss == 1.5

    def test_get_adapter_stats(self, tmp_path):
        """测试适配器统计"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("stat1", "qwen3:8b", AdapterType.STYLE)
        mgr.register_adapter("stat2", "qwen3:14b", AdapterType.GENRE)
        mgr.activate_adapter("stat1")

        stats = mgr.get_adapter_stats()
        assert stats["total"] == 2
        assert "by_type" in stats
        assert stats["active_adapter"] == "stat1"
        assert "total_size_bytes" in stats

    def test_get_router_config(self, tmp_path):
        """测试获取路由配置"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("router_test", "qwen3:8b", AdapterType.STYLE)

        # 无激活时返回空
        assert mgr.get_router_config() == {}

        # 激活后返回配置
        mgr.activate_adapter("router_test")
        config = mgr.get_router_config()
        assert config["adapter_name"] == "router_test"
        assert config["base_model"] == "qwen3:8b"
        assert config["use_adapter"] is True

    def test_apply_to_model_router_with_mock(self, tmp_path):
        """测试应用到模型路由器（mock 对象）"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("router_apply", "qwen3:8b", AdapterType.STYLE)
        mgr.activate_adapter("router_apply")

        # Mock 一个支持 set_adapter 的路由器
        class MockRouter:
            def __init__(self):
                self.adapter = None

            def set_adapter(self, config):
                self.adapter = config

        mock_router = MockRouter()
        result = mgr.apply_to_model_router(mock_router)
        assert result is True
        assert mock_router.adapter is not None
        assert mock_router.adapter["adapter_name"] == "router_apply"

    def test_apply_to_model_router_unsupported(self, tmp_path):
        """测试应用到不支持的路由器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))
        mgr.register_adapter("router_unsup", "qwen3:8b", AdapterType.STYLE)
        mgr.activate_adapter("router_unsup")

        # 不支持适配器的对象
        class PlainObject:
            pass

        result = mgr.apply_to_model_router(PlainObject())
        assert result is False

    def test_apply_to_model_router_no_active(self, tmp_path):
        """测试无激活适配器时应用到路由器"""
        mgr = AdapterManager(adapters_dir=str(tmp_path / "adapters"))

        class MockRouter:
            def set_adapter(self, config):
                pass

        result = mgr.apply_to_model_router(MockRouter())
        assert result is False


# ─── 工厂函数测试 ────────────────────────────────────


class TestFactoryFunctions:
    """便捷工厂函数测试"""

    def test_create_dataset_builder(self):
        builder = create_dataset_builder()
        assert builder is not None
        assert isinstance(builder, DatasetBuilder)

    def test_create_lora_trainer(self):
        config = TrainConfig(base_model="qwen3:8b", adapter_name="test")
        trainer = create_lora_trainer(config)
        assert trainer is not None
        assert isinstance(trainer, LoRATrainer)

    def test_create_adapter_manager(self, tmp_path):
        mgr = create_adapter_manager(adapters_dir=str(tmp_path / "adapters"))
        assert mgr is not None
        assert isinstance(mgr, AdapterManager)


# ─── 集成测试 ────────────────────────────────────────


class TestFinetuneFrameworkIntegration:
    """端到端集成测试"""

    def test_full_pipeline(self, tmp_path):
        """完整流程：构建数据集 → 配置训练 → dry_run → 注册适配器"""
        # 1. 构造书籍数据
        books_dir = tmp_path / "books"
        _make_book_dir(books_dir, "book_integration", num_chapters=3, genre="仙侠")

        # 2. 构建数据集
        builder = DatasetBuilder(books_dir=str(books_dir), output_dir=str(tmp_path / "datasets"))
        chapters = builder.extract_chapters()
        assert len(chapters) > 0

        dataset = builder.build_instruction_tuning_dataset(chapters, style_focus=True)
        assert len(dataset) > 0

        # 保存数据集
        dataset_path = str(tmp_path / "datasets" / "train.jsonl")
        builder.save_dataset(dataset, dataset_path, format="jsonl")
        assert Path(dataset_path).exists()

        # 3. 配置训练
        config = TrainConfig(
            base_model="qwen3:8b",
            adapter_name="integration_adapter",
            adapter_type=AdapterType.STYLE,
            dataset=dataset,
            rank=16,
            alpha=32,
            num_epochs=1,
            max_steps=50,
            output_dir=str(tmp_path / "training_output"),
        )

        # 4. dry_run
        trainer = LoRATrainer(config)
        assert trainer.validate_script_syntax() is True

        dry_result = trainer.dry_run()
        assert dry_result["status"] == "dry_run_success"
        assert dry_result["estimated_trainable_params"] > 0
        assert Path(dry_result["script_path"]).exists()

        # 5. 注册适配器
        adapters_dir = tmp_path / "adapters"
        mgr = AdapterManager(adapters_dir=str(adapters_dir))
        info = mgr.register_adapter(
            name="integration_adapter",
            base_model="qwen3:8b",
            adapter_type=AdapterType.STYLE,
            source_dataset=dataset_path,
            description="集成测试适配器",
            tags=["仙侠", "集成测试"],
        )
        assert info is not None

        # 6. 激活并获取路由配置
        assert mgr.activate_adapter("integration_adapter") is True
        router_config = mgr.get_router_config()
        assert router_config["adapter_name"] == "integration_adapter"
        assert router_config["use_adapter"] is True

        # 7. 验证统计
        stats = mgr.get_adapter_stats()
        assert stats["total"] == 1
        assert stats["active_adapter"] == "integration_adapter"

    def test_dataset_to_continuation_pipeline(self, tmp_path):
        """数据集构建 → 续写格式 → 保存加载 流程"""
        books_dir = tmp_path / "books"
        _make_book_dir(books_dir, "book_cont", num_chapters=2)

        builder = DatasetBuilder(books_dir=str(books_dir))
        chapters = builder.extract_chapters()

        # 构建续写数据集
        cont_dataset = builder.build_continuation_dataset(chapters, context_ratio=0.3)
        assert len(cont_dataset) > 0

        # 保存并重新加载
        path = str(tmp_path / "continuation.jsonl")
        builder.save_dataset(cont_dataset, path)
        loaded = builder.load_dataset(path)
        assert len(loaded) == len(cont_dataset)

        # 统计
        stats = builder.dataset_stats(loaded)
        assert stats["samples"] == len(loaded)

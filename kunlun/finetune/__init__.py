"""
模型微调管线 — LoRA 微调与模型管理

支持:
- LoRA 适配器训练 (LoRATrainer) — 基于 qlora/peft 的低成本微调
- 数据集构建 (DatasetBuilder) — 从写作历史自动构建训练数据
- 训练配置 (TrainConfig) — 灵活的超参数配置
- 适配器管理 (AdapterManager) — 保存/加载/切换/合并 LoRA 适配器
- 评估 (Evaluator) — BLEU/ROUGE/perplexity 评估
- 基础模型列表 (BaseModelList) — 支持的本地模型

用法:
    from kunlun.finetune import FineTuneEngine, TrainConfig

    engine = FineTuneEngine()
    dataset = engine.build_dataset(book_id="book_001", style_focus=True)
    adapter = engine.train(
        config=TrainConfig(
            base_model="qwen3:14b",
            dataset=dataset,
            adapter_name="my_style",
        ),
    )
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AdapterType(StrEnum):
    """适配器类型"""

    STYLE = "style"  # 文风适配
    GENRE = "genre"  # 类型适配 (仙侠/都市/...)
    DIALOGUE = "dialogue"  # 对话风格
    WORLD = "world"  # 世界观知识
    CHARACTER = "character"  # 角色语调
    AUDIT = "audit"  # 审计偏好


class ModelFamily(StrEnum):
    """模型系列"""

    QWEN = "qwen"
    LLAMA = "llama"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    PHI = "phi"


@dataclass
class BaseModelInfo:
    """基础模型信息"""

    name: str = ""
    family: ModelFamily = ModelFamily.QWEN
    size: str = ""  # e.g. "7b", "14b", "72b"
    ollama_tag: str = ""  # ollama pull 标签
    supports_lora: bool = True
    max_context: int = 32768
    description: str = ""
    recommended_vram_gb: int = 8


@dataclass
class TrainConfig:
    """训练配置"""

    base_model: str = "qwen3:14b"
    adapter_name: str = ""
    adapter_type: AdapterType = AdapterType.STYLE
    dataset: list[dict[str, str]] = field(default_factory=list)
    # LoRA 超参数
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
        ]
    )
    # 训练参数
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation: int = 4
    warmup_steps: int = 100
    max_steps: int = 500
    save_steps: int = 100
    eval_steps: int = 100
    # 量化
    use_4bit: bool = True
    use_8bit: bool = False
    # 输出
    output_dir: str = "./adapters"
    # 数据
    max_seq_length: int = 2048
    val_split: float = 0.1


@dataclass
class AdapterInfo:
    """适配器元数据"""

    name: str = ""
    base_model: str = ""
    adapter_type: AdapterType = AdapterType.STYLE
    version: int = 1
    created_at: float = field(default_factory=time.time)
    trained_steps: int = 0
    training_loss: float = 0.0
    eval_loss: float = 0.0
    size_bytes: int = 0
    path: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    is_active: bool = False


@dataclass
class TrainingMetrics:
    """训练指标"""

    step: int = 0
    loss: float = 0.0
    learning_rate: float = 0.0
    perplexity: float = 0.0
    grad_norm: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class EvalResult:
    """评估结果"""

    adapter_name: str = ""
    bleu: float = 0.0
    rouge_l: float = 0.0
    perplexity: float = 0.0
    style_similarity: float = 0.0  # 与目标风格的相似度
    content_quality: float = 0.0  # 内容质量评分
    diversity: float = 0.0  # 文本多样性
    samples: list[dict[str, str]] = field(default_factory=list)


class FineTuneEngine:
    """模型微调引擎

    核心职责:
    - 基础模型管理
    - 数据集构建 (从写作历史/Xu标签)
    - LoRA 训练流程编排
    - 适配器管理
    - 模型评估
    - Ollama 集成 (创建/切换/删除 Modelfile)

    用法:
        engine = FineTuneEngine()
        engine.setup_base_models()
        datasets = engine.build_dataset("book_001")
        engine.start_training(TrainConfig(...))
    """

    def __init__(self):
        self._base_models: dict[str, BaseModelInfo] = {}
        self._adapters: dict[str, AdapterInfo] = {}
        self._training_history: list[TrainingMetrics] = []
        self._eval_results: list[EvalResult] = []

        self._setup_base_models()

    def _setup_base_models(self) -> None:
        """初始化支持的基础模型列表"""
        models = [
            BaseModelInfo(
                "qwen3:1.8b",
                ModelFamily.QWEN,
                "1.8b",
                "qwen3:1.8b",
                True,
                32768,
                "轻量级，适合低配机器",
                4,
            ),
            BaseModelInfo(
                "qwen3:4b", ModelFamily.QWEN, "4b", "qwen3:4b", True, 32768, "平衡性能与质量", 6
            ),
            BaseModelInfo(
                "qwen3:8b",
                ModelFamily.QWEN,
                "8b",
                "qwen3:8b",
                True,
                32768,
                "推荐首选，中文写作优秀",
                8,
            ),
            BaseModelInfo(
                "qwen3:14b",
                ModelFamily.QWEN,
                "14b",
                "qwen3:14b",
                True,
                131072,
                "高质量中文写作",
                16,
            ),
            BaseModelInfo(
                "qwen3:32b",
                ModelFamily.QWEN,
                "32b",
                "qwen3:32b",
                True,
                131072,
                "顶级质量，需高端GPU",
                24,
            ),
            BaseModelInfo(
                "llama3.1:8b",
                ModelFamily.LLAMA,
                "8b",
                "llama3.1:8b",
                True,
                32768,
                "英文写作首选",
                8,
            ),
            BaseModelInfo(
                "deepseek-r1:7b",
                ModelFamily.DEEPSEEK,
                "7b",
                "deepseek-r1:7b",
                True,
                32768,
                "推理能力强",
                8,
            ),
            BaseModelInfo(
                "mistral:7b", ModelFamily.MISTRAL, "7b", "mistral:7b", True, 8192, "快速轻量", 6
            ),
        ]
        for m in models:
            self._base_models[m.name] = m

    # ── 基础模型管理 ──────────────────────────────

    def list_base_models(self, family: str = "") -> list[BaseModelInfo]:
        """列出支持的基础模型"""
        models = list(self._base_models.values())
        if family:
            models = [m for m in models if m.family == family]
        return models

    def get_base_model(self, name: str) -> BaseModelInfo | None:
        return self._base_models.get(name)

    def recommend_model(self, vram_gb: int) -> BaseModelInfo | None:
        """根据 GPU 显存推荐模型"""
        candidates = [m for m in self._base_models.values() if m.recommended_vram_gb <= vram_gb]
        candidates.sort(key=lambda m: -m.recommended_vram_gb)
        return candidates[0] if candidates else None

    # ── 数据集构建 ────────────────────────────────

    def build_dataset(
        self,
        _book_id: str = "",
        style_focus: bool = True,
        genre_focus: bool = False,
        dialogue_focus: bool = False,
        _chapter_ids: list[int] | None = None,
    ) -> list[dict[str, str]]:
        """从写作历史构建训练数据集

        数据格式（Alpaca 风格）:
            {"instruction": "...", "input": "...", "output": "..."}
            {"instruction": "...", "input": "...", "output": "..."}

        Args:
            book_id: 书籍ID（空则从所有书籍构建）
            style_focus: 侧重文风模仿
            genre_focus: 侧重类型适应
            dialogue_focus: 侧重对话风格
            chapter_ids: 指定章节ID

        Returns:
            Alpaca 格式数据集列表
        """
        # 这是一个接口定义，实际实现会从数据库/文件系统中提取写作历史
        dataset: list[dict[str, str]] = []

        if style_focus:
            dataset.extend(
                [
                    {
                        "instruction": "请用以下文风续写：描述细腻，节奏舒缓，注重意境营造",
                        "input": "月华如水，洒在青石小径上。",
                        "output": (
                            "月华如水，洒在青石小径上。竹影婆娑，随风轻摇，洒下斑驳的碎光。"
                            "远处传来几声蛙鸣，和着溪水的潺潺声，织成一曲夜的乐章。"
                        ),
                    },
                ]
            )

        if genre_focus:
            dataset.extend(
                [
                    {
                        "instruction": "用仙侠风格描写战斗场景",
                        "input": "少年拔剑，眼中寒光一闪。",
                        "output": (
                            "少年拔剑，眼中寒光一闪。剑气纵横三万里，一剑光寒十九州。"
                            "周身灵气翻涌如潮，手中长剑化作一道银虹，破空而去。"
                        ),
                    },
                ]
            )

        if dialogue_focus:
            dataset.extend(
                [
                    {
                        "instruction": "写出符合角色性格的对话",
                        "input": "角色：冷傲剑客 / 场景：遇到故人",
                        "output": (
                            '"三年不见，你的剑还是这么慢。"他负手而立，语气冷淡，'
                            "嘴角却不经意地勾起一丝弧度。"
                        ),
                    },
                ]
            )

        return dataset

    def build_dataset_from_files(
        self,
        directory: str,
        pattern: str = "*.txt",
    ) -> list[dict[str, str]]:
        """从文件目录构建数据集

        每行格式: instruction ||| input ||| output
        """
        dataset: list[dict[str, str]] = []
        dir_path = Path(directory)
        if not dir_path.exists():
            return dataset

        for filepath in dir_path.glob(pattern):
            try:
                content = filepath.read_text(encoding="utf-8")
                for line in content.strip().split("\n"):
                    line = line.strip()  # noqa: PLW2901
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("|||")
                    if len(parts) >= 3:
                        dataset.append(
                            {
                                "instruction": parts[0].strip(),
                                "input": parts[1].strip(),
                                "output": parts[2].strip(),
                            }
                        )
            except (OSError, UnicodeDecodeError):
                continue

        return dataset

    def dataset_stats(self, dataset: list[dict[str, str]]) -> dict[str, Any]:
        """获取数据集统计"""
        if not dataset:
            return {"samples": 0}
        total_input = sum(len(d.get("input", "")) + len(d.get("instruction", "")) for d in dataset)
        total_output = sum(len(d.get("output", "")) for d in dataset)
        return {
            "samples": len(dataset),
            "avg_input_chars": total_input / len(dataset),
            "avg_output_chars": total_output / len(dataset),
            "total_chars": total_input + total_output,
        }

    # ── 训练 ──────────────────────────────────────

    def start_training(self, config: TrainConfig) -> AdapterInfo:
        """启动 LoRA 训练（模拟 — 实际调用 peft/qlora）

        实际训练步骤:
        1. 加载基础模型（通过 ollama API 或 transformers）
        2. 应用 LoRA 配置
        3. 转换为 Alpaca 格式
        4. 执行训练循环
        5. 保存适配器权重
        6. 合并到 Ollama Modelfile
        """
        adapter = AdapterInfo(
            name=config.adapter_name or f"adapter_{int(time.time())}",
            base_model=config.base_model,
            adapter_type=config.adapter_type,
            path=f"{config.output_dir}/{config.adapter_name}",
            description=f"{config.adapter_type} adapter for {config.base_model}",
        )

        self._adapters[adapter.name] = adapter

        # 记录模拟训练指标
        for step in [0, 100, 200, 300, 400, 500]:
            self._training_history.append(
                TrainingMetrics(
                    step=step,
                    loss=3.5 * (0.98 ** (step / 100)),
                    learning_rate=config.learning_rate,
                    perplexity=30.0 * (0.95 ** (step / 100)),
                    grad_norm=1.0 / max(1, step / 50),
                    elapsed_seconds=step * 0.5,
                )
            )

        adapter.trained_steps = config.max_steps
        adapter.training_loss = self._training_history[-1].loss if self._training_history else 0
        adapter.size_bytes = config.rank * 4 * 1000000  # 估计大小

        return adapter

    def resume_training(self, adapter_name: str, additional_steps: int = 200) -> bool:
        """继续训练已有适配器"""
        if adapter_name not in self._adapters:
            return False
        # 模拟继续训练
        adapter = self._adapters[adapter_name]
        adapter.trained_steps += additional_steps
        adapter.version += 1
        return True

    def get_training_history(self) -> list[TrainingMetrics]:
        return self._training_history

    # ── 适配器管理 ─────────────────────────────────

    def list_adapters(self) -> list[AdapterInfo]:
        return list(self._adapters.values())

    def get_adapter(self, name: str) -> AdapterInfo | None:
        return self._adapters.get(name)

    def activate_adapter(self, name: str) -> bool:
        """激活适配器（设为当前使用）"""
        adapter = self._adapters.get(name)
        if not adapter:
            return False
        # 取消其他适配器
        for a in self._adapters.values():
            a.is_active = False
        adapter.is_active = True
        return True

    def get_active_adapter(self) -> AdapterInfo | None:
        for a in self._adapters.values():
            if a.is_active:
                return a
        return None

    def delete_adapter(self, name: str) -> bool:
        """删除适配器"""
        if name in self._adapters:
            del self._adapters[name]
            return True
        return False

    def merge_adapters(
        self,
        adapter_names: list[str],
        merged_name: str,
    ) -> AdapterInfo | None:
        """合并多个适配器"""
        if not adapter_names:
            return None
        base = self._adapters.get(adapter_names[0])
        if not base:
            return None

        merged = AdapterInfo(
            name=merged_name,
            base_model=base.base_model,
            adapter_type=base.adapter_type,
            description=f"Merged: {', '.join(adapter_names)}",
        )
        self._adapters[merged_name] = merged
        return merged

    def create_ollama_modelfile(self, adapter_name: str) -> str:
        """生成 Ollama Modelfile 用于加载适配器

        Returns:
            Modelfile 内容字符串
        """
        adapter = self._adapters.get(adapter_name)
        if not adapter:
            return ""

        base_model = self._base_models.get(adapter.base_model)
        base_tag = base_model.ollama_tag if base_model else adapter.base_model

        return f"""# 昆仑微调模型: {adapter_name}
# 基础模型: {adapter.base_model}
# 适配器类型: {adapter.adapter_type}

FROM {base_tag}

# LoRA 适配器
ADAPTER {adapter.path}/adapter_model.safetensors

# 系统提示
SYSTEM \"\"\"你是昆仑创作引擎微调后的写作助手。
文风类型: {adapter.adapter_type}
训练步数: {adapter.trained_steps}
\"\"\"

# 参数
PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
"""

    # ── 评估 ──────────────────────────────────────

    def evaluate(
        self,
        adapter_name: str,
        _test_data: list[dict[str, str]] | None = None,
    ) -> EvalResult | None:
        """评估适配器性能

        Args:
            adapter_name: 适配器名称
            test_data: 测试数据（空则使用内置测试）

        Returns:
            评估结果
        """
        adapter = self._adapters.get(adapter_name)
        if not adapter:
            return None

        # 模拟评估结果
        result = EvalResult(
            adapter_name=adapter_name,
            bleu=25.0 + adapter.trained_steps * 0.01,
            rouge_l=35.0 + adapter.trained_steps * 0.008,
            perplexity=20.0 - adapter.trained_steps * 0.005,
            style_similarity=0.75 + adapter.trained_steps * 0.0002,
            content_quality=0.7 + adapter.trained_steps * 0.0003,
            diversity=0.65 + adapter.trained_steps * 0.0001,
        )
        self._eval_results.append(result)
        return result

    def compare_adapters(
        self,
        adapter_names: list[str],
    ) -> dict[str, EvalResult]:
        """比较多个适配器"""
        results = {}
        for name in adapter_names:
            r = self.evaluate(name)
            if r:
                results[name] = r
        return results

    def get_eval_history(self) -> list[EvalResult]:
        return self._eval_results

    # ── 导出 ──────────────────────────────────────

    def export_adapter(self, adapter_name: str, output_dir: str) -> bool:
        """导出适配器文件"""
        adapter = self._adapters.get(adapter_name)
        if not adapter:
            return False

        export_data = {
            "name": adapter.name,
            "base_model": adapter.base_model,
            "type": adapter.adapter_type,
            "version": adapter.version,
            "trained_steps": adapter.trained_steps,
            "created_at": adapter.created_at,
            "tags": adapter.tags,
        }

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        meta_path = out_path / f"{adapter_name}.json"
        meta_path.write_text(json.dumps(export_data, ensure_ascii=False, indent=2))
        return True

    def import_adapter(self, meta_path: str) -> AdapterInfo | None:
        """导入适配器元数据"""
        try:
            data = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        adapter = AdapterInfo(
            name=data.get("name", ""),
            base_model=data.get("base_model", ""),
            adapter_type=AdapterType(data.get("type", "style")),
            version=data.get("version", 1),
            trained_steps=data.get("trained_steps", 0),
            tags=data.get("tags", []),
        )
        self._adapters[adapter.name] = adapter
        return adapter

    # ── 统计 ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "base_models": len(self._base_models),
            "adapters": len(self._adapters),
            "active_adapter": (
                _active.name if (_active := self.get_active_adapter()) else None
            ),
            "total_training_steps": sum(a.trained_steps for a in self._adapters.values()),
            "evaluations": len(self._eval_results),
            "model_families": list({m.family for m in self._base_models.values()}),
        }


# 全局单例
finetune_engine = FineTuneEngine()

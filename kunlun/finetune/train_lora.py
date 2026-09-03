"""
LoRA 训练脚本生成器 — 框架级实现，dry-run 验证语法

不实际执行训练（环境无 GPU），只生成可运行的训练脚本并验证语法。
所有外部库（transformers/peft/torch）使用 try-except 延迟导入。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

from kunlun.finetune import TrainConfig


class LoRATrainer:
    """LoRA 训练器（框架级）

    生成完整的 QLoRA 训练脚本，支持语法验证和 dry-run 模拟。

    用法:
        trainer = LoRATrainer(config)
        result = trainer.dry_run()
        script_path = trainer.get_training_script_path()
    """

    def __init__(self, config: TrainConfig) -> None:
        self.config = config
        self._script_path: str | None = None

    # ── 环境检查 ──────────────────────────────────

    def setup_environment(self) -> dict[str, Any]:
        """检查训练环境

        Returns:
            环境信息字典，含各库可用性和 GPU 状态
        """
        env: dict[str, Any] = {
            "python_version": sys.version,
            "available": True,
            "libraries": {},
            "gpu_available": False,
            "gpu_count": 0,
            "gpu_name": "",
        }

        # 检查 transformers
        try:
            import transformers  # noqa: F401

            env["libraries"]["transformers"] = {
                "available": True,
                "version": getattr(transformers, "__version__", "unknown"),
            }
        except ImportError:
            env["libraries"]["transformers"] = {"available": False}
            env["available"] = False

        # 检查 peft
        try:
            import peft  # noqa: F401

            env["libraries"]["peft"] = {
                "available": True,
                "version": getattr(peft, "__version__", "unknown"),
            }
        except ImportError:
            env["libraries"]["peft"] = {"available": False}
            env["available"] = False

        # 检查 torch
        try:
            import torch

            env["libraries"]["torch"] = {
                "available": True,
                "version": getattr(torch, "__version__", "unknown"),
            }
            env["gpu_available"] = torch.cuda.is_available()
            env["gpu_count"] = torch.cuda.device_count()
            if env["gpu_available"]:
                env["gpu_name"] = torch.cuda.get_device_name(0)
        except ImportError:
            env["libraries"]["torch"] = {"available": False}
            env["available"] = False

        # 检查 datasets
        try:
            import datasets  # noqa: F401

            env["libraries"]["datasets"] = {
                "available": True,
                "version": getattr(datasets, "__version__", "unknown"),
            }
        except ImportError:
            env["libraries"]["datasets"] = {"available": False}

        # 检查 bitsandbytes
        try:
            import bitsandbytes  # noqa: F401

            env["libraries"]["bitsandbytes"] = {
                "available": True,
                "version": getattr(bitsandbytes, "__version__", "unknown"),
            }
        except ImportError:
            env["libraries"]["bitsandbytes"] = {"available": False}

        return env

    # ── 训练脚本生成 ──────────────────────────────

    def build_training_script(self) -> str:
        """生成完整的 LoRA 训练 Python 脚本

        Returns:
            训练脚本字符串（可直接保存为 .py 执行）
        """
        cfg = self.config
        target_modules_str = ", ".join(f'"{m}"' for m in cfg.target_modules)
        # Windows 路径反斜杠在生成的脚本字符串中会触发 Unicode 转义，统一转为正斜杠
        safe_output_dir = cfg.output_dir.replace("\\", "/")
        safe_base_model = cfg.base_model.replace("\\", "/")
        adapter_name = cfg.adapter_name or "lora_adapter"

        return f'''"""
QLoRA 微调训练脚本 — 由昆仑创作引擎 LoRATrainer 自动生成
基础模型: {safe_base_model}
适配器: {adapter_name}
LoRA rank: {cfg.rank}, alpha: {cfg.alpha}
"""

import json
import os
import sys
from pathlib import Path

# ── 延迟导入（确保无库环境下语法可解析）──────────
try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import Dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("警告: transformers/peft/torch 未安装，无法执行训练")


def load_dataset_from_jsonl(filepath, max_length={cfg.max_seq_length}):
    """从 JSONL 加载数据集并 tokenize"""
    if not TRANSFORMERS_AVAILABLE:
        raise RuntimeError("transformers 未安装")

    raw_data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_data.append(json.loads(line))

    # 格式化为训练文本
    formatted = []
    for item in raw_data:
        instruction = item.get("instruction", "")
        inp = item.get("input", "")
        output = item.get("output", "")
        if instruction and inp:
            text = (
                f"### 指令:\\n{{instruction}}\\n\\n"
                f"### 输入:\\n{{inp}}\\n\\n"
                f"### 输出:\\n{{output}}"
            )
        else:
            text = output or inp
        formatted.append({{"text": text}})

    dataset = Dataset.from_list(formatted)

    tokenizer = AutoTokenizer.from_pretrained("{safe_base_model}", trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize_fn(examples):
        outputs = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )
        outputs["labels"] = outputs["input_ids"].copy()
        return outputs

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    return tokenized, tokenizer


def main():
    if not TRANSFORMERS_AVAILABLE:
        print(
            "错误: 缺少必要的训练库，"
            "请安装: pip install transformers peft torch datasets bitsandbytes"
        )
        sys.exit(1)

    # ── 配置 ──────────────────────────────────────
    base_model = "{safe_base_model}"
    output_dir = "{safe_output_dir}/{adapter_name}"
    dataset_path = os.environ.get("TRAIN_DATASET", "train.jsonl")

    os.makedirs(output_dir, exist_ok=True)

    # ── 4bit 量化配置 ─────────────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit={str(cfg.use_4bit).lower()},
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # ── 加载模型和 tokenizer ──────────────────────
    print(f"加载基础模型: {{base_model}}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = prepare_model_for_kbit_training(model)

    # ── LoRA 配置 ─────────────────────────────────
    lora_config = LoraConfig(
        r={cfg.rank},
        lora_alpha={cfg.alpha},
        lora_dropout={cfg.dropout},
        target_modules=[{target_modules_str}],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── 加载数据集 ────────────────────────────────
    print(f"加载数据集: {{dataset_path}}")
    tokenized_dataset, tokenizer = load_dataset_from_jsonl(dataset_path)

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # ── 训练参数 ──────────────────────────────────
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs={cfg.num_epochs},
        per_device_train_batch_size={cfg.batch_size},
        gradient_accumulation_steps={cfg.gradient_accumulation},
        learning_rate={cfg.learning_rate},
        warmup_steps={cfg.warmup_steps},
        max_steps={cfg.max_steps},
        save_steps={cfg.save_steps},
        logging_steps=10,
        fp16=True,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        save_total_limit=3,
        report_to="none",
    )

    # ── 初始化 Trainer ────────────────────────────
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    # ── 开始训练 ──────────────────────────────────
    print("开始训练...")
    train_result = trainer.train()

    # ── 保存适配器 ────────────────────────────────
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # ── 记录训练指标 ──────────────────────────────
    metrics = train_result.metrics
    metrics_path = os.path.join(output_dir, "training_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"训练完成！适配器已保存到: {{output_dir}}")
    print(f"训练指标: {{metrics}}")


if __name__ == "__main__":
    main()
'''

    # ── 语法验证 ──────────────────────────────────

    def validate_script_syntax(self) -> bool:
        """用 ast.parse 验证生成的训练脚本语法正确性

        Returns:
            True 表示语法正确
        """
        script = self.build_training_script()
        try:
            ast.parse(script)
            return True
        except SyntaxError:
            return False

    # ── Dry Run ──────────────────────────────────

    def dry_run(self) -> dict[str, Any]:
        """模拟训练流程

        验证配置 → 生成脚本 → 验证语法 → 创建输出目录 → 写入脚本文件

        Returns:
            模拟训练结果，含预估参数量、预估训练时间、脚本路径
        """
        cfg = self.config
        result: dict[str, Any] = {
            "status": "pending",
            "config_valid": True,
            "script_syntax_valid": False,
            "estimated_trainable_params": 0,
            "estimated_training_minutes": 0,
            "script_path": "",
            "output_dir": "",
            "environment": {},
        }

        # 1. 验证配置
        if not cfg.base_model:
            result["config_valid"] = False
            result["status"] = "failed: missing base_model"
            return result
        if cfg.rank <= 0:
            result["config_valid"] = False
            result["status"] = "failed: invalid rank"
            return result

        # 2. 环境检查
        result["environment"] = self.setup_environment()

        # 3. 生成脚本并验证语法
        script = self.build_training_script()
        try:
            ast.parse(script)
            result["script_syntax_valid"] = True
        except SyntaxError as e:
            result["script_syntax_valid"] = False
            result["status"] = f"failed: syntax error - {e}"
            return result

        # 4. 创建输出目录并写入脚本
        adapter_name = cfg.adapter_name or "lora_adapter"
        output_dir = Path(cfg.output_dir) / adapter_name
        output_dir.mkdir(parents=True, exist_ok=True)

        script_path = output_dir / "train_lora.py"
        script_path.write_text(script, encoding="utf-8")
        self._script_path = str(script_path)

        # 5. 估算
        result["estimated_trainable_params"] = self.estimate_trainable_params()

        # 预估训练时间（粗略：每1000样本约5分钟，基于batch和梯度累积）
        dataset_size = len(cfg.dataset) if cfg.dataset else 100
        steps = min(cfg.max_steps, (dataset_size // max(1, cfg.batch_size)) * cfg.num_epochs)
        # 每步约 0.5 分钟（含梯度累积），这是非常粗略的估计
        result["estimated_training_minutes"] = round(steps * 0.5 * cfg.gradient_accumulation, 1)

        result["script_path"] = str(script_path)
        result["output_dir"] = str(output_dir)
        result["status"] = "dry_run_success"

        return result

    # ── 参数量估算 ────────────────────────────────

    def estimate_trainable_params(self) -> int:
        """估算可训练参数量

        基于模型大小和 LoRA rank：
        约 = 2 * rank * hidden_dim * num_target_modules

        对于常见模型 hidden_dim 估算：
        - 7B: 4096
        - 8B: 4096
        - 14B: 5120
        - 32B: 5120
        - 70B+: 8192
        """
        cfg = self.config
        rank = cfg.rank
        num_targets = len(cfg.target_modules)

        # 从模型名估算 hidden_dim
        model_lower = cfg.base_model.lower()
        hidden_dim = 4096  # 默认 7B/8B
        if any(s in model_lower for s in ["14b", "32b", "30b"]):
            hidden_dim = 5120
        elif any(s in model_lower for s in ["70b", "65b", "72b"]):
            hidden_dim = 8192
        elif any(s in model_lower for s in ["1.8b", "2b", "1b"]):
            hidden_dim = 2048
        elif any(s in model_lower for s in ["4b", "3b"]):
            hidden_dim = 2560

        # LoRA 参数量 ≈ 2 * rank * hidden_dim * num_target_modules
        # （每个 target module 有 A 和 B 两个矩阵）
        return 2 * rank * hidden_dim * num_targets

    # ── 脚本路径 ──────────────────────────────────

    def get_training_script_path(self) -> str:
        """返回训练脚本保存路径

        如果尚未执行 dry_run，返回默认路径
        """
        if self._script_path:
            return self._script_path

        cfg = self.config
        adapter_name = cfg.adapter_name or "lora_adapter"
        return str(Path(cfg.output_dir) / adapter_name / "train_lora.py")

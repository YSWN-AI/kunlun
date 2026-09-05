"""
本地推理引擎 — 加载基座模型 + LoRA 适配器，提供 OpenAI 兼容生成接口

与 gacha 引擎集成：当 ModelCandidate.provider == "local" 时，
_call_llm 走本地推理路径而非 HTTP API。

设计原则：
- 单例模式，懒加载（首次调用时加载模型到 GPU）
- 支持多适配器切换（通过 adapter_name 加载不同 LoRA）
- OpenAI 格式消息 → 模型 chat template 转换
- 异步接口用 asyncio.to_thread 包装同步生成
- 显存管理：切换适配器时卸载旧模型
"""

from __future__ import annotations

import asyncio
import gc
from pathlib import Path
from typing import Any

import torch
from loguru import logger

# 全局单例
_engine: LocalInferenceEngine | None = None


class LocalInferenceEngine:
    """本地 LoRA 推理引擎

    用法:
        engine = LocalInferenceEngine.get_instance()
        engine.load_adapter("novel_style", base_model_path="...", adapter_path="...")
        result = await engine.chat([{"role": "user", "content": "写一章小说"}], max_tokens=512)
    """

    def __init__(self) -> None:
        self.model: Any | None = None
        self.tokenizer: Any | None = None
        self.current_adapter: str = ""
        self.current_base_model: str = ""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> LocalInferenceEngine:
        """获取全局单例"""
        global _engine
        if _engine is None:
            _engine = cls()
        return _engine

    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self.model is not None and self.tokenizer is not None

    def load_adapter(
        self,
        adapter_name: str,
        base_model_path: str,
        adapter_path: str,
        dtype: str = "float16",
        load_in_4bit: bool = False,
    ) -> bool:
        """加载基座模型 + LoRA 适配器（同步，应在线程中调用）

        Args:
            adapter_name: 适配器名称（用于标识）
            base_model_path: 基座模型路径（safetensors 格式）
            adapter_path: LoRA 适配器目录（含 adapter_config.json + adapter_model.safetensors）
            dtype: 数据类型
            load_in_4bit: 是否使用4bit量化（7B+模型在8GB显存上必须开启）

        Returns:
            True 表示成功
        """
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        # 如果已加载相同适配器，跳过
        if self.is_loaded() and self.current_adapter == adapter_name:
            logger.info(f"LocalInference: 适配器 {adapter_name} 已加载，跳过")
            return True

        # 卸载旧模型
        self.unload()

        logger.info(f"LocalInference: 加载基座模型 {base_model_path} (4bit={load_in_4bit})")
        torch_dtype = getattr(torch, dtype, torch.float16)

        self.tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        model_kwargs: dict[str, Any] = {
            "device_map": "auto" if self.device == "cuda" else None,
            "trust_remote_code": True,
        }

        if load_in_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            model_kwargs["quantization_config"] = bnb_config
            model_kwargs["dtype"] = torch_dtype
        else:
            model_kwargs["torch_dtype"] = torch_dtype

        base_model = AutoModelForCausalLM.from_pretrained(base_model_path, **model_kwargs)

        # 加载 LoRA 适配器
        adapter_dir = Path(adapter_path)
        if adapter_dir.exists() and (adapter_dir / "adapter_config.json").exists():
            logger.info(f"LocalInference: 加载 LoRA 适配器 {adapter_path}")
            self.model = PeftModel.from_pretrained(base_model, adapter_path)
        else:
            logger.warning(f"LocalInference: 适配器目录无效 {adapter_path}，使用基座模型")
            self.model = base_model

        self.model.eval()
        self.current_adapter = adapter_name
        self.current_base_model = base_model_path

        params = sum(p.numel() for p in self.model.parameters())
        logger.info(
            f"LocalInference: 模型加载完成，适配器={adapter_name}，"
            f"参数={params / 1e6:.1f}M，设备={self.device}"
        )
        return True

    def unload(self) -> None:
        """卸载模型，释放显存"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        self.current_adapter = ""
        self.current_base_model = ""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("LocalInference: 模型已卸载，显存已释放")

    def _messages_to_prompt(self, messages: list[dict]) -> str:
        """将 OpenAI 格式消息转换为模型输入文本

        使用 tokenizer.apply_chat_template（如果支持），否则手动拼接。
        """
        if self.tokenizer is None:
            raise RuntimeError("模型未加载")

        try:
            return self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            # 回退：手动拼接 Qwen 格式
            parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    parts.append(f"<|im_start|>system\n{content}<|im_end|>")
                elif role == "user":
                    parts.append(f"<|im_start|>user\n{content}<|im_end|>")
                elif role == "assistant":
                    parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
            parts.append("<|im_start|>assistant\n")
            return "\n".join(parts)

    def generate_sync(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
    ) -> dict:
        """同步生成（应在 asyncio.to_thread 中调用）

        Returns:
            {"content": str, "model": str, "usage": dict}
        """
        if not self.is_loaded():
            raise RuntimeError("模型未加载，请先调用 load_adapter()")

        assert self.model is not None
        assert self.tokenizer is not None

        prompt = self._messages_to_prompt(messages)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        input_len = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else 1.0,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = outputs[0][input_len:]
        content = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        output_len = len(generated_ids)
        return {
            "content": content,
            "model": f"local:{self.current_adapter}",
            "usage": {
                "prompt_tokens": input_len,
                "completion_tokens": output_len,
                "total_tokens": input_len + output_len,
            },
        }

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> dict:
        """异步生成接口（与 gacha _call_llm 返回格式一致）

        Returns:
            {"content": str, "model": str, "usage": dict}
        """
        return await asyncio.to_thread(
            self.generate_sync,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **{k: v for k, v in kwargs.items() if k in ("top_p", "repetition_penalty")},
        )

    def get_info(self) -> dict:
        """获取当前引擎状态"""
        return {
            "loaded": self.is_loaded(),
            "adapter": self.current_adapter,
            "base_model": self.current_base_model,
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "cuda_memory_gb": (
                torch.cuda.get_device_properties(0).total_memory / 1e9
                if torch.cuda.is_available()
                else 0
            ),
        }


# ── 便捷函数 ──────────────────────────────────────


def get_local_engine() -> LocalInferenceEngine:
    """获取全局本地推理引擎单例"""
    return LocalInferenceEngine.get_instance()


def is_local_model(model_name: str) -> bool:
    """判断模型名是否为本地模型（以 local: 开头或在本地模型列表中）"""
    return model_name.startswith("local:") or model_name in _LOCAL_MODEL_NAMES


# 本地模型名称注册表（由 model_router 或配置填充）
_LOCAL_MODEL_NAMES: set[str] = set()


def register_local_model(name: str) -> None:
    """注册本地模型名称"""
    _LOCAL_MODEL_NAMES.add(name)

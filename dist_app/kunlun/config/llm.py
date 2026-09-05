"""
昆仑创作引擎 — LLM配置 (API密钥、成本控制、超时值、本地模型)
"""

from __future__ import annotations

from pydantic import BaseModel

from kunlun.config.defaults import (
    DEFAULT_LLM_MODE,
    DEFAULT_LOCAL_MODEL,
)


class LLMConfig(BaseModel):
    # ── LLM 运行模式 ──────────────────────────────
    llm_mode: str = DEFAULT_LLM_MODE  # "local" | "api" | "auto"
    llm_local_model: str = DEFAULT_LOCAL_MODEL
    ollama_host: str = "http://localhost:11434"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_keys_backup: str = ""

    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    llm_max_tokens_per_request: int = 4096
    llm_max_calls_per_hour: int = 60
    llm_daily_token_budget: int = 500000

    llm_call_timeout: float = 120.0
    llm_stream_timeout: float = 120.0
    kg_query_timeout: float = 30.0
    auto_fix_timeout: float = 60.0
    http_request_timeout: float = 10.0

    circuit_breaker_recovery_timeout: float = 30.0
    circuit_breaker_window_seconds: int = 60
    circuit_breaker_min_calls_before_break: int = 3

    model_config = {"extra": "ignore"}

    def is_local_mode(self) -> bool:
        return self.llm_mode == "local"

    def is_api_mode(self) -> bool:
        return self.llm_mode == "api"

    def validate_api_keys(self) -> list[str]:
        missing = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")
        return missing

    def get_all_api_keys(self) -> list[str]:
        keys = []
        if self.openai_api_key:
            keys.append(self.openai_api_key)
        if self.openai_api_keys_backup:
            keys.extend(k.strip() for k in self.openai_api_keys_backup.split(",") if k.strip())
        return list(dict.fromkeys(keys))

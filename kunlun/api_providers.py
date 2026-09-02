"""
昆仑创作引擎 — 多 API 提供商注册表

支持任意 OpenAI 兼容 API 一键接入。
预置 20+ 提供商模板，自动检测可用模型。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_FILE = PROJECT_ROOT / "data" / "configs" / "api_providers.json"


@dataclass
class ApiProvider:
    """API 提供商配置"""

    name: str  # 显示名称
    key: str  # 唯一标识
    base_url: str  # API 地址
    models: list = field(default_factory=list)  # 已知模型列表
    description: str = ""  # 描述
    requires_key: bool = True  # 是否需要 key
    default_model: str = ""  # 默认模型


# 预置提供商模板
PRESET_PROVIDERS: list[ApiProvider] = [
    ApiProvider(
        name="DeepSeek 官方",
        key="deepseek",
        base_url="https://api.deepseek.com",
        models=["deepseek-chat", "deepseek-reasoner"],
        description="DeepSeek 官方 API，国内可直接访问",
        default_model="deepseek-chat",
    ),
    ApiProvider(
        name="OpenAI 官方",
        key="openai",
        base_url="https://api.openai.com/v1",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"],
        description="OpenAI 官方 API（需海外访问）",
        default_model="gpt-4o-mini",
    ),
    ApiProvider(
        name="Anthropic Claude (兼容)",
        key="anthropic_compat",
        base_url="https://api.anthropic.com/v1",
        models=["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-haiku-3-5"],
        description="Anthropic Claude API（兼容模式）",
        default_model="claude-sonnet-4-20250514",
    ),
    ApiProvider(
        name="Gemini (OpenAI 兼容)",
        key="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        description="Google Gemini API（OpenAI 兼容端点）",
        default_model="gemini-2.5-flash",
    ),
    ApiProvider(
        name="阿里百炼 (Qwen)",
        key="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-max", "qwen-plus", "qwen-turbo", "qwen3-235b-a22b"],
        description="阿里云通义千问（OpenAI 兼容）",
        default_model="qwen-plus",
    ),
    ApiProvider(
        name="智谱 GLM",
        key="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        models=["glm-4", "glm-4-flash", "glm-4-plus"],
        description="智谱 AI GLM 系列",
        default_model="glm-4-flash",
    ),
    ApiProvider(
        name="Moonshot (Kimi)",
        key="moonshot",
        base_url="https://api.moonshot.cn/v1",
        models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        description="月之暗面 Kimi（超长上下文）",
        default_model="moonshot-v1-32k",
    ),
    ApiProvider(
        name="硅基流动 (SiliconFlow)",
        key="siliconflow",
        base_url="https://api.siliconflow.cn/v1",
        models=["Qwen/Qwen2.5-7B-Instruct", "deepseek-ai/DeepSeek-V3", "Pro/Llama-4-Maverick"],
        description="硅基流动 — 国内可访问，免费额度",
        default_model="deepseek-ai/DeepSeek-V3",
    ),
    ApiProvider(
        name="Groq (超快推理)",
        key="groq",
        base_url="https://api.groq.com/openai/v1",
        models=["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "mixtral-8x7b-32768"],
        description="Groq — LPU超快推理，有免费额度",
        default_model="deepseek-r1-distill-llama-70b",
    ),
    ApiProvider(
        name="Together AI",
        key="together",
        base_url="https://api.together.xyz/v1",
        models=["meta-llama/Llama-4-Maverick-17B-128E", "deepseek-ai/DeepSeek-V3"],
        description="Together AI — 开源模型托管",
        default_model="deepseek-ai/DeepSeek-V3",
    ),
    ApiProvider(
        name="Ollama 本地",
        key="ollama",
        base_url="http://localhost:11434/v1",
        models=["llama3", "qwen2.5", "deepseek-r1", "mistral"],
        description="本地 Ollama 服务 — 完全免费，无需联网",
        requires_key=False,
        default_model="qwen2.5",
    ),
    ApiProvider(
        name="vLLM / LocalAI",
        key="vllm",
        base_url="http://localhost:8000/v1",
        models=["default"],
        description="本地 vLLM / LocalAI / text-generation-webui",
        requires_key=False,
        default_model="default",
    ),
    ApiProvider(
        name="自定义 OpenAI 兼容",
        key="custom",
        base_url="https://your-api.com/v1",
        models=["gpt-3.5-turbo"],
        description="任意 OpenAI 兼容 API 端点",
        default_model="gpt-3.5-turbo",
    ),
]


def load_providers() -> list[dict]:
    """加载提供商配置（优先用户自定义，回退到预置）"""
    if PROVIDERS_FILE.exists():
        try:
            data = json.loads(PROVIDERS_FILE.read_text(encoding="utf-8"))
            return data.get("providers", [])
        except Exception:
            logger.debug("加载用户自定义提供商配置失败，回退到预置模板")

    # Convert presets to dict
    return [
        {
            "name": p.name,
            "key": p.key,
            "base_url": p.base_url,
            "models": p.models,
            "description": p.description,
            "requires_key": p.requires_key,
            "default_model": p.default_model,
        }
        for p in PRESET_PROVIDERS
    ]


def save_providers(providers: list[dict]):
    """保存用户自定义的提供商配置"""
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROVIDERS_FILE.write_text(
        json.dumps({"providers": providers, "updated": None}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_provider(key: str) -> dict | None:
    """获取指定提供商"""
    for p in load_providers():
        if p["key"] == key:
            return p
    return None


async def detect_models(base_url: str, api_key: str = "") -> list[str]:
    """检测 API 端点可用的模型列表"""
    try:
        import httpx

        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", [])]
                return models[:50]
    except Exception:
        logger.debug(f"自动检测模型列表失败: {base_url}")
    return []


async def test_connection(base_url: str, api_key: str, model: str) -> dict:
    """测试 API 连接是否正常"""
    try:
        import httpx
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key or "no-key",
            base_url=base_url,
            timeout=httpx.Timeout(15.0, connect=10.0),
        )
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "回复：OK"}],
            max_tokens=10,
        )
        choices = response.choices
        if not choices:
            return {"ok": False, "error": "API 返回空 choices"}
        return {
            "ok": True,
            "model": model,
            "response": (choices[0].message.content or "")[:50],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

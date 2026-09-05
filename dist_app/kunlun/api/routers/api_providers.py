"""
昆仑创作引擎 — API 提供商路由
/api-providers, /api-providers/test, /api-providers/configure, /api-providers/current
"""

import os
from pathlib import Path

from fastapi import APIRouter
from loguru import logger

router = APIRouter(tags=["API配置"])


@router.get("/api-providers", summary="获取所有 API 提供商配置")
async def list_api_providers() -> dict:
    """返回预设 + 用户自定义的 API 提供商列表"""
    from kunlun.api_providers import load_providers

    providers = load_providers()
    return {"success": True, "providers": providers}


@router.post("/api-providers/test", summary="测试 API 连接")
async def test_api_connection(req: dict) -> dict:
    """测试指定 API 配置是否可用"""
    from kunlun.api_providers import detect_models, test_connection

    base_url = req.get("base_url", "")
    api_key = req.get("api_key", "")
    model = req.get("model", "gpt-3.5-turbo")

    if not base_url:
        return {"success": False, "error": "缺少 base_url"}

    models = await detect_models(base_url, api_key)
    result = await test_connection(base_url, api_key, model)
    return {"success": result["ok"], "connection": result, "available_models": models}


@router.post("/api-providers/configure", summary="快速配置 API（一键切换）")
async def configure_api(req: dict) -> dict:
    """一键配置 API 提供商。自动更新 .env 中的对应字段并重载配置。"""
    from kunlun.api_providers import get_provider

    provider_key = req.get("provider", "custom")
    base_url = req.get("base_url", "")
    api_key = req.get("api_key", "")
    model = req.get("model", "")

    preset = get_provider(provider_key)
    if preset:
        base_url = base_url or preset.get("base_url", "")
        model = model or preset.get("default_model", "")

    if not base_url:
        return {"success": False, "error": "缺少 base_url"}

    # Update .env
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8")
        lines = env_content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("DEEPSEEK_API_KEY="):
                new_lines.append(f"DEEPSEEK_API_KEY={api_key}")
            elif line.startswith("DEEPSEEK_BASE_URL="):
                new_lines.append(f"DEEPSEEK_BASE_URL={base_url}")
            elif line.startswith("OPENAI_API_KEY="):
                new_lines.append(f"OPENAI_API_KEY={api_key}")
            elif line.startswith("OPENAI_BASE_URL="):
                new_lines.append(f"OPENAI_BASE_URL={base_url}")
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines), encoding="utf-8")

    # Update model router default
    try:
        from kunlun.model_router import model_router

        model_router.set("writer", model, "openai_compat")
        model_router.set("architect", model, "openai_compat")
        model_router.set("auditor", model, "openai_compat")
    except Exception as e:
        logger.debug(f"Model Router 配置跳过: {e}")

    os.environ["DEEPSEEK_API_KEY"] = api_key
    os.environ["DEEPSEEK_BASE_URL"] = base_url
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = base_url

    return {
        "success": True,
        "message": f"已切换到 {provider_key}，模型: {model}",
        "provider": provider_key,
        "base_url": base_url,
        "model": model,
    }


@router.get("/api-providers/current", summary="获取当前 API 配置")
async def current_api_config() -> dict:
    """查看当前生效的 API 配置"""
    from kunlun.config import settings
    from kunlun.model_router import model_router

    return {
        "success": True,
        "config": {
            "openai_base_url": settings.openai_base_url,
            "deepseek_base_url": settings.deepseek_base_url,
            "has_openai_key": bool(settings.openai_api_key),
            "has_deepseek_key": bool(settings.deepseek_api_key),
            "has_anthropic_key": bool(settings.anthropic_api_key),
        },
        "model_routing": {
            agent: {"model": cfg["model"], "provider": cfg.get("provider", "")}
            for agent, cfg in model_router.list_all().items()
        },
    }

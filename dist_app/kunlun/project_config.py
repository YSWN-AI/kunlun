"""
昆仑 Project Config — 统一项目配置（参考 inkos.json）
管理 kunlun.json 项目级配置 + .env 密钥 + model_routing.json

用法:
  kunlun config show          — 查看配置
  kunlun config show-global   — 查看全局 LLM 配置
  kunlun config set <k> <v>   — 设置配置
  kunlun config set-model     — 设置 Agent 模型
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KUNLUN_JSON = PROJECT_ROOT / "kunlun.json"


@dataclass
class KunlunProject:
    """kunlun.json 项目配置"""

    name: str = "昆仑创作项目"
    version: str = "0.2.0"
    language: str = "zh"

    # LLM
    llm: dict = field(
        default_factory=lambda: {
            "provider": "openai_compat",
            "baseUrl": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "temperature": 0.7,
            "stream": True,
        }
    )

    # Daemon
    daemon: dict = field(
        default_factory=lambda: {
            "enabled": False,
            "schedule": {
                "writeInterval": 15,  # minutes
                "radarInterval": 360,  # minutes (6h)
            },
            "maxConcurrentBooks": 2,
        }
    )

    # Output
    output: dict = field(
        default_factory=lambda: {
            "defaultWordCount": 2800,
            "defaultPlatform": "tomato",
        }
    )


def load_config() -> KunlunProject:
    """加载项目配置"""
    if KUNLUN_JSON.exists():
        try:
            data = json.loads(KUNLUN_JSON.read_text(encoding="utf-8"))
            config = KunlunProject()
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            return config
        except (json.JSONDecodeError, Exception):
            logger.debug("kunlun.json 配置加载失败，使用默认配置")
    return KunlunProject()


def save_config(config: KunlunProject):
    """保存项目配置"""
    data = asdict(config)
    KUNLUN_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def show_config():
    """显示项目配置"""
    config = load_config()
    print()
    print("  项目配置 (kunlun.json)")
    print("  " + "=" * 50)
    print()

    print(f"  项目名: {config.name}")
    print(f"  语言: {config.language}")
    print()

    print("  [LLM 配置]")
    llm = config.llm
    print(f"    Provider: {llm.get('provider', '-')}")
    print(f"    Base URL: {llm.get('baseUrl', '-')}")
    print(f"    Model: {llm.get('model', '-')}")
    print(f"    Temperature: {llm.get('temperature', '-')}")
    print(f"    Stream: {llm.get('stream', '-')}")
    print()

    print("  [守护进程]")
    d = config.daemon
    print(f"    Enabled: {d.get('enabled', False)}")
    print(f"    写入间隔: {d['schedule'].get('writeInterval', '-')} 分钟")
    print(f"    情报间隔: {d['schedule'].get('radarInterval', '-')} 分钟")
    print(f"    并发书籍: {d.get('maxConcurrentBooks', '-')}")
    print()

    print("  [输出设置]")
    o = config.output
    print(f"    默认字数: {o.get('defaultWordCount', '-')}")
    print(f"    默认平台: {o.get('defaultPlatform', '-')}")
    print()

    _show_model_routing()
    _show_api_keys()


def show_global():
    """显示全局 LLM 配置"""
    print()
    print("  全局 LLM 配置 (~/.inkos/.env 风格)")
    print("  " + "=" * 50)
    print()
    _show_api_keys()
    _show_model_routing()


def _show_api_keys():
    """显示 API Key 配置（脱敏）"""
    from kunlun.config import settings

    print("  [API Keys]")
    for var in ["ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
        val = getattr(settings, var, None)
        if val and len(str(val)) > 10:
            masked = str(val)[:8] + "***" + str(val)[-4:]
            print(f"    {var}: {masked}")
        else:
            print(f"    {var}: (未配置)")
    print()


def _show_model_routing():
    """显示模型路由"""
    try:
        from kunlun.model_router import model_router

        print("  [模型路由]")
        for agent, cfg in model_router.list_all().items():
            print(f"    {agent}: {cfg['model']} ({cfg.get('provider', '-')})")
        print()
    except Exception:
        logger.debug("模型路由配置显示失败")


def set_config(key: str, value: str):
    """设置配置值 - 支持点号路径如 llm.model"""
    config = load_config()

    parts = key.split(".")
    obj = config

    # Navigate to the nested object
    for part in parts[:-1]:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        elif isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            print(f"  配置路径不存在: {key}")
            return

    last = parts[-1]

    # Type conversion
    if isinstance(obj, dict):
        if isinstance(obj.get(last), bool):
            obj[last] = value.lower() in ("true", "1", "yes")
        elif isinstance(obj.get(last), (int, float)):
            try:
                obj[last] = int(value) if isinstance(obj[last], int) else float(value)
            except ValueError:
                obj[last] = value
        else:
            obj[last] = value
    elif hasattr(obj, last):
        current = getattr(obj, last)
        if isinstance(current, bool):
            setattr(obj, last, value.lower() in ("true", "1", "yes"))
        elif isinstance(current, (int, float)):
            try:
                setattr(obj, last, int(value) if isinstance(current, int) else float(value))
            except ValueError:
                setattr(obj, last, value)
        else:
            setattr(obj, last, value)

    save_config(config)
    print(f"  {key} = {value}")


def set_model(agent: str, model: str, provider: str = "openai_compat"):
    """设置 Agent 模型"""
    from kunlun.model_router import model_router

    model_router.set(agent, model, provider)
    print(f"  {agent} -> {model} ({provider})")


def init_project(name: str = "昆仑创作项目"):
    """初始化项目配置文件"""
    if KUNLUN_JSON.exists():
        print("  kunlun.json 已存在")
        return

    config = KunlunProject(name=name)
    save_config(config)
    print(f"  项目已初始化: {name}")
    print(f"  配置文件: {KUNLUN_JSON}")

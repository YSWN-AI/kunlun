"""
昆仑创作引擎 — 交互式配置初始化向导

对标 AI_NovelGenerator 的 config.json 易用性，提供命令行交互式问答配置。

用法:
  python kunlun_cli.py setup              # 交互式问答
  python kunlun_cli.py setup --defaults  # 非交互式，全部使用默认值
"""

from __future__ import annotations

import getpass
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


# ── 颜色辅助 ──────────────────────────────────
class _NoColor:
    def __getattr__(self, name):
        return ""


try:
    from colorama import Fore, Style
    from colorama import init as _colorama_init

    _colorama_init(autoreset=True)
    C = Fore
    S = Style
except ImportError:
    C = _NoColor()
    S = _NoColor()


def _icon(ok: bool) -> str:
    if isinstance(C, _NoColor):
        return "[OK]" if ok else "[!!]"
    return f"{C.GREEN}[OK]{S.RESET_ALL}" if ok else f"{C.RED}[!!]{S.RESET_ALL}"


def _dim(text: str) -> str:
    if isinstance(C, _NoColor):
        return text
    return f"{Style.DIM}{text}{Style.RESET_ALL}"


# ── 常量 ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

LLM_MODES = {
    "deepseek": "DeepSeek API — 性价比高，中文能力强",
    "openai": "OpenAI API (兼容) — 生态丰富，兼容性好",
    "anthropic": "Anthropic Claude — 长文本创作，推理能力强",
    "ollama": "Ollama 本地模型 — 免费，隐私安全，需本地 GPU",
}

DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# ── .env 模板 ──────────────────────────────────
_ENV_HEADER = """# ============================================================
# Kunlun Creation Engine — Environment Variables
# 由 `kunlun setup` 交互式向导生成
# ============================================================

"""

_ENV_DATABASE_SECTION = """# --- Neo4j Graph Database ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# --- Redis Cache ---
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# --- NATS Message Queue ---
NATS_URL=nats://localhost:4222

"""

_ENV_LLM_SECTION_TEMPLATE = """# ============================================================
# LLM API 配置 (模式: {llm_mode})
# ============================================================

# --- 主 API Key ---
OPENAI_API_KEY={openai_key}
OPENAI_BASE_URL={openai_base_url}

# --- DeepSeek API ---
DEEPSEEK_API_KEY={deepseek_key}
DEEPSEEK_BASE_URL=https://api.deepseek.com

# --- Anthropic Claude API ---
ANTHROPIC_API_KEY={anthropic_key}

# --- LLM 成本控制 ---
LLM_MAX_TOKENS_PER_REQUEST=4096
LLM_MAX_CALLS_PER_HOUR=60
LLM_DAILY_TOKEN_BUDGET=500000

"""

_ENV_OLLAMA_SECTION = """# --- Ollama 本地模型 ---
OLLAMA_HOST={ollama_host}
LLM_LOCAL_MODEL={local_model}

"""

_ENV_APP_SECTION = """# ============================================================
# Application Server
# ============================================================
APP_HOST=127.0.0.1
APP_PORT=8000
APP_ENV=development
LOG_LEVEL=INFO

# ============================================================
# API 安全
# ============================================================
API_AUTH_ENABLED=false

# ============================================================
# 速率限制
# ============================================================
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_GENERATE_PER_MINUTE=3

# ============================================================
# 全管线创作
# ============================================================
PIPELINE_AUTO_PROOFREAD=true
PIPELINE_AUTO_STRUCTURE_CHECK=true
PIPELINE_CONTEXT_BUDGET=8000
PIPELINE_DEFAULT_GENRE=xuanhuan

# ============================================================
# 昆仑模式
# ============================================================
KUNLUN_MODE={kunlun_mode}
"""


# ── 工具函数 ──────────────────────────────────
def _check_ollama_installed() -> bool:
    """检查 Ollama 是否已安装。"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, Exception):
        return False


def _check_ollama_running(host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """检查 Ollama 服务是否在运行。"""
    try:
        import urllib.request

        url = f"{host.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _list_ollama_models(host: str = DEFAULT_OLLAMA_HOST) -> list[str]:
    """从 Ollama API 获取可用模型列表。"""
    try:
        import urllib.request

        url = f"{host.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return [m for m in models if m]
    except Exception:
        pass

    # fallback: 尝试 ollama list 命令
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            models = []
            for line in result.stdout.strip().split("\n")[1:]:
                if line.strip():
                    name = line.split()[0]
                    models.append(name)
            return models
    except Exception:
        pass
    return []


def _get_default_model_for_mode(llm_mode: str) -> str:
    defaults = {
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
        "ollama": "qwen3:14b",
    }
    return defaults.get(llm_mode, "gpt-4o")


def _get_default_base_url(llm_mode: str) -> str:
    defaults = {
        "deepseek": "https://api.deepseek.com/v1",
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "ollama": "http://localhost:11434/v1",
    }
    return defaults.get(llm_mode, "https://api.openai.com/v1")


# ── 步骤函数 ──────────────────────────────────
def _step_llm_mode(defaults: bool) -> str:
    """步骤 1: 选择 LLM 模式。"""
    print()
    print(f"  {C.CYAN}━━━ 步骤 1/5: 选择 LLM 模式 ━━━{S.RESET_ALL}")
    print()
    for key, desc in LLM_MODES.items():
        print(f"    [{key}]  {desc}")
    print()

    default_mode = "deepseek"
    if defaults:
        print(f"  {_dim('使用默认值:')} {C.YELLOW}{default_mode}{S.RESET_ALL}")
        return default_mode

    while True:
        prompt = f"  请选择 ({'/'.join(LLM_MODES.keys())}) [{default_mode}]: "
        try:
            choice = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not choice:
            choice = default_mode
        if choice in LLM_MODES:
            return choice
        print(f"  {C.RED}无效选择，请输入: {' / '.join(LLM_MODES.keys())}{S.RESET_ALL}")


def _step_api_key(llm_mode: str, defaults: bool) -> str:
    """步骤 2: 输入 API Key。"""
    print()
    print(f"  {C.CYAN}━━━ 步骤 2/5: API Key 配置 ━━━{S.RESET_ALL}")
    print()

    key_name_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = key_name_map.get(llm_mode, "")

    if llm_mode == "ollama":
        print(f"  {_dim('Ollama 本地模式无需 API Key，跳过此步骤')}")
        return "ollama-local"

    if defaults:
        print(f"  {_dim(f'使用默认值: {env_var}=<空>')}")
        return ""

    print(f"  需要配置: {C.YELLOW}{env_var}{S.RESET_ALL}")
    print(f"  {_dim('（输入时光标不会回显，粘贴后直接回车即可）')}")
    print()

    while True:
        try:
            api_key = getpass.getpass(f"  请输入 {env_var}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not api_key:
            print(f"  {C.YELLOW}⚠ 未输入 API Key，将跳过此配置{S.RESET_ALL}")
            print()
            return ""

        if len(api_key) < 8:
            print(f"  {C.YELLOW}⚠ API Key 似乎过短（< 8 字符），请确认{S.RESET_ALL}")
            confirm = input("  确认保存? (y/n) [y]: ").strip().lower()
            if confirm == "n":
                continue

        return api_key


def _step_ollama_host(llm_mode: str, defaults: bool) -> str:
    """步骤 3: 如果是 Ollama 模式，输入 Ollama Host。"""
    print()
    print(f"  {C.CYAN}━━━ 步骤 3/5: Ollama 服务地址 ━━━{S.RESET_ALL}")
    print()

    if llm_mode != "ollama":
        print(f"  {_dim('非 Ollama 模式，跳过此步骤')}")
        return ""

    if defaults:
        print(f"  {_dim(f'使用默认值: {DEFAULT_OLLAMA_HOST}')}")
        return DEFAULT_OLLAMA_HOST

    # 检测 Ollama 是否安装
    if not _check_ollama_installed():
        print(f"  {C.YELLOW}⚠ 未检测到 Ollama 安装{S.RESET_ALL}")
        print()
        print("  请先安装 Ollama:")
        print("    Windows: https://ollama.com/download/windows")
        print("    macOS:   https://ollama.com/download/mac")
        print("    Linux:   curl -fsSL https://ollama.com/install.sh | sh")
        print()
    else:
        print(f"  {_icon(True)} 已检测到 Ollama 安装")

    # 检测 Ollama 是否运行
    if _check_ollama_running(DEFAULT_OLLAMA_HOST):
        print(f"  {_icon(True)} Ollama 服务运行中 ({DEFAULT_OLLAMA_HOST})")
    else:
        print(f"  {C.YELLOW}⚠ Ollama 服务未运行 ({DEFAULT_OLLAMA_HOST}){S.RESET_ALL}")
        print(f"  {_dim('请确保在继续前启动 Ollama: ollama serve')}")

    print()
    prompt = f"  Ollama Host [{DEFAULT_OLLAMA_HOST}]: "
    try:
        host = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    return host if host else DEFAULT_OLLAMA_HOST


def _step_ollama_model(llm_mode: str, ollama_host: str, defaults: bool) -> str:
    """步骤 4: 如果是 Ollama 模式，选择本地模型。"""
    print()
    print(f"  {C.CYAN}━━━ 步骤 4/5: 本地模型选择 ━━━{S.RESET_ALL}")
    print()

    if llm_mode != "ollama":
        print(f"  {_dim('非 Ollama 模式，跳过此步骤')}")
        return ""

    # 自动检测可用模型
    host = ollama_host or DEFAULT_OLLAMA_HOST
    print(f"  {_dim('正在检测 Ollama 可用模型...')}")
    available = _list_ollama_models(host)

    if available:
        print(f"  {_icon(True)} 已安装模型: {', '.join(available)}")
        default_model = available[0]
    else:
        print(f"  {C.YELLOW}⚠ 未检测到已安装模型{S.RESET_ALL}")
        print(f"  {_dim('推荐模型: qwen3:14b (中文写作最佳), qwen3:8b (轻量快速)')}")
        default_model = "qwen3:14b"

    if defaults:
        print(f"  {_dim(f'使用默认值: {default_model}')}")
        return default_model

    print()
    prompt = f"  模型名称 [{default_model}]: "
    try:
        model = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    chosen = model if model else default_model

    if chosen not in available:
        print(f"  {C.YELLOW}⚠ 模型 '{chosen}' 未安装，将自动拉取...{S.RESET_ALL}")
        print(f"  {_dim('（后续运行时会自动下载，或手动执行: ollama pull ' + chosen + '）')}")

    return chosen


def _step_kunlun_mode(defaults: bool) -> str:
    """步骤 5: 选择昆仑运行模式。"""
    print()
    print(f"  {C.CYAN}━━━ 步骤 5/5: 昆仑运行模式 ━━━{S.RESET_ALL}")
    print()
    print("    [personal]   自用模式 — 零外部服务依赖，启动快，适合个人创作")
    print("    [enterprise] 企业模式 — 需要 Docker (Neo4j/Redis/NATS)，适合团队协作")
    print()

    default_mode = "personal"
    if defaults:
        print(f"  {_dim(f'使用默认值: {default_mode}')}")
        return default_mode

    prompt = f"  请选择 (personal/enterprise) [{default_mode}]: "
    try:
        choice = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    if not choice:
        choice = default_mode
    if choice in ("personal", "enterprise"):
        return choice
    print(f"  {C.YELLOW}无效选择，使用默认值: {default_mode}{S.RESET_ALL}")
    return default_mode


# ── 配置写入 ──────────────────────────────────
def _build_env_content(config: dict[str, Any]) -> str:
    """根据配置构建 .env 文件内容。"""
    llm_mode = config["llm_mode"]
    api_key = config.get("api_key", "")

    # 按模式分配 API Key
    key_map = {
        "deepseek": ("", api_key, ""),
        "openai": (api_key, "", ""),
        "anthropic": ("", "", api_key),
        "ollama": ("ollama-local", "", ""),
    }
    openai_key, deepseek_key, anthropic_key = key_map.get(llm_mode, ("", "", ""))

    base_url = _get_default_base_url(llm_mode)

    content = _ENV_HEADER
    content += _ENV_DATABASE_SECTION
    content += _ENV_LLM_SECTION_TEMPLATE.format(
        llm_mode=llm_mode,
        openai_key=openai_key,
        openai_base_url=base_url,
        deepseek_key=deepseek_key,
        anthropic_key=anthropic_key,
    )

    if llm_mode == "ollama":
        content += _ENV_OLLAMA_SECTION.format(
            ollama_host=config.get("ollama_host", DEFAULT_OLLAMA_HOST),
            local_model=config.get("ollama_model", "qwen3:14b"),
        )

    content += _ENV_APP_SECTION.format(kunlun_mode=config.get("kunlun_mode", "personal"))
    return content


def _write_env_file(config: dict[str, Any], defaults: bool = False) -> None:
    """写入 .env 文件，如果已存在则询问是否覆盖。"""
    content = _build_env_content(config)

    if ENV_PATH.exists():
        print()
        print(f"  {C.YELLOW}⚠ .env 文件已存在{S.RESET_ALL}")
        print(f"     路径: {ENV_PATH}")
        print()

        if defaults:
            choice = "b"
            print(f"  {_dim('非交互模式: 自动备份后覆盖')}")
        else:
            # 让用户选择
            print("  [o] 覆盖 (overwrite)")
            print("  [b] 备份后覆盖 (backup + overwrite)")
            print("  [s] 跳过 (skip)")
            print()

            while True:
                try:
                    choice = input("  请选择 (o/b/s) [b]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    sys.exit(0)

                if not choice:
                    choice = "b"

                if choice in ("o", "b", "s"):
                    break
                print(f"  {C.RED}无效选择{S.RESET_ALL}")

        if choice == "o":
            pass
        elif choice == "b":
            backup = ENV_PATH.with_suffix(".env.backup")
            ENV_PATH.rename(backup)
            print(f"  {_icon(True)} 已备份至: {backup}")
        elif choice == "s":
            print(f"  {_dim('跳过 .env 写入，配置未保存')}")
            return

    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"  {_icon(True)} .env 已写入: {ENV_PATH}")


# ── 摘要 ──────────────────────────────────────
def _print_summary(config: dict[str, Any]) -> None:
    """打印配置摘要。"""
    print()
    print(f"  {C.CYAN}{'=' * 54}{S.RESET_ALL}")
    print(f"  {C.CYAN}  配置摘要{S.RESET_ALL}")
    print(f"  {C.CYAN}{'=' * 54}{S.RESET_ALL}")
    print()

    llm_mode = config["llm_mode"]
    print(f"  {'LLM 模式:':<20} {C.GREEN}{llm_mode}{S.RESET_ALL}")

    if llm_mode == "ollama":
        print(f"  {'Ollama Host:':<20} {config.get('ollama_host', DEFAULT_OLLAMA_HOST)}")
        print(f"  {'本地模型:':<20} {config.get('ollama_model', 'qwen3:14b')}")
    else:
        api_key = config.get("api_key", "")
        masked = api_key[:4] + "****" + api_key[-4:] if len(api_key) > 8 else "(未设置)"
        print(f"  {'API Key:':<20} {masked}")
        print(f"  {'Base URL:':<20} {_get_default_base_url(llm_mode)}")

    print(f"  {'运行模式:':<20} {config.get('kunlun_mode', 'personal')}")
    print()
    print(f"  {C.CYAN}{'=' * 54}{S.RESET_ALL}")
    print()

    print(f"  {C.GREEN}✓ 配置完成！{S.RESET_ALL}")
    print()
    print("  下一步:")
    print("    kunlun doctor            检查环境")
    print("    kunlun book create       创建新书")
    print("    kunlun write next        开始创作")
    print("    kunlun up                后台自动写")
    print()


# ── 主入口 ────────────────────────────────────
def run_setup_wizard(defaults: bool = False) -> None:
    """运行交互式配置向导。

    Args:
        defaults: True 时跳过所有问答，全部使用默认值。
    """
    print()
    print(f"  {C.CYAN}╔{'═' * 52}╗{S.RESET_ALL}")
    print(f"  {C.CYAN}║{'昆仑创作引擎 — 配置初始化向导':　^42}║{S.RESET_ALL}")
    print(f"  {C.CYAN}║{'Kunlun Creation Engine Setup Wizard':　^42}║{S.RESET_ALL}")
    print(f"  {C.CYAN}╚{'═' * 52}╝{S.RESET_ALL}")
    print()

    if defaults:
        print(f"  {_dim('非交互模式: 全部使用默认值')}")
    else:
        print(f"  {_dim('按 Enter 使用默认值 | Ctrl+C 退出')}")

    config: dict[str, Any] = {}

    # 步骤 1: LLM 模式
    config["llm_mode"] = _step_llm_mode(defaults)

    # 步骤 2: API Key
    config["api_key"] = _step_api_key(config["llm_mode"], defaults)

    # 步骤 3: Ollama Host (仅 ollama)
    config["ollama_host"] = _step_ollama_host(config["llm_mode"], defaults)

    # 步骤 4: Ollama 模型 (仅 ollama)
    config["ollama_model"] = _step_ollama_model(config["llm_mode"], config["ollama_host"], defaults)

    # 步骤 5: 昆仑模式
    config["kunlun_mode"] = _step_kunlun_mode(defaults)

    # 写入 .env
    _write_env_file(config, defaults=defaults)

    # 显示摘要
    _print_summary(config)

"""
一键本地环境配置 — 自用模式初始化

功能:
  1. 检测 Ollama 是否安装
  2. 自动下载推荐模型
  3. 配置 .env 为本地模式
  4. 验证模型可用

用法:
  python kunlun_cli.py setup-local
  python kunlun_cli.py setup-local --model qwen3:8b
  python kunlun_cli.py setup-local --skip-ollama --skip-model
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# ── 推荐模型列表 ──────────────────────────────────
RECOMMENDED_MODELS = {
    "qwen3:14b": "Qwen3 14B — 中文写作最佳，推荐首选",
    "qwen3:8b": "Qwen3 8B — 轻量快速，8GB 显存可运行",
    "deepseek-r1:8b": "DeepSeek R1 8B — 推理能力强，适合大纲/审计",
    "qwen2.5:14b": "Qwen2.5 14B — 稳定可靠",
}

# ── 最小 .env 内容 ──────────────────────────────────
_MINIMAL_ENV_TEMPLATE = """# 昆仑创作引擎 — 自用配置（由 setup-local 自动生成）
KUNLUN_MODE=personal
LLM_MODE=local
LLM_LOCAL_MODEL={model}
OLLAMA_HOST=http://localhost:11434
"""


def _green(text: str) -> str:
    try:
        from colorama import Fore, Style

        return f"{Fore.GREEN}{text}{Style.RESET_ALL}"
    except ImportError:
        return text


def _red(text: str) -> str:
    try:
        from colorama import Fore, Style

        return f"{Fore.RED}{text}{Style.RESET_ALL}"
    except ImportError:
        return text


def _yellow(text: str) -> str:
    try:
        from colorama import Fore, Style

        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"
    except ImportError:
        return text


def _cyan(text: str) -> str:
    try:
        from colorama import Fore, Style

        return f"{Fore.CYAN}{text}{Style.RESET_ALL}"
    except ImportError:
        return text


def _check_ollama() -> bool:
    """检查 Ollama 是否安装"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  {_green('[OK]')} Ollama 已安装: {version}")
            return True
    except FileNotFoundError:
        pass
    except Exception:
        pass

    print(f"  {_red('[!!]')} Ollama 未安装")
    print()
    print("  请安装 Ollama:")
    print("    Windows: https://ollama.com/download/windows")
    print("    macOS:   https://ollama.com/download/mac")
    print("    Linux:   curl -fsSL https://ollama.com/install.sh | sh")
    return False


def _check_ollama_running() -> bool:
    """检查 Ollama 服务是否运行"""
    try:
        import urllib.request

        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print(f"  {_green('[OK]')} Ollama 服务运行中")
                return True
    except Exception:
        pass

    print(f"  {_yellow('[--]')} Ollama 服务未运行，启动中...")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  {_green('[OK]')} Ollama 服务已启动")
        return True
    except Exception:
        print(f"  {_red('[!!]')} 无法启动 Ollama 服务，请手动运行 'ollama serve'")
        return False


def _list_installed_models() -> list[str]:
    """列出已安装的模型"""
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
            for line in result.stdout.strip().split("\n")[1:]:  # skip header
                if line.strip():
                    name = line.split()[0]
                    models.append(name)
            return models
    except Exception:
        pass
    return []


def _pull_model(model_name: str) -> bool:
    """下载模型"""
    print(f"  {_cyan('>>>')} 正在下载模型: {model_name}...")
    print("     这可能需要几分钟到几十分钟，取决于模型大小和网络速度")
    print()

    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            check=False,
        )
        if result.returncode == 0:
            print(f"  {_green('[OK]')} 模型 {model_name} 下载完成")
            return True
        print(f"  {_red('[!!]')} 模型下载失败 (exit code: {result.returncode})")
        return False
    except Exception as e:
        print(f"  {_red('[!!]')} 模型下载出错: {e}")
        return False


def _test_model(model_name: str) -> bool:
    """测试模型是否可用"""
    print(f"  {_cyan('>>>')} 测试模型: {model_name}...")
    try:
        result = subprocess.run(
            ["ollama", "run", model_name, "--", "你好，请回复'OK'"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            print(f"  {_green('[OK]')} 模型 {model_name} 测试通过")
            return True
        print(f"  {_yellow('[--]')} 模型 {model_name} 测试返回非零: {result.returncode}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  {_yellow('[--]')} 模型 {model_name} 测试超时（可能设备性能不足）")
        return False
    except Exception as e:
        print(f"  {_red('[!!]')} 模型测试出错: {e}")
        return False


def _write_env_file(model_name: str) -> None:
    """写入 .env 文件"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    content = _MINIMAL_ENV_TEMPLATE.format(model=model_name)

    if env_path.exists():
        backup = env_path.with_suffix(".env.backup")
        env_path.rename(backup)
        print(f"  {_yellow('[--]')} 已备份原有 .env → .env.backup")

    env_path.write_text(content, encoding="utf-8")
    print(f"  {_green('[OK]')} .env 已配置为本地模式")


def run_setup(
    model: str = "qwen3:14b",
    skip_ollama: bool = False,
    skip_model: bool = False,
) -> None:
    """执行一键环境配置

    Args:
        model: 要下载的模型名称
        skip_ollama: 跳过 Ollama 安装检查
        skip_model: 跳过模型下载
    """
    print()
    print(f"  {_cyan('=' * 54)}")
    print(f"  {_cyan('昆仑创作引擎 — 本地环境一键配置')}")
    print(f"  {_cyan('=' * 54)}")
    print()

    all_ok = True

    # 1. 检查 Ollama
    if not skip_ollama:
        print("  [1/4] 检查 Ollama 安装...")
        if not _check_ollama():
            print()
            print(f"  {_yellow('提示: 可使用 --skip-ollama 跳过此检查')}")
            return
        if not _check_ollama_running():
            all_ok = False
        print()

    # 2. 检查已安装模型
    print("  [2/4] 检查已安装模型...")
    installed = _list_installed_models()
    if installed:
        print(f"  {_green('[OK]')} 已安装模型: {', '.join(installed)}")
    else:
        print(f"  {_yellow('[--]')} 未检测到已安装模型")
    print()

    # 3. 下载模型
    if not skip_model:
        print("  [3/4] 模型准备...")
        if model in installed:
            print(f"  {_green('[OK]')} 模型 {model} 已安装，跳过下载")
        else:
            print("  推荐模型列表:")
            for name, desc in RECOMMENDED_MODELS.items():
                marker = " ← 当前选择" if name == model else ""
                print(f"    {name:<20} {desc}{marker}")
            print()
            if not _pull_model(model):
                all_ok = False
                print()
                print(f"  {_yellow('提示: 可使用 --skip-model 跳过下载')}")
                print(f"  {_yellow('也可手动下载: ollama pull ' + model)}")
        print()
    else:
        print("  [3/4] 模型下载: 已跳过 (--skip-model)")
        print()

    # 4. 写配置
    print("  [4/4] 配置 .env...")
    _write_env_file(model)
    print()

    # 5. 测试模型
    if not skip_model and model in [*installed, model]:
        installed = _list_installed_models()
        if model in installed:
            _test_model(model)
            print()

    # 总结
    print(f"  {_cyan('=' * 54)}")
    if all_ok:
        print(f"  {_green('配置完成！')}")
        print()
        print("  下一步:")
        print("    python kunlun_cli.py up    启动创作引擎")
        print("    python kunlun_cli.py status 查看状态")
    else:
        print(f"  {_yellow('配置完成（部分步骤需要手动处理）')}")
    print(f"  {_cyan('=' * 54)}")
    print()

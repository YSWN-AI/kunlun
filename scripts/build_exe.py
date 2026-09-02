#!/usr/bin/env python
"""
昆仑创作引擎 — PyInstaller 一键打包脚本

对标 AI_NovelGenerator 的 PyInstaller 打包方案。
生成 dist/kunlun.exe（CLI 版），无需 Python 环境即可运行。

用法:
    python scripts/build_exe.py           打包 CLI 版
    python scripts/build_exe.py --desktop  打包 GUI 桌面版
    python scripts/build_exe.py --clean    清理后重新打包
    python scripts/build_exe.py --all      同时打包 CLI + GUI 版
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST = PROJECT_ROOT / "dist"
BUILD = PROJECT_ROOT / "build"


def run(cmd, **kw):
    """运行命令并打印"""
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
    print(f"  > {cmd_str}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kw)


def clean():
    """清理旧构建"""
    dirs = [DIST, BUILD]
    for d in dirs:
        if d.exists():
            shutil.rmtree(d)
            print(f"  [clean] 已删除 {d.name}/")
    # 清理 PyInstaller 缓存
    for pattern in ["*.spec.bak", "__pycache__"]:
        for p in PROJECT_ROOT.glob(pattern):
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()


def install_pyinstaller():
    """确保 PyInstaller 已安装"""
    try:
        import PyInstaller  # noqa: F401
        print("  [check] PyInstaller 已安装")
    except ImportError:
        print("  [install] 正在安装 PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_cli():
    """打包 CLI 版"""
    spec = PROJECT_ROOT / "kunlun.spec"
    if not spec.exists():
        print(f"  [error] 未找到 {spec}")
        return False

    print("\n  ╔══════════════════════════════════════╗")
    print("  ║  打包 CLI 版: kunlun.exe            ║")
    print("  ╚══════════════════════════════════════╝\n")

    run(["pyinstaller", "--clean", "--noconfirm", str(spec)])

    exe = DIST / "kunlun.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n  ✅ CLI 版打包成功!")
        print(f"     输出: {exe}")
        print(f"     大小: {size_mb:.1f} MB")
        return True
    else:
        print(f"\n  ❌ 打包失败: 未找到 {exe}")
        return False


def build_desktop():
    """打包 GUI 桌面版"""
    spec = PROJECT_ROOT / "kunlun" / "desktop_app.spec"
    if not spec.exists():
        print(f"  [error] 未找到 {spec}")
        return False

    print("\n  ╔══════════════════════════════════════╗")
    print("  ║  打包 GUI 版: kunlun-desktop.exe    ║")
    print("  ╚══════════════════════════════════════╝\n")

    run(["pyinstaller", "--clean", "--noconfirm", str(spec)])

    exe = DIST / "kunlun-desktop.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n  ✅ GUI 版打包成功!")
        print(f"     输出: {exe}")
        print(f"     大小: {size_mb:.1f} MB")
        return True
    else:
        print(f"\n  ❌ 打包失败: 未找到 {exe}")
        return False


def main():
    args = sys.argv[1:]
    do_clean = "--clean" in args
    do_all = "--all" in args
    do_desktop = "--desktop" in args

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║  昆仑创作引擎 — PyInstaller 一键打包        ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    if do_clean:
        clean()

    install_pyinstaller()

    success = True

    if do_all or do_desktop:
        success &= build_desktop()
        if not do_all and not success:
            sys.exit(1)

    if do_all or not do_desktop:
        success &= build_cli()

    if success:
        print("\n  🎉 全部打包完成!")
        if DIST.exists():
            print(f"\n  输出目录: {DIST}")
            for f in sorted(DIST.glob("*.exe")):
                size = f.stat().st_size / (1024 * 1024)
                print(f"    {f.name} ({size:.1f} MB)")
    else:
        print("\n  ❌ 打包过程有失败项")
        sys.exit(1)


if __name__ == "__main__":
    main()
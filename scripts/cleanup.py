#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
昆仑创作引擎 — 项目清理与维护脚本

功能:
  1. 扫描并删除过期的临时文件、重复文件、空目录
  2. 检查依赖版本，报告可升级项
  3. 生成详细操作日志
  4. 预览模式（默认开启），需用户确认后执行不可逆操作

用法:
  python scripts/cleanup.py                    # 预览模式（只扫描不删除）
  python scripts/cleanup.py --execute          # 预览后确认执行
  python scripts/cleanup.py --execute --yes    # 跳过确认，直接执行
  python scripts/cleanup.py --days 30          # 仅清理 30 天前的文件
  python scripts/cleanup.py --check-deps       # 仅检查依赖版本
  python scripts/cleanup.py --full             # 完整扫描+依赖检查+清理
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict

# ─── Windows 控制台 UTF-8 编码修复 ──────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ─── 项目根目录 ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── 可配置参数 ─────────────────────────────────
DEFAULT_DAYS = 14  # 默认清理超过 N 天未访问的文件
CHECKSUM_READ_SIZE = 8192  # 校验和读取块大小

# 日志输出路径
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 需要清理的临时文件模式
TEMP_PATTERNS = [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/*.log",
    "**/build/**",
    "**/dist/**",
    "**/*.egg-info/**",
    "**/.pytest_cache/**",
    "**/htmlcov/**",
    "**/.coverage",
    "**/*.db-journal",
    "**/*.db-wal",
    "**/Thumbs.db",
    "**/.DS_Store",
    "**/*.tmp",
    "**/*.temp",
    "**/~$*",
]

# 需要扫描重复文件的目录（排除大目录）
DUPLICATE_SCAN_DIRS = [
    "kunlun",
    "scripts",
    "tests",
    "tools",
]

# 排除目录（不扫描）
EXCLUDE_DIRS = {
    "venv",
    ".venv",
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "htmlcov",
    "dist",
    "build",
    "昆仑引擎_便携版",
}

# ─── 颜色输出（Windows 兼容）──────────────────
is_windows = sys.platform == "win32"
if is_windows:
    os.system("")  # 启用 ANSI 颜色支持

C = {
    "R": "\033[91m",  # 红
    "G": "\033[92m",  # 绿
    "Y": "\033[93m",  # 黄
    "B": "\033[94m",  # 蓝
    "M": "\033[95m",  # 紫
    "C": "\033[96m",  # 青
    "W": "\033[0m",  # 重置
    "BOLD": "\033[1m",
}


def cprint(color: str, msg: str):
    print(f"{C.get(color, '')}{msg}{C['W']}")


# ─── 文件校验和 ─────────────────────────────────


def file_checksum(path: Path) -> Optional[str]:
    """计算文件 SHA256 校验和（仅读取前 64KB + 文件大小）"""
    try:
        size = path.stat().st_size
        hasher = hashlib.sha256()
        hasher.update(str(size).encode())
        with open(path, "rb") as f:
            # 读取前 64KB
            hasher.update(f.read(65536))
            # 如果文件 > 128KB，读取尾部 64KB
            if size > 131072:
                f.seek(-65536, os.SEEK_END)
                hasher.update(f.read(65536))
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return None


# ─── 日志系统 ─────────────────────────────────


class CleanupLogger:
    """结构化操作日志"""

    def __init__(self, log_path: Path):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = log_path
        self.entries: list[dict] = []
        self._start_time = time.time()
        self._file = open(log_path, "w", encoding="utf-8")
        self._write_header()

    def _write_header(self):
        self._file.write(f"# 昆仑创作引擎 — 清理日志\n")
        self._file.write(f"# 开始时间: {datetime.now().isoformat()}\n")
        self._file.write(f"# 项目目录: {PROJECT_ROOT}\n")
        self._file.write(f"{'=' * 60}\n\n")

    def log(self, action: str, detail: str, status: str = "info"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "detail": detail,
            "status": status,
        }
        self.entries.append(entry)
        prefix = {
            "info": "[INFO]",
            "deleted": "[DEL]",
            "skipped": "[SKIP]",
            "error": "[ERR ]",
            "updated": "[UPD ]",
            "warn": "[WARN]",
        }.get(status, "[INFO]")
        self._file.write(f"{prefix} {entry['timestamp']} | {action}: {detail}\n")
        self._file.flush()

    def summary(self):
        """输出统计摘要"""
        elapsed = time.time() - self._start_time
        actions = defaultdict(int)
        for e in self.entries:
            actions[e["status"]] += 1
        summary_lines = [
            f"\n{'=' * 60}",
            f"  清理完成 | 耗时: {elapsed:.1f}s",
            f"  删除文件: {actions.get('deleted', 0)}",
            f"  跳过文件: {actions.get('skipped', 0)}",
            f"  错误数量: {actions.get('error', 0)}",
            f"  更新项目: {actions.get('updated', 0)}",
            f"{'=' * 60}\n",
        ]
        for line in summary_lines:
            self._file.write(line + "\n")
            print(line)
        return actions

    def close(self):
        self.summary()
        self._file.close()
        print(f"\n  📄 详细日志: {self.path}")


# ─── 清理操作 ─────────────────────────────────


class ProjectCleaner:
    """项目清理器"""

    def __init__(
        self,
        logger: CleanupLogger,
        days: int = DEFAULT_DAYS,
        dry_run: bool = True,
        auto_confirm: bool = False,
    ):
        self.logger = logger
        self.days = days
        self.dry_run = dry_run
        self.auto_confirm = auto_confirm
        self.cutoff_time = time.time() - (days * 86400)
        self._to_delete_files: list[Path] = []
        self._to_delete_dirs: list[Path] = []
        self._duplicates: dict[str, list[Path]] = {}
        self._empty_dirs: list[Path] = []
        self._outdated_deps: list[dict] = []

    # ─── 1. 扫描过期临时文件 ─────────────────

    def scan_temp_files(self) -> list[Path]:
        """扫描匹配临时文件模式的过期文件"""
        cprint("C", "\n  🔍 扫描过期临时文件...")
        found = []

        for pattern in TEMP_PATTERNS:
            for p in PROJECT_ROOT.glob(pattern):
                # 跳过排除目录
                if any(excl in p.parts for excl in EXCLUDE_DIRS):
                    continue
                if p.is_file():
                    try:
                        mtime = p.stat().st_mtime
                        if mtime < self.cutoff_time:
                            found.append(p)
                    except OSError:
                        pass

        found = sorted(set(found))
        cprint("G", f"    发现 {len(found)} 个过期临时文件")

        # 按类型分组统计
        by_ext = defaultdict(int)
        for p in found:
            ext = p.suffix or "(无扩展名)"
            by_ext[ext] += 1
        for ext, count in sorted(by_ext.items(), key=lambda x: -x[1]):
            print(f"      {ext}: {count} 个")

        for p in found:
            self.logger.log(
                "过期临时文件",
                str(p.relative_to(PROJECT_ROOT)),
                "deleted" if not self.dry_run else "skipped",
            )
        return found

    # ─── 2. 扫描空目录 ───────────────────────

    def scan_empty_dirs(self) -> list[Path]:
        """扫描项目中的空目录"""
        cprint("C", "\n  🔍 扫描空目录...")
        found = []
        # 从深层到浅层遍历（先删子目录）
        for root, dirs, files in os.walk(PROJECT_ROOT, topdown=False):
            root_path = Path(root)
            if any(excl in root_path.parts for excl in EXCLUDE_DIRS):
                continue
            if not dirs and not files:
                # 跳过数据目录
                if "data" in root_path.parts and root_path != PROJECT_ROOT / "data":
                    found.append(root_path)

        cprint("G", f"    发现 {len(found)} 个空目录")
        for d in found:
            self.logger.log(
                "空目录",
                str(d.relative_to(PROJECT_ROOT)),
                "deleted" if not self.dry_run else "skipped",
            )
        return found

    # ─── 3. 扫描重复文件 ──────────────────────

    def scan_duplicates(self) -> dict[str, list[Path]]:
        """扫描指定目录中的重复文件（基于 SHA256）"""
        cprint("C", "\n  🔍 扫描重复文件...")
        hashes: dict[str, list[Path]] = defaultdict(list)
        scanned = 0

        for scan_dir in DUPLICATE_SCAN_DIRS:
            target = PROJECT_ROOT / scan_dir
            if not target.exists():
                continue
            for p in target.rglob("*"):
                if p.is_file() and not any(excl in p.parts for excl in EXCLUDE_DIRS):
                    # 跳过非代码文件
                    if p.suffix not in (
                        ".py",
                        ".json",
                        ".md",
                        ".txt",
                        ".yaml",
                        ".yml",
                        ".toml",
                        ".cfg",
                        ".ini",
                        ".html",
                        ".css",
                        ".js",
                    ):
                        continue
                    chk = file_checksum(p)
                    if chk:
                        hashes[chk].append(p)
                        scanned += 1

        # 只保留有重复的
        duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
        dup_count = sum(len(v) - 1 for v in duplicates.values())

        cprint(
            "G", f"    扫描 {scanned} 个文件，发现 {dup_count} 个重复文件 ({len(duplicates)} 组)"
        )
        for h, paths in duplicates.items():
            kept = paths[0]
            for dup in paths[1:]:
                self.logger.log(
                    "重复文件",
                    f"{dup.relative_to(PROJECT_ROOT)} (保留 {kept.relative_to(PROJECT_ROOT)})",
                    "deleted" if not self.dry_run else "skipped",
                )
        return duplicates

    # ─── 4. 检查依赖版本 ────────────────────

    def check_dependencies(self) -> list[dict]:
        """检查 requirements.txt 中的依赖版本，对比 PyPI 最新版"""
        cprint("C", "\n  🔍 检查依赖版本...")
        req_path = PROJECT_ROOT / "requirements.txt"
        if not req_path.exists():
            cprint("Y", "    requirements.txt 未找到，跳过依赖检查")
            return []

        outdated = []
        try:
            # 获取当前已安装的包版本
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=PROJECT_ROOT,
                check=False,
            )
            if result.returncode == 0:
                pip_outdated = json.loads(result.stdout)
            else:
                pip_outdated = []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            cprint("Y", "    ⚠ 无法查询 PyPI（可能无网络），跳过在线检查")
            pip_outdated = []

        # 解析 requirements.txt
        deps = self._parse_requirements(req_path)
        pip_map = {item["name"].lower(): item for item in pip_outdated}

        for name, current in deps.items():
            info = pip_map.get(name.lower())
            if info:
                item = {
                    "name": name,
                    "current": info["version"],
                    "latest": info["latest_version"],
                    "package_type": info.get("package_type", "sdist"),
                }
                outdated.append(item)
                cprint("Y", f"    {name}: {info['version']} → {info['latest_version']}")
                self.logger.log(
                    "依赖过时", f"{name} {info['version']} → {info['latest_version']}", "warn"
                )

        if not outdated:
            cprint("G", "    ✅ 所有依赖均为最新版本")
        else:
            cprint("Y", f"    共 {len(outdated)} 个依赖可升级")

        return outdated

    def _parse_requirements(self, path: Path) -> dict[str, str]:
        """解析 requirements.txt 中的包名和版本"""
        deps = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # 处理 extras: pkg[extra]>=version
                match = re.match(
                    r"^([a-zA-Z0-9_\-]+)(?:\[.*?\])?\s*([><=!~]+\s*[\d.]+(?:\s*,\s*[><=!~]+\s*[\d.]+)*)?",
                    line,
                )
                if match:
                    name = match.group(1)
                    version = match.group(2) or "latest"
                    deps[name] = version.strip() if version else "latest"
        return deps

    # ─── 5. 生成依赖更新命令 ──────────────────

    def generate_upgrade_commands(self, outdated: list[dict]) -> list[str]:
        """生成 pip install --upgrade 命令列表"""
        commands = []
        for dep in outdated:
            name = dep["name"]
            latest = dep["latest"]
            commands.append(f"pip install --upgrade {name}=={latest}")
        return commands

    # ─── 6. 执行删除 ──────────────────────────

    def execute_deletions(self):
        """执行实际的文件/目录删除操作"""
        cprint("M", "\n  🗑️  执行清理...")

        deleted_files = 0
        deleted_dirs = 0
        errors = 0
        freed_bytes = 0

        # 删除过期临时文件
        for p in self._to_delete_files:
            try:
                size = p.stat().st_size
                p.unlink()
                freed_bytes += size
                deleted_files += 1
            except Exception as e:
                self.logger.log("删除失败", f"{p.relative_to(PROJECT_ROOT)}: {e}", "error")
                errors += 1

        # 删除空目录
        for d in self._to_delete_dirs:
            try:
                d.rmdir()
                deleted_dirs += 1
            except Exception as e:
                self.logger.log("删除目录失败", f"{d.relative_to(PROJECT_ROOT)}: {e}", "error")
                errors += 1

        # 删除重复文件（每个重复组保留第一个）
        for h, paths in self._duplicates.items():
            for dup in paths[1:]:
                try:
                    size = dup.stat().st_size
                    dup.unlink()
                    freed_bytes += size
                    deleted_files += 1
                except Exception as e:
                    self.logger.log(
                        "删除重复失败", f"{dup.relative_to(PROJECT_ROOT)}: {e}", "error"
                    )
                    errors += 1

        freed_mb = freed_bytes / (1024 * 1024)
        cprint(
            "G",
            f"    删除文件: {deleted_files} | 删除目录: {deleted_dirs} | 释放: {freed_mb:.1f} MB",
        )
        if errors:
            cprint("Y", f"    ⚠ {errors} 个操作失败（详见日志）")

    # ─── 主流程 ──────────────────────────────

    def run(self, check_deps_only: bool = False):
        """执行完整的扫描/清理流程"""
        cprint("BOLD", "\n╔══════════════════════════════════════════════════╗")
        cprint("BOLD", "║  昆仑创作引擎 — 项目清理与维护工具            ║")
        cprint("BOLD", "╚══════════════════════════════════════════════════╝")

        if self.dry_run:
            cprint("Y", "\n  ⚠ 预览模式 — 不会删除任何文件\n")
        else:
            cprint("R", "\n  ⚠ 执行模式 — 将删除文件！\n")

        # 扫描
        self._to_delete_files = self.scan_temp_files()
        self._to_delete_dirs = self.scan_empty_dirs()
        self._duplicates = self.scan_duplicates()
        self._outdated_deps = self.check_dependencies()

        if check_deps_only:
            self._print_deps_only()
            self.logger.close()
            return

        # 统计
        total_files = len(self._to_delete_files) + sum(
            len(v) - 1 for v in self._duplicates.values()
        )
        total_dirs = len(self._to_delete_dirs)

        # 计算可释放空间
        freed_total = sum(p.stat().st_size for p in self._to_delete_files if p.exists())
        freed_total += sum(
            sum(dup.stat().st_size for dup in paths[1:] if dup.exists())
            for paths in self._duplicates.values()
        )
        freed_mb = freed_total / (1024 * 1024)

        # 预览摘要
        cprint("BOLD", f"\n╔══════════════════════════════════════════════════╗")
        cprint("BOLD", f"║  扫描结果摘要                                    ║")
        cprint("BOLD", f"╚══════════════════════════════════════════════════╝")
        print(f"  过期临时文件: {len(self._to_delete_files)} 个")
        print(f"  重复文件:     {sum(len(v) - 1 for v in self._duplicates.values())} 个")
        print(f"  空目录:       {len(self._to_delete_dirs)} 个")
        print(f"  可升级依赖:   {len(self._outdated_deps)} 个")
        print(f"  预计释放空间: {freed_mb:.1f} MB")
        print()

        if total_files == 0 and total_dirs == 0 and not self._outdated_deps:
            cprint("G", "  ✅ 项目很干净，无需清理！")
            self.logger.close()
            return

        # 预览模式：展示将要删除的文件列表
        if self.dry_run:
            self._show_preview()
            self._ask_to_execute()
        else:
            self._confirm_and_execute()

        self.logger.close()

    def _show_preview(self):
        """展示预览列表"""
        if self._to_delete_files:
            cprint("Y", "\n  📋 待清理的过期临时文件 (前 20 个):")
            for p in sorted(self._to_delete_files)[:20]:
                rel = p.relative_to(PROJECT_ROOT)
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime)
                    age = (datetime.now() - mtime).days
                except OSError:
                    age = "?"
                print(f"    [{age}d] {rel}")
            if len(self._to_delete_files) > 20:
                print(f"    ... 还有 {len(self._to_delete_files) - 20} 个")

        if self._duplicates:
            cprint("Y", "\n  📋 重复文件组 (保留每组第一个):")
            for h, paths in list(self._duplicates.items())[:5]:
                kept = paths[0].relative_to(PROJECT_ROOT)
                print(f"    保留: {kept}")
                for dup in paths[1:]:
                    print(f"    ✗ 删除: {dup.relative_to(PROJECT_ROOT)}")
            if len(self._duplicates) > 5:
                print(f"    ... 还有 {len(self._duplicates) - 5} 组")

        if self._to_delete_dirs:
            cprint("Y", "\n  📋 空目录 (前 10 个):")
            for d in sorted(self._to_delete_dirs)[:10]:
                print(f"    {d.relative_to(PROJECT_ROOT)}")
            if len(self._to_delete_dirs) > 10:
                print(f"    ... 还有 {len(self._to_delete_dirs) - 10} 个")

    def _ask_to_execute(self):
        """询问用户是否执行清理"""
        print()
        choice = input("  是否执行清理? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            self.dry_run = False
            # 重新设置日志状态为 deleted
            for entry in self.logger.entries:
                if entry["status"] == "skipped":
                    entry["status"] = "deleted"
            self.execute_deletions()
        else:
            cprint("Y", "  已取消。使用 --execute 参数可在预览后执行。")

    def _confirm_and_execute(self):
        """确认并执行（执行模式）"""
        if self.auto_confirm:
            self.execute_deletions()
            return
        print(
            f"  将删除 {len(self._to_delete_files)} 个文件 和 {len(self._to_delete_dirs)} 个空目录"
        )
        choice = input("  确认执行? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            self.execute_deletions()
        else:
            cprint("Y", "  已取消。")

    def _print_deps_only(self):
        """仅输出依赖检查结果"""
        if self._outdated_deps:
            cprint("Y", "\n  📋 可升级的依赖:")
            for dep in self._outdated_deps:
                print(f"    {dep['name']}: {dep['current']} → {dep['latest']}")
            cprint("C", "\n  🔧 升级命令:")
            for cmd in self.generate_upgrade_commands(self._outdated_deps):
                print(f"    {cmd}")


# ─── 入口 ─────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="昆仑创作引擎 — 项目清理与维护",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/cleanup.py                    预览模式（只扫描）
  python scripts/cleanup.py --execute          预览后确认执行
  python scripts/cleanup.py --execute --yes    直接执行，跳过确认
  python scripts/cleanup.py --days 30          30天阈值
  python scripts/cleanup.py --check-deps       仅检查依赖
  python scripts/cleanup.py --full             完整扫描
        """,
    )
    parser.add_argument("--execute", "-x", action="store_true", help="执行清理（默认仅预览）")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认提示")
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=DEFAULT_DAYS,
        help=f"清理超过 N 天的临时文件（默认: {DEFAULT_DAYS}）",
    )
    parser.add_argument("--check-deps", action="store_true", help="仅检查依赖版本，不清理文件")
    parser.add_argument("--full", "-f", action="store_true", help="完整扫描（含重复文件检测）")
    parser.add_argument("--no-duplicates", action="store_true", help="跳过重复文件扫描（加速）")

    args = parser.parse_args()

    # 初始化日志
    logger = CleanupLogger(LOG_FILE)

    # 创建清理器
    cleaner = ProjectCleaner(
        logger=logger,
        days=args.days,
        dry_run=not args.execute,
        auto_confirm=args.yes,
    )

    try:
        cleaner.run(check_deps_only=args.check_deps)
    except KeyboardInterrupt:
        cprint("Y", "\n\n  用户中断")
        logger.close()
        sys.exit(0)
    except Exception as e:
        cprint("R", f"\n  ❌ 错误: {e}")
        logger.log("致命错误", str(e), "error")
        logger.close()
        sys.exit(1)


if __name__ == "__main__":
    main()

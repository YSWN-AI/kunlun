"""
昆仑创作引擎 — 版本管理器

基于 Git 的语义版本控制，自动为章节/大纲/设定/配置变更生成 commit，
支持 diff 对比、blame 追溯、回滚和实验性分支。

自动 commit 信息格式：
    [Writer] ch42_v3: Auditor 8.7 → 调整结尾钩子
    [Architect] outline_v2: 赛道趋势变化 → 重规划50-80章
    [Manual] ch42_v4: 作者手动修改对话语气
    [Auditor] ch42_v3: 打回 → 角色口语漂移 3处
    [Config] gate_threshold: 爽点间隔 3→2

设计来源：昆仑_剩余功能补全设计.md §15. 版本管理
"""

from __future__ import annotations

import contextlib
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from loguru import logger

from kunlun.config import settings

# ─── 枚举 ───────────────────────────────────────────


class CommitScope(StrEnum):
    WRITER = "Writer"
    ARCHITECT = "Architect"
    AUDITOR = "Auditor"
    MANUAL = "Manual"
    CONFIG = "Config"
    OUTLINE = "Outline"
    SETTING = "Setting"
    PUBLISH = "Publish"


class DiffFormat(StrEnum):
    UNIFIED = "unified"
    SIDE_BY_SIDE = "side_by_side"
    STAT = "stat"


# ─── 数据结构 ───────────────────────────────────────


@dataclass
class VersionEntry:
    commit_hash: str
    short_hash: str
    scope: CommitScope
    message: str
    author: str
    timestamp: str
    files_changed: int


@dataclass
class DiffResult:
    from_version: str
    to_version: str
    files: list[str]
    additions: int
    deletions: int
    diff_text: str


@dataclass
class BlameLine:
    line_number: int
    commit_hash: str
    short_hash: str
    author: str
    timestamp: str
    content: str


# ─── 版本管理器 ─────────────────────────────────────


class VersionManager:
    """Git 驱动的版本管理器。

    在项目目录自动初始化 Git 仓库，每次文件写入后自动 commit。
    非侵入式：用户完全不感知，除非主动查询历史。
    """

    def __init__(self, repo_path: str | None = None):
        self._repo_path = Path(repo_path or str(getattr(settings, "project_root", Path.cwd()))).resolve()
        self._initialized = False
        self._ensure_git_repo()

    # ── 仓库初始化 ──────────────────────────────────

    def _ensure_git_repo(self) -> bool:
        if self._initialized:
            return True
        try:
            git_dir = self._repo_path / ".git"
            if git_dir.exists():
                self._initialized = True
                return True
            result = subprocess.run(
                ["git", "init"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                self._initialized = True
                logger.info(f"Git 仓库已初始化: {self._repo_path}")
                self._ensure_gitignore()
                return True
            logger.error(f"Git init 失败: {result.stderr}")
            return False
        except FileNotFoundError:
            logger.warning("Git 未安装，版本管理功能不可用")
            return False
        except Exception as e:
            logger.error(f"Git 初始化异常: {e}", exc_info=True)
            return False

    def _ensure_gitignore(self):
        gitignore = self._repo_path / ".gitignore"
        patterns = [
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.egg-info/",
            "dist/",
            "build/",
            "data/drafts/",
            "data/kg_db/",
            "data/vector_db/",
            ".env",
            "*.log",
        ]
        existing: set[str] = set()
        if gitignore.exists():
            existing = set(gitignore.read_text(encoding="utf-8").splitlines())
        new_patterns = [p for p in patterns if p not in existing]
        if new_patterns:
            with gitignore.open("a", encoding="utf-8") as f:
                for p in new_patterns:
                    f.write(f"\n{p}")
            logger.info(f"已更新 .gitignore，新增 {len(new_patterns)} 条规则")

    def is_available(self) -> bool:
        return self._initialized

    # ── 自动提交 ────────────────────────────────────

    def auto_commit(
        self,
        file_path: str,
        scope: CommitScope,
        message: str,
        author: str = "kunlun",
    ) -> str | None:
        """文件写入后自动 add + commit。

        Args:
            file_path: 变更文件路径（相对于 repo_path）
            scope: 操作来源（Writer/Architect/Auditor/Manual/Config）
            message: 变更描述
            author: 提交者标识

        Returns:
            7 位短 commit hash，失败返回 None。
        """
        if not self._initialized:
            return None
        try:
            full_message = f"[{scope.value}] {message}"
            subprocess.run(
                ["git", "add", file_path],
                cwd=str(self._repo_path),
                capture_output=True,
                timeout=10,
                check=False,
            )
            result = subprocess.run(
                ["git", "commit", "-m", full_message, f"--author={author} <{author}@kunlun.local>"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                hash_result = subprocess.run(
                    ["git", "rev-parse", "--short=7", "HEAD"],
                    cwd=str(self._repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                short_hash = hash_result.stdout.strip()
                logger.debug(f"Auto commit: {short_hash} — {full_message}")
                return short_hash
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                # git commit 在无变更时返回非零退出码，检查消息确认
                return None
            logger.warning(f"Commit 失败: {result.stderr.strip()}")
            return None
        except Exception as e:
            logger.error(f"Auto commit 异常: {e}")
            return None

    def commit_all(
        self,
        scope: CommitScope,
        message: str,
        author: str = "kunlun",
    ) -> str | None:
        """add all + commit，用于批量变更。"""
        if not self._initialized:
            return None
        try:
            full_message = f"[{scope.value}] {message}"
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self._repo_path),
                capture_output=True,
                timeout=10,
                check=False,
            )
            result = subprocess.run(
                ["git", "commit", "-m", full_message, f"--author={author} <{author}@kunlun.local>"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                hash_result = subprocess.run(
                    ["git", "rev-parse", "--short=7", "HEAD"],
                    cwd=str(self._repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                return hash_result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Commit all 异常: {e}")
            return None

    # ── 历史查询 ────────────────────────────────────

    def log(
        self,
        file_path: str | None = None,
        max_count: int = 50,
    ) -> list[VersionEntry]:
        """查询版本历史。

        Args:
            file_path: 可选的文件路径过滤
            max_count: 最大返回数
        """
        if not self._initialized:
            return []
        try:
            args = [
                "git",
                "log",
                f"--max-count={max_count}",
                "--pretty=format:%H||%h||%an||%aI||%s",
            ]
            if file_path:
                args.extend(["--", file_path])
            result = subprocess.run(
                args,
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            entries: list[VersionEntry] = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("||", 4)
                if len(parts) < 5:
                    continue
                scope = CommitScope.MANUAL
                raw_msg = parts[4]
                if raw_msg.startswith("[") and "]" in raw_msg[:20]:
                    end = raw_msg.index("]")
                    scope_str = raw_msg[1:end]
                    with contextlib.suppress(ValueError):
                        scope = CommitScope(scope_str)
                    message = raw_msg[end + 1 :].strip()
                else:
                    message = raw_msg

                stat_result = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--numstat", parts[0]],
                    cwd=str(self._repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                files_changed = (
                    len(stat_result.stdout.strip().split("\n")) if stat_result.stdout.strip() else 0
                )

                entries.append(
                    VersionEntry(
                        commit_hash=parts[0],
                        short_hash=parts[1],
                        scope=scope,
                        message=message,
                        author=parts[2],
                        timestamp=parts[3],
                        files_changed=files_changed,
                    )
                )
            return entries
        except Exception as e:
            logger.error(f"Git log 异常: {e}")
            return []

    # ── Diff 对比 ───────────────────────────────────

    def diff(
        self,
        from_version: str = "HEAD~1",
        to_version: str = "HEAD",
        file_path: str | None = None,
    ) -> DiffResult | None:
        """对比两个版本的差异。

        Args:
            from_version: 起始版本（commit hash / HEAD~N）
            to_version: 目标版本
            file_path: 可选的文件过滤
        """
        if not self._initialized:
            return None
        try:
            args = ["git", "diff", from_version, to_version]
            if file_path:
                args.extend(["--", file_path])

            result = subprocess.run(
                args,
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                logger.error(f"Git diff 失败: {result.stderr}")
                return None

            diff_text = result.stdout
            additions = diff_text.count("\n+") - diff_text.count("\n+++")
            deletions = diff_text.count("\n-") - diff_text.count("\n---")

            stat_result = subprocess.run(
                ["git", "diff", "--name-only", from_version, to_version],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            files = stat_result.stdout.strip().split("\n") if stat_result.stdout.strip() else []

            return DiffResult(
                from_version=from_version,
                to_version=to_version,
                files=files,
                additions=additions,
                deletions=deletions,
                diff_text=diff_text,
            )
        except Exception as e:
            logger.error(f"Git diff 异常: {e}")
            return None

    # ── Blame 追溯 ──────────────────────────────────

    def blame(
        self,
        file_path: str,
        max_lines: int = 200,
    ) -> list[BlameLine]:
        """追溯文件每行由谁/哪个 Agent 产生。

        Args:
            file_path: 相对于 repo_path 的文件路径
            max_lines: 最大追溯行数
        """
        if not self._initialized:
            return []
        try:
            result = subprocess.run(
                ["git", "blame", "--line-porcelain", file_path],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            lines: list[BlameLine] = []
            current: dict[str, str] = {}
            line_num = 0
            for raw_line in result.stdout.split("\n"):
                if not raw_line:
                    continue
                if raw_line.startswith("\t"):
                    current["content"] = raw_line[1:]
                    lines.append(
                        BlameLine(
                            line_number=line_num,
                            commit_hash=current.get("hash", ""),
                            short_hash=current.get("hash", "")[:7],
                            author=current.get("author", ""),
                            timestamp=current.get("author-time", ""),
                            content=current.get("content", ""),
                        )
                    )
                    current = {}
                elif " " in raw_line:
                    key, value = raw_line.split(" ", 1)
                    current[key] = value
                    if key == "author":
                        line_num += 1
                if len(lines) >= max_lines:
                    break
            return lines
        except Exception as e:
            logger.error(f"Git blame 异常: {e}")
            return []

    # ── 回滚 ────────────────────────────────────────

    def revert(
        self,
        commit_hash: str,
        file_path: str | None = None,
        dry_run: bool = True,
    ) -> bool:
        """回滚文件到指定版本。

        Args:
            commit_hash: 目标版本 hash
            file_path: 可选的文件限定
            dry_run: 仅预览，不实际执行

        Returns:
            是否成功。
        """
        if not self._initialized:
            return False
        try:
            if dry_run:
                result = subprocess.run(
                    ["git", "show", f"{commit_hash}:{file_path}" if file_path else commit_hash],
                    cwd=str(self._repo_path),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                logger.info(f"Dry-run 回滚预览:\n{result.stdout[:500]}...")
                return True

            args = ["git", "checkout", commit_hash]
            if file_path:
                args.extend(["--", file_path])
            result = subprocess.run(
                args,
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                self.auto_commit(
                    file_path or ".",
                    CommitScope.MANUAL,
                    f"回滚到 {commit_hash[:7]}",
                )
                return True
            logger.error(f"回滚失败: {result.stderr}")
            return False
        except Exception as e:
            logger.error(f"Git revert 异常: {e}")
            return False

    # ── 实验分支 ────────────────────────────────────

    def create_branch(self, branch_name: str) -> bool:
        """创建实验性创作分支。"""
        if not self._initialized:
            return False
        try:
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"创建分支异常: {e}")
            return False

    def merge_branch(self, branch_name: str) -> bool:
        """合并实验分支到当前分支。"""
        if not self._initialized:
            return False
        try:
            result = subprocess.run(
                ["git", "merge", branch_name],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"合并分支异常: {e}")
            return False

    def current_branch(self) -> str:
        """获取当前分支名。"""
        if not self._initialized:
            return "unknown"
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def list_branches(self) -> list[str]:
        """列出所有分支。"""
        if not self._initialized:
            return []
        try:
            result = subprocess.run(
                ["git", "branch"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return [line.lstrip("*").strip() for line in result.stdout.split("\n") if line.strip()]
        except Exception:
            return []

    # ── 版本快照 ────────────────────────────────────

    def get_current_hash(self) -> str | None:
        """获取当前 HEAD 的短 hash。"""
        if not self._initialized:
            return None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=7", "HEAD"],
                cwd=str(self._repo_path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.stdout.strip() or None
        except Exception:
            return None

    def get_version_summary(self) -> dict:
        """获取当前版本总览。"""
        return {
            "available": self._initialized,
            "repo_path": str(self._repo_path),
            "current_branch": self.current_branch(),
            "current_hash": self.get_current_hash(),
            "branches": self.list_branches(),
            "total_commits": len(self.log(max_count=1)),
        }


# ─── 全局单例 ──────────────────────────────────────

version_manager = VersionManager()

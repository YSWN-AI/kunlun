"""
昆仑创作引擎 — 版本管理系统

基于 Git 的章节级语义版本控制，每次修改自动 commit，
支持 diff 对比、blame 追溯、回滚和实验性分支。

设计来源：昆仑_剩余功能补全设计.md §版本管理
"""

from kunlun.versions.manager import VersionManager

__all__ = ["VersionManager"]

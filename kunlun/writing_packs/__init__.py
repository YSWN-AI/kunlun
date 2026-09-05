"""
写作内容包系统 — Rule / Workflow / Skill 三插件体系

对标灵蟹创作 Marketplace，提供内容级写作插件：
- Rule: 个人写作偏好，自动注入 Prompt
- Workflow: 可重用写作步骤，命令触发
- Skill: 专业知识包，按场景自动激活

用法:
    from kunlun.writing_packs import WritingPackManager, PackType
    mgr = WritingPackManager(book_id="test")
    rules = mgr.get_active_rules()
"""

from kunlun.writing_packs.manager import WritingPackManager
from kunlun.writing_packs.models import (
    PackType,
    RulePack,
    SkillPack,
    WorkflowPack,
    WorkflowStep,
)
from kunlun.writing_packs.presets import (
    BUILTIN_RULES,
    BUILTIN_SKILLS,
    BUILTIN_WORKFLOWS,
    get_all_builtin_packs,
)

__all__ = [
    "BUILTIN_RULES",
    "BUILTIN_SKILLS",
    "BUILTIN_WORKFLOWS",
    "PackType",
    "RulePack",
    "SkillPack",
    "WorkflowPack",
    "WorkflowStep",
    "WritingPackManager",
    "get_all_builtin_packs",
]

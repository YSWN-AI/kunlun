"""
写作内容包数据模型 — Rule / Workflow / Skill 三插件体系

对标灵蟹创作 Marketplace 三种插件类型：
- Rule: 个人写作偏好，自动注入 Prompt，无需手动调用
- Workflow: 打包重复写作任务为可重用步骤，命令触发
- Skill: 专业知识包，按场景自动激活
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class PackType(StrEnum):
    """内容包类型"""

    RULE = "rule"
    WORKFLOW = "workflow"
    SKILL = "skill"


class RulePack(BaseModel):
    """规则包 — 个人写作偏好，自动注入系统 Prompt"""

    id: str
    name: str
    description: str
    type: PackType = PackType.RULE
    content: str = Field(..., description="规则内容，将注入到系统Prompt")
    category: str = Field(
        default="general",
        description="分类: style/dialogue/pace/plot/general",
    )
    enabled: bool = True
    builtin: bool = False
    created_at: str = ""


class WorkflowStep(BaseModel):
    """工作流步骤"""

    name: str
    description: str
    prompt: str = Field(..., description="该步骤的LLM Prompt模板")
    input_required: list[str] = Field(default_factory=list)


class WorkflowPack(BaseModel):
    """工作流包 — 打包重复写作任务为可重用步骤"""

    id: str
    name: str
    description: str
    type: PackType = PackType.WORKFLOW
    steps: list[WorkflowStep]
    trigger_command: str = Field(..., description="触发命令，如 /revise、/outline")
    enabled: bool = True
    builtin: bool = False
    created_at: str = ""


class SkillPack(BaseModel):
    """技能包 — 专业知识包，按场景自动激活"""

    id: str
    name: str
    description: str
    type: PackType = PackType.SKILL
    knowledge: str = Field(..., description="专业知识内容，将作为上下文注入")
    trigger_scenes: list[str] = Field(
        default_factory=list,
        description="触发场景: world_building/character_design/plot_structure/combat/dialogue",
    )
    enabled: bool = True
    builtin: bool = False
    created_at: str = ""

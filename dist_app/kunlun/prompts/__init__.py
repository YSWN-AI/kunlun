"""昆仑创作引擎 — Prompt 模板库"""

from .pipeline import (
    PIPELINE_PROMPTS,
    PipelineTemplate,
    format_template,
    get_template,
    inject_skill_context,
)
from .society import PROMPT_PARAMS, SOCIETY_PROMPTS, get_prompt

__all__ = [
    "PIPELINE_PROMPTS",
    "PROMPT_PARAMS",
    "SOCIETY_PROMPTS",
    "PipelineTemplate",
    "format_template",
    "get_prompt",
    "get_template",
    "inject_skill_context",
]

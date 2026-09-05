"""
昆仑创作引擎 — 生成器集合

各生成器均为纯模板+规则实现，不调用 LLM，确保离线可用、零成本。
"""

from kunlun.toolbox.generators.chapter_outline_generator import generate_chapter_outline
from kunlun.toolbox.generators.character_generator import generate_character
from kunlun.toolbox.generators.cheat_generator import generate_cheats
from kunlun.toolbox.generators.name_generator import generate_names
from kunlun.toolbox.generators.opening_generator import generate_opening
from kunlun.toolbox.generators.outline_generator import generate_outline
from kunlun.toolbox.generators.synopsis_generator import generate_synopsis
from kunlun.toolbox.generators.title_generator import generate_titles

__all__ = [
    "generate_chapter_outline",
    "generate_character",
    "generate_cheats",
    "generate_names",
    "generate_opening",
    "generate_outline",
    "generate_synopsis",
    "generate_titles",
]

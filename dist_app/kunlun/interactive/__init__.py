"""
昆仑创作引擎 — 交互式小说模式

对标竞品互动叙事能力：读者选择分支 → 状态追踪 → 多结局 → KG世界状态集成。
"""

from kunlun.interactive.engine import (
    Choice,
    ChoiceOutcome,
    GameState,
    InteractiveFictionEngine,
    StoryEnding,
    get_interactive_engine,
)

__all__ = [
    "Choice",
    "ChoiceOutcome",
    "GameState",
    "InteractiveFictionEngine",
    "StoryEnding",
    "get_interactive_engine",
]

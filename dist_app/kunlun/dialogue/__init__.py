"""
dialogue 扩展模块
"""

from kunlun.dialogue.engine import (
    DialogueEvaluator,
    DialogueLine,
    DialogueMetrics,
    DialogueParser,
    DialogueReport,
    DialogueStyle,
    DistinctivenessLevel,
    SpeakerDistinctiveness,
    SpeakerProfile,
    get_dialogue_evaluator,
)

__all__ = [
    "DialogueEvaluator",
    "DialogueLine",
    "DialogueMetrics",
    "DialogueParser",
    "DialogueReport",
    "DialogueStyle",
    "DistinctivenessLevel",
    "SpeakerDistinctiveness",
    "SpeakerProfile",
    "get_dialogue_evaluator",
]

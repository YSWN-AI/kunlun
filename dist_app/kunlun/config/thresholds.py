"""
昆仑创作引擎 — 阈值配置 (去AI痕迹、审计阈值)
"""

from __future__ import annotations

from pydantic import BaseModel


class ThresholdsConfig(BaseModel):
    humanize_enabled: bool = True
    humanize_default_strategy: str = "standard"
    humanize_auto_strategy: bool = False
    humanize_target_score: float = 0.25
    humanize_max_passes: int = 3

    ai_threshold_sentence_cv: float = 0.30
    ai_threshold_conjunction_density: float = 3.0
    ai_threshold_paragraph_cv: float = 0.20
    ai_threshold_opening_diversity: float = 0.35

    audit_max_new_concepts_per_chapter: int = 3
    audit_max_gaps_between_pleasure_points: int = 3
    audit_max_same_pleasure_type_streak: int = 4
    audit_arc_max_position_deviation: int = 2
    audit_emotion_max_deviation_pct: float = 0.30
    audit_dialogue_max_nonsense_pct: float = 0.20

    model_config = {"extra": "ignore"}

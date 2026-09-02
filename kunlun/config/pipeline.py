"""
昆仑创作引擎 — 管线配置 (全管线、批处理、上下文预算)
"""

from __future__ import annotations

from pydantic import BaseModel


class PipelineConfig(BaseModel):
    pipeline_auto_proofread: bool = True
    pipeline_auto_structure_check: bool = True
    pipeline_auto_coherence_check: bool = True
    pipeline_auto_foreshadowing_check: bool = True
    pipeline_context_budget: int = 8000
    pipeline_default_genre: str = "xuanhuan"
    pipeline_max_parallel_agents: int = 5

    pipeline_max_revisions: int = 3
    pipeline_checkpoint_ttl: int = 86400
    pipeline_default_word_count: int = 2500
    pipeline_sociologist_token_budget: int = 2000
    pipeline_writer_token_budget: int = 5000
    pipeline_icu_token_budget: int = 3000

    batch_generate_size: int = 5
    batch_task_ttl: int = 86400

    model_config = {"extra": "ignore"}

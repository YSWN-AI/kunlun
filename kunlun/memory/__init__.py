"""
昆仑创作引擎 — 四层记忆架构模块

为百万字长篇小说创作提供持久化、可检索、主动遗忘的四层记忆系统。

Usage:
    from kunlun.memory import create_memory_manager, MemoryManager
    from kunlun.memory import WorkingMemory, EpisodicMemory, SemanticMemory, ProceduralMemory
    from kunlun.memory import SemanticEntity, EpisodicEvent, ProceduralPattern

    # 创建记忆管理器
    mm = create_memory_manager(book_id="my_novel", token_budget=6000)

    # 写入章节记忆
    mm.write_chapter_memory(
        chapter=1,
        content="第一章内容...",
        summary="第一章摘要...",
        events=[{"scene": "初登场", "summary": "...", "participants": ["主角"], "event_type": "transition"}],
        entities=[{"name": "主角", "entity_type": "character", "description": "..."}],
    )

    # 查询记忆
    result = mm.query("主角的实力", query_type="general", chapter=5)
    print(result.summary())

    # 获取角色档案
    sheet = mm.get_character_sheet("主角")

    # 获取情节回顾
    recap = mm.get_plot_recap(from_chapter=1)
"""

from kunlun.memory.engine import (
    EpisodicEvent,
    EpisodicMemory,
    MemoryImportance,
    MemoryItem,
    MemoryLayer,
    MemoryManager,
    MemoryQueryResult,
    ProceduralMemory,
    ProceduralPattern,
    SemanticEntity,
    SemanticEntityType,
    SemanticMemory,
    WorkingMemory,
    create_memory_manager,
    extract_entities_from_text,
)

__all__ = [
    "EpisodicEvent",
    "EpisodicMemory",
    "MemoryImportance",
    "MemoryItem",
    "MemoryLayer",
    "MemoryManager",
    "MemoryQueryResult",
    "ProceduralMemory",
    "ProceduralPattern",
    "SemanticEntity",
    "SemanticEntityType",
    "SemanticMemory",
    "WorkingMemory",
    "create_memory_manager",
    "extract_entities_from_text",
]

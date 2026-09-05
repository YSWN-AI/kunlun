"""
昆仑创作引擎 — 剧透过滤系统 (Spoiler Filter)

设计来源: ai-novel-writer 的六阶段渐进式节奏控制 + 四级剧透过滤机制

核心问题:
  AI 在写第5章时就知道第50章的结局，导致早期章节缺乏悬念、
  角色提前做出不符合当前认知的决定、核心冲突被过早暗示或解决。

解决方案:
  将全书分为6个阶段，每个阶段控制:
  1. RAG可见范围 — 能看到前后几章的内容
  2. 剧透过滤级别 — 从 strict(全过滤) 到 none(不过滤)
  3. 节奏目标 — 推进/铺垫/冲突升级/高潮/收尾

六阶段:
  开篇(≤12%)    → 只看本章, 不过滤后续 | strict
  早期发展(12-35%) → ±1章, 不看后续 | strict
  中期发展(35-60%) → ±2章, 看下一章 | moderate
  后期发展(60-78%) → ±2章, 看下一章 | minimal
  高潮(78-92%)   → ±2章, 跨章联动 | none
  收尾(≥92%)     → ±1章, 看下一章 | none
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger


class SpoilerLevel:
    """剧透过滤级别"""

    STRICT = "strict"  # 全过滤：不看任何后续内容
    MODERATE = "moderate"  # 中等：可看下一章标题和概要
    MINIMAL = "minimal"  # 轻微：可看后续伏笔和事件
    NONE = "none"  # 无过滤：可看全部


@dataclass
class StageConfig:
    """阶段配置"""

    name: str
    chapter_range: tuple[float, float]  # 百分比范围 (start, end)
    rag_lookahead: int  # 前后可见章节数
    use_future_rag: bool  # 是否可看未来章节RAG
    spoiler_level: str  # 剧透过滤级别
    pacing_goal: str  # 节奏目标


STAGES = [
    StageConfig(
        "开篇铺垫", (0, 0.12), 0, False, SpoilerLevel.STRICT, "建立世界观，引入主角和核心设定"
    ),
    StageConfig("早期发展", (0.12, 0.35), 1, False, SpoilerLevel.STRICT, "展开冲突，铺垫成长线"),
    StageConfig("中期发展", (0.35, 0.60), 2, True, SpoilerLevel.MODERATE, "冲突升级，多线交织"),
    StageConfig("后期发展", (0.60, 0.78), 2, True, SpoilerLevel.MINIMAL, "临近高潮，收紧线索"),
    StageConfig("高潮迭起", (0.78, 0.92), 2, True, SpoilerLevel.NONE, "核心冲突爆发，密集爽点"),
    StageConfig("收尾完结", (0.92, 1.0), 1, True, SpoilerLevel.NONE, "解决所有伏笔，收束全书"),
]


@dataclass
class StageResult:
    """分析结果"""

    stage: StageConfig
    chapter: int
    total: int
    progress: float
    visible_range: tuple[int, int]  # (start, end) 章节可见范围
    rag_query_modifier: str  # RAG查询修饰语
    spoiler_instructions: str  # 注入Writer的防剧透指令


class SpoilerFilter:
    """
    剧透过滤器

    使用方式:
        filter = SpoilerFilter()
        result = filter.get_stage(chapter=15, total=100)
        # result.rag_query_modifier → 限制RAG只查前几章
        # result.spoiler_instructions → 注入Writer prompt的指令
    """

    @staticmethod
    def get_stage(chapter: int, total: int) -> StageResult:
        """计算指定章节的剧透阶段"""
        progress = chapter / max(total, 1)

        stage = STAGES[-1]  # 默认最后阶段
        for s in STAGES:
            if s.chapter_range[0] < progress <= s.chapter_range[1]:
                stage = s
                break

        # 计算可见章节范围
        if stage.rag_lookahead == 0:
            visible_range = (max(1, chapter - 1), chapter)  # 只看当前和前一章
        else:
            start = max(1, chapter - stage.rag_lookahead)
            end = min(total, chapter + stage.rag_lookahead) if stage.use_future_rag else chapter
            visible_range = (start, end)

        # RAG查询修饰语
        rag_modifiers = {
            SpoilerLevel.STRICT: f"仅检索第{visible_range[0]}章到第{visible_range[1]}章的内容",
            SpoilerLevel.MODERATE: "主要检索已有章节内容，可预览下一章概要",
            SpoilerLevel.MINIMAL: "检索已有内容，可参考后续伏笔设定",
            SpoilerLevel.NONE: "",  # 无限制
        }

        # 注入Writer的防剧透指令
        spoiler_instructions = SpoilerFilter._build_spoiler_instructions(
            stage, chapter, total, visible_range
        )

        return StageResult(
            stage=stage,
            chapter=chapter,
            total=total,
            progress=round(progress * 100, 1),
            visible_range=visible_range,
            rag_query_modifier=rag_modifiers.get(stage.spoiler_level, ""),
            spoiler_instructions=spoiler_instructions,
        )

    @staticmethod
    def _build_spoiler_instructions(
        stage: StageConfig, chapter: int, total: int, visible: tuple[int, int]
    ) -> str:
        """构建注入Writer的防剧透指令"""
        if stage.spoiler_level == SpoilerLevel.STRICT:
            return (
                f"【剧透约束 - STRICT】\n"
                f"当前阶段: {stage.name} (第{chapter}章/共{total}章)\n"
                f"约束: 你的认知仅限于已发生的剧情(第1-{visible[1]}章)。\n"
                f"1. ❌ 不能暗示或提及任何未来情节\n"
                f"2. ❌ 不能过早引入后期才会出现的角色/设定\n"
                f"3. ✅ 专注当前章节的冲突和悬念\n"
                f"4. ✅ 结尾必须留下疑问或未知"
            )
        if stage.spoiler_level == SpoilerLevel.MODERATE:
            return (
                f"【剧透约束 - MODERATE】\n"
                f"当前阶段: {stage.name} (进度{chapter / max(total, 1) * 100:.0f}%)\n"
                f"1. ⚠️ 可参考下一章概要，但不能提前解决其冲突\n"
                f"2. ✅ 可引入新的伏笔和线索\n"
                f"3. ❌ 不能解决核心冲突\n"
                f"4. ✅ 保持多条故事线并行推进"
            )
        if stage.spoiler_level == SpoilerLevel.MINIMAL:
            return (
                f"【剧透约束 - MINIMAL】\n"
                f"当前阶段: {stage.name} (临近高潮)\n"
                f"1. ✅ 可参考后续伏笔安排揭示节奏\n"
                f"2. ⚠️ 逐步收紧线索，为主冲突做准备\n"
                f"3. ✅ 可以在本章结尾留下重大悬念\n"
                f"4. ❌ 保留核心冲突到高潮阶段"
            )
        # NONE
        return (
            f"【剧透约束 - NONE】\n"
            f"当前阶段: {stage.name}\n"
            f"1. ✅ 可自由调用所有已知信息\n"
            f"2. ✅ 可解决伏笔和冲突\n"
            f"3. ✅ 收束所有故事线\n"
            f"4. ✅ 给出完满结局"
        )

    @staticmethod
    def filter_rag_candidates(candidates: list[dict], chapter: int, total: int) -> list[dict]:
        """
        根据剧透阶段过滤RAG候选结果。

        确保早期章节不会从向量库中检索到未来章节的内容。

        Args:
            candidates: RAG检索候选列表，每项含 chapter 字段
            chapter: 当前章节号
            total: 总章节数

        Returns:
            过滤后的候选列表
        """
        stage_info = SpoilerFilter.get_stage(chapter, total)
        start, end = stage_info.visible_range

        filtered = []
        for c in candidates:
            c_chapter = c.get("chapter", 0) if isinstance(c, dict) else 0
            if c_chapter == 0 or (start <= c_chapter <= end):
                filtered.append(c)

        removed = len(candidates) - len(filtered)
        if removed > 0:
            logger.debug(f"[SpoilerFilter] 过滤了{removed}个未来章节的RAG结果")

        return filtered


# 全局单例
spoiler_filter = SpoilerFilter()

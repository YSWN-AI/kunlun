"""
昆仑创作引擎 — Writer 上下文动态压缩 (ReIO 适配)

灵感来源: StoryWriter 论文的 ReIO (Relevant Information Organization) 机制
对标: 长篇网文连载中 Writer Agent 的上下文爆炸问题

核心机制 (ReIO):
  1. Coordinator — 压缩历史叙事，提取关键信息
  2. FinalWriter — 基于压缩后上下文重写增强

昆仑适配:
  - 将 ReIO 机制本地化为 Writer Agent 的上下文窗口管理
  - 动态排名历史章节 → 保留高相关度章节 → 摘要低相关度章节
  - 关键片段抽取 (伏笔/爽点/冲突/角色弧光)
  - 预算感知的上下文组装

核心能力:
  1. 历史章节相关性排名 — 基于关键词/实体/情节线
  2. 关键片段自动抽取 — 伏笔/转折/爽点/对话精华
  3. 上下文组装器 — 按预算 (token/字数) 自动组合最优上下文
  4. 遗忘管理 — 标记哪些信息可以遗忘 (非关键设定/已收束情节)

设计原则:
  - 零 LLM 成本的相关性计算 (纯统计)
  - 预算感知 (避免超出 LLM 上下文窗口)
  - 保留完整性 (关键伏笔不丢失)
  - 与 KG (知识图谱) 互补 (KG 管结构化, 这里管非结构化历史)
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 数据类型
# ══════════════════════════════════════════════════════


class ContextBudgetType(Enum):
    """上下文预算类型"""

    TOKENS = "tokens"  # Token 数
    CHARACTERS = "characters"  # 字符数
    SEGMENTS = "segments"  # 段落数


class RetentionPriority(Enum):
    """保留优先级"""

    CRITICAL = "critical"  # 关键 — 伏笔/核心冲突/角色第一次出场
    HIGH = "high"  # 高 — 爽点/转折/性格揭示
    MEDIUM = "medium"  # 中 — 过渡/日常/描述
    LOW = "low"  # 低 — 可安全压缩/遗忘
    EXPIRED = "expired"  # 过期 — 已完全收束的情节


@dataclass
class ChapterMemory:
    """章节记忆 (非结构化历史)"""

    chapter: int
    full_text: str = ""
    word_count: int = 0
    # 提取的关键信息
    key_snippets: list[str] = field(default_factory=list)  # 关键片段
    summary: str = ""  # AI 生成的摘要 (如果可用)
    entities_mentioned: list[str] = field(default_factory=list)  # 涉及实体
    plot_threads: list[str] = field(default_factory=list)  # 情节线
    foreshadowing_planted: list[str] = field(default_factory=list)  # 埋下的伏笔
    foreshadowing_resolved: list[str] = field(default_factory=list)  # 回收的伏笔
    retention: RetentionPriority = RetentionPriority.MEDIUM
    # 元数据
    surprise_score: float = 0.0  # 反转/惊喜度
    emotion_peak: bool = False  # 是否情绪高潮章
    chapter_title: str = ""


@dataclass
class ContextAssembly:
    """组装后的上下文"""

    target_chapter: int  # 目标章
    total_chars: int = 0  # 总字符数
    total_tokens_est: int = 0  # 估算 token 数
    budget_used_pct: float = 0.0  # 预算使用比例
    full_text_chapters: list[int] = field(default_factory=list)  # 完整保留的章
    summary_chapters: list[int] = field(default_factory=list)  # 摘要保留的章
    dropped_chapters: list[int] = field(default_factory=list)  # 完全丢弃的章
    assembled_text: str = ""  # 最终组装的上下文字符串
    stats: dict[str, Any] = field(default_factory=dict)  # 统计信息


# ══════════════════════════════════════════════════════
# 关键片段抽取器 (零 LLM)
# ══════════════════════════════════════════════════════

# 关键词权重表 (网文场景)
_CONFLICT_KEYWORDS: list[str] = [
    "战斗",
    "杀",
    "死",
    "血",
    "重伤",
    "逃跑",
    "追杀",
    "围攻",
    "阴谋",
    "背叛",
    "翻脸",
    "冲突",
    "决裂",
    "对决",
    "决斗",
]

_PLEASURE_KEYWORDS: list[str] = [
    "突破",
    "晋级",
    "升级",
    "顿悟",
    "觉醒",
    "奇遇",
    "机缘",
    "打脸",
    "逆袭",
    "碾压",
    "震惊",
    "轰动",
    "扬名",
    "成名",
]

_FORESHADOWING_PATTERNS: list[str] = [
    r"(?:似乎|隐约|莫名|说不清).{0,15}(?:感觉|觉得|预感)",
    r"(?:日后|日后|后来).{0,10}才(?:知道|明白|发现)",
    r"(?:当时|那时).{0,5}还?不知[道晓]",
    r"(?:留下|埋下).{0,5}伏笔",
    r"(?:这个|这)[^。]{0,10}(?:秘密|谜团|疑点|蹊跷)",
]

_CHARACTER_EMOTION_PEAKS: list[str] = [
    "泪流满面",
    "嚎啕大哭",
    "狂笑",
    "怒吼",
    "歇斯底里",
    "欣喜若狂",
    "悲痛欲绝",
    "怒不可遏",
    "仰天长啸",
]

_SURPRISE_PATTERNS: list[str] = [
    r"(?:竟然|居然|没想到|不料|谁知|哪知|意想不到)",
    r"(?:原来|其实)[^。]{0,15}(?:是|就是)",
    r"(?:反转|真相|内幕|隐情)",
]


class SnippetExtractor:
    """关键片段抽取器

    零 LLM 成本，纯正则 + 启发式规则
    从章节正文中提取高信息密度的关键片段
    """

    @staticmethod
    def extract(chapter_text: str, chapter_number: int) -> ChapterMemory:  # noqa: PLR0912
        """从章节中提取关键信息"""
        memory = ChapterMemory(chapter=chapter_number, full_text=chapter_text)
        memory.word_count = len(chapter_text)

        if not chapter_text.strip():
            return memory

        snippets: list[tuple[RetentionPriority, str]] = []

        # 1. 冲突场景检测
        conflict_score = 0
        for kw in _CONFLICT_KEYWORDS:
            conflict_score += chapter_text.count(kw)
        if conflict_score > 3:
            # 找到包含冲突关键词最多的段落
            for para in _split_into_paragraphs(chapter_text):
                score = sum(para.count(kw) for kw in _CONFLICT_KEYWORDS)
                if score >= 2 and len(para) > 30:
                    snippets.append((RetentionPriority.HIGH, para.strip()[:200]))

        # 2. 爽点场景检测
        pleasure_score = 0
        for kw in _PLEASURE_KEYWORDS:
            pleasure_score += chapter_text.count(kw)
        if pleasure_score > 2:
            for para in _split_into_paragraphs(chapter_text):
                score = sum(para.count(kw) for kw in _PLEASURE_KEYWORDS)
                if score >= 2 and len(para) > 30:
                    snippets.append((RetentionPriority.HIGH, para.strip()[:200]))

        # 3. 伏笔检测
        foreshadowing: list[str] = []
        for pattern in _FORESHADOWING_PATTERNS:
            for match in re.finditer(pattern, chapter_text):
                start = max(0, match.start() - 20)
                end = min(len(chapter_text), match.end() + 40)
                snippet = chapter_text[start:end].strip().replace("\n", " ")
                foreshadowing.append(snippet)
                snippets.append((RetentionPriority.CRITICAL, snippet[:200]))

        memory.foreshadowing_planted = foreshadowing

        # 4. 情绪高潮检测
        for emotion in _CHARACTER_EMOTION_PEAKS:
            if emotion in chapter_text:
                idx = chapter_text.find(emotion)
                start = max(0, idx - 50)
                end = min(len(chapter_text), idx + 100)
                snippet = chapter_text[start:end].strip().replace("\n", " ")
                snippets.append((RetentionPriority.HIGH, snippet[:200]))
                memory.emotion_peak = True
                break

        # 5. 反转/惊喜检测
        surprise_count = 0
        for pattern in _SURPRISE_PATTERNS:
            surprise_count += len(re.findall(pattern, chapter_text))
        if surprise_count > 0:
            memory.surprise_score = min(1.0, surprise_count / 5)
            for match in re.finditer(_SURPRISE_PATTERNS[0], chapter_text):
                start = max(0, match.start() - 30)
                end = min(len(chapter_text), match.end() + 80)
                snippet = chapter_text[start:end].strip().replace("\n", " ")
                snippets.append((RetentionPriority.HIGH, snippet[:200]))
                break

        # 6. 对话精华 (取首段和最长对话)
        dialogue_blocks = _extract_dialogues(chapter_text)
        if dialogue_blocks:
            # 最长对话块
            longest = max(dialogue_blocks, key=len)
            if len(longest) > 50:
                snippets.append((RetentionPriority.MEDIUM, longest[:200]))
            # 首段对话
            if len(dialogue_blocks) > 1 and len(dialogue_blocks[0]) > 30:
                snippets.append((RetentionPriority.MEDIUM, dialogue_blocks[0][:200]))

        # 7. 实体提取 (简单命名实体)
        memory.entities_mentioned = _extract_named_entities(chapter_text)

        # 去重并排序
        seen: set[str] = set()
        unique_snippets: list[str] = []
        for _priority, snippet in snippets:
            normalized = snippet[:50]  # 用前 50 字去重
            if normalized not in seen:
                seen.add(normalized)
                unique_snippets.append(snippet)

        memory.key_snippets = unique_snippets[:15]  # 最多 15 条

        # 决定整章保留优先级
        memory.retention = SnippetExtractor._determine_retention(
            memory, conflict_score, pleasure_score, surprise_count
        )

        return memory

    @staticmethod
    def _determine_retention(
        memory: ChapterMemory,
        conflict_score: int,
        pleasure_score: int,
        surprise_count: int,
    ) -> RetentionPriority:
        """决定章节整体保留优先级"""
        critical_indicators = 0

        if memory.foreshadowing_planted:
            critical_indicators += 2
        if memory.emotion_peak:
            critical_indicators += 1
        if conflict_score > 5:
            critical_indicators += 1
        if pleasure_score > 3:
            critical_indicators += 1
        if surprise_count > 2:
            critical_indicators += 1

        if critical_indicators >= 4:
            return RetentionPriority.CRITICAL
        if critical_indicators >= 2:
            return RetentionPriority.HIGH
        if critical_indicators >= 1:
            return RetentionPriority.MEDIUM
        return RetentionPriority.LOW


# ══════════════════════════════════════════════════════
# 历史章节相关性排名
# ══════════════════════════════════════════════════════


class ChapterRanker:
    """历史章节相关性排名器

    基于:
    1. 章节近邻 (越近的章越相关)
    2. 实体重叠 (与当前章共享角色的章)
    3. 情节线连续性 (同一情节线的章)
    4. 伏笔/回收关系
    """

    @staticmethod
    def rank(
        target_chapter: int,
        memories: dict[int, ChapterMemory],
        current_entities: list[str] | None = None,
        current_plot_threads: list[str] | None = None,
    ) -> list[tuple[int, float, ChapterMemory]]:
        """对历史章节进行相关性排名"""
        scored: list[tuple[int, float, ChapterMemory]] = []

        for ch, memory in memories.items():
            if ch >= target_chapter:
                continue

            score = 0.0

            # 1. 近邻加分 (指数衰减)
            distance = target_chapter - ch
            if distance <= 3:
                score += 3.0 / max(distance, 1)
            elif distance <= 10:
                score += 1.0 / (distance - 2)
            else:
                score += 0.3 / (distance * 0.1)

            # 2. 实体重叠加分
            if current_entities and memory.entities_mentioned:
                overlap = len(set(current_entities) & set(memory.entities_mentioned))
                score += overlap * 0.5

            # 3. 情节线连续性加分
            if current_plot_threads and memory.plot_threads:
                thread_overlap = len(set(current_plot_threads) & set(memory.plot_threads))
                score += thread_overlap * 1.0

            # 4. 保留优先级加分
            priority_bonus = {
                RetentionPriority.CRITICAL: 5.0,
                RetentionPriority.HIGH: 3.0,
                RetentionPriority.MEDIUM: 1.0,
                RetentionPriority.LOW: 0.2,
                RetentionPriority.EXPIRED: 0.0,
            }
            score += priority_bonus.get(memory.retention, 0)

            # 5. 伏笔/爽点/反转加分
            if memory.foreshadowing_planted:
                score += len(memory.foreshadowing_planted) * 0.5
            if memory.emotion_peak:
                score += 1.0
            if memory.surprise_score > 0.5:
                score += 2.0

            scored.append((ch, score, memory))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# ══════════════════════════════════════════════════════
# 上下文组装器
# ══════════════════════════════════════════════════════


class ContextAssembler:
    """上下文组装器 — 按预算自动组合最优上下文

    策略:
    1. CRITICAL 章 → 保留关键片段 (最多 2 章完整)
    2. HIGH 章 → 保留摘要 + 关键片段
    3. MEDIUM 章 → 保留摘要
    4. LOW 章 → 丢弃或仅一句话概括
    5. EXPIRED 章 → 完全丢弃

    预算分配:
    - 50% 近邻章节 (最近 3 章完整)
    - 30% 高相关章节片段
    - 15% 伏笔/关键冲突
    - 5%  情节摘要
    """

    def __init__(self, max_chars: int = 8000, max_tokens_est: int = 3000):
        self.max_chars = max_chars
        self.max_tokens_est = max_tokens_est

    def assemble(
        self,
        target_chapter: int,
        memories: dict[int, ChapterMemory],
        current_context_hints: str = "",
    ) -> ContextAssembly:
        """组装最优上下文"""
        assembly = ContextAssembly(target_chapter=target_chapter)

        # 排名
        ranked = ChapterRanker.rank(target_chapter, memories)
        if not ranked:
            assembly.assembled_text = current_context_hints
            return assembly

        chars_used = 0
        sections: list[str] = []

        # 分类
        criticals = [(ch, s, m) for ch, s, m in ranked if m.retention == RetentionPriority.CRITICAL]
        highs = [(ch, s, m) for ch, s, m in ranked if m.retention == RetentionPriority.HIGH]
        mediums = [(ch, s, m) for ch, s, m in ranked if m.retention == RetentionPriority.MEDIUM]
        lows = [(ch, s, m) for ch, s, m in ranked if m.retention == RetentionPriority.LOW]

        remaining_budget = self.max_chars

        # Layer 1: CRITICAL 章 — 关键片段
        for ch, _score, mem in criticals[:3]:
            for snippet in mem.key_snippets[:5]:
                snippet_len = len(snippet)
                if chars_used + snippet_len < self.max_chars * 0.6:
                    sections.append(f"[第{ch}章·关键] {snippet}")
                    chars_used += snippet_len
                else:
                    break
            assembly.full_text_chapters.append(ch)

        # Layer 2: 近邻 3 章 — 完整 (如果预算允许)
        for ch, _score, mem in ranked:
            if target_chapter - ch <= 3:
                text = mem.full_text
                if len(text) > 2000:
                    text = text[:2000] + "..."
                if chars_used + len(text) < remaining_budget * 0.5:
                    sections.append(f"\n--- 第{ch}章 (完整) ---\n{text}")
                    chars_used += len(text)
                    assembly.full_text_chapters.append(ch)

        # Layer 3: HIGH 章 — 摘要 + 关键片段
        for ch, _score, mem in highs[:5]:
            for snippet in mem.key_snippets[:3]:
                if chars_used + len(snippet) < remaining_budget:
                    sections.append(f"[第{ch}章] {snippet}")
                    chars_used += len(snippet)
                else:
                    break
            assembly.summary_chapters.append(ch)

        # Layer 4: MEDIUM 章 — 一句概括
        for ch, _score, mem in mediums[:8]:
            if chars_used + 200 < remaining_budget:
                first_snippet = mem.key_snippets[0] if mem.key_snippets else f"第{ch}章"
                sections.append(f"[第{ch}章·摘要] {first_snippet[:100]}")
                chars_used += min(len(first_snippet), 100)
                assembly.summary_chapters.append(ch)

        # Layer 5: LOW 章 — 丢弃
        for ch, _score, _mem in lows:
            assembly.dropped_chapters.append(ch)

        # 加入当前上下文提示
        if current_context_hints and chars_used + len(current_context_hints) < self.max_chars:
            sections.insert(0, f"[当前创作提示]\n{current_context_hints}")

        assembly.assembled_text = "\n\n".join(sections)
        assembly.total_chars = len(assembly.assembled_text)
        assembly.total_tokens_est = assembly.total_chars // 2  # 粗略估算: 2 chars ≈ 1 token
        assembly.budget_used_pct = round(chars_used / self.max_chars * 100, 1)

        assembly.stats = {
            "full_text_chapters": len(assembly.full_text_chapters),
            "summary_chapters": len(assembly.summary_chapters),
            "dropped_chapters": len(assembly.dropped_chapters),
            "critical_retained": len(criticals),
            "total_snippets": sum(len(m.key_snippets) for _, _, m in ranked[:10]),
        }

        return assembly

    def assemble_for_budget(
        self,
        target_chapter: int,
        memories: dict[int, ChapterMemory],
        _budget_type: ContextBudgetType = ContextBudgetType.CHARACTERS,
        budget_value: int = 8000,
        current_context_hints: str = "",
    ) -> ContextAssembly:
        """按指定预算组装"""
        saved_max = self.max_chars
        self.max_chars = budget_value
        result = self.assemble(target_chapter, memories, current_context_hints)
        self.max_chars = saved_max
        return result


# ══════════════════════════════════════════════════════
# Writer 上下文管理器 (主入口)
# ══════════════════════════════════════════════════════


class WriterContextManager:
    """Writer 上下文管理器 — ReIO 本地化实现

    用法:
        mgr = WriterContextManager(book_id="my_book")
        # 每章写完后注册
        mgr.register_chapter(chapter=5, text="...")
        # 写新章时获取压缩上下文
        ctx = mgr.build_context(target_chapter=6, current_hints="...")
        # ctx.assembled_text 可直接注入 Writer prompt
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.context_dir = settings.DATA_DIR / "writer_context" / book_id
        self.context_dir.mkdir(parents=True, exist_ok=True)

        self._memories: dict[int, ChapterMemory] = {}
        self._extractor = SnippetExtractor()
        self._assembler = ContextAssembler(max_chars=8000)
        self._load_memories()

    def _load_memories(self):
        """从磁盘加载已有章节记忆"""
        index_path = self.context_dir / "index.json"
        if not index_path.exists():
            return
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            for ch_str, mem_data in data.items():
                ch = int(ch_str)
                self._memories[ch] = ChapterMemory(
                    chapter=ch,
                    word_count=mem_data.get("word_count", 0),
                    key_snippets=mem_data.get("key_snippets", []),
                    summary=mem_data.get("summary", ""),
                    entities_mentioned=mem_data.get("entities_mentioned", []),
                    plot_threads=mem_data.get("plot_threads", []),
                    foreshadowing_planted=mem_data.get("foreshadowing_planted", []),
                    foreshadowing_resolved=mem_data.get("foreshadowing_resolved", []),
                    retention=RetentionPriority(mem_data.get("retention", "medium")),
                    surprise_score=mem_data.get("surprise_score", 0.0),
                    emotion_peak=mem_data.get("emotion_peak", False),
                )
        except Exception as e:
            logger.warning(f"加载 Writer 上下文失败: {e}")

    def _save_memories(self):
        """持久化章节记忆到磁盘"""
        data = {}
        for ch, mem in self._memories.items():
            data[str(ch)] = {
                "word_count": mem.word_count,
                "key_snippets": mem.key_snippets,
                "summary": mem.summary,
                "entities_mentioned": mem.entities_mentioned,
                "plot_threads": mem.plot_threads,
                "foreshadowing_planted": mem.foreshadowing_planted,
                "foreshadowing_resolved": mem.foreshadowing_resolved,
                "retention": mem.retention.value,
                "surprise_score": mem.surprise_score,
                "emotion_peak": mem.emotion_peak,
            }

        index_path = self.context_dir / "index.json"
        index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_chapter(
        self,
        chapter: int,
        text: str,
        entities: list[str] | None = None,
        plot_threads: list[str] | None = None,
        summary: str = "",
    ) -> ChapterMemory:
        """注册新章节到记忆系统"""
        memory = self._extractor.extract(text, chapter)

        if entities:
            memory.entities_mentioned = entities
        if plot_threads:
            memory.plot_threads = plot_threads
        if summary:
            memory.summary = summary

        self._memories[chapter] = memory
        self._save_memories()
        logger.debug(
            f"Writer 上下文: 注册第{chapter}章 "
            f"(字{memory.word_count}/优先级{memory.retention.value})"
        )
        return memory

    def build_context(
        self,
        target_chapter: int,
        current_hints: str = "",
        max_chars: int = 8000,
    ) -> ContextAssembly:
        """为指定目标章构建压缩上下文

        target_chapter: 即将要写的章节号
        current_hints: 当前创作提示 (来自 Architect/Editor)
        max_chars: 最大字符预算

        返回可直接注入 Writer prompt 的上下文
        """
        # 更新预算
        self._assembler.max_chars = max_chars

        # 组装
        assembly = self._assembler.assemble(
            target_chapter=target_chapter,
            memories=self._memories,
            current_context_hints=current_hints,
        )

        logger.info(
            f"Writer 上下文: ch{target_chapter} "
            f"完整章{assembly.stats['full_text_chapters']} "
            f"摘要章{assembly.stats['summary_chapters']} "
            f"丢弃章{assembly.stats['dropped_chapters']} "
            f"总{assembly.total_chars}字 ({assembly.budget_used_pct:.0f}%预算)"
        )

        return assembly

    def mark_chapters_expired(self, chapters: list[int]):
        """标记某些章节为过期 (情节已完全收束)"""
        for ch in chapters:
            if ch in self._memories:
                self._memories[ch].retention = RetentionPriority.EXPIRED
        self._save_memories()

    def get_memory(self, chapter: int) -> ChapterMemory | None:
        """获取单章记忆"""
        return self._memories.get(chapter)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total = len(self._memories)
        if total == 0:
            return {"total_chapters": 0}

        critical = sum(
            1 for m in self._memories.values() if m.retention == RetentionPriority.CRITICAL
        )
        high = sum(1 for m in self._memories.values() if m.retention == RetentionPriority.HIGH)
        medium = sum(1 for m in self._memories.values() if m.retention == RetentionPriority.MEDIUM)
        low = sum(1 for m in self._memories.values() if m.retention == RetentionPriority.LOW)
        expired = sum(
            1 for m in self._memories.values() if m.retention == RetentionPriority.EXPIRED
        )
        total_snippets = sum(len(m.key_snippets) for m in self._memories.values())
        total_foreshadowing = sum(len(m.foreshadowing_planted) for m in self._memories.values())

        return {
            "total_chapters": total,
            "by_priority": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
                "expired": expired,
            },
            "total_snippets": total_snippets,
            "total_foreshadowing_planted": total_foreshadowing,
            "avg_word_count": int(sum(m.word_count for m in self._memories.values()) / total)
            if total > 0
            else 0,
        }


# ══════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════


def _split_into_paragraphs(text: str, max_paragraphs: int = 20) -> list[str]:
    """将文本按段落分割"""
    lines = text.split("\n")
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
            if len(paragraphs) >= max_paragraphs:
                break

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def _extract_dialogues(text: str) -> list[str]:
    """提取对话块"""
    # 中文引号对话
    dialogues: list[str] = []
    pattern = r'"[^"]*"'
    current_block: list[str] = []
    last_end = 0

    for match in re.finditer(pattern, text):
        # 如果对话间距离小于 50 字，视为同一对话块
        if current_block and (match.start() - last_end) < 50:
            current_block.append(match.group())
        else:
            if current_block:
                dialogues.append(" ".join(current_block))
            current_block = [match.group()]
        last_end = match.end()

    if current_block:
        dialogues.append(" ".join(current_block))

    return dialogues


def _extract_named_entities(text: str, max_entities: int = 20) -> list[str]:
    """简单命名实体提取"""
    # 匹配 "XX说/道/问" 中的说话人 (通常为人名)
    speaker_pattern = re.compile(r"([\u4e00-\u9fff]{2,4})(?:说|道|问|答|讲|喊|叫|嚷|叹)")
    speakers = speaker_pattern.findall(text)

    # 计数并取高频
    counter = Counter(speakers)
    return [name for name, _ in counter.most_common(max_entities)]


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_managers: dict[str, WriterContextManager] = {}


def get_writer_context_manager(book_id: str) -> WriterContextManager:
    """获取 Writer 上下文管理器"""
    if book_id not in _managers:
        _managers[book_id] = WriterContextManager(book_id)
    return _managers[book_id]


__all__ = [
    "ChapterMemory",
    "ChapterRanker",
    "ContextAssembler",
    "ContextAssembly",
    "ContextBudgetType",
    "RetentionPriority",
    "SnippetExtractor",
    "WriterContextManager",
    "get_writer_context_manager",
]

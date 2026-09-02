"""
昆仑创作引擎 — 上下文 Token 预算分配器

灵感来源:
  - WenShape budget_allocator.py: 6段百分比分配
  - SAGA sliding window: 章节距离加权

核心机制:
  - 每章总 Token 预算按 6 段比例分配
  - 超出比例的内容通过距离衰减函数截断
  - 离当前章节越近的上下文权重越高

使用方式:
    allocator = ContextBudgetAllocator(total_budget=8000)
    context = allocator.assemble({
        "system_rules": system_text,
        "character_cards": cards_text,
        "chapter_summaries": summaries_text,
        "current_blueprint": blueprint_text,
        "current_draft": draft_text,
    })
"""

from __future__ import annotations

import math

# WenShape 6段预算分配比例（各项占总预算的百分比，总和=1.0）
DEFAULT_BUDGET_ALLOCATION = {
    "system_rules": 0.06,  # 系统规则
    "character_cards": 0.18,  # 角色/世界观卡片
    "dynamic_facts": 0.12,  # 动态事实（真相文件关键点）
    "chapter_summaries": 0.22,  # 历史章节摘要
    "current_blueprint": 0.12,  # 当前蓝图
    "output_reserve": 0.30,  # 输出预留（LLM 生成空间）
}


def log_distance_decay(chapter_distance: int) -> float:
    """对数型距离衰减 — 越近权重越高

    WenShape distance_decay.py 实现。
    距当前 1 章: 0.59, 10 章: 0.29, 50 章: 0.20

    作用: 遥远章节的事实仍然保留低权重（不会直接被丢弃），
    这对世界观一致性至关重要。
    """
    if chapter_distance <= 0:
        return 1.0
    return 1.0 / (1 + math.log(1 + chapter_distance))


def sliding_window_weight(chapter_number: int, current_chapter: int, _total_chapters: int) -> float:
    """滑动窗口加权 — SAGA: 最近的场景获得最大的上下文份额"""
    dist = abs(current_chapter - chapter_number)
    if dist <= 1:
        return 1.0
    if dist <= 5:
        return 0.8
    if dist <= 10:
        return 0.6
    if dist <= 20:
        return 0.4
    return log_distance_decay(dist)


class ContextBudgetAllocator:
    """
    上下文 Token 预算分配器

    用法:
        allocator = ContextBudgetAllocator(total_budget=8000)
        # 预算充足时：全量返回
        # 预算不足时：按距离衰减截断

    Args:
        total_budget: 总 Token 预算（包含输出预留）
        allocation: 自定义分配比例，不传则使用 DEFAULT_BUDGET_ALLOCATION
        current_chapter: 当前章节号（用于距离衰减）
    """

    def __init__(
        self,
        total_budget: int = 8000,
        allocation: dict[str, float] | None = None,
        current_chapter: int = 0,
    ):
        self.total_budget = total_budget
        self.allocation = allocation or DEFAULT_BUDGET_ALLOCATION
        self.current_chapter = current_chapter

        # 输出预留不用于输入上下文
        self._input_budget = total_budget * (1 - self.allocation.get("output_reserve", 0.2))
        self._reserve_budget = total_budget * self.allocation.get("output_reserve", 0.2)

    def get_segment_budget(self, segment_key: str) -> int:
        """获取某段落的 Token 预算"""
        ratio = self.allocation.get(segment_key, 0.05)
        return int(self._input_budget * ratio)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """更准确的 token 数量估算（中英文混合）

        基于经验规则：中文≈1.5 char/token, 英文≈4 char/token, 其他≈3 char/token
        """
        import re as _re

        chinese_chars = len(_re.findall(r"[一-鿿]", text))
        english_chars = len(_re.findall(r"[a-zA-Z]", text))
        other_chars = max(0, len(text) - chinese_chars - english_chars)
        return int(chinese_chars / 1.5 + english_chars / 4.0 + other_chars / 3.0)

    def truncate_to_budget(self, text: str, budget_tokens: int, chapter_distance: int = 0) -> str:
        """按预算截断文本，考虑距离衰减

        Args:
            text: 待截断文本
            budget_tokens: 该段的 Token 预算
            chapter_distance: 与当前章的章节距离（用于衰减）
        """
        if not text:
            return ""

        # 距离衰减：遥远章节的有效预算更少
        decay = log_distance_decay(chapter_distance)
        effective_budget = int(budget_tokens * decay)

        # 使用 token 估算判断是否需要截断
        if self.estimate_tokens(text) <= effective_budget:
            return text

        # 二分搜索找到合适的中文字符截断点
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.estimate_tokens(text[:mid]) <= effective_budget:
                lo = mid + 1
            else:
                hi = mid
        truncate_at = lo - 1

        # 在句子边界断开（同时支持中文和英文标点）
        truncated = text[:truncate_at]
        for punct in ["。", "！", "？", "\n", "…", ".", "!", "?"]:
            pos = truncated.rfind(punct)
            if pos > truncate_at * 0.5:
                return truncated[: pos + 1]
        return truncated + "\n[后续内容因Token预算截断...]"

    def assemble(
        self, segments: dict[str, str], chapter_distances: dict[str, int] | None = None
    ) -> dict[str, str]:
        """
        按预算装配上下文

        Args:
            segments: {段键名: 文本内容}
            chapter_distances: {段键名: 与当前章的章节距离}

        Returns:
            {段键名: 装配后的文本（适配预算）}
        """
        result = {}

        for key, text in segments.items():
            if not text:
                result[key] = ""
                continue

            budget = self.get_segment_budget(key)
            distance = (chapter_distances or {}).get(key, 0)
            truncated = self.truncate_to_budget(text, budget, distance)
            result[key] = truncated

        return result

    def get_summary(self, segments: dict[str, str], result: dict[str, str]) -> str:
        """返回预算分配概况"""
        lines = [
            f"总预算: {self.total_budget} tokens "
            f"(输入={int(self._input_budget)}, 输出预留={int(self._reserve_budget)})"
        ]
        for key in sorted(segments.keys()):
            original = len(segments.get(key, ""))
            final = len(result.get(key, ""))
            ratio = self.allocation.get(key, 0) * 100
            if original > 0:
                pct = final / original * 100
                lines.append(f"  {key}: {ratio:.0f}% → {final}字符 (原{original}, {pct:.0f}%)")
            else:
                lines.append(f"  {key}: {ratio:.0f}% → 0字符 (空)")
        return "\n".join(lines)


# 便捷函数
def create_context_budget(
    total_budget: int = 8000, current_chapter: int = 0, **segments
) -> dict[str, str]:
    """一键装配上下文"""
    allocator = ContextBudgetAllocator(total_budget=total_budget, current_chapter=current_chapter)
    return allocator.assemble(segments)

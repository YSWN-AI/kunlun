"""
昆仑创作引擎 — 定向修改引擎

设计来源: Morpheus 的 Modification Directions 机制

核心功能:
  1. 不重新生成全章，只修改用户指定的部分
  2. 支持多种修改类型：改情节/增描写/调节奏/改对话/修bug
  3. 修改后做局部一致性检查，不影响未修改部分

使用方式:
    modifier = ChapterModifier()
    result = await modifier.modify(draft, instruction="让主角更强势一些",
                                    focus_area="dialog", book_id="...")
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from loguru import logger

MODIFICATION_TYPES = {
    "plot": "修改情节走向",  # 改剧情
    "dialog": "优化对话",  # 改对话
    "description": "增删描写",  # 改描写
    "emotion": "调整情绪基调",  # 改情绪
    "pacing": "调整节奏",  # 改进奏
    "character": "调整角色表现",  # 改角色
    "fix": "修复问题",  # 修bug
    "style": "调整文风",  # 改风格
}


@dataclass
class ModificationResult:
    """定向修改结果"""

    success: bool
    modified_draft: str
    modifications: list[dict]  # 每处修改的位置和内容
    change_count: int
    warning: str = ""


class ChapterModifier:
    """
    章节定向修改器

    使用方式:
        modifier = ChapterModifier()
        # 指定段落修改
        result = await modifier.modify_paragraph(
            draft, "让这段对话更有张力",
            paragraph_index=3, book_id="...")
        # 全局风格修改
        result = await modifier.modify(
            draft, "增加环境描写",
            focus_area="description", book_id="...")
    """

    @staticmethod
    async def modify(
        draft: str, instruction: str, focus_area: str = "", _book_id: str = "", style_hint: str = ""
    ) -> ModificationResult:
        """
        对全文应用定向修改指令。

        Args:
            draft: 原稿
            instruction: 修改指令（自然语言，如"让主角更果断"）
            focus_area: 修改焦点（plot/dialog/description/emotion/pacing/character/fix/style）
            book_id: 作品ID
            style_hint: 风格提示

        Returns:
            ModificationResult
        """
        if not draft or len(draft) < 50:
            return ModificationResult(
                success=False,
                modified_draft=draft,
                modifications=[],
                change_count=0,
                warning="正文过短",
            )

        area_hint = MODIFICATION_TYPES.get(focus_area, "")
        area_guide = {
            "plot": "- 只修改情节相关的段落，不改变其他内容",
            "dialog": "- 只修改对话部分，不改叙事和描写",
            "description": "- 只修改环境/外貌/动作描写，不改对话和情节",
            "emotion": "- 只调整情绪基调（如从悲伤→希望），不改其他内容",
            "pacing": "- 调整段落节奏（合并短段落/拆分长段落），不改内容",
            "character": "- 只修改角色相关的言行表现，不改其他角色或情节",
            "fix": "- 修复逻辑矛盾/设定冲突，保持其他内容不变",
            "style": "- 调整文风（句式/用词/语气），保持内容不变",
        }.get(focus_area, "")

        prompt_parts = [
            "请对以下正文应用修改指令，保持其他部分不变。",
            "",
            f"修改指令: {instruction}",
        ]
        if area_hint:
            prompt_parts.append(f"修改焦点: {area_hint}")
        if area_guide:
            prompt_parts.append(area_guide)
        if style_hint:
            prompt_parts.append(f"\n风格参考:\n{style_hint[:300]}")
        prompt_parts.extend(
            [
                "",
                "要求:",
                "1. 只修改需要改的地方，不要重写全文",
                "2. 保持角色一致性和情节连贯性",
                "3. 保持段落结构基本不变",
                "4. 输出时用 **修改** 标注每处修改（便于对比）",
                "",
                "--- 正文 ---",
                "",
                draft,
            ]
        )

        from kunlun.gacha.engine import gacha_engine

        try:
            result = await gacha_engine.generate(
                "\n".join(prompt_parts), mode="single_fix", agent="writer"
            )
            modified = result.get("best_text", draft)

            # 检测修改位置
            changes = re.findall(r"\*\*修改[^:]*:\*\*|\[修改\]|【修改】", modified)
            change_count = len(changes)

            if change_count == 0 and modified.strip() == draft.strip():
                return ModificationResult(
                    success=True,
                    modified_draft=modified,
                    modifications=[],
                    change_count=0,
                    warning="未检测到实际修改（模型可能未能执行指令）",
                )

            logger.info(f"[Modifier] 定向修改完成: {change_count}处变更")
            return ModificationResult(
                success=True,
                modified_draft=modified,
                modifications=[{"type": "auto_detected", "count": change_count}],
                change_count=change_count,
            )
        except Exception as e:
            logger.warning(f"[Modifier] 定向修改失败: {e}")
            return ModificationResult(
                success=False,
                modified_draft=draft,
                modifications=[],
                change_count=0,
                warning=str(e),
            )

    @staticmethod
    async def modify_paragraph(
        draft: str, instruction: str, paragraph_index: int, _book_id: str = ""
    ) -> ModificationResult:
        """
        只修改指定段落的定向修改。

        Args:
            draft: 原稿
            instruction: 修改指令
            paragraph_index: 段落索引（从0开始）
            book_id: 作品ID

        Returns:
            ModificationResult
        """
        paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
        if paragraph_index < 0 or paragraph_index >= len(paragraphs):
            return ModificationResult(
                success=False,
                modified_draft=draft,
                modifications=[],
                change_count=0,
                warning=f"段落索引越界: {paragraph_index}/{len(paragraphs)}",
            )

        target = paragraphs[paragraph_index]
        context_before = "\n".join(paragraphs[:paragraph_index][-2:]) if paragraph_index > 0 else ""
        context_after = (
            "\n".join(paragraphs[paragraph_index + 1 :][:2])
            if paragraph_index < len(paragraphs) - 1
            else ""
        )

        prompt_parts = [
            "请修改以下段落，保持上下文衔接。",
            "",
            f"修改指令: {instruction}",
            "",
        ]
        if context_before:
            prompt_parts.append(f"上文:\n{context_before}\n")
        prompt_parts.append(f"待修改段落:\n{target}\n")
        if context_after:
            prompt_parts.append(f"下文:\n{context_after}\n")
        prompt_parts.append("要求: 只输出修改后的段落本身，不要带上下文。")

        from kunlun.gacha.engine import gacha_engine

        try:
            result = await gacha_engine.generate(
                "\n".join(prompt_parts), mode="single_fix", agent="writer"
            )
            modified_para = result.get("best_text", "").strip()
            if not modified_para or len(modified_para) < 10:
                return ModificationResult(
                    success=False,
                    modified_draft=draft,
                    modifications=[],
                    change_count=0,
                    warning="修改结果为空",
                )

            paragraphs[paragraph_index] = modified_para
            new_draft = "\n\n".join(paragraphs)

            return ModificationResult(
                success=True,
                modified_draft=new_draft,
                modifications=[
                    {
                        "paragraph": paragraph_index,
                        "before": target[:100],
                        "after": modified_para[:100],
                    }
                ],
                change_count=1,
            )
        except Exception as e:
            logger.warning(f"[Modifier] 段落修改失败: {e}")
            return ModificationResult(
                success=False,
                modified_draft=draft,
                modifications=[],
                change_count=0,
                warning=str(e),
            )


# 全局单例
chapter_modifier = ChapterModifier()

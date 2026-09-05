"""
昆仑创作引擎 — AI字数治理器 (LengthRevise)

设计来源: CogWriter (ACL 2025) 的 LengthRevise 函数

核心功能:
  1. 检测正文是否在目标字数范围内
  2. 字数不足时：AI扩写（添加细节/描写/对话）
  3. 字数超限时：AI压缩（精简冗余表达合并同类项）
  4. 双向保持情节完整和角色一致性

使用场景:
  - Pipeline中StyleEngineer后检查字数
  - 作者指定"每章2000字"约束
  - 批量生成时统一控制章节长度
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger


@dataclass
class LengthCheckResult:
    """字数检查结果"""

    word_count: int
    target: int
    min_acceptable: int
    max_acceptable: int
    in_range: bool
    deviation_pct: float  # 偏离百分比
    action_needed: str  # "none" / "expand" / "compress"


class LengthGovernor:
    """
    字数治理器

    使用方式:
        gov = LengthGovernor()
        check = gov.check(draft, target=2500)
        if check.action_needed == "expand":
            draft = await gov.expand(draft, target=2500, book_id="...")
        elif check.action_needed == "compress":
            draft = await gov.compress(draft, target=2500)
    """

    # 字数区间容差比例
    TOLERANCE = 0.15  # ±15%

    @staticmethod
    def check(draft: str, target: int = 2500) -> LengthCheckResult:
        """
        检查字数是否在目标范围内。

        Args:
            draft: 正文
            target: 目标字数

        Returns:
            LengthCheckResult
        """
        # 中文字数 = 中文字符数（不含标点空格）
        total_chars = len(draft.replace(" ", "").replace("\n", ""))

        min_ok = int(target * (1 - LengthGovernor.TOLERANCE))
        max_ok = int(target * (1 + LengthGovernor.TOLERANCE))

        deviation = (total_chars - target) / max(target, 1)

        if total_chars < min_ok:
            action = "expand"
        elif total_chars > max_ok:
            action = "compress"
        else:
            action = "none"

        return LengthCheckResult(
            word_count=total_chars,
            target=target,
            min_acceptable=min_ok,
            max_acceptable=max_ok,
            in_range=action == "none",
            deviation_pct=round(deviation * 100, 1),
            action_needed=action,
        )

    @staticmethod
    async def expand(draft: str, target: int = 2500, book_id: str = "") -> str:
        """
        AI扩写到目标字数。

        策略:
        - 增加环境/感官描写
        - 扩展对话
        - 添加角色心理活动
        - 补充细节动作

        Args:
            draft: 原稿
            target: 目标字数
            book_id: 作品ID（用于获取风格上下文）

        Returns:
            扩写后的正文
        """
        from kunlun.gacha.engine import gacha_engine

        current_len = len(draft.replace(" ", "").replace("\n", ""))
        needed = target - current_len

        if needed < 50:
            return draft  # 差距太小不处理

        style_hint = ""
        if book_id:
            try:
                from kunlun.filesync import get_syncer

                syncer = get_syncer(book_id)
                fp, loaded = syncer.get_style_context()
                if loaded and fp:
                    style_hint = f"\n保持以下风格:\n{fp[:500]}"
            except Exception:
                logger.debug("文风上下文加载失败，跳过风格提示")

        prompt = (
            f"请扩写以下正文，从当前的约{current_len}字扩展到约{target}字。\n\n"
            f"扩写指南:\n"
            f"1. 增加环境/感官描写（视觉、听觉、触觉）\n"
            f"2. 扩展对话（让角色多说话、增加反应）\n"
            f"3. 添加角色心理活动和内心独白\n"
            f"4. 补充动作细节（手势、表情、姿态）\n"
            f"5. 不要改变情节走向和角色设定\n"
            f"6. 不要添加新角色或新事件\n"
            f"7. 扩写后字数应在{target}字左右\n"
            f"{style_hint}\n\n"
            f"--- 正文 ---\n\n{draft}"
        )

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix", agent="writer")
            expanded = result.get("best_text", draft)

            # 验证扩写效果，如果没增加足够字数则退回原稿
            new_len = len(expanded.replace(" ", "").replace("\n", ""))
            if new_len <= current_len + 20:
                logger.info(f"[LengthGov] 扩写效果不足({new_len}→{current_len})，保留原稿")
                return draft

            logger.info(f"[LengthGov] 扩写完成: {current_len}→{new_len}字 (目标{target})")
            return expanded
        except Exception as e:
            logger.warning(f"[LengthGov] 扩写失败: {e}")
            return draft

    @staticmethod
    async def compress(draft: str, target: int = 2500) -> str:
        """
        AI压缩到目标字数。

        策略:
        - 合并同类描述
        - 精简冗余修饰词
        - 删除重复信息
        - 缩短过度描写

        Args:
            draft: 原稿
            target: 目标字数

        Returns:
            压缩后的正文
        """
        from kunlun.gacha.engine import gacha_engine

        current_len = len(draft.replace(" ", "").replace("\n", ""))
        excess = current_len - target

        if excess < 50:
            return draft

        prompt = (
            f"请压缩以下正文，从当前的约{current_len}字压缩到约{target}字。\n\n"
            f"压缩指南:\n"
            f"1. 合并同类描述（不要重复说同一件事）\n"
            f"2. 精简冗余修饰词（删除不必要的形容词/副词）\n"
            f"3. 删除重复信息（同一信息不要出现两次）\n"
            f"4. 缩短过长的环境/心理描写\n"
            f"5. 保持核心情节完整\n"
            f"6. 保持对话的流畅性\n"
            f"7. 压缩后字数应在{target}字左右\n\n"
            f"--- 正文 ---\n\n{draft}"
        )

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix", agent="writer")
            compressed = result.get("best_text", draft)

            new_len = len(compressed.replace(" ", "").replace("\n", ""))
            if new_len >= current_len - 10:
                logger.info(f"[LengthGov] 压缩效果不足({current_len}→{new_len})，保留原稿")
                return draft

            logger.info(f"[LengthGov] 压缩完成: {current_len}→{new_len}字 (目标{target})")
            return compressed
        except Exception as e:
            logger.warning(f"[LengthGov] 压缩失败: {e}")
            return draft

    @staticmethod
    def build_prompt_hint(target: int = 2500) -> str:
        """生成字数提示，注入Writer prompt"""
        min_ok = int(target * (1 - LengthGovernor.TOLERANCE))
        max_ok = int(target * (1 + LengthGovernor.TOLERANCE))
        return (
            f"【字数约束】\n"
            f"目标字数: {target}字\n"
            f"允许范围: {min_ok}-{max_ok}字\n"
            f"超出或不足将触发AI自动修订"
        )


# 全局单例
length_governor = LengthGovernor()

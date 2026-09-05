"""
短篇生成引擎 — 短文/短篇故事/开头生成

支持模式:
  - short_story: 3000-10000字短篇故事
  - opening_hook: 500-1500字黄金开篇
  - flash_fiction: 500-2000字微小说
  - essay: 1000-3000字随笔/评论
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from loguru import logger

SHORTFORM_TEMPLATES = {
    "short_story": {
        "word_count": (3000, 10000),
        "structure": ["hook", "buildup", "climax", "resolution"],
        "scene_count": (3, 6),
    },
    "opening_hook": {
        "word_count": (500, 1500),
        "structure": ["hook", "setup", "cliffhanger"],
        "scene_count": (1, 2),
    },
    "flash_fiction": {
        "word_count": (500, 2000),
        "structure": ["hook", "twist"],
        "scene_count": (1, 1),
    },
    "essay": {
        "word_count": (1000, 3000),
        "structure": ["thesis", "argument", "conclusion"],
        "scene_count": (1, 3),
    },
}


@dataclass
class ShortformResult:
    success: bool
    text: str
    word_count: int
    mode: str
    model_used: str
    generation_time: float


class ShortformEngine:
    """短篇生成引擎"""

    async def generate(
        self,
        prompt: str,
        mode: str = "short_story",
        style: str = "网文风格",
        extra_context: str = "",
    ) -> ShortformResult:
        """生成短篇内容（真实LLM调用）"""
        import time

        from kunlun.gacha.engine import gacha_engine

        template = SHORTFORM_TEMPLATES.get(mode, SHORTFORM_TEMPLATES["short_story"])
        wmin, wmax = template["word_count"]
        structure = " → ".join(str(s) for s in template["structure"])

        system_prompt = f"""你是专业短篇写手。请根据以下要求创作{mode}。

要求:
- 字数: {wmin}-{wmax}字
- 结构: {structure}
- 风格: {style}
- 直接输出正文，不要标题和注释
{extra_context}

用户输入: {prompt}"""

        t0 = time.time()
        try:
            result = await gacha_engine.generate(system_prompt, mode="single_fix")
            text = result.get("best_text", "")
            return ShortformResult(
                success=bool(text and len(text) > 50),
                text=text,
                word_count=len(text),
                mode=mode,
                model_used=result.get("model_used", "deepseek-chat"),
                generation_time=time.time() - t0,
            )
        except Exception as e:
            logger.error(f"[Shortform] 生成失败: {e}")
            return ShortformResult(False, "", 0, mode, "", time.time() - t0)

    async def generate_opening_variations(self, core_idea: str, count: int = 3) -> list[str]:
        """为一个故事核心生成多个开篇变体，供作者选择"""
        from kunlun.gacha.engine import gacha_engine

        prompt = f"""为以下故事核心生成{count}个不同的开篇方式。每个开篇100-200字，标注序号。

故事核心: {core_idea}

要求:
- 每个开篇从不同角度切入（动作开场/对话开场/描写开场/悬念开场/倒叙开场）
- 标注每个开篇的类型和适合的读者群体"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            text = result.get("best_text", "")
            # 解析变体
            variations = [v.strip() for v in text.split("\n\n") if v.strip() and len(v) > 30]
            return variations[:count]
        except Exception as e:
            logger.error(f"[Shortform] 开篇变体生成失败: {e}")
            return []


# 全局单例
shortform_engine = ShortformEngine()

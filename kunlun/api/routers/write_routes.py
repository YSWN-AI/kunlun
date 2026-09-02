"""
昆仑创作引擎 — 创作辅助路由 (v2)
/next-outline: AI 情节推演，生成多个后续剧情选项

参考 Maliang 的 Next Outline 功能。
"""

import json

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/write", tags=["创作"])


class NextOutlineRequest(BaseModel):
    book_id: str = Field(..., description="书籍ID")
    chapter: int = Field(..., description="当前章节号")
    count: int = Field(default=3, description="生成选项数")


@router.post("/next-outline", summary="AI 情节推演 — 生成多个后续剧情选项")
async def next_outline(req: NextOutlineRequest) -> dict:
    """
    参考 Maliang 的 Next Outline 功能：AI 基于当前章节生成 N 个后续剧情发展方向。
    用户选择一个方向后，可在此基础上继续创作。
    """
    try:
        gacha_engine = cached_import("kunlun.gacha.engine", "gacha_engine")
        snapshot_manager = cached_import("kunlun.kg.snapshot", "snapshot_manager")

        # 获取当前状态
        snap = snapshot_manager.get_latest(req.book_id)
        current_ch = snap.chapter if snap else 0

        # 构建 prompt
        prompt = f"""你是专业网文编辑。基于当前进度（第{current_ch}章），\
请推演接下来第{req.chapter}章的 {req.count} 种可能的剧情发展方向。

要求：
- 每个方向 2-3 句话描述核心情节
- 标注每个方向的【基调】（热血/温情/悬疑/暗黑/幽默/虐心）
- 标注每个方向的【走向】（升级/感情线/揭秘/冲突/转折/伏笔回收）
- {req.count} 个方向要有明显差异，覆盖不同可能性

请用 JSON 格式输出：
{{"options": [{{"summary": "...", "tone": "...", "direction": "..."}}]}}
"""
        result = await gacha_engine.chat(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek-chat",
            temperature=0.85,
            max_tokens=1500,
        )

        # 解析 JSON
        content = result.get("content", "{}")
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        parsed = json.loads(content.strip())
        return {
            "success": True,
            "data": {
                "options": parsed.get("options", []),
                "chapter": req.chapter,
            },
        }
    except json.JSONDecodeError:
        # Fallback: return demo options
        return {
            "success": True,
            "data": {
                "options": [
                    {
                        "summary": "主角发现隐藏线索，深入调查...",
                        "tone": "悬疑",
                        "direction": "揭秘",
                    },
                    {
                        "summary": "反派主动出击，主角被迫应战...",
                        "tone": "热血",
                        "direction": "冲突",
                    },
                    {
                        "summary": "感情线发展，角色关系产生微妙变化...",
                        "tone": "温情",
                        "direction": "感情线",
                    },
                ],
                "chapter": req.chapter,
                "fallback": True,
            },
        }
    except Exception as e:
        logger.error(f"Next Outline 生成失败: {e}")
        raise

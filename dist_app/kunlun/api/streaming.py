"""
流式输出 — SSE实时推送生成文本到前端

用法:
  GET /api/v1/stream/generate?book_id=xxx&chapter=1&prompt=写一章...
  → SSE events: start → progress → chunk (逐token) → audit → done/error

v2.0: 支持真正的 LLM stream=True 逐 token 推送，
不再等待完整生成后才分块。
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator

from loguru import logger


class StreamingGenerator:
    """流式生成器 — 包装GachaEngine，逐 token 实时推送"""

    def __init__(self):
        self._active_streams: dict[str, asyncio.Queue] = {}

    async def stream_generate(
        self,
        book_id: str,
        chapter: int,
        prompt: str,
        mode: str = "single_fix",
        agent: str = "writer",
    ) -> AsyncGenerator[str, None]:
        """流式生成章节，yield SSE 事件。

        优先使用真正的 LLM stream=True 逐 token 推送；
        当 gacha_cascade 等多模型模式时，回退到非流式后分块推送。
        """
        stream_id = f"{book_id}_ch{chapter}_{int(time.time())}"
        yield self._sse_event("start", {"stream_id": stream_id, "chapter": chapter})

        from kunlun.gacha.engine import gacha_engine

        try:
            full_text = ""

            # 判断是否支持真实流式：只有 single_fix / single_chat 模式可以流式
            _stream_modes = ("single_fix", "single_chat")
            if mode in _stream_modes:
                yield self._sse_event(
                    "progress", {"step": "generating", "message": "AI 正在逐字创作..."}
                )

                # 真实流式：逐 token 从 LLM 推送
                messages = [{"role": "user", "content": prompt}]
                async for chunk in gacha_engine.chat_stream(
                    messages=messages,
                    model="",
                    temperature=0.8,
                    max_tokens=4096,
                    agent=agent,
                ):
                    if chunk["type"] == "chunk":
                        full_text += chunk["content"]
                        yield self._sse_event(
                            "chunk", {"text": chunk["content"], "streaming": True}
                        )
                    elif chunk["type"] == "done":
                        logger.info(f"[Stream] 流式生成完成: {len(full_text)} 字")
                    elif chunk["type"] == "error":
                        yield self._sse_event("error", {"error": chunk["error"]})
                        return
            else:
                # 多模型抽卡模式：回退到非流式（需要等待所有模型返回后评分选最优）
                yield self._sse_event("progress", {"step": "gacha", "message": "多模型抽卡中..."})
                result = await gacha_engine.generate(prompt, mode)
                full_text = result.get("best_text", "")

                if full_text:
                    # 分块快速推送（抽卡模式下无法实时流式，但尽快推送）
                    chunks = self._split_into_chunks(full_text, chunk_size=200)
                    for i, chunk_text in enumerate(chunks):
                        yield self._sse_event(
                            "chunk",
                            {"text": chunk_text, "index": i, "total": len(chunks)},
                        )
                        if len(chunks) > 10:
                            await asyncio.sleep(0.01)

            # 生成后审计
            if full_text:
                yield self._sse_event("progress", {"step": "audit", "message": "33维审计中..."})

                from kunlun.audit.audit33 import auditor33

                report = await asyncio.to_thread(
                    auditor33.run_audit, full_text, chapter, {}, book_id
                )

                yield self._sse_event(
                    "done",
                    {
                        "stream_id": stream_id,
                        "word_count": len(full_text),
                        "audit_passed": report.passed,
                        "audit_score": report.overall_score,
                        "ai_score": report.ai_detection_score,
                        "full_text": full_text,
                    },
                )
            else:
                yield self._sse_event("done", {"stream_id": stream_id, "word_count": 0})

        except Exception as e:
            logger.error(f"[Stream] 生成失败: {e}")
            yield self._sse_event("error", {"error": str(e)})

    @staticmethod
    def _split_into_chunks(text: str, chunk_size: int = 50) -> list[str]:
        """将文本按合理断点切分为 chunks（兜底逻辑）"""
        chunks = []
        i = 0
        while i < len(text):
            end = min(i + chunk_size, len(text))
            if end < len(text):
                for punct in ["。", "！", "？", "\n", "，", "、"]:
                    pos = text.rfind(punct, i, end)
                    if pos > i + chunk_size // 2:
                        end = pos + 1
                        break
            chunks.append(text[i:end])
            i = end
        return chunks

    @staticmethod
    def _sse_event(event: str, data: dict) -> str:
        """格式化为 SSE 事件"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# 全局单例
streaming_generator = StreamingGenerator()

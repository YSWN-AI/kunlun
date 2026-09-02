"""
昆仑创作引擎 — 语音合成模块 (TTS)

支持多引擎语音合成，可将章节转换为有声书。
引擎: Edge TTS (免费), Piper (本地), Fish Audio (中文优化)

用法:
    from kunlun.tts import TTSEngine, get_tts_engine

    engine = get_tts_engine()
    await engine.synthesize("第一章内容...", output_path="chapter1.mp3")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TTSEngineType(StrEnum):
    """TTS 引擎类型"""

    EDGE = "edge"  # Microsoft Edge TTS (免费)
    PIPER = "piper"  # Piper TTS (本地)
    FISH = "fish"  # Fish Audio (中文优化)
    COQUI = "coqui"  # Coqui TTS (自托管)
    BARK = "bark"  # Bark (Suno AI)


class TTSError(Exception):
    """TTS 引擎错误"""


@dataclass
class TTSVoice:
    """语音配置"""

    name: str
    locale: str = "zh-CN"
    gender: str = "Female"
    engine: TTSEngineType = TTSEngineType.EDGE


@dataclass
class TTSResult:
    """TTS 合成结果"""

    output_path: Path
    duration_seconds: float = 0.0
    character_count: int = 0
    engine: TTSEngineType = TTSEngineType.EDGE


@dataclass
class TTSSegment:
    """TTS 分段（用于多角色配音）"""

    text: str
    voice: TTSVoice | None = None
    pause_before: float = 0.0  # 前置停顿（秒）
    pause_after: float = 0.0  # 后置停顿（秒）
    speed: float = 1.0  # 语速倍率


@dataclass
class TTSConfig:
    """TTS 全局配置"""

    engine: TTSEngineType = TTSEngineType.EDGE
    default_voice: TTSVoice = field(
        default_factory=lambda: TTSVoice(
            name="zh-CN-XiaoxiaoNeural",
            locale="zh-CN",
            gender="Female",
        )
    )
    narrator_voice: TTSVoice = field(
        default_factory=lambda: TTSVoice(
            name="zh-CN-YunxiNeural",
            locale="zh-CN",
            gender="Male",
        )
    )
    output_dir: str = "data/tts"
    speech_rate: float = 1.0  # 全局语速
    volume: float = 1.0  # 全局音量
    split_by_paragraph: bool = True
    max_chunk_chars: int = 2000


@dataclass
class BookAudiobook:
    """有声书配置"""

    book_id: str
    title: str
    chapters: list[dict[str, Any]] = field(default_factory=list)
    narrator_voice: TTSVoice | None = None
    output_format: str = "mp3"  # mp3, wav, ogg
    include_cover: bool = True
    metadata: dict[str, str] = field(default_factory=dict)


class TTSEngine:
    """TTS 引擎 — 多引擎语音合成统一入口

    用法:
        engine = TTSEngine()
        result = await engine.synthesize(
            text="第一章...",
            output_path="chapter1.mp3",
        )
    """

    def __init__(self, config: TTSConfig | None = None):
        self.config = config or TTSConfig()
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        self.api_key = os.environ.get("TTS_API_KEY", "")
        self.api_base = os.environ.get("TTS_API_BASE", "https://api.fish.audio")
        self._available = bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        """返回 API 认证头"""
        return {"Authorization": f"Bearer {self.api_key}"}

    async def synthesize(
        self,
        text: str,
        output_path: str | Path | None = None,
        voice: TTSVoice | None = None,
        engine: TTSEngineType | None = None,
    ) -> TTSResult:
        """合成单段文本为语音"""
        engine = engine or self.config.engine
        voice = voice or self.config.default_voice

        output = Path(output_path) if output_path else Path(self.config.output_dir) / "output.mp3"

        try:
            if engine == TTSEngineType.EDGE:
                return await self._synthesize_edge(text, output, voice)
            if engine == TTSEngineType.PIPER:
                return await self._synthesize_piper(text, output, voice)
            if engine == TTSEngineType.FISH:
                return await self._synthesize_fish(text, output, voice)
            raise TTSError(f"Unsupported TTS engine: {engine}")
        except Exception as e:
            logger.exception("TTS synthesis failed: %s", e)
            raise TTSError(f"TTS synthesis failed: {e}") from e

    async def synthesize_segments(
        self,
        segments: list[TTSSegment],
        output_path: str | Path,
    ) -> TTSResult:
        """合成多角色分段语音（对话配音）

        支持不同角色使用不同语音，段落间插入停顿。
        """
        import tempfile

        output = Path(output_path)
        temp_dir = Path(tempfile.mkdtemp())
        temp_files: list[Path] = []

        try:
            for i, seg in enumerate(segments):
                seg_path = temp_dir / f"seg_{i:04d}.mp3"
                voice = seg.voice or self.config.narrator_voice
                await self._synthesize_edge(seg.text, seg_path, voice)
                temp_files.append(seg_path)

            # 合并音频文件
            await self._merge_audio(temp_files, output, segments)

            # 清理临时文件
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

            return TTSResult(
                output_path=output,
                character_count=sum(len(s.text) for s in segments),
                engine=self.config.engine,
            )
        except Exception as e:
            logger.exception("Segment synthesis failed: %s", e)
            raise TTSError(f"Segment synthesis failed: {e}") from e

    async def generate_audiobook(
        self,
        audiobook: BookAudiobook,
    ) -> list[TTSResult]:
        """生成整本有声书

        按章节顺序合成，每个章节一个文件，可选生成封面音频。
        """
        results: list[TTSResult] = []
        book_dir = Path(self.config.output_dir) / audiobook.book_id
        book_dir.mkdir(parents=True, exist_ok=True)

        for i, chapter in enumerate(audiobook.chapters):
            output_path = book_dir / f"chapter_{i + 1:04d}.{audiobook.output_format}"
            result = await self.synthesize(
                text=chapter.get("content", ""),
                output_path=output_path,
                voice=audiobook.narrator_voice,
            )
            results.append(result)
            logger.info(
                "[TTS] Chapter %d/%d: %s (%.1fs)",
                i + 1,
                len(audiobook.chapters),
                output_path.name,
                result.duration_seconds,
            )

        return results

    async def list_voices(self, engine: TTSEngineType | None = None) -> list[TTSVoice]:
        """列出可用的语音"""
        engine = engine or self.config.engine
        if engine == TTSEngineType.EDGE:
            return await self._list_edge_voices()
        return []

    # ── Edge TTS 实现 ──────────────────────────────

    async def _synthesize_edge(
        self,
        text: str,
        output: Path,
        voice: TTSVoice,
    ) -> TTSResult:
        try:
            import edge_tts
        except ImportError:
            raise TTSError("edge-tts not installed. Run: pip install edge-tts") from None

        communicate = edge_tts.Communicate(text, voice.name)
        await communicate.save(str(output))

        return TTSResult(
            output_path=output,
            character_count=len(text),
            engine=TTSEngineType.EDGE,
        )

    async def _list_edge_voices(self) -> list[TTSVoice]:
        try:
            import edge_tts
        except ImportError:
            return []

        voices = await edge_tts.VoicesManager.create()
        return [
            TTSVoice(
                name=v["ShortName"],
                locale=v.get("Locale", "zh-CN"),
                gender=v.get("Gender", "Female"),
            )
            for v in voices.voices
            if v["Locale"].startswith("zh")
        ]

    # ── Piper TTS 实现 ──────────────────────────────

    async def _synthesize_piper(
        self,
        text: str,
        output: Path,
        voice: TTSVoice,
    ) -> TTSResult:
        try:
            import subprocess
        except ImportError:
            raise TTSError("subprocess not available") from None

        # Piper 使用命令行调用
        model_path = Path(f"data/piper_models/{voice.name}.onnx")
        if not model_path.exists():
            raise TTSError(f"Piper model not found: {model_path}")

        result = subprocess.run(
            [
                "piper",
                "--model",
                str(model_path),
                "--output_file",
                str(output),
            ],
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise TTSError(f"Piper synthesis failed: {result.stderr}")

        return TTSResult(
            output_path=output,
            character_count=len(text),
            engine=TTSEngineType.PIPER,
        )

    # ── Fish Audio 实现 ─────────────────────────────

    async def _synthesize_fish(
        self,
        text: str,
        output: Path,
        voice: TTSVoice,
    ) -> TTSResult:
        try:
            import httpx
        except ImportError:
            raise TTSError("httpx not installed. Run: pip install httpx") from None

        # Resolve API key: env var first, then settings
        if not self.api_key:
            from kunlun.config import settings

            self.api_key = getattr(settings, "fish_audio_api_key", "")

        if not self.api_key:
            raise TTSError(
                "Fish Audio API key not configured. "
                "Set TTS_API_KEY environment variable or configure fish_audio_api_key in settings."
            )

        api_base = self.api_base or "https://api.fish.audio"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{api_base}/v1/tts",
                json={
                    "text": text,
                    "voice": voice.name,
                    "format": "mp3",
                },
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise TTSError(f"Fish Audio API error: {resp.text}")

            output.write_bytes(resp.content)

        return TTSResult(
            output_path=output,
            character_count=len(text),
            engine=TTSEngineType.FISH,
        )

    # ── 音频合并 ───────────────────────────────────

    async def _merge_audio(
        self,
        temp_files: list[Path],
        output: Path,
        segments: list[TTSSegment],
    ) -> None:
        """合并多个音频片段

        使用 pydub 或 ffmpeg 进行合并，支持段落间静音插入。
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            # 回退到直接拼接文件
            with output.open("wb") as out:
                for f in temp_files:
                    if f.exists():
                        out.write(f.read_bytes())
            return

        combined = AudioSegment.empty()
        for _i, (seg, seg_path) in enumerate(zip(segments, temp_files, strict=False)):
            if not seg_path.exists():
                continue

            # 前置静音
            if seg.pause_before > 0:
                combined += AudioSegment.silent(duration=int(seg.pause_before * 1000))

            audio = AudioSegment.from_file(seg_path)
            if seg.speed != 1.0:
                audio = audio.speedup(playback_speed=seg.speed)

            combined += audio

            # 后置静音
            if seg.pause_after > 0:
                combined += AudioSegment.silent(duration=int(seg.pause_after * 1000))

        combined.export(output, format=output.suffix.lstrip("."))


# ── 全局单例 ───────────────────────────────────────

_tts_engine: TTSEngine | None = None


def get_tts_engine(config: TTSConfig | None = None) -> TTSEngine:
    """获取全局 TTS 引擎实例"""
    global _tts_engine  # noqa: PLW0603
    if _tts_engine is None:
        _tts_engine = TTSEngine(config)
    return _tts_engine

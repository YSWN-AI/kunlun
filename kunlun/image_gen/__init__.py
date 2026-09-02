"""
昆仑创作引擎 — AI图像生成模块

支持封面生成、角色立绘、场景插图。
引擎: Stable Diffusion (ComfyUI API), Fooocus, DALL-E

用法:
    from kunlun.image_gen import ImageGenEngine, get_image_gen

    engine = get_image_gen()
    cover = await engine.generate_cover(
        book_title="星辰大海",
        genre="科幻",
        style="写实",
    )
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ImageEngine(StrEnum):
    """图像生成引擎"""

    COMPFY = "comfy"  # ComfyUI (本地/自托管)
    FOOOCUS = "foocus"  # Fooocus (本地)
    SD_WEBUI = "sd_webui"  # Stable Diffusion WebUI
    OPENAI = "openai"  # DALL-E (OpenAI)
    SEEDREAM = "seedream"  # 字节 Seedream


class ImageStyle(StrEnum):
    """图像风格"""

    REALISTIC = "realistic"  # 写实
    ANIME = "anime"  # 动漫
    INK_WASH = "ink_wash"  # 水墨
    FANTASY = "fantasy"  # 奇幻
    SCI_FI = "sci_fi"  # 科幻
    HISTORICAL = "historical"  # 古风
    MODERN = "modern"  # 现代
    MINIMALIST = "minimalist"  # 极简


class ImageType(StrEnum):
    """图像类型"""

    COVER = "cover"  # 封面
    CHARACTER_PORTRAIT = "character_portrait"  # 角色立绘
    SCENE_ILLUSTRATION = "scene_illustration"  # 场景插图
    CHAPTER_HEADER = "chapter_header"  # 章节头图
    PROMOTIONAL = "promotional"  # 宣传图


@dataclass
class ImageGenConfig:
    """图像生成配置"""

    engine: ImageEngine = ImageEngine.COMPFY
    comfy_url: str = "http://localhost:8188"
    sd_webui_url: str = "http://localhost:7860"
    output_dir: str = "data/images"
    default_style: ImageStyle = ImageStyle.REALISTIC
    default_width: int = 768
    default_height: int = 1024
    default_steps: int = 20
    default_cfg_scale: float = 7.0
    negative_prompt: str = "low quality, blurry, distorted, ugly"


@dataclass
class ImageGenRequest:
    """图像生成请求"""

    image_type: ImageType
    prompt: str
    negative_prompt: str = ""
    style: ImageStyle = ImageStyle.REALISTIC
    width: int = 768
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1
    reference_image: str | None = None  # 参考图路径（图生图）


@dataclass
class ImageGenResult:
    """图像生成结果"""

    image_path: Path
    image_type: ImageType
    prompt: str
    engine: ImageEngine
    generation_time: float = 0.0


@dataclass
class CoverRequest:
    """封面生成请求"""

    book_title: str
    author: str = ""
    genre: str = ""
    style: ImageStyle = ImageStyle.REALISTIC
    description: str = ""
    include_title_text: bool = True


@dataclass
class CharacterPortraitRequest:
    """角色立绘生成请求"""

    character_name: str
    appearance: str = ""  # 外貌描述
    clothing: str = ""  # 服装描述
    pose: str = ""  # 姿势描述
    style: ImageStyle = ImageStyle.REALISTIC
    expression: str = ""  # 表情描述
    background: str = ""  # 背景描述


@dataclass
class SceneRequest:
    """场景插图生成请求"""

    scene_description: str
    style: ImageStyle = ImageStyle.REALISTIC
    mood: str = ""  # 氛围
    time_of_day: str = ""  # 时间
    key_elements: list[str] = field(default_factory=list)


class ImageGenEngine:
    """AI图像生成引擎

    用法:
        engine = ImageGenEngine()
        result = await engine.generate_cover(
            CoverRequest(book_title="星辰大海", genre="科幻")
        )
    """

    def __init__(self, config: ImageGenConfig | None = None):
        self.config = config or ImageGenConfig()
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        self.api_key = os.environ.get("IMAGE_GEN_API_KEY", "")
        self.api_base = os.environ.get("IMAGE_GEN_API_BASE", "https://api.openai.com")
        self._available = bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        """返回 API 认证头"""
        return {"Authorization": f"Bearer {self.api_key}"}

    async def generate_cover(self, request: CoverRequest) -> ImageGenResult:
        """生成书籍封面"""
        prompt = self._build_cover_prompt(request)
        return await self._generate(
            ImageGenRequest(
                image_type=ImageType.COVER,
                prompt=prompt,
                style=request.style,
                width=768,
                height=1024,
            )
        )

    async def generate_character_portrait(
        self,
        request: CharacterPortraitRequest,
    ) -> ImageGenResult:
        """生成角色立绘"""
        prompt = self._build_character_prompt(request)
        return await self._generate(
            ImageGenRequest(
                image_type=ImageType.CHARACTER_PORTRAIT,
                prompt=prompt,
                style=request.style,
                width=512,
                height=768,
            )
        )

    async def generate_scene(
        self,
        request: SceneRequest,
    ) -> ImageGenResult:
        """生成场景插图"""
        prompt = self._build_scene_prompt(request)
        return await self._generate(
            ImageGenRequest(
                image_type=ImageType.SCENE_ILLUSTRATION,
                prompt=prompt,
                style=request.style,
                width=1024,
                height=576,
            )
        )

    async def generate_chapter_header(
        self,
        chapter_title: str,
        style: ImageStyle = ImageStyle.REALISTIC,
    ) -> ImageGenResult:
        """生成章节头图"""
        prompt = (
            f"Beautiful decorative header illustration for chapter "
            f"'{chapter_title}', {style.value} style, elegant, book aesthetic"
        )
        return await self._generate(
            ImageGenRequest(
                image_type=ImageType.CHAPTER_HEADER,
                prompt=prompt,
                style=style,
                width=1024,
                height=256,
            )
        )

    # ── 提示词构建 ─────────────────────────────────

    def _build_cover_prompt(self, req: CoverRequest) -> str:
        parts = [
            f"Professional book cover design for '{req.book_title}'",
            f"{req.genre} novel" if req.genre else "",
            f"{req.style.value} style",
            "high quality, detailed, professional typography",
            req.description,
        ]
        return ", ".join(p for p in parts if p)

    def _build_character_prompt(self, req: CharacterPortraitRequest) -> str:
        parts = [
            f"Character portrait of {req.character_name}",
            req.appearance,
            req.clothing,
            req.pose,
            req.expression,
            req.background,
            f"{req.style.value} style",
            "high quality, detailed, professional illustration",
        ]
        return ", ".join(p for p in parts if p)

    def _build_scene_prompt(self, req: SceneRequest) -> str:
        parts = [
            req.scene_description,
            req.mood,
            req.time_of_day,
            f"{req.style.value} style",
            "high quality, detailed, cinematic lighting",
            ", ".join(req.key_elements) if req.key_elements else "",
        ]
        return ", ".join(p for p in parts if p)

    # ── 核心生成逻辑 ────────────────────────────────

    async def _generate(self, request: ImageGenRequest) -> ImageGenResult:
        import time

        start = time.time()

        output_dir = Path(self.config.output_dir) / request.image_type.value
        output_dir.mkdir(parents=True, exist_ok=True)

        if request.negative_prompt == "":
            request.negative_prompt = self.config.negative_prompt

        try:
            if self.config.engine == ImageEngine.COMPFY:
                output_path = await self._generate_comfy(request, output_dir)
            elif self.config.engine == ImageEngine.FOOOCUS:
                output_path = await self._generate_foocus(request, output_dir)
            elif self.config.engine == ImageEngine.SD_WEBUI:
                output_path = await self._generate_sd_webui(request, output_dir)
            elif self.config.engine == ImageEngine.OPENAI:
                output_path = await self._generate_openai(request, output_dir)
            else:
                output_path = await self._generate_comfy(request, output_dir)
        except Exception as e:
            logger.exception("Image generation failed: %s", e)
            raise

        elapsed = time.time() - start
        logger.info(
            "[ImageGen] %s generated in %.1fs: %s",
            request.image_type.value,
            elapsed,
            output_path,
        )

        return ImageGenResult(
            image_path=output_path,
            image_type=request.image_type,
            prompt=request.prompt,
            engine=self.config.engine,
            generation_time=elapsed,
        )

    # ── ComfyUI 实现 ────────────────────────────────

    async def _generate_comfy(
        self,
        request: ImageGenRequest,
        output_dir: Path,
    ) -> Path:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx not installed") from None

        workflow = self._build_comfy_workflow(request)
        output_path = output_dir / f"comfy_{request.seed or 'random'}.png"

        async with httpx.AsyncClient(timeout=120) as client:
            # 提交工作流
            resp = await client.post(
                f"{self.config.comfy_url}/prompt",
                json={"prompt": workflow},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"ComfyUI error: {resp.text}")

            prompt_id = resp.json()["prompt_id"]

            # 轮询等待完成
            import asyncio

            for _ in range(60):
                await asyncio.sleep(1)
                history_resp = await client.get(f"{self.config.comfy_url}/history/{prompt_id}")
                history = history_resp.json()
                if prompt_id in history:
                    # 获取输出图片
                    outputs = history[prompt_id]["outputs"]
                    for node_output in outputs.values():
                        for img in node_output.get("images", []):
                            img_resp = await client.get(
                                f"{self.config.comfy_url}/view",
                                params={
                                    "filename": img["filename"],
                                    "subfolder": img.get("subfolder", ""),
                                },
                            )
                            output_path.write_bytes(img_resp.content)
                            return output_path

        raise RuntimeError("ComfyUI generation timed out")

    def _build_comfy_workflow(self, request: ImageGenRequest) -> dict:
        """构建 ComfyUI 工作流"""
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": request.seed if request.seed >= 0 else 42,
                    "steps": request.steps,
                    "cfg": request.cfg_scale,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": request.width,
                    "height": request.height,
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": (f"{request.prompt}, masterpiece, best quality, {request.style.value}"),
                    "clip": ["4", 1],
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": request.negative_prompt,
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "kunlun",
                    "images": ["8", 0],
                },
            },
        }

    # ── Fooocus 实现 ────────────────────────────────

    async def _generate_foocus(
        self,
        request: ImageGenRequest,
        output_dir: Path,
    ) -> Path:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx not installed") from None

        output_path = output_dir / f"foocus_{request.seed or 'random'}.png"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "http://localhost:7865/v1/generation",
                json={
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "style_selections": [request.style.value],
                    "performance_selection": "Speed",
                    "aspect_ratios_selection": (f"{request.width}x{request.height}"),
                    "image_seed": request.seed if request.seed >= 0 else -1,
                    "image_number": 1,
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Fooocus error: {resp.text}")

            data = resp.json()
            import base64

            img_data = base64.b64decode(data[0]["base64"])
            output_path.write_bytes(img_data)

        return output_path

    # ── SD WebUI 实现 ───────────────────────────────

    async def _generate_sd_webui(
        self,
        request: ImageGenRequest,
        output_dir: Path,
    ) -> Path:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx not installed") from None

        output_path = output_dir / f"sd_{request.seed or 'random'}.png"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.config.sd_webui_url}/sdapi/v1/txt2img",
                json={
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "steps": request.steps,
                    "cfg_scale": request.cfg_scale,
                    "width": request.width,
                    "height": request.height,
                    "seed": request.seed if request.seed >= 0 else -1,
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"SD WebUI error: {resp.text}")

            data = resp.json()
            import base64

            img_data = base64.b64decode(data["images"][0])
            output_path.write_bytes(img_data)

        return output_path

    # ── OpenAI DALL-E 实现 ──────────────────────────

    async def _generate_openai(
        self,
        request: ImageGenRequest,
        output_dir: Path,
    ) -> Path:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx not installed") from None

        # Resolve API key: env var first, then settings
        if not self.api_key:
            from kunlun.config import settings

            self.api_key = getattr(settings, "openai_api_key", "")

        if not self.api_key:
            raise RuntimeError(
                "OpenAI API key not configured. "
                "Set IMAGE_GEN_API_KEY environment variable "
                "or configure openai_api_key in settings."
            )

        api_base = self.api_base or "https://api.openai.com"

        output_path = output_dir / f"dalle_{request.seed or 'random'}.png"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{api_base}/v1/images/generations",
                json={
                    "model": "dall-e-3",
                    "prompt": request.prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "standard",
                },
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise RuntimeError(f"DALL-E error: {resp.text}")

            data = resp.json()
            img_url = data["data"][0]["url"]

            img_resp = await client.get(img_url)
            output_path.write_bytes(img_resp.content)

        return output_path


# ── 全局单例 ───────────────────────────────────────

_image_gen: ImageGenEngine | None = None


def get_image_gen(config: ImageGenConfig | None = None) -> ImageGenEngine:
    """获取全局图像生成引擎实例"""
    global _image_gen  # noqa: PLW0603
    if _image_gen is None:
        _image_gen = ImageGenEngine(config)
    return _image_gen

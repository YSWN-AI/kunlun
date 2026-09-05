"""
昆仑创作引擎 — 图像生成 API 路由

封装 kunlun.image_gen 模块，提供封面/人物卡/场景插图生成端点。
内置降级方案：图像生成服务不可用时，调用 LLM 生成图像描述提示词返回给前端。

端点:
  POST /image-gen/cover       — 生成封面
  POST /image-gen/character   — 生成人物卡图像
  POST /image-gen/scene       — 生成场景插图
  GET  /image-gen/styles      — 获取可用风格列表
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/image-gen", tags=["图像生成"])


# ─── 请求模型 ─────────────────────────────────────────────


class CoverGenRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    title: str = Field(..., description="书名")
    style: str = Field(
        default="fantasy",
        description="风格: realistic/anime/ink_wash/fantasy/sci_fi/historical/modern/minimalist",
    )
    elements: list[str] = Field(default_factory=list, description="封面关键元素")
    color_scheme: str = Field(default="", description="配色方案")


class CharacterGenRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    character_name: str = Field(..., description="角色名")
    appearance: str = Field(default="", description="外貌描述")
    personality: str = Field(default="", description="性格描述")
    style: str = Field(default="anime", description="风格")


class SceneGenRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    scene_description: str = Field(..., description="场景描述")
    style: str = Field(default="realistic", description="风格")
    mood: str = Field(default="", description="氛围")


# ─── 可用风格 ─────────────────────────────────────────────

AVAILABLE_STYLES: list[dict] = [
    {"id": "realistic", "name": "写实", "description": "真实细腻的写实风格"},
    {"id": "anime", "name": "动漫", "description": "日系动漫风格"},
    {"id": "ink_wash", "name": "水墨", "description": "中国传统水墨风格"},
    {"id": "fantasy", "name": "奇幻", "description": "西方奇幻插画风格"},
    {"id": "sci_fi", "name": "科幻", "description": "科幻概念艺术风格"},
    {"id": "historical", "name": "古风", "description": "中国古风插画风格"},
    {"id": "modern", "name": "现代", "description": "现代简约风格"},
    {"id": "minimalist", "name": "极简", "description": "极简主义风格"},
]


def _resolve_style(style_str: str) -> str:
    """将风格字符串映射为 ImageStyle 枚举值，无效时返回 fantasy"""
    valid = {s["id"] for s in AVAILABLE_STYLES}
    return style_str if style_str in valid else "fantasy"


def _build_fallback_prompt(image_type: str, params: dict) -> str:
    """构建降级提示词（不依赖 LLM，直接根据参数拼接）"""
    parts = []
    if image_type == "cover":
        parts.append(f"Book cover design for '{params.get('title', '')}'")
        if params.get("elements"):
            parts.append("Elements: " + ", ".join(params["elements"]))
        if params.get("color_scheme"):
            parts.append(f"Color scheme: {params['color_scheme']}")
        parts.append(f"{params.get('style', 'fantasy')} style")
        parts.append("high quality, professional, detailed")
    elif image_type == "character":
        parts.append(f"Character portrait of {params.get('character_name', '')}")
        if params.get("appearance"):
            parts.append(params["appearance"])
        if params.get("personality"):
            parts.append(f"Personality: {params['personality']}")
        parts.append(f"{params.get('style', 'anime')} style")
        parts.append("high quality, detailed character illustration")
    elif image_type == "scene":
        parts.append(params.get("scene_description", ""))
        if params.get("mood"):
            parts.append(f"Mood: {params['mood']}")
        parts.append(f"{params.get('style', 'realistic')} style")
        parts.append("cinematic lighting, high quality, detailed")
    return ", ".join(p for p in parts if p)


async def _llm_enhance_prompt(base_prompt: str, image_type: str) -> str:
    """调用 LLM 增强图像提示词（降级方案的增强版）"""
    try:
        gacha_engine = cached_import("kunlun.gacha", "gacha_engine")
        type_names = {
            "cover": "书籍封面",
            "character": "角色立绘",
            "scene": "场景插图",
        }
        type_name = type_names.get(image_type, "图像")
        messages = [
            {
                "role": "system",
                "content": (
                    "你是专业的图像提示词工程师。根据用户描述，生成一段详细的"
                    "英文图像生成提示词（用于 Stable Diffusion / DALL-E）。"
                    "只输出提示词本身，不要解释。"
                ),
            },
            {
                "role": "user",
                "content": f"请为以下{type_name}生成详细的图像提示词：\n{base_prompt}",
            },
        ]
        result = await gacha_engine.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            agent="image_prompt",
        )
        content = result.get("content", "").strip()
        if content:
            return content
    except Exception as e:
        logger.warning(f"[ImageGen] LLM 提示词增强失败: {e}")
    return base_prompt


async def _try_generate(
    image_type: str,
    fallback_params: dict,
) -> dict:
    """尝试调用 ImageGenEngine，失败时降级为提示词生成

    Returns:
        统一响应 dict
    """
    # 尝试直接调用图像生成引擎
    try:
        get_image_gen = cached_import("kunlun.image_gen", "get_image_gen")
        engine = get_image_gen()

        if image_type == "cover":
            from kunlun.image_gen import CoverRequest, ImageStyle

            style_enum = ImageStyle(_resolve_style(fallback_params.get("style", "fantasy")))
            cover_req = CoverRequest(
                book_title=fallback_params.get("title", ""),
                genre="",
                style=style_enum,
                description=", ".join(fallback_params.get("elements", [])),
            )
            result = await engine.generate_cover(cover_req)
        elif image_type == "character":
            from kunlun.image_gen import CharacterPortraitRequest, ImageStyle

            style_enum = ImageStyle(_resolve_style(fallback_params.get("style", "anime")))
            char_req = CharacterPortraitRequest(
                character_name=fallback_params.get("character_name", ""),
                appearance=fallback_params.get("appearance", ""),
                style=style_enum,
                expression=fallback_params.get("personality", ""),
            )
            result = await engine.generate_character_portrait(char_req)
        elif image_type == "scene":
            from kunlun.image_gen import ImageStyle, SceneRequest

            style_enum = ImageStyle(_resolve_style(fallback_params.get("style", "realistic")))
            scene_req = SceneRequest(
                scene_description=fallback_params.get("scene_description", ""),
                style=style_enum,
                mood=fallback_params.get("mood", ""),
            )
            result = await engine.generate_scene(scene_req)
        else:
            raise ValueError(f"Unknown image type: {image_type}")

        return {
            "success": True,
            "data": {
                "image_type": image_type,
                "image_path": str(result.image_path),
                "prompt": result.prompt,
                "engine": str(result.engine),
                "generation_time": round(result.generation_time, 2),
                "mode": "direct",
            },
            "message": "图像生成成功",
        }

    except Exception as e:
        logger.warning(f"[ImageGen] 直接生成失败 ({image_type}), 启用降级: {e}")

        # 降级：生成提示词
        base_prompt = _build_fallback_prompt(image_type, fallback_params)
        enhanced_prompt = await _llm_enhance_prompt(base_prompt, image_type)

        return {
            "success": True,
            "data": {
                "image_type": image_type,
                "image_path": None,
                "prompt": enhanced_prompt,
                "engine": "fallback_llm",
                "generation_time": 0,
                "mode": "fallback",
                "fallback_reason": str(e),
            },
            "message": "图像生成服务不可用，已返回提示词供前端使用",
        }


# ─── 路由端点 ─────────────────────────────────────────────


@router.post("/cover", summary="生成封面")
async def generate_cover(req: CoverGenRequest) -> dict:
    """生成书籍封面图像。图像服务不可用时自动降级为提示词生成。"""
    logger.info(f"[ImageGen] 封面生成请求: book={req.book_id}, title={req.title}")
    params = {
        "title": req.title,
        "style": req.style,
        "elements": req.elements,
        "color_scheme": req.color_scheme,
    }
    return await _try_generate("cover", params)


@router.post("/character", summary="生成人物卡图像")
async def generate_character(req: CharacterGenRequest) -> dict:
    """生成角色立绘图像。图像服务不可用时自动降级为提示词生成。"""
    logger.info(f"[ImageGen] 人物生成请求: book={req.book_id}, char={req.character_name}")
    params = {
        "character_name": req.character_name,
        "appearance": req.appearance,
        "personality": req.personality,
        "style": req.style,
    }
    return await _try_generate("character", params)


@router.post("/scene", summary="生成场景插图")
async def generate_scene(req: SceneGenRequest) -> dict:
    """生成场景插图。图像服务不可用时自动降级为提示词生成。"""
    logger.info(f"[ImageGen] 场景生成请求: book={req.book_id}")
    params = {
        "scene_description": req.scene_description,
        "style": req.style,
        "mood": req.mood,
    }
    return await _try_generate("scene", params)


@router.get("/styles", summary="获取可用风格列表")
async def get_styles() -> dict:
    """获取图像生成可用的风格列表"""
    return {
        "success": True,
        "data": AVAILABLE_STYLES,
    }

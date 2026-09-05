"""
昆仑创作引擎 — 封面生成模块

基于题材/世界观/角色信息自动生成封面图的提示词。
支持对接多种文生图服务（DALL-E/Midjourney/Stable Diffusion/ComfyUI）。
"""

from kunlun.cover.engine import (
    PLATFORM_SIZES,
    STYLE_TEMPLATES,
    CoverAspectRatio,
    CoverConfig,
    CoverPrompt,
    CoverPromptGenerator,
    CoverStyle,
    ImageService,
    get_aspect_ratio_for_platform,
    get_cover_generator,
    get_platform_size,
)

__all__ = [
    "PLATFORM_SIZES",
    "STYLE_TEMPLATES",
    "CoverAspectRatio",
    "CoverConfig",
    "CoverPrompt",
    "CoverPromptGenerator",
    "CoverStyle",
    "ImageService",
    "get_aspect_ratio_for_platform",
    "get_cover_generator",
    "get_platform_size",
]

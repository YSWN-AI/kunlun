"""
昆仑创作引擎 — 提示词模板库

12大类60+高质量提示词模板，支持搜索、收藏、使用统计和自定义模板。
存储在 data/prompt_library/ 目录，全局共享不绑定书籍。
"""

from kunlun.prompt_library.models import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    CategoryInfo,
    CustomTemplateCreate,
    CustomTemplateUpdate,
    FavoriteAction,
    PromptTemplate,
    RateRequest,
    TemplateListResponse,
)
from kunlun.prompt_library.service import (
    create_custom_template,
    delete_custom_template,
    get_categories,
    get_favorites,
    get_template,
    is_favorite,
    list_templates,
    rate_template,
    record_usage,
    toggle_favorite,
    update_custom_template,
)
from kunlun.prompt_library.templates import BUILTIN_TEMPLATES, get_builtin_templates

__all__ = [
    "BUILTIN_TEMPLATES",
    "CATEGORIES",
    "CATEGORY_DESCRIPTIONS",
    "CategoryInfo",
    "CustomTemplateCreate",
    "CustomTemplateUpdate",
    "FavoriteAction",
    "PromptTemplate",
    "RateRequest",
    "TemplateListResponse",
    "create_custom_template",
    "delete_custom_template",
    "get_builtin_templates",
    "get_categories",
    "get_favorites",
    "get_template",
    "is_favorite",
    "list_templates",
    "rate_template",
    "record_usage",
    "toggle_favorite",
    "update_custom_template",
]

__version__ = "0.1.0"

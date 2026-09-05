"""
昆仑创作引擎 — 提示词模板库 服务层

提供模板的 CRUD、搜索、收藏、使用统计等功能。
内置模板只读，自定义模板和收藏存储在 data/prompt_library/ 目录。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.prompt_library.models import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    CategoryInfo,
    CustomTemplateCreate,
    CustomTemplateUpdate,
    PromptTemplate,
    RateRequest,
)
from kunlun.prompt_library.templates import BUILTIN_TEMPLATES


def _get_storage_dir() -> Path:
    """获取存储目录，延迟导入 settings。"""
    from kunlun.config import settings

    p = settings.DATA_DIR / "prompt_library"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_custom_path() -> Path:
    return _get_storage_dir() / "custom_templates.json"


def _get_favorites_path() -> Path:
    return _get_storage_dir() / "favorites.json"


def _get_stats_path() -> Path:
    return _get_storage_dir() / "stats.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data: Any) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning(f"[PromptLibrary] 保存失败 {path}: {e}")


def _builtin_to_template(tpl: dict[str, Any]) -> PromptTemplate:
    """将内置模板 dict 转为 PromptTemplate。"""
    return PromptTemplate(
        id=tpl["id"],
        name=tpl["name"],
        description=tpl["description"],
        category=tpl["category"],
        content=tpl["content"],
        use_case=tpl.get("use_case", ""),
        tags=tpl.get("tags", []),
        variables=tpl.get("variables", []),
        is_custom=False,
    )


def _get_all_templates() -> list[PromptTemplate]:
    """获取所有模板（内置 + 自定义），合并使用统计。"""
    templates: list[PromptTemplate] = []

    # 内置模板
    templates = [_builtin_to_template(tpl) for tpl in BUILTIN_TEMPLATES]

    # 自定义模板
    custom_data = _load_json(_get_custom_path(), [])
    for tpl in custom_data:
        try:
            templates.append(PromptTemplate(**tpl))
        except Exception as e:
            logger.debug(f"[PromptLibrary] 跳过无效自定义模板: {e}")

    # 合并使用统计
    stats = _load_json(_get_stats_path(), {})
    for tpl in templates:
        if tpl.id in stats:
            s = stats[tpl.id]
            tpl.usage_count = s.get("usage_count", 0)
            tpl.rating = s.get("rating", 0.0)
            tpl.rating_count = s.get("rating_count", 0)

    return templates


def list_templates(
    category: str = "",
    search: str = "",
    tag: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PromptTemplate], int]:
    """
    获取模板列表，支持分类/搜索/标签筛选和分页。

    返回 (模板列表, 总数)。
    """
    templates = _get_all_templates()

    # 筛选
    if category:
        templates = [t for t in templates if t.category == category]
    if tag:
        templates = [t for t in templates if tag in t.tags]
    if search:
        search_lower = search.lower()
        templates = [
            t
            for t in templates
            if search_lower in t.name.lower()
            or search_lower in t.description.lower()
            or search_lower in t.content.lower()
            or any(search_lower in tag.lower() for tag in t.tags)
        ]

    total = len(templates)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    templates = templates[start:end]

    return templates, total


def get_template(template_id: str) -> PromptTemplate | None:
    """获取单个模板详情。"""
    templates = _get_all_templates()
    for t in templates:
        if t.id == template_id:
            return t
    return None


def get_categories() -> list[CategoryInfo]:
    """获取所有分类及数量。"""
    templates = _get_all_templates()
    counts: dict[str, int] = {}
    for t in templates:
        counts[t.category] = counts.get(t.category, 0) + 1

    result = [
        CategoryInfo(
            name=cat,
            description=CATEGORY_DESCRIPTIONS.get(cat, ""),
            count=counts.get(cat, 0),
        )
        for cat in CATEGORIES
    ]
    # 包含自定义分类
    for cat, count in counts.items():
        if cat not in CATEGORIES:
            result.append(CategoryInfo(name=cat, description="自定义分类", count=count))
    return result


def record_usage(template_id: str) -> bool:
    """记录模板使用，usage_count +1。"""
    template = get_template(template_id)
    if template is None:
        return False

    stats = _load_json(_get_stats_path(), {})
    if template_id not in stats:
        stats[template_id] = {"usage_count": 0, "rating": 0.0, "rating_count": 0}
    stats[template_id]["usage_count"] += 1
    _save_json(_get_stats_path(), stats)
    return True


def rate_template(template_id: str, req: RateRequest) -> bool:
    """评分模板（1-5星），计算平均分。"""
    template = get_template(template_id)
    if template is None:
        return False

    stats = _load_json(_get_stats_path(), {})
    if template_id not in stats:
        stats[template_id] = {"usage_count": 0, "rating": 0.0, "rating_count": 0}

    s = stats[template_id]
    old_count = s.get("rating_count", 0)
    old_rating = s.get("rating", 0.0)
    new_count = old_count + 1
    new_rating = (old_rating * old_count + req.rating) / new_count

    s["rating_count"] = new_count
    s["rating"] = round(new_rating, 2)
    _save_json(_get_stats_path(), stats)
    return True


def get_favorites() -> list[PromptTemplate]:
    """获取收藏列表。"""
    fav_ids = _load_json(_get_favorites_path(), [])
    templates = _get_all_templates()
    return [t for t in templates if t.id in fav_ids]


def toggle_favorite(template_id: str) -> bool:
    """
    收藏/取消收藏。

    返回当前是否收藏。
    """
    template = get_template(template_id)
    if template is None:
        return False

    fav_ids: list[str] = _load_json(_get_favorites_path(), [])
    if template_id in fav_ids:
        fav_ids.remove(template_id)
        is_fav = False
    else:
        fav_ids.append(template_id)
        is_fav = True
    _save_json(_get_favorites_path(), fav_ids)
    return is_fav


def is_favorite(template_id: str) -> bool:
    """检查是否已收藏。"""
    fav_ids = _load_json(_get_favorites_path(), [])
    return template_id in fav_ids


def create_custom_template(req: CustomTemplateCreate) -> PromptTemplate:
    """创建自定义模板。"""
    custom_data = _load_json(_get_custom_path(), [])

    # 提取变量
    import re

    variables = list(set(re.findall(r"\{\{(.+?)\}\}", req.content)))

    template = PromptTemplate(
        id=f"custom_{uuid.uuid4().hex[:8]}",
        name=req.name,
        description=req.description,
        category=req.category,
        content=req.content,
        use_case=req.use_case,
        tags=req.tags,
        variables=variables,
        is_custom=True,
        created_at=datetime.now(),
    )

    custom_data.append(template.model_dump(mode="json"))
    _save_json(_get_custom_path(), custom_data)
    return template


def update_custom_template(template_id: str, req: CustomTemplateUpdate) -> PromptTemplate | None:
    """更新自定义模板。"""
    custom_data = _load_json(_get_custom_path(), [])
    for tpl in custom_data:
        if tpl["id"] == template_id:
            if req.name is not None:
                tpl["name"] = req.name
            if req.description is not None:
                tpl["description"] = req.description
            if req.category is not None:
                tpl["category"] = req.category
            if req.content is not None:
                tpl["content"] = req.content
                import re

                tpl["variables"] = list(set(re.findall(r"\{\{(.+?)\}\}", req.content)))
            if req.use_case is not None:
                tpl["use_case"] = req.use_case
            if req.tags is not None:
                tpl["tags"] = req.tags
            _save_json(_get_custom_path(), custom_data)
            return PromptTemplate(**tpl)
    return None


def delete_custom_template(template_id: str) -> bool:
    """删除自定义模板。"""
    custom_data = _load_json(_get_custom_path(), [])
    original_len = len(custom_data)
    custom_data = [t for t in custom_data if t["id"] != template_id]
    if len(custom_data) == original_len:
        return False
    _save_json(_get_custom_path(), custom_data)

    # 同时从收藏中移除
    fav_ids = _load_json(_get_favorites_path(), [])
    if template_id in fav_ids:
        fav_ids.remove(template_id)
        _save_json(_get_favorites_path(), fav_ids)

    return True

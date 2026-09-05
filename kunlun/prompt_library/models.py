"""
昆仑创作引擎 — 提示词模板库 数据模型

Pydantic v2 模型，支持内置模板和自定义模板。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── 分类定义 ─────────────────────────────────────────────

CATEGORIES: list[str] = [
    "角色描写",
    "场景描述",
    "情感表达",
    "故事开头",
    "对话生成",
    "人物塑造",
    "情节转折",
    "世界观构建",
    "悬疑氛围",
    "冲突设计",
    "结局设计",
    "爽点设计",
]

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "角色描写": "外貌、神态、动作、心理、服饰等角色细节描写",
    "场景描述": "自然、城市、室内、战斗、氛围等场景刻画",
    "情感表达": "喜悦、悲伤、愤怒、恐惧、爱恋等情感渲染",
    "故事开头": "冲突前置、悬念、场景代入等开篇技巧",
    "对话生成": "紧张对峙、温馨日常、幽默调侃等对话创作",
    "人物塑造": "主角成长、反派魅力、配角弧光等人物深度",
    "情节转折": "反转、升级、揭秘、背叛、重逢等剧情拐点",
    "世界观构建": "力量体系、社会结构、地理风貌等设定",
    "悬疑氛围": "伏笔铺设、紧张感、谜团设计等悬疑元素",
    "冲突设计": "人际冲突、内心挣扎、阵营对抗等矛盾设计",
    "结局设计": "圆满、悲剧、开放式、反转等结局方案",
    "爽点设计": "打脸、升级、逆袭、收获、装逼等爽文要素",
}


class PromptTemplate(BaseModel):
    """提示词模板"""

    id: str = Field(..., description="模板唯一ID")
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    category: str = Field(..., description="分类")
    content: str = Field(..., description="完整提示词内容，含{{变量}}占位符")
    use_case: str = Field(default="", description="适用场景说明")
    usage_count: int = Field(default=0, description="使用次数统计")
    rating: float = Field(default=0.0, ge=0, le=5, description="平均评分")
    rating_count: int = Field(default=0, description="评分人数")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    is_custom: bool = Field(default=False, description="是否为自定义模板")
    variables: list[str] = Field(default_factory=list, description="模板中使用的变量列表")


class CustomTemplateCreate(BaseModel):
    """创建自定义模板请求"""

    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: str = Field(default="", max_length=500, description="模板描述")
    category: str = Field(..., description="分类")
    content: str = Field(..., min_length=1, description="提示词内容")
    use_case: str = Field(default="", description="适用场景")
    tags: list[str] = Field(default_factory=list, description="标签")


class CustomTemplateUpdate(BaseModel):
    """更新自定义模板请求"""

    name: str | None = Field(default=None, max_length=100, description="模板名称")
    description: str | None = Field(default=None, max_length=500, description="模板描述")
    category: str | None = Field(default=None, description="分类")
    content: str | None = Field(default=None, description="提示词内容")
    use_case: str | None = Field(default=None, description="适用场景")
    tags: list[str] | None = Field(default=None, description="标签")


class RateRequest(BaseModel):
    """评分请求"""

    rating: int = Field(..., ge=1, le=5, description="评分（1-5星）")


class TemplateListResponse(BaseModel):
    """模板列表响应"""

    templates: list[PromptTemplate] = Field(..., description="模板列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    has_more: bool = Field(..., description="是否有更多")


class CategoryInfo(BaseModel):
    """分类信息"""

    name: str = Field(..., description="分类名称")
    description: str = Field(..., description="分类描述")
    count: int = Field(..., description="该分类下模板数量")


class FavoriteAction(BaseModel):
    """收藏操作结果"""

    template_id: str = Field(..., description="模板ID")
    is_favorite: bool = Field(..., description="当前是否收藏")

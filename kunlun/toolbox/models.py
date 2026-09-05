"""
昆仑创作引擎 — 专业生成器工具箱 数据模型

所有生成器的请求/响应模型，使用 Pydantic v2。
生成器均为纯模板+规则，不调用 LLM，确保离线可用。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── 通用枚举 ──────────────────────────────────────────────

GeneratorType = Literal[
    "title",
    "synopsis",
    "outline",
    "chapter_outline",
    "opening",
    "cheat",
    "name",
    "character",
]

GENERATOR_TYPES: tuple[str, ...] = (
    "title",
    "synopsis",
    "outline",
    "chapter_outline",
    "opening",
    "cheat",
    "name",
    "character",
)

GENERATOR_LABELS: dict[str, str] = {
    "title": "书名生成器",
    "synopsis": "简介生成器",
    "outline": "大纲生成器",
    "chapter_outline": "细纲生成器",
    "opening": "黄金开篇生成器",
    "cheat": "金手指生成器",
    "name": "名字生成器",
    "character": "人设生成器",
}

# ── 各生成器请求模型 ──────────────────────────────────────


class TitleGenerateRequest(BaseModel):
    """书名生成请求"""

    genre: str = Field(default="玄幻", description="题材：玄幻/都市/科幻/历史/言情等")
    style: str = Field(default="番茄", description="风格：番茄/起点/晋江")
    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    count: int = Field(default=5, ge=1, le=20, description="生成数量")


class SynopsisGenerateRequest(BaseModel):
    """简介生成请求"""

    title: str = Field(..., description="书名")
    genre: str = Field(default="玄幻", description="题材")
    protagonist: str = Field(..., description="主角设定")
    core_conflict: str = Field(..., description="核心冲突")
    word_count: int = Field(default=250, ge=100, le=500, description="目标字数")


class OutlineGenerateRequest(BaseModel):
    """大纲生成请求"""

    genre: str = Field(default="玄幻", description="题材")
    protagonist: str = Field(..., description="主角设定")
    core_conflict: str = Field(..., description="核心冲突")
    structure_type: Literal["three_act", "hero_journey"] = Field(
        default="three_act", description="结构类型：三幕式/英雄之旅"
    )
    volume_count: int = Field(default=8, ge=3, le=15, description="卷数")


class ChapterOutlineGenerateRequest(BaseModel):
    """细纲生成请求"""

    volume_outline: str = Field(..., description="卷大纲内容")
    volume_title: str = Field(default="", description="卷标题")
    chapter_count: int = Field(default=20, ge=1, le=100, description="章节数")
    genre: str = Field(default="玄幻", description="题材")


class OpeningGenerateRequest(BaseModel):
    """黄金开篇生成请求"""

    genre: str = Field(default="玄幻", description="题材")
    protagonist: str = Field(..., description="主角设定")
    core_conflict: str = Field(..., description="核心冲突")
    word_count: int = Field(default=500, ge=200, le=1000, description="每种方案字数")


class CheatGenerateRequest(BaseModel):
    """金手指生成请求"""

    genre: str = Field(default="玄幻", description="题材类型")
    count: int = Field(default=5, ge=1, le=10, description="生成数量")


class NameGenerateRequest(BaseModel):
    """名字生成请求"""

    name_type: Literal["character", "location", "item", "technique"] = Field(
        default="character", description="类型：角色/地点/物品/功法"
    )
    style: Literal["ancient", "modern", "western"] = Field(
        default="ancient", description="风格：古风/现代/西方"
    )
    count: int = Field(default=10, ge=1, le=50, description="生成数量")
    gender: str = Field(default="", description="角色性别（仅角色名时生效）：男/女")


class CharacterGenerateRequest(BaseModel):
    """人设生成请求"""

    role_type: Literal["protagonist", "antagonist", "supporting"] = Field(
        default="protagonist", description="角色类型：主角/反派/配角"
    )
    genre: str = Field(default="玄幻", description="题材")
    core_trait: str = Field(..., description="核心特质")
    name: str = Field(default="", description="指定姓名（留空则自动生成）")


# ── 通用生成请求（用于 /generate/{generator_type}） ───────


class GenericGenerateRequest(BaseModel):
    """通用生成请求，字段按需填充"""

    genre: str = Field(default="玄幻", description="题材")
    style: str = Field(default="番茄", description="风格")
    keywords: list[str] = Field(default_factory=list, description="关键词")
    title: str = Field(default="", description="书名")
    protagonist: str = Field(default="", description="主角设定")
    core_conflict: str = Field(default="", description="核心冲突")
    structure_type: str = Field(default="three_act", description="结构类型")
    volume_count: int = Field(default=8, ge=3, le=15, description="卷数")
    volume_outline: str = Field(default="", description="卷大纲")
    volume_title: str = Field(default="", description="卷标题")
    chapter_count: int = Field(default=20, ge=1, le=100, description="章节数")
    word_count: int = Field(default=250, ge=100, le=1000, description="目标字数")
    name_type: str = Field(default="character", description="名字类型")
    name_style: str = Field(default="ancient", description="名字风格")
    count: int = Field(default=5, ge=1, le=50, description="生成数量")
    gender: str = Field(default="", description="性别")
    role_type: str = Field(default="protagonist", description="角色类型")
    core_trait: str = Field(default="", description="核心特质")
    name: str = Field(default="", description="指定姓名")
    book_id: str = Field(default="", description="书籍ID（用于保存）")


# ── 各生成器响应模型 ──────────────────────────────────────


class TitleResult(BaseModel):
    """书名结果"""

    titles: list[str] = Field(..., description="候选书名列表")


class SynopsisResult(BaseModel):
    """简介结果"""

    synopsis: str = Field(..., description="生成的简介文本")
    word_count: int = Field(..., description="实际字数")


class VolumeOutline(BaseModel):
    """单卷大纲"""

    volume_number: int = Field(..., description="卷序号")
    title: str = Field(..., description="卷标题")
    core_events: list[str] = Field(..., description="核心事件列表")
    ending_twist: str = Field(..., description="结局转折")


class OutlineResult(BaseModel):
    """大纲结果"""

    structure_type: str = Field(..., description="结构类型")
    volumes: list[VolumeOutline] = Field(..., description="卷级大纲列表")


class ChapterOutlineItem(BaseModel):
    """单章细纲"""

    chapter_number: int = Field(..., description="章节序号")
    title: str = Field(..., description="章节标题")
    scene: str = Field(..., description="场景描述")
    conflict: str = Field(..., description="冲突点")
    hook: str = Field(..., description="章末钩子")


class ChapterOutlineResult(BaseModel):
    """细纲结果"""

    volume_title: str = Field(..., description="所属卷标题")
    chapters: list[ChapterOutlineItem] = Field(..., description="章节细纲列表")


class OpeningScheme(BaseModel):
    """单种开篇方案"""

    scheme_type: str = Field(..., description="方案类型：冲突前置型/悬念设置型/场景代入型")
    content: str = Field(..., description="开篇正文")


class OpeningResult(BaseModel):
    """黄金开篇结果"""

    schemes: list[OpeningScheme] = Field(..., description="开篇方案列表")


class CheatScheme(BaseModel):
    """金手指方案"""

    name: str = Field(..., description="金手指名称")
    category: str = Field(..., description="类别：系统/穿越/重生/异能/血脉等")
    ability_description: str = Field(..., description="能力描述")
    growth_path: str = Field(..., description="成长路径")
    limitation: str = Field(..., description="限制条件")


class CheatResult(BaseModel):
    """金手指结果"""

    cheats: list[CheatScheme] = Field(..., description="金手指方案列表")


class NameResult(BaseModel):
    """名字结果"""

    names: list[str] = Field(..., description="生成的名字列表")


class CharacterProfile(BaseModel):
    """完整人设"""

    name: str = Field(..., description="姓名")
    age: str = Field(..., description="年龄")
    appearance: str = Field(..., description="外貌描写")
    background: str = Field(..., description="背景故事")
    personality: str = Field(..., description="性格特征")
    motivation: str = Field(..., description="核心动机")
    ability: str = Field(..., description="能力设定")
    growth_arc: str = Field(..., description="成长弧光")
    classic_lines: list[str] = Field(..., description="经典台词")


class CharacterResult(BaseModel):
    """人设结果"""

    character: CharacterProfile = Field(..., description="完整人设")


# ── 保存与历史 ────────────────────────────────────────────


class SaveRequest(BaseModel):
    """保存生成结果请求"""

    book_id: str = Field(..., description="书籍ID")
    generator_type: str = Field(..., description="生成器类型")
    result: dict[str, Any] = Field(..., description="生成结果数据")
    label: str = Field(default="", description="备注标签")


class HistoryRecord(BaseModel):
    """生成历史记录"""

    id: str = Field(..., description="记录ID")
    generator_type: str = Field(..., description="生成器类型")
    book_id: str = Field(default="", description="书籍ID")
    request_data: dict[str, Any] = Field(default_factory=dict, description="请求参数")
    result_data: dict[str, Any] = Field(default_factory=dict, description="生成结果")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class GeneratorInfo(BaseModel):
    """生成器元信息"""

    type: str = Field(..., description="生成器类型标识")
    name: str = Field(..., description="生成器名称")
    description: str = Field(..., description="功能描述")
    request_model: str = Field(..., description="请求模型类名")


# ── 统一响应 ──────────────────────────────────────────────


class GenerateResponse(BaseModel):
    """统一生成响应"""

    success: bool = True
    generator_type: str = Field(..., description="生成器类型")
    data: dict[str, Any] = Field(..., description="生成结果数据")

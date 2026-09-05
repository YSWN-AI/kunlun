"""
昆仑创作引擎 — AI拆书案例库 数据模型

Pydantic v2 模型，定义拆书案例的完整结构。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NarrativeRhythmPhase(BaseModel):
    """叙事节奏单阶段分析。"""

    description: str = Field(default="", description="阶段描述")
    score: int = Field(default=7, ge=1, le=10, description="节奏评分(1-10)")


class NarrativeRhythm(BaseModel):
    """叙事节奏分析 — 开局/中期/高潮/结局四阶段。"""

    opening: NarrativeRhythmPhase = Field(default_factory=NarrativeRhythmPhase)
    middle: NarrativeRhythmPhase = Field(default_factory=NarrativeRhythmPhase)
    climax: NarrativeRhythmPhase = Field(default_factory=NarrativeRhythmPhase)
    ending: NarrativeRhythmPhase = Field(default_factory=NarrativeRhythmPhase)


class PleasurePoint(BaseModel):
    """爽点设置。"""

    type: str = Field(default="", description="爽点类型（打脸/逆袭/装逼/收获/揭秘等）")
    position: str = Field(default="", description="出现位置（开局/前中期/中期/高潮/结局）")
    description: str = Field(default="", description="爽点具体描述")
    effect_score: int = Field(default=7, ge=1, le=10, description="效果评分(1-10)")


class PlotStructure(BaseModel):
    """情节结构。"""

    main_line: str = Field(default="", description="主线概述")
    sub_lines: list[str] = Field(default_factory=list, description="支线列表")
    foreshadowing_count: int = Field(default=0, ge=0, description="伏笔数量")
    twist_count: int = Field(default=0, ge=0, description="转折数量")
    structure_type: str = Field(default="线性", description="结构类型（线性/多线/环形/嵌套等）")


class CharacterArc(BaseModel):
    """人物弧光。"""

    name: str = Field(default="", description="角色名")
    role_type: str = Field(default="", description="角色类型（主角/反派/配角/导师/对手等）")
    initial_state: str = Field(default="", description="初始状态")
    growth_path: str = Field(default="", description="成长路径")
    final_state: str = Field(default="", description="最终状态")
    arc_type: str = Field(default="", description="弧光类型（成长/堕落/救赎/扁平/循环等）")


class StyleFingerprint(BaseModel):
    """风格指纹 — 12维度评分 + 文字特征描述。"""

    sentence_style: str = Field(default="", description="句式特点")
    vocabulary_preference: str = Field(default="", description="用词偏好")
    narrative_perspective: str = Field(default="", description="叙事视角")
    rhythm_feature: str = Field(default="", description="节奏特征")
    dialogue_style: str = Field(default="", description="对话风格")
    scores: dict[str, int] = Field(
        default_factory=dict,
        description="12维度评分（画面感/节奏感/情绪张力/信息密度/幽默度/严肃度/文学性/通俗性/创新度/代入感/爽感/文笔）",
    )


class BookAnalysisCase(BaseModel):
    """完整拆书案例。"""

    id: str = Field(default="", description="案例唯一ID")
    title: str = Field(default="", description="作品名称")
    author: str = Field(default="", description="作者")
    genre: str = Field(default="", description="题材（玄幻/都市/科幻/历史/悬疑等）")
    platform: str = Field(default="", description="平台（番茄/起点/晋江等）")
    tags: list[str] = Field(default_factory=list, description="标签")
    word_count: str = Field(default="", description="字数规模")
    status: str = Field(default="完结", description="状态（连载/完结）")
    summary: str = Field(default="", description="作品简介")
    narrative_rhythm: NarrativeRhythm = Field(default_factory=NarrativeRhythm)
    pleasure_points: list[PleasurePoint] = Field(default_factory=list)
    plot_structure: PlotStructure = Field(default_factory=PlotStructure)
    character_arcs: list[CharacterArc] = Field(default_factory=list)
    style_fingerprint: StyleFingerprint = Field(default_factory=StyleFingerprint)
    methodology: list[str] = Field(default_factory=list, description="可复用方法论（10条以上）")
    key_quotes: list[str] = Field(default_factory=list, description="经典片段/金句")
    created_at: str = Field(default="", description="创建时间")
    is_custom: bool = Field(default=False, description="是否为用户自定义案例")


class CompareRequest(BaseModel):
    """对比分析请求。"""

    case_ids: list[str] = Field(default_factory=list, description="要对比的案例ID列表")


class MethodologyRequest(BaseModel):
    """共性方法论提炼请求。"""

    case_ids: list[str] = Field(default_factory=list, description="要提炼的案例ID列表")


class CustomCaseCreateRequest(BaseModel):
    """创建自定义拆书案例请求。"""

    title: str = Field(..., description="作品名称")
    author: str = Field(default="", description="作者")
    genre: str = Field(default="", description="题材")
    platform: str = Field(default="", description="平台")
    tags: list[str] = Field(default_factory=list, description="标签")
    word_count: str = Field(default="", description="字数规模")
    status: str = Field(default="完结", description="状态")
    summary: str = Field(default="", description="作品简介")
    narrative_rhythm: dict = Field(default_factory=dict, description="叙事节奏分析")
    pleasure_points: list[dict] = Field(default_factory=list, description="爽点设置")
    plot_structure: dict = Field(default_factory=dict, description="情节结构")
    character_arcs: list[dict] = Field(default_factory=list, description="人物弧光")
    style_fingerprint: dict = Field(default_factory=dict, description="风格指纹")
    methodology: list[str] = Field(default_factory=list, description="可复用方法论")
    key_quotes: list[str] = Field(default_factory=list, description="经典片段/金句")


class CustomCaseUpdateRequest(BaseModel):
    """更新自定义拆书案例请求 — 所有字段可选。"""

    title: str | None = Field(default=None)
    author: str | None = Field(default=None)
    genre: str | None = Field(default=None)
    platform: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    word_count: str | None = Field(default=None)
    status: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    narrative_rhythm: dict | None = Field(default=None)
    pleasure_points: list[dict] | None = Field(default=None)
    plot_structure: dict | None = Field(default=None)
    character_arcs: list[dict] | None = Field(default=None)
    style_fingerprint: dict | None = Field(default=None)
    methodology: list[str] | None = Field(default=None)
    key_quotes: list[str] | None = Field(default=None)

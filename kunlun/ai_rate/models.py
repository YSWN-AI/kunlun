"""
昆仑创作引擎 — 降AI工作台数据模型

Pydantic v2 模型，定义12维度分析、8种改写策略、前后对比等数据结构。
所有分数均为 0-100，分数越高表示 AI 特征越明显。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    """单维度AI特征得分。"""

    name: str = Field(..., description="维度名称，如 vocabulary_repetition")
    label: str = Field(..., description="维度中文标签，如 词汇重复率")
    score: float = Field(..., ge=0, le=100, description="维度得分 0-100，越高越AI")
    level: str = Field(..., description="风险等级: low/medium/high")
    suggestions: list[str] = Field(default_factory=list, description="改进建议列表")
    detail: dict = Field(default_factory=dict, description="维度详细统计数据")


class RiskPhrase(BaseModel):
    """风险短语，带位置信息供前端高亮。"""

    text: str = Field(..., description="风险短语原文")
    start: int = Field(..., ge=0, description="在原文中的起始字符偏移")
    end: int = Field(..., ge=0, description="在原文中的结束字符偏移（不含）")
    dimension: str = Field(..., description="所属维度名称")
    reason: str = Field(default="", description="风险原因说明")
    severity: str = Field(default="medium", description="严重程度: low/medium/high")


class AiAnalysisResult(BaseModel):
    """12维度AI率分析结果。"""

    overall_score: float = Field(..., ge=0, le=100, description="总体AI率 0-100")
    level: str = Field(..., description="总体等级: very_low/low/medium/high/very_high")
    dimensions: list[DimensionScore] = Field(default_factory=list, description="12个维度得分")
    risk_phrases: list[RiskPhrase] = Field(
        default_factory=list, description="风险短语列表（带位置）"
    )
    summary: str = Field(default="", description="分析摘要文本")
    word_count: int = Field(default=0, description="总字数")
    sentence_count: int = Field(default=0, description="句子数")
    paragraph_count: int = Field(default=0, description="段落数")


class EditRecord(BaseModel):
    """单条修改记录，原文→新文映射。"""

    original: str = Field(..., description="原文片段")
    replaced: str = Field(..., description="改写后片段")
    position: int = Field(default=0, ge=0, description="在原文中的起始字符偏移")
    strategy: str = Field(..., description="使用的改写策略标识")
    description: str = Field(default="", description="修改说明")


class HumanizeResult(BaseModel):
    """按策略改写结果。"""

    original_text: str = Field(..., description="原始文本")
    rewritten_text: str = Field(..., description="改写后文本")
    edit_records: list[EditRecord] = Field(default_factory=list, description="修改记录列表")
    before_score: float = Field(default=0, ge=0, le=100, description="改写前AI率")
    after_score: float = Field(default=0, ge=0, le=100, description="改写后AI率")
    strategies_used: list[str] = Field(default_factory=list, description="实际生效的策略列表")
    word_count_before: int = Field(default=0, description="改写前字数")
    word_count_after: int = Field(default=0, description="改写后字数")


class DiffSegment(BaseModel):
    """前后对比差异片段。"""

    type: str = Field(..., description="差异类型: same/removed/added/modified")
    original: str = Field(default="", description="原文片段")
    rewritten: str = Field(default="", description="改写后片段")
    original_start: int = Field(default=0, description="原文起始偏移")
    rewritten_start: int = Field(default=0, description="改写文起始偏移")


class CompareResult(BaseModel):
    """前后对比结果。"""

    before_score: float = Field(..., ge=0, le=100, description="原文AI率")
    after_score: float = Field(..., ge=0, le=100, description="改写文AI率")
    improvement: float = Field(default=0, description="AI率下降幅度（正数表示改善）")
    diff_segments: list[DiffSegment] = Field(default_factory=list, description="差异高亮数据")
    dimension_improvements: list[dict] = Field(default_factory=list, description="各维度改善情况")
    summary: str = Field(default="", description="对比摘要")


class StrategyInfo(BaseModel):
    """改写策略元信息。"""

    id: str = Field(..., description="策略标识")
    name: str = Field(..., description="策略中文名")
    description: str = Field(..., description="策略说明")
    category: str = Field(default="", description="策略分类: vocabulary/sentence/paragraph/style")


class DimensionInfo(BaseModel):
    """分析维度元信息。"""

    name: str = Field(..., description="维度标识")
    label: str = Field(..., description="维度中文名")
    description: str = Field(..., description="维度说明")
    weight: float = Field(default=1.0, description="在总体评分中的权重")

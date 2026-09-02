"""
昆仑创作引擎 — 追读力系统 类型定义

包含所有枚举和数据类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ─── 枚举定义 ────────────────────────────────────────


class RiskLevel(Enum):
    """风险等级"""

    SAFE = "SAFE"  # 无风险
    WATCH = "WATCH"  # 需关注
    WARN = "WARN"  # 警告
    CRITICAL = "CRITICAL"  # 严重


class HookType(Enum):
    """钩子类型 (基于网文黄金法则)"""

    CLIFFHANGER = "cliffhanger"  # 悬念断章 — "他不知道，门后是..."
    REVELATION = "revelation"  # 真相揭示 — "原来他才是..."
    CONFRONTATION = "confrontation"  # 冲突升级 — "你敢！"
    PROMISE = "promise"  # 承诺预告 — "明天，一切将改变"
    EMOTIONAL = "emotional"  # 情绪高点 — 感动/愤怒/爽
    MYSTERY = "mystery"  # 谜题抛出 — "那个符号的意思是..."
    POWER_UP = "power_up"  # 实力提升预告 — "突破在即"
    REVERSAL = "reversal"  # 反转 — "所有人都被骗了"


class PleasureCategory(Enum):
    """爽点分类 (webnovel-writer 分类体系)"""

    FACE_SLAP = "face_slap"  # 打脸
    POWER_UP = "power_up"  # 升级突破
    TREASURE = "treasure"  # 获得宝物/机缘
    REVENGE = "revenge"  # 复仇
    ROMANCE = "romance"  # 感情线推进
    MYSTERY_SOLVE = "mystery_solve"  # 谜题破解
    PRESTIGE = "prestige"  # 声望提升
    COUNTERATTACK = "counterattack"  # 绝境反击
    ALLIANCE = "alliance"  # 结盟/收服
    BETRAYAL = "betrayal"  # 背叛（反向爽点）
    SACRIFICE = "sacrifice"  # 牺牲（催泪爽点）
    COMEDY = "comedy"  # 搞笑/玩梗


class DebtType(Enum):
    """债务类型 — 未兑现的承诺"""

    FORESHADOW = "foreshadow"  # 伏笔未回收
    CONFLICT = "conflict"  # 冲突未解决
    MYSTERY = "mystery"  # 谜题未揭示
    CHARACTER_ARC = "character_arc"  # 角色成长未完成
    ROMANCE = "romance"  # 感情线未推进
    CHEKHOV_GUN = "chekhov_gun"  # 契诃夫之枪（埋了没用）


# ─── 数据模型 ────────────────────────────────────────


@dataclass
class HookResult:
    """单个钩子检测结果"""

    hook_type: HookType
    position: str  # "opening" | "closing" | "mid_chapter"
    paragraph_index: int
    strength: float  # 0.0~1.0
    matched_text: str = ""
    keywords_matched: list[str] = field(default_factory=list)


@dataclass
class PleasurePoint:
    """单个爽点"""

    category: PleasureCategory
    paragraph_index: int
    intensity: float  # 0.0~1.0
    matched_text: str = ""
    is_climax: bool = False


@dataclass
class MicroPayoff:
    """微兑现记录"""

    payoff_type: str  # "foreshadow" | "promise" | "setup"
    setup_chapter: int  # 埋设章节
    payoff_chapter: int  # 兑现章节
    description: str
    delay_chapters: int  # 延迟章节数
    is_satisfying: bool  # 兑现是否令人满意


@dataclass
class Debt:
    """未兑现债务"""

    debt_type: DebtType
    description: str
    created_chapter: int
    age_chapters: int  # 已拖欠章节数
    severity: RiskLevel
    should_resolve_by: int  # 建议解决章节


@dataclass
class ChapterFeatures:
    """章节特征 (供追读力计算)"""

    chapter_number: int
    word_count: int
    paragraph_count: int
    dialogue_ratio: float  # 0.0~1.0
    action_ratio: float  # 0.0~1.0
    description_ratio: float  # 0.0~1.0
    scene_count: int
    pov_count: int


@dataclass
class RetentionReport:
    """追读力综合报告"""

    chapter_number: int
    overall_score: float  # 0.0~1.0 综合追读力

    # 四大子系统
    hook_score: float  # 钩子强度
    pleasure_score: float  # 爽点评分
    payoff_score: float  # 微兑现评分
    debt_score: float  # 债务健康度 (1.0=无债务)

    # 详情
    hooks: list[HookResult] = field(default_factory=list)
    pleasure_points: list[PleasurePoint] = field(default_factory=list)
    active_debts: list[Debt] = field(default_factory=list)
    recent_payoffs: list[MicroPayoff] = field(default_factory=list)

    # 特征
    features: ChapterFeatures | None = None

    # 风险
    risk_level: RiskLevel = RiskLevel.SAFE
    risk_reasons: list[str] = field(default_factory=list)

    # 平台适配评分
    platform_scores: dict[str, float] = field(default_factory=dict)
    # 如 {"fanqie": 0.85, "qidian": 0.72, "qimao": 0.90}

    # 建议
    suggestions: list[str] = field(default_factory=list)

    # 时序数据
    debt_trend: list[float] = field(default_factory=list)  # 最近10章债务变化


@dataclass
class DropOffPrediction:
    """章节读者流失预测"""

    chapter_number: int
    predicted_dropoff_rate: float  # 预测流失率 0-1
    risk_level: RiskLevel
    contributing_factors: list[str] = field(default_factory=list)
    hook_strength: float = 0.0
    word_count_score: float = 0.0
    pace_score: float = 0.0
    fatigue_score: float = 0.0
    cliff_strength: float = 0.0


@dataclass
class HookStrengthReport:
    """钩子强度详细报告"""

    chapter_number: int
    opening_hook_score: float  # 开头吸引力 0-1
    closing_hook_score: float  # 结尾悬念度 0-1
    mid_hook_score: float  # 中间锚点 0-1
    overall_score: float  # 综合评分 0-1
    weak_spots: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    cliffhanger_present: bool = False
    emotional_peak_present: bool = False
    mystery_hook_present: bool = False


@dataclass
class RetentionOptimizationPlan:
    """留存优化方案"""

    chapter_number: int
    overall_retention_score: float
    priority_actions: list[dict[str, Any]]  # 按优先级排序的行动项
    quick_wins: list[str]  # 快速改善项
    structural_changes: list[str]  # 结构性改善项
    platform_specific_tips: dict[str, list[str]]  # 平台特定建议

"""
pleasure 爽点引擎 — 类型定义、配置、数据类、关键词词典
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ============================================================================
# 枚举定义
# ============================================================================


class PleasureType(StrEnum):
    """爽点类型 — 12+种类型，每种带有强度系数/疲劳衰减/最佳间隔/适配题材"""

    FACE_SLAP = "face_slap"  # 打脸/装逼打脸
    LEVEL_UP = "level_up"  # 升级/突破
    ACQUISITION = "acquisition"  # 获得宝物/技能/机缘
    OVERWHELM = "overwhelm"  # 碾压/横扫
    REVEAL = "reveal"  # 揭秘/身份暴露
    ROMANCE = "romance"  # 暧昧/感情升温
    REVENGE = "revenge"  # 复仇/清算
    PROTECT = "protect"  # 守护/护短
    SHOW_OFF = "show_off"  # 装逼/显圣
    TWIST = "twist"  # 反转/神转折
    TOUCHING = "touching"  # 感动/泪点
    HOT_BLOOD = "hot_blood"  # 热血/燃
    AWAKENING = "awakening"  # 觉醒/觉醒时刻
    SYSTEM_REWARD = "system_reward"  # 系统奖励/金手指发放
    FORTUNATE = "fortunate"  # 奇遇/机缘
    HAREM = "harem"  # 后宫/收服
    TORTURE = "torture"  # 虐主/先抑后扬
    RHYTHM_BREAK = "rhythm_break"  # 爽文节奏/节奏切换


class FatigueLevel(StrEnum):
    """疲劳度等级"""

    FRESH = "fresh"  # 新鲜
    NORMAL = "normal"  # 正常
    TIRING = "tiring"  # 开始疲劳
    EXHAUSTED = "exhausted"  # 完全疲劳（再写同类效果减半）


# ============================================================================
# 爽点类型配置 — 每种类型携带: 强度系数/疲劳衰减/最佳间隔/适配题材
# ============================================================================


@dataclass
class PleasureTypeConfig:
    """爽点类型配置 — 基于50款竞品调研的最佳实践参数"""

    event_type: PleasureType
    name_cn: str  # 中文名
    intensity_base: float  # 基础强度系数 0-1
    fatigue_decay: float  # 疲劳衰减因子 (每次重复 ×衰减)
    optimal_interval: int  # 最佳间隔(字数)
    min_interval: int  # 最小间隔(字数)，低于此值爽感减半
    suitable_genres: list[str]  # 适配题材列表
    grade: str = "S"  # S/A/B/C 等级

    def get_effective_intensity(self, interval: int, previous_count: int) -> float:
        """计算考虑间距和历史次数后的有效强度"""
        base = self.intensity_base
        if interval < self.min_interval:
            base *= 0.5
        decay = 1.0 - min(self.fatigue_decay * previous_count, 0.8)
        return base * max(decay, 0.2)


PLEASURE_TYPE_CONFIGS: dict[PleasureType, PleasureTypeConfig] = {
    PleasureType.FACE_SLAP: PleasureTypeConfig(
        event_type=PleasureType.FACE_SLAP,
        name_cn="打脸",
        intensity_base=0.90,
        fatigue_decay=0.10,
        optimal_interval=2500,
        min_interval=1200,
        suitable_genres=["都市修真", "都市装逼", "系统流", "重生流", "玄幻"],
        grade="S",
    ),
    PleasureType.LEVEL_UP: PleasureTypeConfig(
        event_type=PleasureType.LEVEL_UP,
        name_cn="升级",
        intensity_base=0.85,
        fatigue_decay=0.08,
        optimal_interval=3000,
        min_interval=1500,
        suitable_genres=["玄幻", "修真", "系统流", "游戏"],
        grade="S",
    ),
    PleasureType.ACQUISITION: PleasureTypeConfig(
        event_type=PleasureType.ACQUISITION,
        name_cn="收获",
        intensity_base=0.70,
        fatigue_decay=0.12,
        optimal_interval=3500,
        min_interval=2000,
        suitable_genres=["玄幻", "修真", "系统流", "末日"],
        grade="A",
    ),
    PleasureType.SHOW_OFF: PleasureTypeConfig(
        event_type=PleasureType.SHOW_OFF,
        name_cn="装逼",
        intensity_base=0.88,
        fatigue_decay=0.15,
        optimal_interval=2200,
        min_interval=1000,
        suitable_genres=["都市修真", "都市装逼", "系统流", "重生流"],
        grade="S",
    ),
    PleasureType.AWAKENING: PleasureTypeConfig(
        event_type=PleasureType.AWAKENING,
        name_cn="觉醒",
        intensity_base=0.92,
        fatigue_decay=0.06,
        optimal_interval=5000,
        min_interval=3000,
        suitable_genres=["玄幻", "系统流", "重生流", "末日"],
        grade="S",
    ),
    PleasureType.OVERWHELM: PleasureTypeConfig(
        event_type=PleasureType.OVERWHELM,
        name_cn="碾压",
        intensity_base=0.86,
        fatigue_decay=0.14,
        optimal_interval=2800,
        min_interval=1500,
        suitable_genres=["都市修真", "玄幻", "系统流", "游戏"],
        grade="A",
    ),
    PleasureType.TWIST: PleasureTypeConfig(
        event_type=PleasureType.TWIST,
        name_cn="反转",
        intensity_base=0.82,
        fatigue_decay=0.05,
        optimal_interval=4000,
        min_interval=2500,
        suitable_genres=["悬疑", "言情", "科幻", "重生流"],
        grade="A",
    ),
    PleasureType.TORTURE: PleasureTypeConfig(
        event_type=PleasureType.TORTURE,
        name_cn="虐主",
        intensity_base=0.60,
        fatigue_decay=0.20,
        optimal_interval=3500,
        min_interval=2000,
        suitable_genres=["言情", "古装言情", "都市"],
        grade="B",
    ),
    PleasureType.RHYTHM_BREAK: PleasureTypeConfig(
        event_type=PleasureType.RHYTHM_BREAK,
        name_cn="爽文节奏",
        intensity_base=0.75,
        fatigue_decay=0.10,
        optimal_interval=3000,
        min_interval=2000,
        suitable_genres=["系统流", "重生流", "都市装逼", "网游竞技"],
        grade="A",
    ),
    PleasureType.FORTUNATE: PleasureTypeConfig(
        event_type=PleasureType.FORTUNATE,
        name_cn="奇遇",
        intensity_base=0.78,
        fatigue_decay=0.09,
        optimal_interval=3500,
        min_interval=2000,
        suitable_genres=["玄幻", "修真", "穿越", "系统流"],
        grade="A",
    ),
    PleasureType.HAREM: PleasureTypeConfig(
        event_type=PleasureType.HAREM,
        name_cn="后宫",
        intensity_base=0.65,
        fatigue_decay=0.18,
        optimal_interval=4000,
        min_interval=2500,
        suitable_genres=["都市", "玄幻", "古装言情", "游戏"],
        grade="B",
    ),
    PleasureType.SYSTEM_REWARD: PleasureTypeConfig(
        event_type=PleasureType.SYSTEM_REWARD,
        name_cn="系统奖励",
        intensity_base=0.80,
        fatigue_decay=0.13,
        optimal_interval=2500,
        min_interval=1200,
        suitable_genres=["系统流", "游戏", "重生流"],
        grade="S",
    ),
    PleasureType.REVENGE: PleasureTypeConfig(
        event_type=PleasureType.REVENGE,
        name_cn="复仇",
        intensity_base=0.87,
        fatigue_decay=0.07,
        optimal_interval=5000,
        min_interval=3000,
        suitable_genres=["都市装逼", "重生流", "玄幻", "悬疑"],
        grade="S",
    ),
    PleasureType.REVEAL: PleasureTypeConfig(
        event_type=PleasureType.REVEAL,
        name_cn="揭秘",
        intensity_base=0.72,
        fatigue_decay=0.06,
        optimal_interval=4000,
        min_interval=2500,
        suitable_genres=["悬疑", "科幻", "修真"],
        grade="A",
    ),
    PleasureType.ROMANCE: PleasureTypeConfig(
        event_type=PleasureType.ROMANCE,
        name_cn="暧昧",
        intensity_base=0.55,
        fatigue_decay=0.08,
        optimal_interval=3000,
        min_interval=1500,
        suitable_genres=["言情", "古装言情", "都市生活"],
        grade="B",
    ),
    PleasureType.TOUCHING: PleasureTypeConfig(
        event_type=PleasureType.TOUCHING,
        name_cn="感动",
        intensity_base=0.50,
        fatigue_decay=0.12,
        optimal_interval=4500,
        min_interval=3000,
        suitable_genres=["言情", "古装言情", "都市生活", "末日"],
        grade="B",
    ),
    PleasureType.HOT_BLOOD: PleasureTypeConfig(
        event_type=PleasureType.HOT_BLOOD,
        name_cn="热血",
        intensity_base=0.84,
        fatigue_decay=0.06,
        optimal_interval=3500,
        min_interval=2000,
        suitable_genres=["玄幻", "游戏", "末日", "科幻"],
        grade="A",
    ),
    PleasureType.PROTECT: PleasureTypeConfig(
        event_type=PleasureType.PROTECT,
        name_cn="守护",
        intensity_base=0.62,
        fatigue_decay=0.10,
        optimal_interval=4000,
        min_interval=2500,
        suitable_genres=["都市", "言情", "玄幻"],
        grade="B",
    ),
}


def get_pleasure_config(ptype: PleasureType) -> PleasureTypeConfig:
    """获取爽点类型配置，未配置的类型返回默认值"""
    return PLEASURE_TYPE_CONFIGS.get(
        ptype,
        PleasureTypeConfig(
            event_type=ptype,
            name_cn=ptype.value,
            intensity_base=0.60,
            fatigue_decay=0.10,
            optimal_interval=3000,
            min_interval=1500,
            suitable_genres=[],
            grade="C",
        ),
    )


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class PleasureEvent:
    """单个爽点事件"""

    event_type: PleasureType
    position: int  # 在文本中的位置（字数偏移）
    intensity: float  # 强度 0-1
    keywords_matched: list[str]  # 匹配到的关键词
    context_snippet: str = ""  # 上下文片段（前后20字）
    paragraph_index: int = 0

    def __repr__(self) -> str:
        return (
            f"<PleasureEvent {self.event_type.value} "
            f"@{self.position} intensity={self.intensity:.2f}>"
        )


@dataclass
class TypeFatigue:
    """某类爽点的疲劳度状态"""

    event_type: PleasureType
    total_occurrences: int = 0
    recent_interval: float = 0.0  # 距离上次出现的字数间隔
    consecutive_count: int = 0  # 连续出现次数
    fatigue_level: FatigueLevel = FatigueLevel.FRESH
    decay_factor: float = 1.0  # 爽感衰减系数（1.0=无衰减，<1=衰减）

    def apply_decay(self, base_intensity: float) -> float:
        """应用疲劳衰减后的实际爽感强度"""
        return base_intensity * self.decay_factor


@dataclass
class PleasureReport:
    """爽点分析报告"""

    book_id: str
    chapter_id: str = ""
    events: list[PleasureEvent] = field(default_factory=list)
    total_events: int = 0
    density_per_1000: float = 0.0  # 每千字爽点密度
    type_distribution: dict[str, int] = field(default_factory=dict)
    fatigue_map: dict[str, TypeFatigue] = field(default_factory=dict)
    rhythm_score: float = 0.0  # 节奏评分 0-100
    golden_3_ok: bool = True  # 黄金三章节奏是否达标
    suggestions: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"爽点报告 [{self.chapter_id or self.book_id}]: "
            f"{self.total_events}个爽点, "
            f"密度{self.density_per_1000:.1f}/千字, "
            f"节奏{self.rhythm_score:.0f}/100"
        )


# ============================================================================
# 爽点关键词词典（12类，中文网文专属）
# ============================================================================

PLEASURE_KEYWORDS: dict[PleasureType, dict[str, list[str]]] = {
    PleasureType.FACE_SLAP: {
        "high": [
            "打脸",
            "啪啪打脸",
            "脸都肿了",
            "当众打脸",
            "方才还",
            "刚才还嘲讽",
            "现在傻眼了",
            "目瞪口呆",
            "难以置信地看着",
            "脸色铁青",
            "脸色一阵青一阵白",
            "悔得肠子都青了",
            "恨不得找个地缝",
            "无地自容",
        ],
        "medium": [
            "后悔了",
            "没想到",
            "居然",
            "怎么可能",
            "震惊了",
            "傻眼了",
            "愣住",
            "呆住了",
            "说不出话",
            "哑口无言",
            "脸色大变",
        ],
    },
    PleasureType.LEVEL_UP: {
        "high": [
            "突破",
            "晋级",
            "晋升",
            "破境",
            "渡劫成功",
            "瓶颈松动",
            "一朝突破",
            "厚积薄发",
            "水到渠成",
            "境界提升",
            "实力暴涨",
            "修为大增",
        ],
        "medium": [
            "提升了",
            "增强了",
            "变强了",
            "更进一步",
            "瓶颈",
            "关卡",
            "突破在即",
        ],
    },
    PleasureType.ACQUISITION: {
        "high": [
            "获得",
            "得到",
            "收获",
            "机缘",
            "奇遇",
            "天材地宝",
            "神器",
            "绝世功法",
            "传承",
            "洞府",
            "秘境",
            "宝藏",
            "灵药",
        ],
        "medium": [
            "捡到",
            "发现",
            "找到",
            "寻得",
            "入手",
            "宝物",
            "秘籍",
            "功法",
            "丹药",
        ],
    },
    PleasureType.OVERWHELM: {
        "high": [
            "碾压",
            "横扫",
            "秒杀",
            "一招击败",
            "一击必杀",
            "摧枯拉朽",
            "势如破竹",
            "无人能挡",
            "所向披靡",
            "以一敌百",
            "如入无人之境",
        ],
        "medium": [
            "轻松击败",
            "不费吹灰之力",
            "毫无还手之力",
            "碾压而过",
            "一路横扫",
        ],
    },
    PleasureType.REVEAL: {
        "high": [
            "身份暴露",
            "真实身份",
            "原来你是",
            "竟然是",
            "隐藏的实力",
            "深藏不露",
            "扮猪吃虎",
            "低调的",
            "真正的",
            "背后的人",
        ],
        "medium": [
            "露出",
            "展现出",
            "暴露了",
            "揭穿",
            "原来是",
            "居然是",
        ],
    },
    PleasureType.ROMANCE: {
        "high": [
            "心跳加速",
            "脸红",
            "耳根发烫",
            "小鹿乱撞",
            "暧昧",
            "柔情",
            "温柔",
            "宠溺",
            "心动",
            "四目相对",
            "近在咫尺",
            "呼吸可闻",
        ],
        "medium": [
            "微微一笑",
            "嘴角上扬",
            "目光柔和",
            "轻声道",
            "关心",
            "在意",
            "在意他",
        ],
    },
    PleasureType.REVENGE: {
        "high": [
            "报仇",
            "复仇",
            "血债血偿",
            "清算",
            "终于等到这一天",
            "大仇得报",
            "手刃仇人",
            "以牙还牙",
            "加倍奉还",
        ],
        "medium": [
            "报复",
            "算账",
            "讨回",
            "还债",
            "不会放过",
            "等着",
        ],
    },
    PleasureType.PROTECT: {
        "high": [
            "守护",
            "护短",
            "谁敢动他",
            "动他试试",
            "霸气护",
            "霸气回应",
            "霸气外露",
            "他是我的",
            "谁也不许",
            "不许碰",
        ],
        "medium": [
            "保护",
            "护着",
            "护在身后",
            "挡在前面",
            "站了出来",
        ],
    },
    PleasureType.SHOW_OFF: {
        "high": [
            "装逼",
            "显圣",
            "装逼打脸",
            "惊艳全场",
            "技惊四座",
            "万众瞩目",
            "全场哗然",
            "一鸣惊人",
            "大放异彩",
        ],
        "medium": [
            "展示",
            "展露",
            "显露",
            "秀",
            "露一手",
            "震惊全场",
            "惊艳",
        ],
    },
    PleasureType.TWIST: {
        "high": [
            "反转",
            "神转折",
            "峰回路转",
            "没想到",
            "居然是",
            "竟然是这样",
            "原来一切",
            "剧情反转",
            "出人意料",
        ],
        "medium": [
            "却",
            "然而",
            "但是",
            "不过",
            "没想到的是",
            "令人意外的是",
        ],
    },
    PleasureType.TOUCHING: {
        "high": [
            "泪目",
            "感动",
            "热泪盈眶",
            "泣不成声",
            "鼻子一酸",
            "心头一暖",
            "红了眼眶",
            "触动心弦",
            "感人至深",
        ],
        "medium": [
            "哭了",
            "流泪",
            "眼眶湿润",
            "感动不已",
            "心头一热",
        ],
    },
    PleasureType.HOT_BLOOD: {
        "high": [
            "热血沸腾",
            "燃",
            "战意",
            "燃起来了",
            "战意滔天",
            "无所畏惧",
            "勇往直前",
            "舍我其谁",
            "拼了",
            "死战",
        ],
        "medium": [
            "冲",
            "上",
            "杀",
            "战",
            "来吧",
            "热血",
            "燃烧",
            "斗志",
        ],
    },
}

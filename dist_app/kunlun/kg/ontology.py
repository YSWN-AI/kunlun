# ============================================================
# 昆仑创作引擎 — KG 本体定义 (Ontology)
# 定义所有实体类型、属性规范、关系类型和约束
# ============================================================

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ─── 枚举类型 ───────────────────────────────────────────


class ForeshadowingStatus(StrEnum):
    PLANTED = "planted"
    REVEALED = "revealed"
    ABANDONED = "abandoned"


class ArcStage(StrEnum):
    ORDINARY_WORLD = "ordinary_world"  # 平凡世界
    CALL_TO_ADVENTURE = "call"  # 冒险召唤
    REFUSAL = "refusal"  # 拒绝召唤
    MENTOR = "mentor"  # 遇见导师
    CROSSING = "crossing"  # 越过第一道门槛
    TESTS = "tests"  # 考验/盟友/敌人
    APPROACH = "approach"  # 接近最深处洞穴
    ORDEAL = "ordeal"  # 磨难
    REWARD = "reward"  # 报酬
    ROAD_BACK = "road_back"  # 返回的路
    RESURRECTION = "resurrection"  # 复活
    RETURN = "return"  # 携万能药回归


class PleasureType(StrEnum):
    SLAP_FACE = "slap_face"  # 打脸
    LEVEL_UP = "level_up"  # 升级/突破
    TREASURE = "treasure"  # 获得宝物/机缘
    REVENGE = "revenge"  # 复仇/清算
    REVELATION = "revelation"  # 真相揭露
    ROMANCE = "romance"  # 感情推进
    SHOW_OFF = "show_off"  # 扬名/展示实力


class CultivationRealm(StrEnum):
    """示例修炼体系，实际使用时由作者自定义"""

    DOU_ZHI_LI = "斗之力"
    DOU_ZHE = "斗者"
    DOU_SHI = "斗师"
    DA_DOU_SHI = "大斗师"
    DOU_LING = "斗灵"
    DOU_WANG = "斗王"
    DOU_HUANG = "斗皇"
    DOU_ZONG = "斗宗"
    DOU_ZUN = "斗尊"
    DOU_SHENG = "斗圣"
    DOU_DI = "斗帝"


# ─── 实体定义 ───────────────────────────────────────────


class BaseEntity(BaseModel):
    """所有KG实体的基类"""

    uid: str  # 唯一标识 (如 char_001, item_rune_sword)
    name: str  # 显示名
    description: str = ""  # 描述
    first_appearance_chapter: int = 0  # 首次出现章节
    last_modified_chapter: int = 0  # 最后修改章节
    # ⚠️ Pydantic v2 中 "metadata" 是 Field() 的保留参数，使用 extra_data 避免冲突
    extra_data: dict = Field(default_factory=dict, alias="meta_data")


class Character(BaseEntity):
    """角色"""

    aliases: list[str] = Field(default_factory=list)
    current_realm: CultivationRealm | None = None
    realm_timeline: list[dict] = Field(default_factory=list)
    # [{chapter: 1, realm: 斗者, stage: "三星"}, ...]

    personality_vector: list[float] = Field(default_factory=lambda: [0.5] * 12)
    # 12维: 勇敢/谨慎/智慧/冲动/善良/冷酷/幽默/严肃/外向/内向/果断/犹豫

    arc_stage: ArcStage = ArcStage.ORDINARY_WORLD
    arc_progress: float = 0.0  # 0.0-1.0

    is_alive: bool = True

    # 基础属性（可扩展）
    age: int | None = None
    gender: str | None = None
    role_type: str | None = None  # 主角/导师/对手/伙伴/情感线/配角/路人


class Location(BaseEntity):
    """地点"""

    location_type: str = ""  # 城市/秘境/学院/野外/...
    parent_location_uid: str | None = None
    current_state: str = ""  # 当前状态描述
    embedding_vector: list[float] | None = None  # 描述向量


class Item(BaseEntity):
    """物品"""

    item_type: str = ""  # 武器/丹药/功法/材料/信物/...
    grade: str = ""  # 品阶 (黄/玄/地/天 或自定义)
    owner_history: list[dict] = Field(default_factory=list)
    # [{character_uid: "char_001", from_chapter: 1, to_chapter: null}]
    abilities: list[str] = Field(default_factory=list)
    is_sealed: bool = False
    is_destroyed: bool = False


class Organization(BaseEntity):
    """组织/势力"""

    org_type: str = ""  # 宗门/家族/帝国/商会/...
    member_character_uids: list[str] = Field(default_factory=list)
    hostile_org_uids: list[str] = Field(default_factory=list)
    influence_scope: str = ""  # 势力范围描述


class Skill(BaseEntity):
    """技能/功法"""

    skill_type: str = ""  # 攻击/防御/身法/辅助/...
    grade: str = ""
    masters: list[dict] = Field(default_factory=list)
    # [{character_uid: "char_001", proficiency: "小成"}]
    evolution_of_uid: str | None = None  # 由哪个技能演化而来


class Event(BaseEntity):
    """事件"""

    event_type: str = ""  # 战斗/探索/社交/突破/交易/...
    involved_characters: list[str] = Field(default_factory=list)
    location_uid: str | None = None
    chapter_range: tuple[int, int] = (0, 0)
    impact_description: str = ""


class Foreshadowing(BaseEntity):
    """伏笔"""

    planted_chapter: int = 0
    content: str = ""
    expected_reveal_chapter: int | None = None
    actual_reveal_chapter: int | None = None
    status: ForeshadowingStatus = ForeshadowingStatus.PLANTED
    priority: int = 0  # 0-10, 越高越重要


class Knowledge(BaseEntity):
    """世界观知识"""

    category: str = ""  # 修炼体系/势力分布/历史/地理/...
    content: str = ""
    revealed_in_chapter: int | None = None
    reveal_percentage: float = 0.0  # 当前揭示比例
    is_retconned: bool = False  # 是否被吃书


class ChapterSnapshot(BaseEntity):
    """章节级 KG 快照"""

    chapter_number: int = 0
    snapshot_data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


# ─── 关系类型 ───────────────────────────────────────────

RELATIONSHIP_TYPES = {
    # Character ↔ Character
    "KNOWS": "认识",
    "TRUSTS": "信任(0-1)",
    "HOSTILE": "敌对(0-1)",
    "IN_LOVE_WITH": "爱慕",
    "MASTER_OF": "师徒(师傅→徒弟)",
    "SUBORDINATE_OF": "从属(从属→上级)",
    "FRIEND_OF": "朋友",
    "RIVAL_OF": "对手",
    "FAMILY_OF": "亲属",
    # Character ↔ Location
    "LOCATED_AT": "位于",
    # Character ↔ Item
    "POSSESSES": "拥有{from_chapter}-{to_chapter}",
    # Character ↔ Skill
    "KNOWS_SKILL": "掌握{proficiency}",
    # Character ↔ Event
    "INVOLVED_IN": "参与{role}",
    # Character ↔ Organization
    "MEMBER_OF": "属于{role}",
    # Location ↔ Location
    "PARENT_OF": "上级地点",
    # Organization ↔ Organization
    "HOSTILE_ORG": "敌对组织",
    # Skill ↔ Skill
    "EVOLUTION_OF": "演化自",
    # Event ↔ Location
    "HAPPENED_AT": "发生于",
    # Foreshadowing → Event/Character
    "PLANTED_FOR": "为...埋设",
    "REVEALED_BY": "由...揭示",
    # Knowledge ↔ Chapter
    "REVEALED_IN": "在...章揭示",
}

# ─── 约束规则 ───────────────────────────────────────────

CONSTRAINTS = {
    "unique_item_ownership": "同一物品同一时间只能被一个角色拥有",
    "realm_monotonic": "修为境界只能前进不能倒退（除非有明确事件解释）",
    "item_no_duplicate": "同名物品视为同一实体（通过别名匹配）",
    "location_continuity": "角色位置变化必须有过渡（除非有传送事件）",
    "foreshadowing_must_resolve": "伏笔必须在设定章节±5章内揭示，否则标记逾期",
    "character_death_final": "已标记死亡的角色的关系边自动标记 validTo",
}

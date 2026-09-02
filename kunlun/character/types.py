"""
昆仑创作引擎 — 角色设定类型定义

包含角色相关的枚举（Dramatica角色职能、弧线类型、关系类型等）
和数据类（CharacterProfile、CharacterDialogueStyle）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ══════════════════════════════════════════════════════
# 枚举定义
# ══════════════════════════════════════════════════════


class DramaticaRole(StrEnum):
    """Dramatica 7种角色职能"""

    PROTAGONIST = "protagonist"  # 主角 — 推动故事前进
    ANTAGONIST = "antagonist"  # 反派 — 与主角目标对立
    IMPACT = "impact_character"  # 冲击者 — 改变主角认知
    GUARDIAN = "guardian"  # 守护者 — 导师/引导者
    CONTAGONIST = "contagonist"  # 阻碍者 — 表面帮助实则拖延
    SIDEKICK = "sidekick"  # 伙伴 — 忠诚支持者
    SKEPTIC = "skeptic"  # 怀疑者 — 质疑与反面声音

    @property
    def label(self) -> str:
        _l = {
            "protagonist": "主角",
            "antagonist": "反派",
            "impact_character": "冲击者",
            "guardian": "守护者",
            "contagonist": "阻碍者",
            "sidekick": "伙伴",
            "skeptic": "怀疑者",
        }
        return _l.get(self.value, self.value)


class CharacterArcType(StrEnum):
    """角色弧线类型 — 网文特化版"""

    POSITIVE_CHANGE = "positive_change"  # 正向改变（凡人→英雄）
    FLAT_ARC = "flat_arc"  # 平稳弧线（主角改变世界）
    NEGATIVE_CHANGE = "negative_change"  # 负向改变（堕落/黑化）
    REDEMPTION = "redemption"  # 救赎弧线（罪人→救世主）
    CORRUPTION = "corruption"  # 腐化弧线（好人→反派）
    REVENGE = "revenge"  # 复仇弧线（网文经典）
    LEVEL_UP = "level_up"  # 升级弧线（修真/玄幻标配）
    MYSTERY_REVEAL = "mystery_reveal"  # 身份揭示弧线


class CharacterRole(StrEnum):
    """角色定位"""

    MAIN = "main"  # 主角
    DEUTERAGONIST = "deuteragonist"  # 第二主角/重要配角
    SUPPORTING = "supporting"  # 配角
    ANTAGONIST = "antagonist"  # 反派
    MENTOR = "mentor"  # 导师
    LOVE_INTEREST = "love_interest"  # 感情线
    COMIC_RELIEF = "comic_relief"  # 搞笑担当
    FOIL = "foil"  # 对比角色
    CAMEO = "cameo"  # 客串/工具人


class RelationshipType(StrEnum):
    """角色关系类型"""

    FAMILY = "family"  # 家族
    FRIEND = "friend"  # 朋友
    ROMANCE = "romance"  # 恋爱
    RIVAL = "rival"  # 对手
    ENEMY = "enemy"  # 敌人
    MASTER_STUDENT = "master_student"  # 师徒
    ALLIANCE = "alliance"  # 同盟
    BOSS_SUBORDINATE = "boss_subordinate"  # 上下级
    SAVIOR_SAVED = "savior_saved"  # 救命恩人
    BETRAYER_BETRAYED = "betrayer_betrayed"  # 背叛


# ══════════════════════════════════════════════════════
# 数据类
# ══════════════════════════════════════════════════════


@dataclass
class CharacterDialogueStyle:
    """角色对话风格 — 用于保持角色对话一致性"""

    character_id: str

    # 语言特征
    avg_sentence_length: float = 15.0
    common_words: list[str] = field(default_factory=list)
    catchphrases: list[str] = field(default_factory=list)  # 口头禅
    taboo_words: list[str] = field(default_factory=list)  # 从不说的词

    # 语气特征
    tone: str = "neutral"  # neutral/aggressive/gentle/sarcastic/cold/enthusiastic
    formality: str = "casual"  # casual/formal/archaic/vulgar
    sentence_patterns: list[str] = field(default_factory=list)  # 惯用句式

    # 对话习惯
    uses_rhetorical_questions: bool = False  # 反问句
    uses_proverbs: bool = False  # 引用古语
    interruption_frequency: float = 0.0  # 打断别人频率 (0-1)
    response_delay_tendency: str = "normal"  # normal/quick/slow

    def to_prompt_instruction(self, name: str) -> str:
        """生成注入 prompt 的对话指导"""
        parts = [f"{name}的对话风格："]

        if self.catchphrases:
            parts.append(f"口头禅：{'、'.join(self.catchphrases)}")
        if self.common_words:
            parts.append(f"常用词：{'、'.join(self.common_words[:5])}")
        if self.taboo_words:
            parts.append(f"从不说：{'、'.join(self.taboo_words)}")

        tone_map = {
            "aggressive": "语气强硬直接",
            "gentle": "语气温和婉转",
            "sarcastic": "带讽刺意味",
            "cold": "语气冷淡疏离",
            "enthusiastic": "语气热情洋溢",
            "neutral": "语气中性自然",
        }
        parts.append(tone_map.get(self.tone, "语气自然"))

        if self.uses_rhetorical_questions:
            parts.append("经常使用反问句")
        if self.uses_proverbs:
            parts.append("偶尔引用古语或成语")

        return "；".join(parts)


@dataclass
class CharacterProfile:
    """完整角色档案 — 整合分散模块的数据"""

    character_id: str
    name: str
    role: CharacterRole = CharacterRole.SUPPORTING
    dramatica_role: DramaticaRole | None = None

    # 基本信息
    age: str = ""
    gender: str = ""
    appearance: str = ""
    personality: list[str] = field(default_factory=list)
    background: str = ""

    # 能力设定
    abilities: list[str] = field(default_factory=list)
    power_level: str = ""  # 当前境界/等级
    special_items: list[str] = field(default_factory=list)

    # 弧线设定
    arc_type: CharacterArcType = CharacterArcType.POSITIVE_CHANGE
    arc_description: str = ""
    arc_stages: list[dict] = field(default_factory=list)  # [{stage, description, chapter_range}]
    inner_conflict: str = ""  # 内心冲突
    external_goal: str = ""  # 外部目标
    internal_need: str = ""  # 内在需求（Dramatica 双层需求）

    # 对话风格
    dialogue_style: CharacterDialogueStyle | None = None

    # 关系
    relationships: list[dict] = field(
        default_factory=list
    )  # [{target_id, type, strength, description}]

    # 元数据
    first_appearance_chapter: int = 0
    status: str = "active"  # active/dead/missing/retired

    def get_dialogue_instruction(self) -> str:
        """获取该角色的对话指导（注入 Writer prompt）"""
        if self.dialogue_style:
            return self.dialogue_style.to_prompt_instruction(self.name)
        return f"{self.name}：按角色设定自然对话"

    def get_arc_progress(self, current_chapter: int) -> dict:
        """获取当前弧线进度"""
        if not self.arc_stages:
            return {"stage": "未知", "progress_pct": 0}

        for stage in self.arc_stages:
            ch_range = stage.get("chapter_range", "0-0")
            try:
                start, end = map(int, ch_range.split("-"))
                if start <= current_chapter <= end:
                    progress = (current_chapter - start) / max(end - start, 1) * 100
                    return {"stage": stage.get("stage", ""), "progress_pct": round(progress)}
            except (ValueError, AttributeError):
                pass
        return {"stage": self.arc_stages[-1].get("stage", ""), "progress_pct": 100}

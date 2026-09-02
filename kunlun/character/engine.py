"""
昆仑创作引擎 — 角色引擎

深度融合 Dramatica 7角色职能 + StoryCraft Studio 角色关系图 + 网文角色弧线理论。

核心类:
  - CharacterArcEngine: 角色弧线引擎（Dramatica + Hero's Journey + 网文特化）
  - CharacterRelationshipGraph: 角色关系图（力导向+关系强度）
  - CharacterDialogueStyleAnalyzer: 角色对话风格分析
  - CharacterConsistencyChecker: 角色一致性检测（OOC检测）
  - CharacterEngine: 统一入口
"""

from __future__ import annotations

import re
from collections import Counter
from typing import ClassVar

from kunlun.character.types import (
    CharacterArcType,
    CharacterDialogueStyle,
    CharacterProfile,
    CharacterRole,
    RelationshipType,
)

# ══════════════════════════════════════════════════════
# CharacterArcEngine — 角色弧线引擎
# ══════════════════════════════════════════════════════


class CharacterArcEngine:
    """角色弧线引擎 — Dramatica 双层需求模型 + 网文升级弧线"""

    ARC_BLUEPRINTS: ClassVar[dict[CharacterArcType, dict]] = {
        CharacterArcType.LEVEL_UP: {
            "name": "升级弧线",
            "stages": [
                {"stage": "初始弱小", "pct": 10, "description": "展示主角的平凡/弱小状态"},
                {"stage": "首次突破", "pct": 25, "description": "获得金手指/首次突破，看到希望"},
                {"stage": "快速成长", "pct": 50, "description": "连续突破，但遇到瓶颈"},
                {"stage": "重大挫折", "pct": 65, "description": "遇到前所未有的强敌/困境"},
                {"stage": "觉醒突破", "pct": 80, "description": "领悟关键，突破瓶颈"},
                {"stage": "巅峰对决", "pct": 95, "description": "最终突破，登顶巅峰"},
            ],
            "typical_chapters": "100-500章",
            "webnovel_note": "网文最常见的弧线类型，每50-100章一次大突破",
        },
        CharacterArcType.REVENGE: {
            "name": "复仇弧线",
            "stages": [
                {"stage": "惨遭灭门/背叛", "pct": 5, "description": "触发复仇动机"},
                {"stage": "隐忍修炼", "pct": 35, "description": "隐藏身份，积累实力"},
                {"stage": "初次交锋", "pct": 55, "description": "与仇人初次接触，实力不足"},
                {"stage": "真相揭露", "pct": 75, "description": "发现复仇背后的更大真相"},
                {"stage": "最终复仇", "pct": 95, "description": "复仇成功/选择放下"},
            ],
            "typical_chapters": "50-200章",
            "webnovel_note": "常见于都市/玄幻开篇，注意避免复仇后空虚感",
        },
        CharacterArcType.POSITIVE_CHANGE: {
            "name": "正向改变",
            "stages": [
                {"stage": "普通状态", "pct": 15, "description": "展示缺点和局限"},
                {"stage": "被迫改变", "pct": 40, "description": "外部事件迫使改变"},
                {"stage": "挣扎适应", "pct": 65, "description": "在新旧自我之间挣扎"},
                {"stage": "完成蜕变", "pct": 90, "description": "成为更好的自己"},
            ],
            "typical_chapters": "50-200章",
            "webnovel_note": "Hero's Journey 的简化版，适合成长型主角",
        },
    }

    @classmethod
    def get_arc_blueprint(cls, arc_type: CharacterArcType) -> dict:
        return cls.ARC_BLUEPRINTS.get(
            arc_type, cls.ARC_BLUEPRINTS[CharacterArcType.POSITIVE_CHANGE]
        )

    @classmethod
    def get_current_stage(
        cls, arc_type: CharacterArcType, chapter_num: int, total_chapters: int
    ) -> dict:
        """获取角色当前弧线阶段"""
        blueprint = cls.get_arc_blueprint(arc_type)
        position_pct = (chapter_num / max(total_chapters, 1)) * 100

        current_stage = blueprint["stages"][0]
        for stage in blueprint["stages"]:
            if position_pct >= stage["pct"]:
                current_stage = stage
            else:
                break

        return {
            "arc_type": arc_type.value,
            "arc_name": blueprint["name"],
            "current_stage": current_stage["stage"],
            "stage_description": current_stage["description"],
            "progress_pct": round(position_pct),
            "next_stage": cls._get_next_stage(blueprint["stages"], current_stage),
        }

    @staticmethod
    def _get_next_stage(stages: list[dict], current: dict) -> dict | None:
        for i, stage in enumerate(stages):
            if stage == current and i + 1 < len(stages):
                return stages[i + 1]
        return None

    @classmethod
    def generate_arc_checklist(cls, character: CharacterProfile) -> list[str]:
        """生成角色弧线检查清单"""
        blueprint = cls.get_arc_blueprint(character.arc_type)
        checklist = [
            f"弧线类型：{blueprint['name']}",
            f"参考章节数：{blueprint.get('typical_chapters', '未指定')}",
        ]
        checklist.extend(
            f"- {stage['stage']}（约{stage['pct']}%）：{stage['description']}"
            for stage in blueprint["stages"]
        )
        if character.inner_conflict:
            checklist.append(f"内心冲突：{character.inner_conflict}")
        if character.external_goal:
            checklist.append(f"外部目标：{character.external_goal}")
        return checklist


# ══════════════════════════════════════════════════════
# CharacterRelationshipGraph — 角色关系图
# ══════════════════════════════════════════════════════


class CharacterRelationshipGraph:
    """角色关系图 — StoryCraft Studio 力导向图设计理念"""

    def __init__(self) -> None:
        self._relationships: dict[
            str, dict[str, dict]
        ] = {}  # {char_a: {char_b: {type, strength, ...}}}

    def add_relationship(
        self,
        char_a: str,
        char_b: str,
        rel_type: RelationshipType,
        strength: int = 0,
        description: str = "",
    ) -> None:
        """添加关系（双向自动同步）"""
        rel_data = {"type": rel_type.value, "strength": strength, "description": description}
        self._relationships.setdefault(char_a, {})[char_b] = rel_data
        self._relationships.setdefault(char_b, {})[char_a] = rel_data

    def get_relationship(self, char_a: str, char_b: str) -> dict | None:
        return self._relationships.get(char_a, {}).get(char_b)

    def get_all_relationships(self, char_id: str) -> dict[str, dict]:
        return self._relationships.get(char_id, {})

    def get_force_graph_data(self) -> dict:
        """生成力导向图数据"""
        nodes_set = set()
        edges = []

        for char_a, relations in self._relationships.items():
            nodes_set.add(char_a)
            for char_b, rel_data in relations.items():
                if char_a < char_b:  # 去重
                    edges.append(
                        {
                            "source": char_a,
                            "target": char_b,
                            "type": rel_data["type"],
                            "strength": rel_data["strength"],
                        }
                    )
                nodes_set.add(char_b)

        nodes = [{"id": n, "name": n} for n in nodes_set]
        return {"nodes": nodes, "edges": edges}

    def detect_conflicts(self) -> list[dict]:
        """检测角色间的冲突关系"""
        conflicts = []
        for char_a, relations in self._relationships.items():
            for char_b, rel_data in relations.items():
                if char_a < char_b and rel_data["type"] in ("enemy", "rival", "betrayer_betrayed"):
                    conflicts.append(
                        {
                            "char_a": char_a,
                            "char_b": char_b,
                            "type": rel_data["type"],
                            "strength": rel_data["strength"],
                        }
                    )
        return conflicts

    def find_love_polygons(self) -> list[list[str]]:
        """检测多角关系"""
        romance_map: dict[str, set[str]] = {}
        for char_a, relations in self._relationships.items():
            for char_b, rel_data in relations.items():
                if rel_data["type"] == "romance":
                    romance_map.setdefault(char_a, set()).add(char_b)

        return [
            [a, b, c]
            for a, targets in romance_map.items()
            for b in targets
            if b in romance_map
            for c in romance_map[b]
            if c != a and c in targets
        ]


# ══════════════════════════════════════════════════════
# CharacterDialogueStyleAnalyzer — 对话风格分析
# ══════════════════════════════════════════════════════


class CharacterDialogueStyleAnalyzer:
    """从角色对话文本中提取对话风格特征"""

    @staticmethod
    def analyze(dialogues: list[str]) -> CharacterDialogueStyle:
        """从对话样本中分析角色对话风格"""
        if not dialogues:
            return CharacterDialogueStyle(character_id="unknown")

        lengths = [len(d) for d in dialogues]
        avg_len = sum(lengths) / len(lengths)

        all_words: list[str] = []
        for d in dialogues:
            for i in range(len(d) - 1):
                bigram = d[i : i + 2]
                if re.match(r"[\u4e00-\u9fff]{2}", bigram):
                    all_words.append(bigram)

        word_counter = Counter(all_words)
        common_words = [w for w, _ in word_counter.most_common(10)]
        catchphrases = [w for w, c in word_counter.most_common(20) if c >= 3 and len(w) >= 3]
        tone = CharacterDialogueStyleAnalyzer._detect_tone(dialogues)
        rhetorical = sum(
            1 for d in dialogues if d.rstrip().endswith("？") or "难道" in d or "岂" in d
        )
        uses_rhetorical = rhetorical > len(dialogues) * 0.15

        return CharacterDialogueStyle(
            character_id="",
            avg_sentence_length=round(avg_len, 1),
            common_words=common_words[:5],
            catchphrases=catchphrases[:3],
            tone=tone,
            uses_rhetorical_questions=uses_rhetorical,
        )

    @staticmethod
    def _detect_tone(dialogues: list[str]) -> str:
        """检测语气"""
        aggressive_kw = ["杀", "死", "滚", "闭嘴", "放肆", "找死"]
        gentle_kw = ["谢谢", "请", "好", "呢", "吧", "呀", "啊"]
        cold_kw = ["哼", "呵", "不过如此", "无聊"]
        sarcastic_kw = ["呵呵", "是吗", "有趣", "真是"]

        scores = {"aggressive": 0, "gentle": 0, "cold": 0, "sarcastic": 0}
        for d in dialogues:
            for kw in aggressive_kw:
                if kw in d:
                    scores["aggressive"] += 1
            for kw in gentle_kw:
                if kw in d:
                    scores["gentle"] += 1
            for kw in cold_kw:
                if kw in d:
                    scores["cold"] += 1
            for kw in sarcastic_kw:
                if kw in d:
                    scores["sarcastic"] += 1

        return max(scores, key=lambda k: scores[k]) if max(scores.values()) > 0 else "neutral"


# ══════════════════════════════════════════════════════
# CharacterConsistencyChecker — OOC检测
# ══════════════════════════════════════════════════════


class CharacterConsistencyChecker:
    """角色一致性检测 — 检测角色言行是否符合设定"""

    def __init__(self) -> None:
        self._profiles: dict[str, CharacterProfile] = {}

    def register_character(self, profile: CharacterProfile) -> None:
        self._profiles[profile.character_id] = profile

    def check_dialogue_consistency(self, character_id: str, dialogue: str) -> list[str]:
        """检查角色对话是否与其设定一致"""
        profile = self._profiles.get(character_id)
        if not profile:
            return [f"未找到角色 '{character_id}' 的设定"]

        issues = []

        if profile.dialogue_style and profile.dialogue_style.taboo_words:
            issues.extend(
                f"角色'{profile.name}'说出了禁忌词'{word}'"
                for word in profile.dialogue_style.taboo_words
                if word in dialogue
            )

        if profile.personality:
            issues.extend(self._check_personality_consistency(profile, dialogue))

        if profile.dialogue_style and profile.dialogue_style.catchphrases:
            catchphrase_used = any(cp in dialogue for cp in profile.dialogue_style.catchphrases)
            if not catchphrase_used and len(dialogue) > 30:
                issues.append(f"角色'{profile.name}'在本段对话中未使用任何口头禅")

        return issues

    @staticmethod
    def _check_personality_consistency(profile: CharacterProfile, text: str) -> list[str]:
        """检查性格一致性"""
        issues = []
        personality_map = {
            "冷酷": {"should_not_say": ["谢谢", "对不起", "请", "拜托", "好开心"]},
            "善良": {"should_not_say": ["去死", "活该", "废物"]},
            "高傲": {"should_not_say": ["求求你", "拜托", "饶命"]},
        }
        for trait in profile.personality:
            if trait in personality_map:
                issues.extend(
                    f"角色'{profile.name}'（{trait}）说出了不符合性格的词'{word}'"
                    for word in personality_map[trait]["should_not_say"]
                    if word in text
                )
        return issues

    def check_ability_consistency(self, character_id: str, text: str) -> list[str]:
        """检查能力一致性"""
        profile = self._profiles.get(character_id)
        if not profile:
            return []

        issues = []
        ability_keywords = ["释放", "施展", "使用", "发动", "祭出", "催动"]
        for akw in ability_keywords:
            for match in re.finditer(
                rf"{akw}([\u4e00-\u9fff]{{2,6}}(?:术|法|诀|功|技|剑|刀|掌))", text
            ):
                ability = match.group(1)
                if ability not in profile.abilities and profile.abilities:
                    issues.append(f"角色'{profile.name}'使用了未设定的能力'{ability}'")
        return issues

    def full_check(self, character_id: str, dialogue: str, narration: str = "") -> dict:
        """全面一致性检查"""
        dialogue_issues = self.check_dialogue_consistency(character_id, dialogue)
        ability_issues = self.check_ability_consistency(character_id, narration or dialogue)
        return {
            "character_id": character_id,
            "total_issues": len(dialogue_issues) + len(ability_issues),
            "dialogue_issues": dialogue_issues,
            "ability_issues": ability_issues,
            "is_consistent": len(dialogue_issues) == 0 and len(ability_issues) == 0,
        }


# ══════════════════════════════════════════════════════
# CharacterEngine — 角色引擎主入口
# ══════════════════════════════════════════════════════


class CharacterEngine:
    """角色引擎 — 整合所有角色相关能力的统一入口"""

    def __init__(self) -> None:
        self.profiles: dict[str, CharacterProfile] = {}
        self.arc_engine = CharacterArcEngine()
        self.relationship_graph = CharacterRelationshipGraph()
        self.dialogue_analyzer = CharacterDialogueStyleAnalyzer()
        self.consistency_checker = CharacterConsistencyChecker()

    def register_character(self, profile: CharacterProfile) -> None:
        self.profiles[profile.character_id] = profile
        self.consistency_checker.register_character(profile)

    def get_character(self, character_id: str) -> CharacterProfile | None:
        return self.profiles.get(character_id)

    def list_characters(self, role: CharacterRole | None = None) -> list[CharacterProfile]:
        result = list(self.profiles.values())
        if role:
            result = [p for p in result if p.role == role]
        return result

    def get_all_dialogue_instructions(self) -> str:
        """获取所有角色的对话指导（注入 Writer prompt）"""
        return "\n".join(
            profile.get_dialogue_instruction()
            for profile in self.profiles.values()
            if profile.role
            in (CharacterRole.MAIN, CharacterRole.DEUTERAGONIST, CharacterRole.ANTAGONIST)
        )

    def get_cast_summary(self) -> dict:
        return {
            "total": len(self.profiles),
            "by_role": {role.value: len(self.list_characters(role)) for role in CharacterRole},
            "main_characters": [p.name for p in self.list_characters(CharacterRole.MAIN)],
            "antagonists": [p.name for p in self.list_characters(CharacterRole.ANTAGONIST)],
        }

    def build_context_for_chapter(self, character_ids: list[str]) -> str:
        """为章节生成角色上下文（注入 prompt）"""
        lines = ["## 当前章节出场角色\n"]
        for cid in character_ids:
            profile = self.profiles.get(cid)
            if not profile:
                continue
            lines.append(f"### {profile.name}（{profile.role.value}）")
            if profile.personality:
                lines.append(f"- 性格：{'、'.join(profile.personality)}")
            if profile.abilities:
                lines.append(f"- 能力：{'、'.join(profile.abilities[:5])}")
            if profile.dialogue_style:
                lines.append(
                    f"- 对话：{profile.dialogue_style.to_prompt_instruction(profile.name)}"
                )
            relations = self.relationship_graph.get_all_relationships(cid)
            if relations:
                rel_strs = [f"{name}({data['type']})" for name, data in list(relations.items())[:3]]
                lines.append(f"- 关系：{'、'.join(rel_strs)}")
            lines.append("")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════
# 模块级便捷实例
# ══════════════════════════════════════════════════════

character_engine = CharacterEngine()

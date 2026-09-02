"""
A组: 角色一致性 (A1-A8) — 记忆、性格、外貌、能力、位置、关系、情感、对话风格
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .._base33 import DimResult


class Auditor33GroupA:
    """A组: 角色一致性 mixin"""

    _truth_manager: Any | None = None

    def _check_A1_character_memory(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        knowledge_pattern = re.findall(
            r"(?:知道|记得|想起|回忆起|想起来)(?:了)?[，,]?\s*(.{5,50})", draft
        )
        issues = [
            f"角色记忆回溯未验证: {k[:30]}"
            for k in knowledge_pattern
            if any(w in k for w in ["前世", "穿越前", "系统", "之前", "曾经"])
        ]

        if self._truth_manager:
            char_matrix = self._truth_manager.get("character_matrix")
            interactions = char_matrix.get("interactions", [])
            for interaction in interactions:
                info_transferred = interaction.get("info_transferred", [])
                char_a = interaction.get("char_a", "")
                for info in info_transferred:
                    if info in draft and char_a in draft:
                        pass

        if issues:
            return DimResult(
                "A1",
                "角色记忆",
                60,
                "WARN",
                f"记忆回溯需验证: {'; '.join(issues[:3])}",
                '确保角色只"记得"其亲眼所见或被告知的信息',
                False,
            )
        return DimResult("A1", "角色记忆", 95, "PASS", "角色记忆边界正常")

    def _check_A2_character_personality(
        self, draft: str, _chapter: int, _blueprint: dict
    ) -> DimResult:
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            issues = []
            for name, data in chars.items():
                if name in draft and "personality" in data:
                    personality = data.get("personality", [])
                    if "冷静" in personality:
                        anger_kw = ["怒吼", "咆哮", "暴怒", "怒喝"]
                        for kw in anger_kw:
                            if kw in draft:
                                idx = draft.find(kw)
                                context = draft[max(0, idx - 50) : idx + 50]
                                if name in context:
                                    issues.append(f"{name} 性格矛盾: 设定为冷静但出现{kw}行为")
                                    break
                    if "温柔" in personality:
                        violent_kw = ["杀", "斩", "打", "踢", "踹"]
                        for kw in violent_kw:
                            if kw in draft:
                                idx = draft.find(kw)
                                context = draft[max(0, idx - 50) : idx + 50]
                                if name in context:
                                    issues.append(
                                        f"{name} 性格矛盾: 设定为温柔但出现暴力行为({kw})"
                                    )
                                    break
            if issues:
                return DimResult(
                    "A2",
                    "性格一致性",
                    55,
                    "WARN",
                    f"发现{len(issues)}处性格矛盾: {'; '.join(issues[:2])}",
                    "检查角色行为是否符合设定性格标签",
                    False,
                )

        return DimResult("A2", "性格一致性", 90, "PASS", "角色行为与设定一致")

    def _check_A3_appearance(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        appearance_refs = re.findall(
            r"(?:头发|眼眸|眼睛|瞳孔|皮肤|身材|身高|体型|面容|脸)(.{5,30})", draft
        )
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            issues = []
            for name, data in chars.items():
                if name in draft and "appearance" in data:
                    stored_appearance = data.get("appearance", {})
                    hair_color = stored_appearance.get("hair", "")
                    eye_color = stored_appearance.get("eyes", "")
                    if hair_color and hair_color in ["黑", "黑色", "黑发"]:
                        for alt in ["白发", "白发苍苍", "银发"]:
                            if alt in draft:
                                idx = draft.find(alt)
                                context = draft[max(0, idx - 30) : idx + 30]
                                if name in context:
                                    issues.append(
                                        f"{name} 外貌矛盾: 已记录为{hair_color}但出现{alt}"
                                    )
                    if eye_color and eye_color in ["黑", "黑色", "黑瞳"]:
                        for alt in ["蓝眸", "金瞳", "红眼", "紫瞳"]:
                            if alt in draft:
                                idx = draft.find(alt)
                                context = draft[max(0, idx - 30) : idx + 30]
                                if name in context and not any(name in iss for iss in issues):
                                    issues.append(
                                        f"{name} 外貌矛盾: 已记录为{eye_color}但出现{alt}"
                                    )
            if issues:
                return DimResult(
                    "A3",
                    "外貌一致性",
                    45,
                    "WARN",
                    f"发现{len(issues)}处外貌矛盾",
                    "确认外貌变化是否有剧情合理依据(如突破/受伤)",
                    False,
                )

        detail = (
            f"检测到{len(appearance_refs)}处外貌描写"
            if appearance_refs
            else "无新外貌描写,一致性正常"
        )
        return DimResult("A3", "外貌一致性", 92, "PASS", detail)

    def _check_A4_ability_consistency(
        self, draft: str, _chapter: int, _blueprint: dict
    ) -> DimResult:
        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            issues = []
            for name, data in chars.items():
                if name in draft and "abilities" in data:
                    known_abilities = set(data.get("abilities", []))
                    ability_patterns = re.findall(
                        r"(?:施展|使用|发动|释放|激活)(?:了)?(?:出)?([一-鿿]{2,6}(?:术|法|功|诀|剑|掌|拳|指|刀))",
                        draft,
                    )
                    issues.extend(
                        f"{name} 使用了未记录的能力: {ability}"
                        for ability in ability_patterns
                        if ability not in known_abilities
                    )
            if issues:
                return DimResult(
                    "A4",
                    "能力一致性",
                    40,
                    "WARN",
                    f"发现{len(issues)}个未记录能力: {'; '.join(issues[:3])}",
                    "确认能力是否在前文已获得,或添加获得场景",
                    False,
                )

        return DimResult("A4", "能力一致性", 90, "PASS", "能力使用与记录一致")

    def _check_A5_location(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        locations = set(
            re.findall(
                r"(?:在|到|去|来|抵达|进入)(?:了)?([一-鿿]{2,4}(?:城|镇|山|宗|府|楼|店|市|国|界|域|谷|林|海|殿|宫))",
                draft,
            )
        )

        if self._truth_manager:
            state = self._truth_manager.get("current_state")
            chars = state.get("characters", {})
            issues = []
            for name, data in chars.items():
                stored_loc = data.get("location", "")
                if not stored_loc or name not in draft:
                    continue
                for loc in locations:
                    if loc != stored_loc:
                        idx = draft.find(loc)
                        context = draft[max(0, idx - 40) : idx + 40]
                        if name in context:
                            move_patterns = [
                                f"{name}.*?(?:到了|来到|抵达|进入){loc}",
                                f"(?:来到|到了|抵达|进入).*?{loc}.*?{name}",
                            ]
                            has_transition = any(re.search(pat, context) for pat in move_patterns)
                            if not has_transition and stored_loc not in context:
                                issues.append(
                                    f'{name} 位置异常: 记录在"{stored_loc}"但出现在"{loc}"附近'
                                )
            if issues:
                return DimResult(
                    "A5",
                    "位置一致性",
                    50,
                    "WARN",
                    f"位置矛盾: {'; '.join(issues[:2])}",
                    "添加从旧位置到新位置的过渡描述",
                    False,
                )

        return DimResult(
            "A5",
            "位置一致性",
            95,
            "PASS",
            f"涉及{len(locations)}个地点,位置关系正常" if locations else "无明确地点切换",
        )

    def _check_A6_relationship(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            char_matrix = self._truth_manager.get("character_matrix")
            interactions = char_matrix.get("interactions", [])
            issues = []

            for inter in interactions:
                if inter.get("type") == "enemy":
                    a, b = inter.get("char_a", ""), inter.get("char_b", "")
                    if a and b and a in draft and b in draft:
                        friendly_kw = ["握手", "拥抱", "笑道", "微笑", "信任", "亲密"]
                        for kw in friendly_kw:
                            idx = draft.find(kw)
                            if idx >= 0:
                                context = draft[max(0, idx - 50) : idx + 50]
                                if a in context and b in context:
                                    issues.append(f"{a}对{b}(敌对关系)出现{kw}行为")

            if issues:
                return DimResult(
                    "A6",
                    "关系一致性",
                    55,
                    "WARN",
                    f"关系矛盾: {'; '.join(issues[:2])}",
                    "确认关系变化是否有剧情合理依据",
                    False,
                )

        return DimResult("A6", "关系一致性", 90, "PASS", "角色关系与记录一致")

    def _check_A7_emotional_state(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            arcs = self._truth_manager.get("emotional_arcs")
            arc_data = arcs.get("arcs", {})
            issues = []

            for name, data in arc_data.items():
                if name not in draft:
                    continue
                points = data.get("points", [])
                if not points:
                    continue
                last_emotion = points[-1].get("emotion", "")
                intensity = points[-1].get("intensity", 0.5)

                negative_high = last_emotion in ["fear", "anger", "sadness"] and intensity > 0.7
                if negative_high:
                    positive_kw = ["欢笑", "欣喜", "快乐", "心满意足", "兴高采烈"]
                    for kw in positive_kw:
                        if kw in draft:
                            idx = draft.find(kw)
                            context = draft[max(0, idx - 50) : idx + 50]
                            if name in context:
                                issues.append(
                                    f"{name} 情绪跳跃: 上一章为{last_emotion}(强度{intensity})"
                                    f",本章出现{kw}"
                                )

            if issues:
                return DimResult(
                    "A7",
                    "情绪状态",
                    60,
                    "WARN",
                    f"情绪突跳: {'; '.join(issues[:2])}",
                    "为情绪变化添加触发事件作为过渡",
                    False,
                )

        return DimResult("A7", "情绪状态", 85, "PASS", "情绪过渡自然")

    def _check_A8_dialogue_style(self, draft: str, _chapter: int, _blueprint: dict) -> DimResult:
        dialogue_by_char = {}
        for m in re.finditer(
            r'(?:^|。|！|？|"|」)([一-鿿]{2,4})(?:说道|喊道|问道|笑道|怒道|淡淡道|冷声道|道|说)',
            draft,
        ):
            name = m.group(1)
            end = min(m.end() + 50, len(draft))
            if name not in dialogue_by_char:
                dialogue_by_char[name] = []
            dialogue_by_char[name].append(draft[m.end() : end])

        if len(dialogue_by_char) >= 2:
            avg_lens = {
                n: sum(len(d) for d in ds) / len(ds) for n, ds in dialogue_by_char.items() if ds
            }
            if len(avg_lens) >= 2:
                lens = avg_lens.values()
                if max(lens) - min(lens) < 10 and max(lens) > 30:
                    return DimResult(
                        "A8",
                        "对话风格",
                        60,
                        "WARN",
                        "多个角色对话长度高度相近,缺乏个性化",
                        "为不同角色添加独特的口癖、句式、语气词",
                        True,
                    )

            tags = re.findall(
                r"(?:说道|喊道|问道|笑道|怒道|淡淡道|冷声道|低声道|高声道|厉声道|喝道)", draft
            )
            if tags:
                tag_counter = Counter(tags)
                dominant_tag = tag_counter.most_common(1)[0]
                if dominant_tag[1] / len(tags) > 0.6:
                    return DimResult(
                        "A8",
                        "对话风格",
                        65,
                        "WARN",
                        f'对话标签过于单一: "{dominant_tag[0]}"'
                        f"占比{dominant_tag[1] / len(tags):.0%}",
                        '丰富对话标签,用动作/神情代替"XX道"',
                        True,
                    )

        return DimResult("A8", "对话风格", 88, "PASS", "角色对话风格区分度良好")

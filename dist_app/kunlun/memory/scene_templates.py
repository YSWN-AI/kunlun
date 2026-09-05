"""
昆仑创作引擎 — 场景模板库与爽点模式 (L4 程序记忆增强)

为程序记忆提供结构化的场景模板库和爽点模式库，支持：
  - 7 类场景模板（战斗/对话/揭示/转折/高潮/描写/内心）
  - 15 个预设爽点模式
  - 基于场景类型和上下文关键词的模板推荐
  - 从已写章节自动提取模式（纯规则：关键词+句式+段落结构）
  - 模板使用效果记录与更新
  - 序列化/反序列化

纯规则零 LLM，无外部服务依赖。

Author: 昆仑创作引擎
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# ══════════════════════════════════════════════════════
# 场景类型常量
# ══════════════════════════════════════════════════════


class SceneType:
    """场景类型常量"""

    BATTLE = "battle"  # 战斗
    DIALOGUE = "dialogue"  # 对话
    REVELATION = "revelation"  # 揭示
    TRANSITION = "transition"  # 转折
    CLIMAX = "climax"  # 高潮
    DESCRIPTION = "description"  # 描写
    INTROSPECTION = "introspection"  # 内心

    ALL_TYPES = [BATTLE, DIALOGUE, REVELATION, TRANSITION, CLIMAX, DESCRIPTION, INTROSPECTION]


# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


@dataclass
class SceneTemplate:
    """场景模板"""

    id: str
    name: str
    scene_type: str  # SceneType 常量
    structure_steps: list[str] = field(default_factory=list)  # 结构步骤
    pacing_notes: str = ""  # 节奏建议
    trope_ids: list[str] = field(default_factory=list)  # 关联套路 ID
    effectiveness: float = 0.5  # 效果评分 0-1
    usage_count: int = 0
    keywords: list[str] = field(default_factory=list)  # 匹配关键词

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SceneTemplate:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PleasurePoint:
    """爽点模式"""

    id: str
    name: str
    description: str
    trigger_conditions: list[str] = field(default_factory=list)
    structure: list[str] = field(default_factory=list)
    effectiveness: float = 0.5
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)  # 匹配关键词

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PleasurePoint:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ══════════════════════════════════════════════════════
# 场景模板库
# ══════════════════════════════════════════════════════


class SceneTemplateLibrary:
    """场景模板库 — 场景模板 + 爽点模式 + 模式提取"""

    def __init__(self):
        self.templates: dict[str, SceneTemplate] = {}
        self.pleasure_points: dict[str, PleasurePoint] = {}
        self._type_index: dict[str, list[str]] = {}  # scene_type -> [template_ids]

    # ── 模板管理 ──────────────────────────────────────

    def add_template(self, template: SceneTemplate):
        """添加场景模板"""
        self.templates[template.id] = template
        self._type_index.setdefault(template.scene_type, []).append(template.id)

    def get_template(self, template_id: str) -> SceneTemplate | None:
        """获取指定模板"""
        return self.templates.get(template_id)

    def get_templates_by_type(self, scene_type: str) -> list[SceneTemplate]:
        """按场景类型获取模板"""
        ids = self._type_index.get(scene_type, [])
        return [self.templates[i] for i in ids if i in self.templates]

    def get_recommended_templates(
        self,
        scene_type: str,
        context_keywords: list[str] | None = None,
        limit: int = 3,
    ) -> list[SceneTemplate]:
        """基于场景类型和上下文关键词推荐模板

        评分 = effectiveness * 0.5 + 关键词匹配度 * 0.3 + usage_count归一化 * 0.2
        """
        candidates = self.get_templates_by_type(scene_type)
        if not candidates:
            # 类型不匹配时返回全部模板中效果最高的
            candidates = list(self.templates.values())

        scored: list[tuple[float, SceneTemplate]] = []
        max_usage = max((t.usage_count for t in candidates), default=1)

        for t in candidates:
            score = t.effectiveness * 0.5
            # 关键词匹配
            if context_keywords and t.keywords:
                matches = sum(1 for kw in context_keywords if kw in t.keywords)
                keyword_score = matches / max(len(t.keywords), 1)
                score += keyword_score * 0.3
            # 使用次数归一化
            usage_score = (t.usage_count / max_usage) if max_usage > 0 else 0
            score += usage_score * 0.2
            scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]

    def record_template_usage(self, template_id: str, success: bool = True):
        """记录模板使用情况并更新 effectiveness"""
        t = self.templates.get(template_id)
        if t:
            t.usage_count += 1
            if success:
                t.effectiveness = min(1.0, t.effectiveness + 0.02)
            else:
                t.effectiveness = max(0.0, t.effectiveness - 0.05)

    # ── 爽点模式管理 ──────────────────────────────────

    def get_pleasure_points(self, limit: int = 10) -> list[PleasurePoint]:
        """获取爽点模式（按效果排序）"""
        points = sorted(self.pleasure_points.values(), key=lambda p: p.effectiveness, reverse=True)
        return points[:limit]

    def get_pleasure_point(self, point_id: str) -> PleasurePoint | None:
        """获取指定爽点模式"""
        return self.pleasure_points.get(point_id)

    # ── 从章节提取模式（纯规则） ──────────────────────

    def extract_patterns_from_chapter(
        self, chapter_text: str, chapter_num: int = 0
    ) -> dict[str, Any]:
        """从已写章节自动提取模式（纯规则：关键词匹配+句式分析+段落结构分析）

        Args:
            chapter_text: 章节正文
            chapter_num: 章节号

        Returns:
            含 matched_templates, matched_pleasure_points, scene_type_scores, analysis 的字典
        """
        result: dict[str, Any] = {
            "chapter": chapter_num,
            "matched_templates": [],
            "matched_pleasure_points": [],
            "scene_type_scores": {},
            "analysis": {},
        }

        if not chapter_text or len(chapter_text) < 10:
            return result

        text_length = len(chapter_text)
        paragraphs = [p.strip() for p in chapter_text.split("\n") if p.strip()]
        paragraph_count = len(paragraphs)

        # 句式分析
        short_sentences = len(re.findall(r"[。！？!?]", chapter_text))
        exclamation_count = chapter_text.count("！") + chapter_text.count("!")
        question_count = chapter_text.count("？") + chapter_text.count("?")
        dialogue_count = len(re.findall(r'[""「『].*?[""」』]', chapter_text, re.DOTALL))

        # 段落结构分析
        avg_paragraph_len = text_length / max(paragraph_count, 1)

        result["analysis"] = {
            "text_length": text_length,
            "paragraph_count": paragraph_count,
            "avg_paragraph_length": round(avg_paragraph_len, 1),
            "short_sentence_count": short_sentences,
            "exclamation_count": exclamation_count,
            "question_count": question_count,
            "dialogue_count": dialogue_count,
        }

        # 场景类型评分（关键词 + 结构特征）
        type_scores = self._score_scene_types(
            chapter_text, exclamation_count, dialogue_count, avg_paragraph_len
        )
        result["scene_type_scores"] = type_scores

        # 匹配模板
        for t in self.templates.values():
            match_score = self._match_template(t, chapter_text, type_scores)
            if match_score > 0.3:
                result["matched_templates"].append(
                    {
                        "template_id": t.id,
                        "name": t.name,
                        "scene_type": t.scene_type,
                        "match_score": round(match_score, 3),
                    }
                )
        result["matched_templates"].sort(key=lambda x: x["match_score"], reverse=True)

        # 匹配爽点模式
        for pp in self.pleasure_points.values():
            match_score = self._match_pleasure_point(pp, chapter_text)
            if match_score > 0.2:
                result["matched_pleasure_points"].append(
                    {
                        "point_id": pp.id,
                        "name": pp.name,
                        "match_score": round(match_score, 3),
                    }
                )
        result["matched_pleasure_points"].sort(key=lambda x: x["match_score"], reverse=True)

        return result

    def _score_scene_types(
        self,
        text: str,
        exclamation_count: int,
        dialogue_count: int,
        avg_paragraph_len: float,
    ) -> dict[str, float]:
        """对7种场景类型进行评分"""
        scores: dict[str, float] = {}

        # 战斗：动作词 + 感叹号多 + 短句
        battle_keywords = [
            "战",
            "斗",
            "攻",
            "击",
            "杀",
            "斩",
            "拳",
            "剑",
            "招",
            "势",
            "轰",
            "爆",
            "挡",
            "避",
            "退",
            "冲",
            "撞",
        ]
        battle_score = sum(1 for kw in battle_keywords if kw in text) / len(battle_keywords)
        battle_score += min(exclamation_count / 10, 0.3)
        scores[SceneType.BATTLE] = min(battle_score, 1.0)

        # 对话：引号多 + 对话动词
        dialogue_keywords = ["说", "道", "问", "答", "喊", "叫", "笑", "怒", "叹", "低语", "沉声"]
        dialogue_score = sum(1 for kw in dialogue_keywords if kw in text) / len(dialogue_keywords)
        dialogue_score += min(dialogue_count / 5, 0.4)
        scores[SceneType.DIALOGUE] = min(dialogue_score, 1.0)

        # 揭示：秘密/真相/身份相关词
        revelation_keywords = [
            "原来",
            "竟然",
            "居然",
            "真相",
            "秘密",
            "身份",
            "揭开",
            "揭晓",
            "隐藏",
            "隐瞒",
            "露出",
            "显露",
            "恍然大悟",
        ]
        revelation_score = sum(1 for kw in revelation_keywords if kw in text) / len(
            revelation_keywords
        )
        scores[SceneType.REVELATION] = min(revelation_score, 1.0)

        # 转折：但是/然而/突然/却
        transition_keywords = [
            "但是",
            "然而",
            "突然",
            "却",
            "不料",
            "谁知",
            "就在",
            "此刻",
            "变故",
            "转折",
        ]
        transition_score = sum(1 for kw in transition_keywords if kw in text) / len(
            transition_keywords
        )
        scores[SceneType.TRANSITION] = min(transition_score, 1.0)

        # 高潮：最强/终极/终于/极限 + 感叹号
        climax_keywords = [
            "最强",
            "终极",
            "终于",
            "极限",
            "巅峰",
            "全力",
            "拼命",
            "最后",
            "决一",
            "生死",
            "爆发",
        ]
        climax_score = sum(1 for kw in climax_keywords if kw in text) / len(climax_keywords)
        climax_score += min(exclamation_count / 8, 0.3)
        scores[SceneType.CLIMAX] = min(climax_score, 1.0)

        # 描写：长段落 + 形容词/环境词
        description_keywords = [
            "宛如",
            "犹如",
            "仿佛",
            "似乎",
            "笼罩",
            "弥漫",
            "矗立",
            "蜿蜒",
            "巍峨",
            "壮阔",
            "美丽",
            "绚烂",
        ]
        description_score = sum(1 for kw in description_keywords if kw in text) / len(
            description_keywords
        )
        description_score += min(avg_paragraph_len / 200, 0.3)
        scores[SceneType.DESCRIPTION] = min(description_score, 1.0)

        # 内心：心理/想法/感受词
        introspection_keywords = [
            "心想",
            "暗道",
            "不禁",
            "心中",
            "内心",
            "思绪",
            "念头",
            "想法",
            "感受",
            "回忆",
            "记忆",
            "感慨",
        ]
        introspection_score = sum(1 for kw in introspection_keywords if kw in text) / len(
            introspection_keywords
        )
        scores[SceneType.INTROSPECTION] = min(introspection_score, 1.0)

        return scores

    def _match_template(
        self, template: SceneTemplate, text: str, type_scores: dict[str, float]
    ) -> float:
        """计算模板与文本的匹配度"""
        score = 0.0
        # 场景类型匹配
        type_score = type_scores.get(template.scene_type, 0)
        score += type_score * 0.5
        # 关键词匹配
        if template.keywords:
            matches = sum(1 for kw in template.keywords if kw in text)
            score += (matches / len(template.keywords)) * 0.5
        return min(score, 1.0)

    def _match_pleasure_point(self, pp: PleasurePoint, text: str) -> float:
        """计算爽点模式与文本的匹配度"""
        if not pp.keywords:
            return 0.0
        matches = sum(1 for kw in pp.keywords if kw in text)
        return matches / len(pp.keywords)

    # ── 默认模板加载 ──────────────────────────────────

    def load_default_templates(self):
        """加载预设场景模板（每类至少2个，共14+个）"""
        defaults = [
            # ── 战斗类 ──
            SceneTemplate(
                id="tpl_battle_duel",
                name="单挑对决",
                scene_type=SceneType.BATTLE,
                structure_steps=["对峙铺垫", "第一招试探", "招式升级", "大招对决", "胜负揭晓"],
                pacing_notes="前慢后快，试探阶段用中长句，对决阶段短句密集，每3句一个转折",
                trope_ids=["trope_face_slap", "trope_underdog"],
                effectiveness=0.82,
                keywords=["战", "斗", "攻", "击", "招", "势", "对决", "单挑"],
            ),
            SceneTemplate(
                id="tpl_battle_siege",
                name="围攻战",
                scene_type=SceneType.BATTLE,
                structure_steps=["敌人包围", "主角突围", "逐个击破", "首领现身", "最终决战"],
                pacing_notes="开头紧张压迫感，中段节奏稍缓展示策略，末段爆发",
                trope_ids=["trope_underdog"],
                effectiveness=0.75,
                keywords=["围", "困", "突", "破", "包围", "围攻", "群战"],
            ),
            # ── 对话类 ──
            SceneTemplate(
                id="tpl_dialogue_negotiation",
                name="谈判博弈",
                scene_type=SceneType.DIALOGUE,
                structure_steps=["双方落座", "开场试探", "条件交锋", "底线博弈", "达成/破裂"],
                pacing_notes="对话暗藏机锋，每轮对话推进一个信息点，沉默和停顿也是武器",
                trope_ids=[],
                effectiveness=0.7,
                keywords=["说", "道", "问", "答", "谈判", "条件", "交易"],
            ),
            SceneTemplate(
                id="tpl_dialogue_confrontation",
                name="对峙质问",
                scene_type=SceneType.DIALOGUE,
                structure_steps=["气氛紧张", "一方质问", "另一方辩解", "证据抛出", "真相/冲突升级"],
                pacing_notes="短句对话为主，语气逐步升级，关键信息用单独段落强调",
                trope_ids=["trope_face_slap"],
                effectiveness=0.78,
                keywords=["质问", "对峙", "辩解", "证据", "为什么", "竟然"],
            ),
            # ── 揭示类 ──
            SceneTemplate(
                id="tpl_revelation_identity",
                name="身份揭露",
                scene_type=SceneType.REVELATION,
                structure_steps=["悬念铺垫", "线索浮现", "众人猜测", "身份揭晓", "各方反应"],
                pacing_notes="前半段缓慢积累悬念，揭晓瞬间用短句冲击，后续反应分层次展示",
                trope_ids=["trope_underdog"],
                effectiveness=0.85,
                keywords=["身份", "原来", "竟然", "居然", "揭开", "隐藏", "真面目"],
            ),
            SceneTemplate(
                id="tpl_revelation_truth",
                name="真相大白",
                scene_type=SceneType.REVELATION,
                structure_steps=["迷雾重重", "关键线索", "推理串联", "真相揭示", "余波荡漾"],
                pacing_notes="推理过程逻辑清晰，真相揭示时回溯前文伏笔，结尾留余韵",
                trope_ids=[],
                effectiveness=0.8,
                keywords=["真相", "秘密", "原来", "终于", "揭晓", "隐瞒", "事实"],
            ),
            # ── 转折类 ──
            SceneTemplate(
                id="tpl_transition_reversal",
                name="局势逆转",
                scene_type=SceneType.TRANSITION,
                structure_steps=[
                    "看似定局",
                    "变数出现",
                    "局势翻转",
                    "新的危机/机遇",
                    "过渡到下一幕",
                ],
                pacing_notes="先营造尘埃落定的氛围，转折用突然的短句，后续快速展开新局面",
                trope_ids=["trope_face_slap"],
                effectiveness=0.83,
                keywords=["但是", "然而", "突然", "却", "不料", "变故", "逆转"],
            ),
            SceneTemplate(
                id="tpl_transition_journey",
                name="场景转换",
                scene_type=SceneType.TRANSITION,
                structure_steps=[
                    "当前场景收尾",
                    "过渡描写",
                    "新场景引入",
                    "新人物/事件出现",
                    "新篇章开启",
                ],
                pacing_notes="过渡段用环境描写串联，新场景先给全景再聚焦，节奏由缓到紧",
                trope_ids=[],
                effectiveness=0.65,
                keywords=["离开", "前往", "到达", "新的", "从此", "转场", "路途"],
            ),
            # ── 高潮类 ──
            SceneTemplate(
                id="tpl_climax_triple",
                name="三重高潮",
                scene_type=SceneType.CLIMAX,
                structure_steps=[
                    "第一波小高潮",
                    "短暂回落",
                    "第二波中高潮",
                    "悬念悬置",
                    "第三波大高潮爆发",
                ],
                pacing_notes="每波高潮后留呼吸空间，最终高潮用最短句子和最强动词，结尾戛然而止",
                trope_ids=["trope_face_slap", "trope_underdog"],
                effectiveness=0.88,
                keywords=["最强", "终极", "全力", "爆发", "巅峰", "最后", "决一"],
            ),
            SceneTemplate(
                id="tpl_climax_betrayal",
                name="背叛高潮",
                scene_type=SceneType.CLIMAX,
                structure_steps=[
                    "信任铺垫",
                    "背叛信号",
                    "背叛实施",
                    "主角震惊/反击",
                    "关系彻底破裂",
                ],
                pacing_notes="背叛前用细节暗示，背叛瞬间信息量大，后续情绪爆发要充分",
                trope_ids=[],
                effectiveness=0.82,
                keywords=["背叛", "暗算", "背后", "竟然", "原来", "信任", "欺骗"],
            ),
            # ── 描写类 ──
            SceneTemplate(
                id="tpl_description_atmosphere",
                name="氛围营造",
                scene_type=SceneType.DESCRIPTION,
                structure_steps=["大环境全景", "中景聚焦", "细节特写", "人物感受", "氛围定格"],
                pacing_notes="由远及近，由宏观到微观，用比喻和通感增强画面感，段落较长",
                trope_ids=[],
                effectiveness=0.75,
                keywords=["宛如", "犹如", "仿佛", "笼罩", "弥漫", "矗立", "壮阔"],
            ),
            SceneTemplate(
                id="tpl_description_action",
                name="动作描写",
                scene_type=SceneType.DESCRIPTION,
                structure_steps=["起势", "动作过程", "力量展示", "结果呈现", "余韵"],
                pacing_notes="动词密集，短句为主，用拟声词和比喻增强冲击力，每个动作独立成句",
                trope_ids=[],
                effectiveness=0.78,
                keywords=["轰", "爆", "斩", "击", "冲", "撞", "势如", "宛如"],
            ),
            # ── 内心类 ──
            SceneTemplate(
                id="tpl_introspection_struggle",
                name="内心挣扎",
                scene_type=SceneType.INTROSPECTION,
                structure_steps=["触发事件", "矛盾浮现", "理性与情感交锋", "抉择时刻", "决心下定"],
                pacing_notes="内心独白为主，用反问和假设句展现矛盾，抉择后用行动外化决心",
                trope_ids=[],
                effectiveness=0.72,
                keywords=["心想", "暗道", "心中", "内心", "矛盾", "挣扎", "抉择"],
            ),
            SceneTemplate(
                id="tpl_introspection_realization",
                name="顿悟觉醒",
                scene_type=SceneType.INTROSPECTION,
                structure_steps=["困惑状态", "关键触动", "思维串联", "顿悟瞬间", "境界提升"],
                pacing_notes="困惑阶段用长句展现思绪纷乱，顿悟时短句清晰，后续用行动验证",
                trope_ids=["trope_underdog"],
                effectiveness=0.8,
                keywords=["顿悟", "觉醒", "恍然大悟", "原来", "明白", "领悟", "突破"],
            ),
        ]
        for t in defaults:
            self.add_template(t)

    def load_default_pleasure_points(self):
        """加载预设爽点模式（15个）"""
        defaults = [
            PleasurePoint(
                id="pp_face_slap",
                name="装逼打脸",
                description="反派挑衅→主角隐忍→关键时刻爆发→反派震惊→众人膜拜",
                trigger_conditions=["反派挑衅", "看不起主角", "质疑实力"],
                structure=[
                    "反派轻蔑挑衅",
                    "主角表面平静",
                    "契机出现",
                    "主角一招制敌",
                    "反派脸色惨白",
                    "围观者倒吸凉气",
                ],
                effectiveness=0.9,
                tags=["爽点", "打脸", "装逼"],
                keywords=["轻蔑", "挑衅", "看不起", "一招", "震惊", "倒吸", "膜拜", "打脸"],
            ),
            PleasurePoint(
                id="pp_underdog",
                name="废柴逆袭",
                description="主角被轻视→隐藏实力曝光→震惊全场→地位逆转",
                trigger_conditions=["被轻视", "修为低", "出身差"],
                structure=["众人轻视主角", "主角不卑不亢", "实力意外展现", "全场震惊", "地位逆转"],
                effectiveness=0.88,
                tags=["爽点", "逆袭", "隐藏"],
                keywords=["废柴", "废物", "轻视", "隐藏", "实力", "震惊", "逆袭", "竟然"],
            ),
            PleasurePoint(
                id="pp_beauty_save",
                name="英雄救美",
                description="美女遇险→主角出手→美女倾心→获得好感/资源",
                trigger_conditions=["美女遇险", "被围困", "危机时刻"],
                structure=["美女陷入危机", "主角及时出现", "强势解救", "美女心生好感", "获得回报"],
                effectiveness=0.8,
                tags=["爽点", "救美", "好感"],
                keywords=["美女", "遇险", "围困", "危机", "解救", "倾心", "好感", "英雄"],
            ),
            PleasurePoint(
                id="pp_cross_rank",
                name="越级挑战",
                description="主角以低境界挑战高境界敌人→利用特殊手段/意志→以弱胜强",
                trigger_conditions=["境界差距", "强敌当前", "不得不战"],
                structure=["强敌压迫", "众人以为必败", "主角爆发特殊手段", "以弱胜强", "名震一方"],
                effectiveness=0.85,
                tags=["爽点", "越级", "以弱胜强"],
                keywords=["越级", "境界", "以弱胜强", "挑战", "强敌", "爆发", "不可思议"],
            ),
            PleasurePoint(
                id="pp_treasure",
                name="宝物出世",
                description="天降宝物/遗迹开启→众人争夺→主角获得→实力大增",
                trigger_conditions=["宝物出世", "遗迹开启", "机缘巧合"],
                structure=[
                    "宝物/遗迹出现",
                    "各方势力争夺",
                    "主角凭实力/运气获得",
                    "炼化宝物",
                    "实力大增",
                ],
                effectiveness=0.82,
                tags=["爽点", "宝物", "机缘"],
                keywords=["宝物", "神器", "遗迹", "出世", "争夺", "获得", "炼化", "机缘"],
            ),
            PleasurePoint(
                id="pp_identity_expose",
                name="身份曝光",
                description="主角隐藏真实身份→关键时刻暴露→众人震惊→态度逆转",
                trigger_conditions=["身份隐藏", "被轻视", "需要亮明身份"],
                structure=[
                    "主角隐藏身份",
                    "被人轻视/刁难",
                    "身份意外暴露",
                    "众人震惊惶恐",
                    "态度大逆转",
                ],
                effectiveness=0.87,
                tags=["爽点", "身份", "曝光"],
                keywords=["身份", "隐藏", "暴露", "竟然是", "震惊", "惶恐", "下跪", "真面目"],
            ),
            PleasurePoint(
                id="pp_comeback",
                name="绝地反杀",
                description="主角陷入绝境→看似败局已定→绝境爆发→反杀敌人",
                trigger_conditions=["陷入绝境", "身受重伤", "敌人得意"],
                structure=[
                    "主角陷入绝境",
                    "敌人得意忘形",
                    "主角绝境爆发",
                    "惊天反杀",
                    "敌人难以置信",
                ],
                effectiveness=0.89,
                tags=["爽点", "反杀", "绝境"],
                keywords=["绝境", "反杀", "重伤", "得意", "爆发", "难以置信", "翻盘", "垂死"],
            ),
            PleasurePoint(
                id="pp_beauty_fall",
                name="美人倾心",
                description="高冷/强大美女→被主角特质吸引→逐渐倾心→主动示好",
                trigger_conditions=["美女在场", "主角展现魅力", "互动机会"],
                structure=[
                    "美女初始冷淡",
                    "主角展现独特魅力",
                    "美女态度微妙变化",
                    "主动接近/示好",
                    "确立关系",
                ],
                effectiveness=0.78,
                tags=["爽点", "美女", "感情"],
                keywords=["美女", "倾心", "冷淡", "魅力", "脸红", "心动", "主动", "芳心"],
            ),
            PleasurePoint(
                id="pp_faction_submit",
                name="势力臣服",
                description="主角展现压倒性实力→敌对势力敬畏→主动臣服/结盟",
                trigger_conditions=["势力冲突", "实力碾压", "需要收服"],
                structure=[
                    "势力挑衅/对立",
                    "主角展现实力",
                    "对方高层震惊",
                    "主动臣服/结盟",
                    "势力扩张",
                ],
                effectiveness=0.83,
                tags=["爽点", "势力", "臣服"],
                keywords=["势力", "臣服", "敬畏", "碾压", "结盟", "归顺", "下跪", "投靠"],
            ),
            PleasurePoint(
                id="pp_breakthrough",
                name="功法突破",
                description="主角修炼遇瓶颈→机缘/顿悟→突破境界→实力暴涨",
                trigger_conditions=["修炼瓶颈", "机缘到来", "顿悟时刻"],
                structure=[
                    "修炼遇瓶颈",
                    "苦苦思索/等待机缘",
                    "顿悟/获得机缘",
                    "突破境界",
                    "实力暴涨验证",
                ],
                effectiveness=0.84,
                tags=["爽点", "突破", "修炼"],
                keywords=["突破", "瓶颈", "顿悟", "境界", "修炼", "暴涨", "晋升", "闭关"],
            ),
            PleasurePoint(
                id="pp_truth_reveal",
                name="真相揭露",
                description="隐藏的阴谋/秘密→线索逐步浮现→真相大白→坏人受惩",
                trigger_conditions=["悬念积累", "线索齐全", "揭示时机"],
                structure=[
                    "悬念/阴谋铺垫",
                    "关键线索出现",
                    "推理串联",
                    "真相大白",
                    "坏人受惩/正义伸张",
                ],
                effectiveness=0.81,
                tags=["爽点", "真相", "揭露"],
                keywords=["真相", "阴谋", "揭露", "原来", "证据", "大白", "报应", "幕后"],
            ),
            PleasurePoint(
                id="pp_enemy_meet",
                name="仇人相见",
                description="主角与仇人意外相遇→新仇旧恨→冲突爆发→复仇进展",
                trigger_conditions=["仇人出现", "仇恨未消", "冲突时机"],
                structure=[
                    "仇人意外出现",
                    "主角认出仇人",
                    "气氛剑拔弩张",
                    "冲突爆发",
                    "复仇取得进展",
                ],
                effectiveness=0.86,
                tags=["爽点", "复仇", "冲突"],
                keywords=["仇人", "复仇", "仇恨", "相见", "认出", "剑拔弩张", "血债", "旧恨"],
            ),
            PleasurePoint(
                id="pp_old_friend",
                name="旧友重逢",
                description="主角与故人久别重逢→回忆往昔→情谊加深→获得助力",
                trigger_conditions=["故人出现", "久别之后", "情感节点"],
                structure=["故人意外出现", "认出彼此", "回忆往昔", "情谊加深", "获得助力/并肩作战"],
                effectiveness=0.75,
                tags=["爽点", "友情", "重逢"],
                keywords=["旧友", "故人", "重逢", "多年", "回忆", "兄弟", "并肩", "久违"],
            ),
            PleasurePoint(
                id="pp_desperate_adventure",
                name="绝境奇遇",
                description="主角陷入绝境/濒死→意外发现奇遇→获得传承/宝物→浴火重生",
                trigger_conditions=["濒死绝境", "误入禁地", "机缘巧合"],
                structure=[
                    "主角陷入绝境/濒死",
                    "意外发现隐秘之地",
                    "获得传承/宝物",
                    "浴火重生",
                    "实力蜕变",
                ],
                effectiveness=0.84,
                tags=["爽点", "奇遇", "绝境"],
                keywords=["绝境", "奇遇", "濒死", "禁地", "传承", "浴火", "蜕变", "大难不死"],
            ),
            PleasurePoint(
                id="pp_king_return",
                name="王者归来",
                description="主角离开/沉寂一段时间→以更强姿态回归→震慑全场→旧敌胆寒",
                trigger_conditions=["主角离开", "时间流逝", "回归时机"],
                structure=[
                    "主角离开/沉寂",
                    "外界以为其陨落/没落",
                    "以更强姿态回归",
                    "震慑全场",
                    "旧敌胆寒/新局开启",
                ],
                effectiveness=0.88,
                tags=["爽点", "回归", "王者"],
                keywords=["归来", "回归", "王者", "沉寂", "陨落", "震慑", "胆寒", "重现"],
            ),
        ]
        for pp in defaults:
            self.pleasure_points[pp.id] = pp

    # ── 序列化 ────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates": {k: v.to_dict() for k, v in self.templates.items()},
            "pleasure_points": {k: v.to_dict() for k, v in self.pleasure_points.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SceneTemplateLibrary:
        lib = cls()
        for tid, tdata in data.get("templates", {}).items():
            t = SceneTemplate.from_dict(tdata)
            lib.templates[tid] = t
            lib._type_index.setdefault(t.scene_type, []).append(tid)
        for pid, pdata in data.get("pleasure_points", {}).items():
            lib.pleasure_points[pid] = PleasurePoint.from_dict(pdata)
        return lib

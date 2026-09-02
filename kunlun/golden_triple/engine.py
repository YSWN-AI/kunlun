"""
黄金三章引擎 — 开篇分析 + 模板生成 + Agent集成
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import ClassVar

from loguru import logger

from kunlun.agents.base import AgentMessage, AgentStatus, BaseAgent
from kunlun.golden_triple.templates import (
    ARCHETYPES,
    CHAPTER_THREE_PLAN,
    CORE_TEMPLATES,
    ArchetypeTemplate,
)


@dataclass
class HookScore:
    """钩子评分结果"""

    conflict_intensity: float = 0.0
    information_gap: float = 0.0
    emotional_impact: float = 0.0
    immersion: float = 0.0
    rhythm_score: float = 0.0
    total: float = 0.0
    level: str = "弱"
    suggestions: list[str] = field(default_factory=list)
    breakdown: str = ""


@dataclass
class ArchetypeMatch:
    """原型匹配结果"""

    archetype: ArchetypeTemplate | None = None
    match_score: float = 0.0
    match_reason: str = ""
    alternative_archetypes: list[dict] = field(default_factory=list)


@dataclass
class ChapterPlan:
    """黄金三章计划"""

    archetype: ArchetypeTemplate | None = None
    chapters: list[dict] = field(default_factory=list)
    estimated_words: int = 0
    hook_blueprint: dict = field(default_factory=dict)
    core_conflict: str = ""
    protagonist_anchor: str = ""
    specific_suggestions: list[str] = field(default_factory=list)
    genre_tips: dict = field(default_factory=dict)


@dataclass
class GoldenTripleResult:
    """黄金三章生成/分析结果"""

    success: bool = True
    plan: ChapterPlan | None = None
    hook_score: HookScore | None = None
    archetype_match: ArchetypeMatch | None = None
    generated_prompt: str = ""
    error: str = ""
    meta: dict = field(default_factory=dict)


class GoldenTripleEngine:
    """黄金三章引擎 — 开篇分析 + 模板生成 + 抽卡集成

    与现有系统集成：
    - GachaEngine: 通过 generate_with_prompt() 调用多模型抽卡生成
    - Agent系统: 可作为独立Agent或嵌入Architect/Writer工作流
    - 管线系统: 通过 ChapterPlan 注入 Pipeline
    """

    AGENT_NAME: ClassVar[str] = "golden_triple"
    CAPABILITIES: ClassVar[list[str]] = [
        "analyze_opening",
        "generate_plan",
        "score_hooks",
        "match_archetype",
    ]

    HOOK_DIMENSIONS: ClassVar[dict[str, float]] = {
        "conflict_intensity": 0.25,
        "information_gap": 0.25,
        "emotional_impact": 0.20,
        "immersion": 0.15,
        "rhythm_score": 0.15,
    }

    def __init__(self):
        self._call_count: int = 0
        self._last_plan: ChapterPlan | None = None
        self._status = AgentStatus.IDLE

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def last_plan(self) -> ChapterPlan | None:
        return self._last_plan

    def list_archetypes(self) -> list[dict]:
        """列出所有开篇原型"""
        result = []
        for slug, arch in ARCHETYPES.items():
            result.append(
                {
                    "slug": slug,
                    "name": arch.name,
                    "description": arch.description,
                    "target_genres": arch.target_genres,
                    "hook_phrase_examples": arch.hook_phrase_examples[:2],
                    "strength_profile": arch.strength_profile,
                }
            )
        return result

    def get_archetype(self, slug: str) -> ArchetypeTemplate | None:
        """获取指定原型"""
        return ARCHETYPES.get(slug)

    def suggest_archetype(
        self, genre: str = "", theme: str = "", _tone: str = ""
    ) -> ArchetypeMatch:
        """根据题材/主题/基调推荐开篇原型"""
        scores: dict[str, float] = {}

        for slug, arch in ARCHETYPES.items():
            score = 0.0
            if genre and genre in arch.target_genres:
                score += 0.5
            if genre:
                genre_terms = set(genre.replace("都市", "").split())
                tag_terms = set()
                for g in arch.target_genres:
                    token = g[:2]
                    tag_terms.add(token)
                overlap = sum(1 for t in genre_terms if t in "".join(arch.target_genres))
                score += overlap * 0.15
            # 根据主题调整
            if theme in {"热血", "战斗"}:
                score += 0.3 if slug in ("conflict", "strong_return") else 0
            elif theme in {"烧脑", "悬疑"}:
                score += 0.3 if slug in ("suspense", "daily_anomaly") else 0
            elif theme in {"爽文", "逆袭"}:
                score += 0.3 if slug in ("contrast", "system_arrival", "strong_return") else 0
            elif theme == "轻松":
                score += 0.3 if slug in ("daily_anomaly", "system_arrival") else 0
            scores[slug] = min(1.0, score)

        scored = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_slug, best_score = scored[0]
        alternatives = [
            {"slug": s, "name": ARCHETYPES[s].name, "score": round(sc, 2)}
            for s, sc in scored[1:4]
            if sc > 0.1
        ]

        return ArchetypeMatch(
            archetype=ARCHETYPES[best_slug],
            match_score=round(best_score, 2),
            match_reason=f"题材'{genre}'匹配度{best_score:.0%}",
            alternative_archetypes=alternatives,
        )

    def analyze_opening(self, text: str, _genre: str = "", chapter_number: int = 1) -> HookScore:
        """分析开篇文本的钩子质量 — 纯文本统计，零LLM成本"""
        if not text or len(text) < 100:
            return HookScore(
                total=0,
                level="未知",
                suggestions=["文本过短（<100字），无法有效分析"],
            )

        dims = {
            "conflict_intensity": self._score_conflict_intensity(text),
            "information_gap": self._score_information_gap(text),
            "emotional_impact": self._score_emotional_impact(text),
            "immersion": self._score_immersion(text),
            "rhythm_score": self._score_rhythm(text),
        }

        total = sum(dims[k] * self.HOOK_DIMENSIONS[k] for k in dims) * 100

        if total >= 80:
            level = "极强"
        elif total >= 65:
            level = "强"
        elif total >= 50:
            level = "中等"
        elif total >= 35:
            level = "弱"
        else:
            level = "极弱"

        suggestions = self._generate_suggestions(dims, text, chapter_number)

        breakdown_parts = []
        dim_labels = {
            "conflict_intensity": "冲突强度",
            "information_gap": "信息差",
            "emotional_impact": "情绪冲击",
            "immersion": "代入感",
            "rhythm_score": "节奏感",
        }
        for key, label in dim_labels.items():
            raw = dims[key]
            pct = int(raw * 100)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            breakdown_parts.append(f"{label}: {pct} [{bar}]")

        return HookScore(
            conflict_intensity=round(dims["conflict_intensity"], 2),
            information_gap=round(dims["information_gap"], 2),
            emotional_impact=round(dims["emotional_impact"], 2),
            immersion=round(dims["immersion"], 2),
            rhythm_score=round(dims["rhythm_score"], 2),
            total=round(total, 1),
            level=level,
            suggestions=suggestions,
            breakdown="\n".join(breakdown_parts),
        )

    def _score_conflict_intensity(self, text: str) -> float:
        """冲突强度 — 暴力词/对抗词密度 + 对话冲突"""
        conflict_words = re.findall(
            r"(杀|死|伤|血|恨|仇|战|斗|打|斩|灭|毁|断|碎|破|败|"
            r"威胁|危机|死亡|危险|敌人|对手|仇人|反抗|挣扎|逃|"
            r"不敢相信|震惊|愤怒|冷漠|冷笑|不屑|嘲笑|轻蔑|暴怒)",
            text,
        )
        density = len(conflict_words) / max(len(text) / 100, 1)

        _quote_chars = "\u201c\u201d\u2018\u2019\u300c\u300d"
        _quote_pattern = (
            f"[{_quote_chars}]"
            f"(?=.*?(?:你敢|找死|不要脸|放肆|滚|凭什么|你算什么|不知天高地厚|找死))"
            f"[^{_quote_chars}]*[{_quote_chars}]"
        )
        dialogue_conflict = len(re.findall(_quote_pattern, text))

        return min(1.0, density * 0.7 + dialogue_conflict * 0.15)

    def _score_information_gap(self, text: str) -> float:
        """信息差 — 未解信息密度（问句、异常描述、模糊指代）"""
        questions = len(re.findall(r"[？?]", text))
        anomalies = len(
            re.findall(
                r"(异常|奇怪|不对|不对劲|不可能|怎么会|竟然|居然|"
                r"怎么会|诡异|不可思议|难以置信|不应该是|为什么)",
                text,
            )
        )
        vague_refs = len(
            re.findall(
                r"(那[个位种件事]|某[个种些人天次]|有人|谁|什么东西|"
                r"不知道|不清楚|不明白|记忆.*?空白|一片.*?空白)",
                text,
            )
        )

        total_signals = questions + anomalies * 2 + vague_refs
        density = total_signals / max(len(text) / 100, 1)

        return min(1.0, density * 0.6)

    def _score_emotional_impact(self, text: str) -> float:
        """情绪冲击 — 情绪词强度分布"""
        strong_emotion = len(
            re.findall(
                r"(震惊|不可思议|撕心裂肺|绝望|恐惧|崩溃|天崩地裂|五雷轰顶|"
                r"愤怒|狂怒|暴怒|痛不欲生|欣喜若狂|泪流满面|瞠目结舌|目瞪口呆)",
                text,
            )
        )
        moderate_emotion = len(
            re.findall(
                r"(惊讶|失落|伤心|难过|感动|激动|不安|紧张|害怕|担心|着急|"
                r"委屈|无奈|心酸|欣慰|开心|高兴|兴奋|期待)",
                text,
            )
        )

        strength = strong_emotion * 3 + moderate_emotion
        density = strength / max(len(text) / 100, 1)

        return min(1.0, density * 0.5)

    def _score_immersion(self, text: str) -> float:
        """代入感 — 感官细节密度 + 第一/第二人称 + 日常锚点"""
        sensory = len(
            re.findall(
                r"(看到|听到|闻到|感到|觉得|触到|温暖|冰冷|炙热|"
                r"刺眼|刺耳|腥|香|臭|甜|苦)",
                text,
            )
        )
        self_pronouns = len(re.findall(r"(我|我们|自己|他|她)", text))
        daily_anchors = len(
            re.findall(
                r"(手机|电脑|教室|办公室|公司|家|房间|厨房|客厅|"
                r"床|车|地铁|公交|路边|便利店|超市|饭店|食堂|"
                r"工资|房租|考试|加班|上学|放学|上班|下班)",
                text,
            )
        )

        return min(1.0, (sensory * 0.03 + self_pronouns * 0.005 + daily_anchors * 0.04))

    def _score_rhythm(self, text: str) -> float:
        """节奏感 — 短句比例 + 句长变异 + 动作句密度"""
        sentences = re.split(r"[。！？.!?\n]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
        if not sentences:
            return 0.0

        lengths = [len(s) for s in sentences]
        short_ratio = sum(1 for length in lengths if length <= 15) / max(len(lengths), 1)

        if len(lengths) >= 2:
            mean_l = sum(lengths) / len(lengths)
            var = sum((length - mean_l) ** 2 for length in lengths) / len(lengths)
            cv = math.sqrt(var) / max(mean_l, 1)
            variation_score = 1.0 - abs(cv - 0.45)
        else:
            variation_score = 0.5

        action_sentences = len(
            re.findall(
                r"(伸手|抬脚|转身|回头|拔出|抽出|挥出|冲|跑|跳|飞|"
                r"一掌|一拳|一剑|一刀|一脚|一击|斩落|轰|炸)",
                text,
            )
        )
        action_density = min(1.0, action_sentences / max(len(sentences), 1) * 5)

        score = short_ratio * 0.4 + variation_score * 0.3 + action_density * 0.3
        return min(1.0, score)

    def _generate_suggestions(self, dims: dict, text: str, chapter_number: int) -> list[str]:
        """根据评分生成改进建议"""
        suggestions = []

        if dims["conflict_intensity"] < 0.3:
            suggestions.append("冲突强度不足：建议在前500字加入对抗元素或紧张情境")
        if dims["conflict_intensity"] < 0.5:
            suggestions.append("冲突可更尖锐：增加一对一的对手或明确的时间压力")

        if dims["information_gap"] < 0.3:
            suggestions.append("信息差不足：加入悬念、未解之谜或异常现象激发好奇心")
        if dims["information_gap"] > 0.85:
            suggestions.append("信息差过大：避免让读者完全摸不着头脑，适当提供线索")

        if dims["emotional_impact"] < 0.3:
            suggestions.append("情绪冲击弱：增加强烈情绪场景（震惊/愤怒/悲伤/狂喜）")
        if dims["emotional_impact"] > 0.9:
            suggestions.append("情绪过度饱和：适当加入缓冲段落，避免读者疲劳")

        if dims["immersion"] < 0.3:
            suggestions.append("代入感不足：增加感官细节和日常场景锚点")

        if dims["rhythm_score"] < 0.3:
            suggestions.append("节奏平淡：增加短句和动作描写，提升节奏变化")
        if dims["rhythm_score"] < 0.5:
            suggestions.append("节奏可优化：短句（≤15字）比例偏低")

        if chapter_number == 1:
            opening_300 = text[:300]
            if len(opening_300) >= 100:
                has_hook = bool(
                    re.search(
                        r"(？|\?|！)|(突然|竟然|没想到|谁会|怎么会|"
                        r"为什么|不可思议|那一刻|瞬间|下一刻)",
                        opening_300,
                    )
                )
                if not has_hook:
                    suggestions.append("开篇300字内未检测到钩子元素（问句/转折/异常）")
            if len(re.findall(r"(修炼体系|境界划分|功法等级|灵气.*?分为)", text)) > 0:
                suggestions.append("第1章出现修炼体系说明——建议移至后续章节")

        if chapter_number == 3:
            end_500 = text[-500:] if len(text) > 500 else text
            has_cliffhanger = bool(
                re.search(
                    r"(？|\?)|(突然|竟然|没想到|下一刻|就在这时|"
                    r"然而|但是|可是|新的|更大的|更强的)",
                    end_500,
                )
            )
            if not has_cliffhanger:
                suggestions.append("第3章结尾未检测到悬念——付费意愿点缺失")
            strong_end_emo = len(
                re.findall(
                    r"(震惊|不可思议|不敢置信|目瞪口呆|轰|碾压|秒杀|"
                    r"完胜|碾压|秒杀|碾压|瞬杀)",
                    end_500,
                )
            )
            if strong_end_emo < 1:
                suggestions.append("第3章结尾情绪强度偏低——建议加强打脸效果或悬念力度")

        if not suggestions:
            suggestions.append("当前开篇质量良好，继续保持")

        return suggestions

    def generate_plan(
        self,
        archetype_slug: str = "",
        genre: str = "",
        theme: str = "",
        protagonist: str = "",
        core_conflict: str = "",
        platform: str = "起点",
    ) -> GoldenTripleResult:
        """生成黄金三章写作计划"""
        match = self.suggest_archetype(genre, theme)
        archetype = self.get_archetype(archetype_slug) if archetype_slug else match.archetype

        if archetype is None:
            archetype = ARCHETYPES["suspense"]

        chapters = []
        total_words = 0
        for ch_key in ["chapter_1", "chapter_2", "chapter_3"]:
            ch_template = CHAPTER_THREE_PLAN[ch_key]
            chapters.append(
                {
                    "number": int(ch_key.split("_")[1]),
                    "name": ch_template["name"],
                    "word_range": ch_template["word_range"],
                    "structure": [
                        {"section": s[0], "word_range": s[1], "note": s[2]}
                        for s in ch_template["structure"]
                    ],
                    "checklist": ch_template["checklist"].copy(),
                    "taboos": ch_template["taboos"].copy(),
                }
            )
            total_words += 3000

        # 用核心冲突扩展章尾模板
        cliffhanger_template = CORE_TEMPLATES["chapter_end_cliffhanger"]
        cliffhanger_filled = cliffhanger_template.template_text.replace(
            "{cliffhanger_type}", "信息揭示式" if "秘密" in core_conflict else "危机逼近式"
        ).replace("{cliffhanger_intensity}", "8/10")

        hook_blueprint = {
            "opening_archetype": archetype.name,
            "hook_phrase_suggestions": archetype.hook_phrase_examples,
            "conflict_setup_template": CORE_TEMPLATES["conflict_setup"].template_text.format(
                conflict_type=core_conflict or "对抗型冲突",
                antagonist="待定义",
                protagonist_disadvantage="待定义",
                escalation_path="待规划",
            ),
            "protagonist_intro_template": CORE_TEMPLATES["protagonist_intro"].template_text.format(
                character_anchor=protagonist or "待定义",
                character_dilemma="待定义",
                character_tag="待定义",
            ),
            "chapter_end_template": cliffhanger_filled,
        }

        platform_tips = {}
        if genre:
            if "起点" in platform:
                platform_tips["起点"] = [
                    "前三章必须体现题材辨识度",
                    "加分项：包含'这个题材我没见过'的创新点",
                ]
            if "番茄" in platform:
                platform_tips["番茄"] = [
                    "每章结束必须让读者想点'下一章'",
                    "第3章出现第一个付费意愿点",
                ]
            if "七猫" in platform:
                platform_tips["七猫"] = [
                    "开场300字必须直接进入冲突（不可有环境描写）",
                    "主角人设足够鲜明，读者能一句话总结",
                ]

        specific = []
        specific.append(f"选用{archetype.name}原型开篇")
        specific.append(f"题材匹配度: {match.match_score:.0%}")
        if archetype.taboos:
            specific.append(f"禁忌: {'; '.join(archetype.taboos[:2])}")
        for _slug, arch in match.alternative_archetypes[:1]:
            specific.append(f"备选原型: {arch['name']} ({arch['score']:.0%})")

        plan = ChapterPlan(
            archetype=archetype,
            chapters=chapters,
            estimated_words=total_words,
            hook_blueprint=hook_blueprint,
            core_conflict=core_conflict,
            protagonist_anchor=protagonist,
            specific_suggestions=specific,
            genre_tips=platform_tips,
        )
        self._last_plan = plan
        self._call_count += 1

        return GoldenTripleResult(
            success=True,
            plan=plan,
            archetype_match=match,
            meta={
                "archetype_count": len(ARCHETYPES),
                "generated_at": time.time(),
            },
        )

    def generate_prompt(self, plan: ChapterPlan, chapter: int = 1) -> str:
        """基于计划生成可送给GachaEngine的提示词"""
        if plan is None or not plan.chapters:
            return ""

        ch = plan.chapters[chapter - 1]
        archetype = plan.archetype
        if archetype is None:
            archetype = ARCHETYPES["suspense"]

        prompt_parts = [
            f"【第{chapter}章：{ch['name']}】",
            f"字数要求：{ch['word_range']}字",
            "",
            f"开篇原型：{archetype.name}（{archetype.description}）",
            "",
            f"核心冲突：{plan.core_conflict or '无'}",
            f"主角：{plan.protagonist_anchor or '无'}",
            "",
            "【本章结构】",
        ]

        prompt_parts.extend(
            f"- {section['section']}（{section['word_range']}）：{section['note']}"
            for section in ch["structure"]
        )

        prompt_parts.extend(
            [
                "",
                "【必须遵守】",
                f"- {chr(10).join(f'  □ {item}' for item in ch['checklist'])}",
                "",
                "【绝对禁止】",
                f"- {chr(10).join(f'  ✗ {item}' for item in ch['taboos'])}",
                "",
                "【原型要求】",
                f"- {chr(10).join(f'  · {t}' for t in archetype.taboos)}",
                "",
                "【参考钩子】",
            ]
            + [f"- {ex}" for ex in archetype.hook_phrase_examples[:2]]
        )

        return "\n".join(prompt_parts)

    async def generate_with_gacha(
        self, plan: ChapterPlan, chapter: int = 1, mode: str = "gacha_cascade"
    ) -> dict:
        """使用GachaEngine生成黄金三章内容"""
        prompt = self.generate_prompt(plan, chapter)
        if not prompt:
            return {"success": False, "error": "无法生成提示词"}

        try:
            from kunlun.gacha.engine import gacha_engine

            result = await gacha_engine.generate(
                prompt=prompt,
                mode=mode,
                agent="golden_triple",
                chapter_type="opening",
                humanize=True,
            )
            result["success"] = bool(result.get("best_text"))
            result["prompt"] = prompt
            return result
        except Exception as e:
            logger.error(f"GoldenTripleEngine: Gacha生成失败: {e}")
            return {"success": False, "error": str(e), "prompt": prompt}


class GoldenTripleAgent(BaseAgent):
    """黄金三章Agent — 可接入消息总线，响应ANALYZE_OPENING/GENERATE_PLAN消息"""

    agent_name: str = "golden_triple"
    capabilities: ClassVar[list[str]] = [
        "analyze_opening",
        "generate_plan",
        "suggest_archetype",
        "generate_chapter",
    ]

    def __init__(self, nats_client=None):
        super().__init__(nats_client=nats_client)
        self._engine = GoldenTripleEngine()

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        """处理消息总线消息"""
        try:
            if msg.msg_type == "ANALYZE_OPENING":
                result = self._engine.analyze_opening(
                    text=msg.payload.get("text", ""),
                    _genre=msg.payload.get("genre", ""),
                    chapter_number=msg.payload.get("chapter_number", 1),
                )
                return AgentMessage(
                    from_agent=self.agent_name,
                    to_agent=msg.from_agent,
                    msg_type="OPENING_ANALYZED",
                    payload={
                        "total": result.total,
                        "level": result.level,
                        "suggestions": result.suggestions,
                        "breakdown": result.breakdown,
                    },
                    correlation_id=msg.correlation_id,
                )
            if msg.msg_type == "GENERATE_PLAN":
                gr = self._engine.generate_plan(
                    archetype_slug=msg.payload.get("archetype", ""),
                    genre=msg.payload.get("genre", ""),
                    theme=msg.payload.get("theme", ""),
                    protagonist=msg.payload.get("protagonist", ""),
                    core_conflict=msg.payload.get("core_conflict", ""),
                    platform=msg.payload.get("platform", "起点"),
                )
                if gr.success and gr.plan:
                    return AgentMessage(
                        from_agent=self.agent_name,
                        to_agent=msg.from_agent,
                        msg_type="PLAN_GENERATED",
                        payload={
                            "archetype": gr.plan.archetype.name if gr.plan.archetype else "",
                            "chapters": gr.plan.chapters,
                            "estimated_words": gr.plan.estimated_words,
                            "hook_blueprint": gr.plan.hook_blueprint,
                            "specific_suggestions": gr.plan.specific_suggestions,
                        },
                        correlation_id=msg.correlation_id,
                    )
                return AgentMessage(
                    from_agent=self.agent_name,
                    to_agent=msg.from_agent,
                    msg_type="PLAN_FAILED",
                    payload={"error": gr.error},
                    correlation_id=msg.correlation_id,
                )
            if msg.msg_type == "SUGGEST_ARCHETYPE":
                match = self._engine.suggest_archetype(
                    genre=msg.payload.get("genre", ""),
                    theme=msg.payload.get("theme", ""),
                )
                return AgentMessage(
                    from_agent=self.agent_name,
                    to_agent=msg.from_agent,
                    msg_type="ARCHETYPE_SUGGESTED",
                    payload={
                        "archetype": match.archetype.name if match.archetype else "",
                        "match_score": match.match_score,
                        "alternatives": match.alternative_archetypes,
                    },
                    correlation_id=msg.correlation_id,
                )
        except Exception as e:
            logger.error(f"GoldenTripleAgent.on_message 失败: {e}")
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="ERROR",
                payload={"error": str(e)},
                correlation_id=msg.correlation_id,
            )

        return None

    async def execute(self, task: dict) -> dict:
        """执行任务"""
        action = task.get("action", "")
        try:
            if action == "analyze_opening":
                result = self._engine.analyze_opening(
                    text=task.get("text", ""),
                    _genre=task.get("genre", ""),
                    chapter_number=task.get("chapter_number", 1),
                )
                return {
                    "success": True,
                    "total": result.total,
                    "level": result.level,
                    "suggestions": result.suggestions,
                    "breakdown": result.breakdown,
                    "conflict_intensity": result.conflict_intensity,
                    "information_gap": result.information_gap,
                    "emotional_impact": result.emotional_impact,
                    "immersion": result.immersion,
                    "rhythm_score": result.rhythm_score,
                }
            if action == "generate_plan":
                gr = self._engine.generate_plan(
                    archetype_slug=task.get("archetype", ""),
                    genre=task.get("genre", ""),
                    theme=task.get("theme", ""),
                    protagonist=task.get("protagonist", ""),
                    core_conflict=task.get("core_conflict", ""),
                    platform=task.get("platform", "起点"),
                )
                if gr.success and gr.plan:
                    return {
                        "success": True,
                        "archetype": gr.plan.archetype.name if gr.plan.archetype else "",
                        "chapters": gr.plan.chapters,
                        "estimated_words": gr.plan.estimated_words,
                        "hook_blueprint": gr.plan.hook_blueprint,
                        "specific_suggestions": gr.plan.specific_suggestions,
                        "genre_tips": gr.plan.genre_tips,
                    }
                return {"success": False, "error": gr.error}
            if action == "suggest_archetype":
                match = self._engine.suggest_archetype(
                    genre=task.get("genre", ""),
                    theme=task.get("theme", ""),
                )
                return {
                    "success": True,
                    "archetype": match.archetype.name if match.archetype else "",
                    "slug": match.archetype.slug if match.archetype else "",
                    "match_score": match.match_score,
                    "alternatives": match.alternative_archetypes,
                }
            return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            logger.error(f"GoldenTripleAgent.execute 失败: {e}")
            return {"success": False, "error": str(e)}


golden_triple_engine = GoldenTripleEngine()

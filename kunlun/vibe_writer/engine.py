"""
vibe_writer 随性写作引擎 — 自然语言意图路由+自由创作+灵感激发

核心能力:
1. 意图识别（用户想做什么类型的写作）
2. 多意图路由（续写/改写/扩写/润色/灵感）
3. 自由创作模式（不打断flow的随性写作）
4. 上下文感知（基于已有内容给出建议）
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule


class VibeIntent(Enum):
    """写作意图"""

    CONTINUE = "continue"  # 续写（从当前位置继续）
    REWRITE = "rewrite"  # 改写（重写选中段落）
    EXPAND = "expand"  # 扩写（丰富细节）
    POLISH = "polish"  # 润色（优化文笔）
    INSPIRE = "inspire"  # 灵感（需要写作建议）
    BRAINSTORM = "brainstorm"  # 头脑风暴（发散想法）
    OUTLINE = "outline"  # 大纲（生成/调整大纲）
    DIALOGUE = "dialogue"  # 对话（专门写对话）
    DESCRIPTION = "description"  # 描写（环境/人物描写）
    ACTION = "action"  # 动作场景
    TRANSITION = "transition"  # 过渡段落
    ENDING = "ending"  # 结尾/收尾


class VibeMood(Enum):
    """写作情绪/风格"""

    SERIOUS = "serious"  # 严肃
    LIGHT = "light"  # 轻松
    TENSE = "tense"  # 紧张
    ROMANTIC = "romantic"  # 浪漫
    MYSTERIOUS = "mysterious"  # 神秘
    EPIC = "epic"  # 史诗
    DARK = "dark"  # 黑暗
    HUMOROUS = "humorous"  # 幽默


@dataclass
class VibeContext:
    """写作上下文"""

    current_text: str = ""  # 当前正在写的文本
    selected_text: str = ""  # 用户选中的文本（如果有）
    cursor_position: int = 0  # 光标位置
    chapter_title: str = ""
    previous_paragraph: str = ""  # 上一段
    genre: str = ""  # 作品类型
    style_notes: str = ""  # 风格备注
    character_in_scene: list[str] = field(default_factory=list)  # 场景中的角色


@dataclass
class VibeResponse:
    """写作响应"""

    response_id: str
    intent: VibeIntent
    generated_text: str = ""
    suggestions: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)  # 备选方案
    mood: VibeMood | None = None
    explanation: str = ""  # 为什么这样写
    word_count: int = 0
    quality_feedback: dict | None = None  # 即时质量反馈
    created_at: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "intent": self.intent.value,
            "word_count": self.word_count,
            "suggestions_count": len(self.suggestions),
            "alternatives_count": len(self.alternatives),
            "mood": self.mood.value if self.mood else None,
            "quality_score": self.quality_feedback.get("overall_score", 0) if self.quality_feedback else 0,
            "ai_rate": self.quality_feedback.get("ai_rate", 0) if self.quality_feedback else 0,
        }


class IntentRouter(BaseExtensionModule):
    """意图路由器 — 根据用户输入识别写作意图"""

    SUBDIR = "vibe_writer"

    # 意图关键词映射
    INTENT_KEYWORDS: dict[VibeIntent, list[str]] = {
        VibeIntent.CONTINUE: ["继续", "接着写", "往下", "然后呢", "继续写"],
        VibeIntent.REWRITE: ["重写", "改写", "改一下", "换种写法", "重新写"],
        VibeIntent.EXPAND: ["扩写", "展开", "详细一点", "丰富", "多写点"],
        VibeIntent.POLISH: ["润色", "优化", "改好一点", "润一下", "修饰"],
        VibeIntent.INSPIRE: ["没灵感", "不知道怎么写", "帮我想想", "建议", "灵感"],
        VibeIntent.BRAINSTORM: ["头脑风暴", "发散", "脑洞", "想法", "点子"],
        VibeIntent.OUTLINE: ["大纲", "提纲", "框架", "结构"],
        VibeIntent.DIALOGUE: ["对话", "台词", "说话", "交谈"],
        VibeIntent.DESCRIPTION: ["描写", "描述", "场景", "环境", "外貌"],
        VibeIntent.ACTION: ["动作", "打斗", "战斗", "动作描写"],
        VibeIntent.TRANSITION: ["过渡", "转场", "衔接", "承上启下"],
        VibeIntent.ENDING: ["结尾", "收尾", "结局", "结尾怎么写"],
    }

    # 情绪关键词映射
    MOOD_KEYWORDS: dict[VibeMood, list[str]] = {
        VibeMood.SERIOUS: ["严肃", "正式", "庄重"],
        VibeMood.LIGHT: ["轻松", "轻快", "活泼", "日常"],
        VibeMood.TENSE: ["紧张", "悬疑", "刺激", "惊险"],
        VibeMood.ROMANTIC: ["浪漫", "温馨", "甜蜜", "恋爱"],
        VibeMood.MYSTERIOUS: ["神秘", "诡异", "悬疑", "迷雾"],
        VibeMood.EPIC: ["史诗", "宏大", "壮观", "热血"],
        VibeMood.DARK: ["黑暗", "压抑", "阴郁", "沉重"],
        VibeMood.HUMOROUS: ["幽默", "搞笑", "轻松", "吐槽"],
    }

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)

    def detect_intent(
        self, user_input: str, context: VibeContext | None = None
    ) -> tuple[VibeIntent, float]:
        """检测用户写作意图，返回(意图, 置信度)"""
        input_lower = user_input.lower()

        scores: dict[VibeIntent, float] = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in input_lower:
                    score += 1.0
            if score > 0:
                scores[intent] = min(score / len(keywords), 1.0)

        if not scores:
            # 无明确关键词，根据上下文推断
            if context and context.selected_text:
                return VibeIntent.REWRITE, 0.5
            return VibeIntent.CONTINUE, 0.3

        # 返回得分最高的意图
        best = max(scores, key=lambda k: scores[k])
        return best, scores[best]

    def detect_mood(self, user_input: str) -> VibeMood | None:
        """检测期望的情绪/风格"""
        input_lower = user_input.lower()
        for mood, keywords in self.MOOD_KEYWORDS.items():
            for kw in keywords:
                if kw in input_lower:
                    return mood
        return None

    def generate_prompt(
        self,
        intent: VibeIntent,
        context: VibeContext,
        mood: VibeMood | None = None,
        extra_instructions: str = "",
    ) -> str:
        """根据意图生成写作提示词"""
        prompts = {
            VibeIntent.CONTINUE: (
                f"请从以下文本继续写作，保持风格一致：\n\n"
                f"上文：\n{context.current_text[-500:]}\n\n"
                f"请自然流畅地续写下一段。"
            ),
            VibeIntent.REWRITE: (
                f"请改写以下段落，"
                f"{'风格要求：' + mood.value if mood else '保持原意但优化表达'}：\n\n"
                f"原文：\n{context.selected_text or context.current_text[-300:]}\n\n"
                f"{extra_instructions}"
            ),
            VibeIntent.EXPAND: (
                f"请对以下段落进行扩写，增加细节和描写：\n\n"
                f"原文：\n{context.selected_text or context.current_text[-200:]}\n\n"
                f"请增加环境描写、心理活动、动作细节等。"
            ),
            VibeIntent.POLISH: (
                f"请润色以下文本，提升文笔质量，{'保持' + mood.value + '风格，' if mood else ''}"
                f"修正不通顺的句子：\n\n"
                f"原文：\n{context.selected_text or context.current_text[-300:]}"
            ),
            VibeIntent.INSPIRE: (
                f"我正在写{context.genre or '小说'}，当前章节'{context.chapter_title}'。\n"
                f"当前位置的内容是：\n{context.current_text[-300:]}\n\n"
                f"请给我3个不同的写作建议，帮助我继续。"
                f"每个建议包含：发展方向 + 可能的冲突 + 情感走向。"
            ),
            VibeIntent.BRAINSTORM: (
                f"基于以下内容进行头脑风暴，给我5个创意方向：\n\n"
                f"当前内容：\n{context.current_text[-200:]}\n\n"
                f"类型：{context.genre or '不限'}\n"
                f"请大胆发挥，给出意想不到但有逻辑的展开方向。"
            ),
            VibeIntent.OUTLINE: (
                f"请为以下内容生成/调整大纲：\n\n"
                f"现有内容：\n{context.current_text[:500]}\n\n"
                f"类型：{context.genre or '不限'}\n"
                f"请给出结构清晰的大纲，标注关键情节点。"
            ),
            VibeIntent.DIALOGUE: (
                f"请为以下场景写一段对话：\n\n"
                f"场景上下文：\n{context.current_text[-300:]}\n"
                f"场景中的角色："
                + (
                    ", ".join(context.character_in_scene)
                    if context.character_in_scene
                    else "未指定"
                )
                + "\n"
                "请写出自然、有角色辨识度的对话。"
            ),
            VibeIntent.DESCRIPTION: (
                f"请为以下场景添加描写：\n\n"
                f"上下文：\n{context.current_text[-300:]}\n"
                f"请从环境、气氛、感官细节等方面进行描写。"
            ),
            VibeIntent.ACTION: (
                f"请为以下场景写动作场面：\n\n"
                f"上下文：\n{context.current_text[-300:]}\n"
                f"请写出节奏紧凑、画面感强的动作描写。"
            ),
            VibeIntent.TRANSITION: (
                f"请在以下两段之间添加过渡：\n\n"
                f"上一段：\n{context.previous_paragraph[-200:]}\n\n"
                f"当前段：\n{context.current_text[:200]}\n\n"
                f"请写出自然的过渡段落。"
            ),
            VibeIntent.ENDING: (
                f"请为以下内容写一个有力的结尾：\n\n"
                f"内容：\n{context.current_text[-500:]}\n\n"
                f"类型：{context.genre or '不限'}\n"
                f"请写出一个令人印象深刻的收尾。"
            ),
        }

        base_prompt = prompts.get(intent, prompts[VibeIntent.CONTINUE])

        if extra_instructions and intent not in (VibeIntent.REWRITE,):
            base_prompt += f"\n\n额外要求：{extra_instructions}"

        return base_prompt


@dataclass
class VibeParsedIntent:
    """Vibe Writing 意图解析结果（供 /vibe/express API 展示）"""

    scene_type: str = ""
    emotion: str = ""
    pace: str = ""
    intensity: str = ""
    key_elements: list[str] = field(default_factory=list)


class VibeWriter(BaseExtensionModule):
    """随性写作引擎 — 主入口"""

    SUBDIR = "vibe_writer"

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._router = IntentRouter(book_id)
        self._context: VibeContext | None = None
        self._history: list[VibeResponse] = []
        self._response_counter = 0

    async def express(self, user_input: str) -> VibeParsedIntent:
        """解析用户的创作意图（供 /vibe/express API 调用）。

        通过关键词规则从用户输入中提取场景类型、情感基调、节奏与强度，
        供前端展示「已理解意图」的反馈。
        """
        intent, _confidence = self._router.detect_intent(user_input, self._context)
        # 场景类型关键词
        scene_map = {
            "打": "战斗", "战": "战斗", "斗": "战斗", "追": "追逐", "逃": "追逐",
            "说": "对话", "谈": "对话", "问": "对话", "想": "内心", "回忆": "回忆",
            "描写": "环境", "景": "环境", "修炼": "修炼", "突破": "修炼", "交易": "交易",
        }
        # 情感基调关键词
        emo_map = {
            "怒": "愤怒", "激": "兴奋", "激动": "兴奋", "紧张": "紧张", "危急": "紧张",
            "悲": "悲伤", "伤心": "悲伤", "甜": "甜蜜", "暖": "温馨", "开心": "喜悦", "平静": "平静",
        }
        # 节奏关键词
        pace_map = {"快": "快速", "紧凑": "紧凑", "急": "急促", "慢": "舒缓", "悠闲": "舒缓", "稳": "稳健"}
        # 强度关键词
        inten_map = {"激烈": "高", "惨烈": "高", "生死": "高", "高": "强", "轻松": "低", "日常": "低"}

        scene = next((v for k, v in scene_map.items() if k in user_input), "")
        emotion = next((v for k, v in emo_map.items() if k in user_input), "")
        pace = next((v for k, v in pace_map.items() if k in user_input), "")
        intensity = next((v for k, v in inten_map.items() if k in user_input), "")
        key_elements = [intent.value]
        if scene:
            key_elements.append(scene)
        if emotion:
            key_elements.append(emotion)
        if pace:
            key_elements.append(pace)
        return VibeParsedIntent(
            scene_type=scene,
            emotion=emotion,
            pace=pace,
            intensity=intensity,
            key_elements=key_elements,
        )

    def set_context(self, context: VibeContext):
        """设置当前写作上下文"""
        self._context = context
        logger.info(f"写作上下文已更新: {context.chapter_title or '未命名章节'}")

    def get_context(self) -> VibeContext | None:
        return self._context

    def write(
        self,
        user_input: str,
        llm_call: Callable[[str], str] | None = None,
        extra_instructions: str = "",
    ) -> VibeResponse:
        """
        主入口：根据用户输入生成写作内容

        Args:
            user_input: 用户的自然语言输入
            llm_call: LLM调用函数（传入prompt，返回生成文本）
            extra_instructions: 额外指令
        """
        if not self._context:
            self._context = VibeContext()

        # 1. 意图识别
        intent, confidence = self._router.detect_intent(user_input, self._context)
        mood = self._router.detect_mood(user_input)

        # 2. 生成提示词
        prompt = self._router.generate_prompt(intent, self._context, mood, extra_instructions)

        # 3. 调用LLM（如果提供）
        generated_text = ""
        if llm_call:
            try:
                generated_text = llm_call(prompt)
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                generated_text = f"[生成失败: {e}]"

        # 4. 即时质量反馈
        quality_fb = None
        if generated_text and len(generated_text) > 50:
            try:
                from kunlun.vibe_writer.quality_feedback import vibe_quality_feedback
                qf = vibe_quality_feedback.analyze(generated_text, chapter=0)
                quality_fb = qf.to_dict()
            except Exception as e:
                logger.debug(f"质量反馈生成失败: {e}")

        # 5. 构建响应
        self._response_counter += 1
        response = VibeResponse(
            response_id=f"vibe_{self._response_counter}_{int(time.time())}",
            intent=intent,
            generated_text=generated_text,
            suggestions=self._generate_suggestions(intent, generated_text),
            mood=mood,
            explanation=f"检测到意图：{intent.value}（置信度{confidence:.0%}）"
            + (f"，情绪：{mood.value}" if mood else ""),
            word_count=len(generated_text),
            quality_feedback=quality_fb,
        )

        self._history.append(response)
        logger.info(f"VibeWriter生成: {intent.value} ({response.word_count}字)")

        return response

    def get_quality_feedback(self, text: str = "", chapter: int = 0) -> dict | None:
        """获取即时质量反馈"""
        target_text = text or (self._context.current_text if self._context else "")
        if not target_text or len(target_text.strip()) < 20:
            return None
        try:
            from kunlun.vibe_writer.quality_feedback import vibe_quality_feedback
            qf = vibe_quality_feedback.analyze(target_text, chapter)
            return qf.to_dict()
        except Exception as e:
            logger.debug(f"质量反馈失败: {e}")
            return None

    def get_suggestions(self, context: VibeContext | None = None) -> list[str]:
        """获取写作建议（不生成文本，只给建议）"""
        ctx = context or self._context
        if not ctx:
            return ["请先设置写作上下文"]

        suggestions = []
        text = ctx.current_text

        if len(text) < 100:
            suggestions.append("当前内容较短，可以先多写一些再回头优化")
        if len(text) > 2000:
            suggestions.append("当前段落较长，考虑分段或加入对话打破单调")
        if "说" in text[-100:] and "道" not in text[-100:]:
            suggestions.append("对话标签可以更丰富，尝试用动作代替'说'")
        if text.count("。") < 3 and len(text) > 200:
            suggestions.append("句子偏长，适当断句可以提高可读性")

        if not suggestions:
            suggestions = [
                "尝试增加环境描写，营造氛围",
                "加入角色内心独白，增强代入感",
                "埋下一个伏笔，为后续剧情做铺垫",
                "添加感官细节（视觉/听觉/嗅觉），让场景更立体",
            ]

        return suggestions

    def _generate_suggestions(self, intent: VibeIntent, _generated_text: str) -> list[str]:
        """根据意图生成后续建议"""
        suggestion_map = {
            VibeIntent.CONTINUE: [
                "继续写下一段",
                "加入一个意外转折",
                "切换到另一个角色视角",
            ],
            VibeIntent.REWRITE: [
                "如果还不满意，可以换个角度重写",
                "试试用对话来传达同样的信息",
                "缩短这段文字，让它更精炼",
            ],
            VibeIntent.EXPAND: [
                "检查是否有可以增加感官细节的地方",
                "考虑加入角色内心活动",
                "这段扩写可以作为独立的场景发展",
            ],
            VibeIntent.POLISH: [
                "朗读一遍检查节奏",
                "检查是否有重复用词",
                "确保对话标签多样化",
            ],
            VibeIntent.INSPIRE: [
                "选择一个建议开始写作",
                "可以先写大纲再填充细节",
                "从角色的情感出发推动剧情",
            ],
        }

        return suggestion_map.get(intent, ["继续创作", "检查上下文一致性", "考虑读者感受"])

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最近的写作历史"""
        return [r.summary() for r in self._history[-limit:]]

    def clear_history(self):
        """清除写作历史"""
        self._history.clear()
        logger.info("写作历史已清除")


_writers: dict[str, VibeWriter] = {}


def get_vibe_writer(book_id: str = "") -> VibeWriter:
    """获取随性写作引擎实例"""
    if book_id not in _writers:
        _writers[book_id] = VibeWriter(book_id=book_id)
    return _writers[book_id]

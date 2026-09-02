"""
多策略降AI重写引擎

基于 humanize-text 的4种人性化方法论进行深度重构：
  1. 翻译链 (TranslationChain): EN→ZH→JA→FI→EN 跨语种翻译破坏统计指纹
  2. 多轮LLM重写 (MultiPassRewriter): 逐步调整句子节奏、词汇多样性、结构变化
  3. 检测反馈闭环 (FeedbackLoop): 检测→重写→再检测→迭代精修
  4. 规则后处理 (RulePostProcessor): AI词汇替换 + 句子节奏打乱 + 连接词替换

网文特化:
  - 对话口语化（保留角色语气，去除AI味回应）
  - 叙事节奏控制（快节奏打斗、慢节奏日常、中节奏过渡）
  - 文风保持（不改变作者设定的风格标签）
  - 黄金三章规避（开头三章AI检测风险最高，特殊处理）

用法:
    from kunlun.humanize.rewriter import TranslationChain, MultiPassRewriter

    chain = TranslationChain()
    result = await chain.rewrite(text)

    rewriter = MultiPassRewriter()
    result = await rewriter.rewrite(text, passes=2)
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from loguru import logger

from kunlun.humanize.detector import ai_mode_detector
from kunlun.humanize.fingerprint import text_fingerprint


@dataclass
class RewriteResult:
    """重写结果"""

    original: str = ""
    rewritten: str = ""
    strategy: str = ""  # 使用的策略名称
    passes: int = 0  # 实际轮次
    fingerprint_before: dict = field(default_factory=dict)
    fingerprint_after: dict = field(default_factory=dict)
    markers_before: int = 0  # 重写前AI模式命中数
    markers_after: int = 0  # 重写后AI模式命中数
    ai_score_before: float = 0.0
    ai_score_after: float = 0.0
    reduction_pct: float = 0.0  # AI得分降低百分比
    changes_summary: str = ""  # 变更摘要


# ═══════════════════════════════════════════════════════
# 中文网文特化：去AI味Prompt模板
# ═══════════════════════════════════════════════════════

WEBNOVEL_HUMANIZE_SYSTEM_PROMPT = """你是一位资深网文编辑，\
擅长将AI生成的机械文本改写为自然的人类写作风格。

核心原则：
1. 保持原文核心语义和情节不变
2. 降低AI检测率，让文本更符合网文读者的阅读习惯
3. 像朋友讲故事一样写作，而非学术论文

改写要点：
- 连接词替换：然而→可/不过，因此→所以/于是，此外→另外，与此同时→此刻/另一边
- 句式打破：被字句→主动句，长定语→短句拆分，书面倒装→正常语序
- 对话自然化：减少客套话，增加打断和沉默，符合角色身份
- 节奏变化：短句交锋、中句叙事、长句描写交替出现
- 去模板化：避免"嘴角勾起"、"眼神一凝"、"众人震惊"等网文套路
- 用具体描写代替抽象总结

禁止：
- 不要改变角色名称、关系和核心情节
- 不要添加原文没有的信息
- 不要改变叙事视角（第一人称/第三人称）
- 不要输出解释性旁白"""

WEBNOVEL_HUMANIZE_USER_PROMPT = """请改写以下网文章节，使其更自然、更像人类写作：

改写要求：
- 句子长度要有变化（短句3-5字，长句30-50字，交替出现）
- 对话要自然（角色说话符合身份，不要过于礼貌和完整）
- 减少成语堆砌，用具体描写替代
- 段落长度不要均匀（有的段2-3句，有的段5-8句）
- 适当加入口语化表达和网文特有的节奏感
- 保持原有的情节推进和情感走向

原文：
{text}

请直接输出改写后的文本，不要添加任何解释或说明。"""


# ═══════════════════════════════════════════════════════
# 策略1：翻译链 — 跨语种翻译破坏统计指纹
# ═══════════════════════════════════════════════════════

# 翻译链配置：语种跳数越多，统计指纹破坏越彻底，但语义偏移越大
TRANSLATION_CHAINS = {
    "standard": ["en", "zh", "ja", "en"],  # 标准3跳
    "aggressive": ["en", "zh", "ja", "fi", "en"],  # 激进4跳
    "minimal": ["en", "zh", "en"],  # 最小2跳（保真度高）
}


class TranslationChain:
    """
    翻译链重写策略

    原理：通过跨语种翻译破坏文本的统计指纹。
    AI检测器依赖文本的统计特征（perplexity、burstiness等），
    翻译过程会重新组织句子结构、词汇选择，从而改变统计分布。

    网文适配：
    - 使用 standard 链（3跳）作为默认，平衡降AI效果和语义保真
    - 对黄金三章使用 aggressive（4跳）加强效果
    - 对关键情节使用 minimal（2跳）保持语义
    """

    def __init__(self, chain_type: str = "standard"):
        self.chain = TRANSLATION_CHAINS.get(chain_type, TRANSLATION_CHAINS["standard"])
        self._fingerprint = text_fingerprint

    async def rewrite(
        self,
        text: str,
        llm_caller=None,
    ) -> RewriteResult:
        """
        执行翻译链重写

        Args:
            text: 原始文本
            llm_caller: 可选，LLM调用函数 async fn(prompt, system_prompt) -> str
                       如果不提供，使用内置的模拟翻译

        Returns:
            RewriteResult
        """
        if not text or len(text) < 50:
            return RewriteResult(original=text, rewritten=text, strategy="translation_chain")

        before_fp = self._fingerprint.analyze(text)
        before_markers = ai_mode_detector.detect(text)

        if llm_caller:
            rewritten = await self._llm_translation_chain(text, llm_caller)
        else:
            rewritten = self._rule_based_chain(text)

        after_fp = self._fingerprint.analyze(rewritten)
        after_markers = ai_mode_detector.detect(rewritten)

        reduction = 0.0
        if before_fp.ai_likelihood > 0:
            reduction = (
                (before_fp.ai_likelihood - after_fp.ai_likelihood) / before_fp.ai_likelihood * 100
            )

        return RewriteResult(
            original=text,
            rewritten=rewritten,
            strategy=f"translation_chain ({len(self.chain) - 1} hops)",
            passes=1,
            fingerprint_before={
                "perplexity": round(before_fp.perplexity_score, 2),
                "burstiness": round(before_fp.burstiness, 3),
                "ai_likelihood": round(before_fp.ai_likelihood, 3),
            },
            fingerprint_after={
                "perplexity": round(after_fp.perplexity_score, 2),
                "burstiness": round(after_fp.burstiness, 3),
                "ai_likelihood": round(after_fp.ai_likelihood, 3),
            },
            markers_before=before_markers.total_markers,
            markers_after=after_markers.total_markers,
            ai_score_before=before_fp.ai_likelihood,
            ai_score_after=after_fp.ai_likelihood,
            reduction_pct=round(reduction, 1),
            changes_summary=f"翻译链 {len(self.chain) - 1} 跳: "
            f"AI得分 {before_fp.ai_likelihood:.2f}→{after_fp.ai_likelihood:.2f} "
            f"({reduction:.0f}%)",
        )

    async def _llm_translation_chain(self, text: str, llm_caller) -> str:
        """使用LLM执行翻译链"""
        current = text
        for i, src_lang in enumerate(self.chain[:-1]):
            tgt_lang = self.chain[i + 1]
            prompt = (
                f"Translate the following text from {src_lang} to {tgt_lang}. "
                f"Make it sound natural in {tgt_lang}, not like a machine translation.\n\n"
                f"{current}"
            )
            try:
                current = await llm_caller(prompt, "You are a professional literary translator.")
            except Exception as e:
                logger.warning(f"翻译链第{i + 1}跳失败: {e}")
                break
        return current

    def _rule_based_chain(self, text: str) -> str:
        """
        基于规则的模拟翻译链

        原理：通过多层文本变换模拟翻译过程对统计指纹的破坏：
        1. 句子重组（改变语序）
        2. 词汇替换（同义词）
        3. 结构打乱（拆分合并）
        4. 连接词替换
        """
        result = text

        # 第1层：连接词替换
        result = self._replace_conjunctions(result)

        # 第2层：句子结构变换
        result = self._shuffle_sentence_structure(result)

        # 第3层：词汇多样性注入
        result = self._inject_vocabulary_variety(result)

        # 第4层：句子长度调整
        result, _ = text_fingerprint.optimize(result, target_burstiness=0.45, target_cv=0.55)

        return result

    def _replace_conjunctions(self, text: str) -> str:
        """替换AI味连接词"""
        replacements = [
            ("然而", random.choice(["可", "不过", "但偏偏", "谁知"])),
            ("因此", random.choice(["所以", "于是乎", "这下"])),
            ("此外", random.choice(["另外", "还有", "再说"])),
            ("与此同时", random.choice(["此刻", "另一边", "这时候"])),
            ("总而言之", random.choice(["说白了", "一句话", ""])),
            ("不可否认", random.choice(["确实", "说实话", ""])),
            ("值得注意的是", random.choice(["注意", "关键是", ""])),
            ("综上所述", ""),
            ("首先", random.choice(["先", "头一个", ""])),
            ("其次", random.choice(["然后", "接着", ""])),
        ]
        result = text
        for old, new in replacements:
            if old in result:
                result = result.replace(old, new)
        return result

    def _shuffle_sentence_structure(self, text: str) -> str:
        """句子结构变换：被字句→主动句，长定语拆分"""
        # 被字句→主动句
        passive_pattern = re.compile(r"([^，。！？\n]{2,15})被([^，。！？\n]{2,20})([了过到得着])")

        def _active(m):
            return f"{m.group(2)}{m.group(3)}{m.group(1)}"

        # 只替换部分被字句（约40%），避免过度变换
        matches = list(passive_pattern.finditer(text))
        if matches:
            # 随机选择40%进行替换
            selected = random.sample(matches, max(1, int(len(matches) * 0.4)))
            # 从后往前替换，保持位置索引
            for m in sorted(selected, key=lambda x: x.start(), reverse=True):
                text = text[: m.start()] + _active(m) + text[m.end() :]

        return text

    def _inject_vocabulary_variety(self, text: str) -> str:
        """注入词汇多样性"""
        # 高频AI词汇 → 随机替换
        variety_map = {
            "展现": random.choice(["显出", "露出", "透出", "呈现"]),
            "呈现": random.choice(["显出", "展现", "露出"]),
            "充满": random.choice(["满是", "尽是", "弥漫"]),
            "显得": random.choice(["看起来", "似乎", ""]),
            "感到": random.choice(["觉得", "只觉", "心头"]),
            "发现": random.choice(["察觉", "注意到", "看出"]),
            "认为": random.choice(["觉得", "想", "认定"]),
            "决定": random.choice(["打定主意", "下了决心", "心一横"]),
            "出现": random.choice(["冒出来", "浮现", "现身"]),
            "产生": random.choice(["生出", "涌起", "冒出"]),
            "进行": random.choice(["展开", "动手", ""]),
            "实现": random.choice(["达成", "做到", "完成"]),
        }
        result = text
        for word, replacement in variety_map.items():
            if word in result and replacement:
                # 只替换部分出现（约50%）
                count = result.count(word)
                if count > 1:
                    # 随机替换一半
                    positions = [i for i in range(len(result)) if result.startswith(word, i)]
                    for pos in random.sample(positions, max(1, count // 2)):
                        result = result[:pos] + replacement + result[pos + len(word) :]
                elif random.random() < 0.5:
                    result = result.replace(word, replacement, 1)
        return result


# ═══════════════════════════════════════════════════════
# 策略2：多轮LLM重写 — 逐步调整文本特征
# ═══════════════════════════════════════════════════════


class MultiPassRewriter:
    """
    多轮LLM重写策略

    原理：通过多轮LLM调用，每轮专注于不同的文本特征调整：
    - 第1轮：连接词替换 + 句式打破
    - 第2轮：词汇多样性 + 节奏调整
    - 第3轮：对话自然化 + 统计指纹优化

    网文适配：
    - 每轮使用不同的temperature（1.1→1.2→1.0）逐步收敛
    - 保留角色名称和关键情节元素
    """

    def __init__(self, max_passes: int = 3):
        self.max_passes = max_passes
        self._fingerprint = text_fingerprint
        self._detector = ai_mode_detector

    async def rewrite(
        self,
        text: str,
        passes: int = 2,
        llm_caller=None,
        chapter_type: str = "normal",  # normal / opening / climax / daily
    ) -> RewriteResult:
        """
        执行多轮重写

        Args:
            text: 原始文本
            passes: 重写轮次（1-3）
            llm_caller: LLM调用函数
            chapter_type: 章节类型（影响重写策略）

        Returns:
            RewriteResult
        """
        if not text or len(text) < 50:
            return RewriteResult(original=text, rewritten=text, strategy="multi_pass")

        before_fp = self._fingerprint.analyze(text)
        before_markers = self._detector.detect(text)

        current = text
        actual_passes = 0

        for p in range(min(passes, self.max_passes)):
            if llm_caller:
                current = await self._llm_pass(current, p, llm_caller, chapter_type)
            else:
                current = self._rule_pass(current, p, chapter_type)
            actual_passes += 1

            # 中途检测：如果已经大幅改善，提前终止
            mid_fp = self._fingerprint.analyze(current)
            if mid_fp.ai_likelihood < 0.25:
                logger.info(
                    f"MultiPassRewriter: 第{p + 1}轮后AI得分已降至"
                    f"{mid_fp.ai_likelihood:.2f}，提前终止"
                )
                break

        after_fp = self._fingerprint.analyze(current)
        after_markers = self._detector.detect(current)

        reduction = 0.0
        if before_fp.ai_likelihood > 0:
            reduction = (
                (before_fp.ai_likelihood - after_fp.ai_likelihood) / before_fp.ai_likelihood * 100
            )

        return RewriteResult(
            original=text,
            rewritten=current,
            strategy=f"multi_pass ({actual_passes} passes)",
            passes=actual_passes,
            fingerprint_before={
                "perplexity": round(before_fp.perplexity_score, 2),
                "burstiness": round(before_fp.burstiness, 3),
                "ai_likelihood": round(before_fp.ai_likelihood, 3),
            },
            fingerprint_after={
                "perplexity": round(after_fp.perplexity_score, 2),
                "burstiness": round(after_fp.burstiness, 3),
                "ai_likelihood": round(after_fp.ai_likelihood, 3),
            },
            markers_before=before_markers.total_markers,
            markers_after=after_markers.total_markers,
            ai_score_before=before_fp.ai_likelihood,
            ai_score_after=after_fp.ai_likelihood,
            reduction_pct=round(reduction, 1),
            changes_summary=f"多轮重写 {actual_passes} 轮: "
            f"AI得分 {before_fp.ai_likelihood:.2f}→{after_fp.ai_likelihood:.2f}",
        )

    async def _llm_pass(self, text: str, pass_num: int, llm_caller, chapter_type: str) -> str:
        """LLM驱动的单轮重写"""

        pass_focus = {
            0: "打破AI句式结构（被字句→主动句、长定语拆分、书面倒装→口语化）",
            1: "增加词汇多样性和句子节奏变化（短句3-5字、长句30-50字交替）",
            2: "对话自然化和细节描写（减少成语堆砌、增加感官细节）",
        }

        focus = pass_focus.get(pass_num, pass_focus[0])

        prompt = WEBNOVEL_HUMANIZE_USER_PROMPT.format(text=text)
        prompt += f"\n\n本轮重点: {focus}"
        if chapter_type == "opening":
            prompt += "\n额外要求: 这是开头章节，需要更加自然，避免任何AI痕迹。"

        try:
            return await llm_caller(prompt, WEBNOVEL_HUMANIZE_SYSTEM_PROMPT)
        except Exception as e:
            logger.warning(f"MultiPassRewriter 第{pass_num + 1}轮失败: {e}")
            return text

    def _rule_pass(self, text: str, pass_num: int, chapter_type: str) -> str:
        """基于规则的单轮重写（零LLM成本）"""
        result = text

        if pass_num == 0:
            # 第1轮：连接词替换 + 句式打破
            chain = TranslationChain("minimal")
            result = chain._replace_conjunctions(result)
            result = chain._shuffle_sentence_structure(result)

        elif pass_num == 1:
            # 第2轮：词汇多样性 + 统计优化
            chain = TranslationChain("standard")
            result = chain._inject_vocabulary_variety(result)
            result, _ = text_fingerprint.optimize(result, target_burstiness=0.45, target_cv=0.55)

        else:
            # 第3轮：对话优化 + 节奏调整
            result = self._optimize_dialogue(result)
            # 针对开头章节更激进
            if chapter_type == "opening":
                chain = TranslationChain("aggressive")
                result = chain._replace_conjunctions(result)
                result = chain._inject_vocabulary_variety(result)

        return result

    def _optimize_dialogue(self, text: str) -> str:
        """优化对话：去除AI味回应，增加自然打断"""
        # 去除AI味对话回应
        ai_responses = [
            "你说得对",
            "我明白了",
            "原来如此",
            "这倒是个问题",
            "确实如此",
            "有道理",
            "说得没错",
            "我懂了",
        ]
        for resp in ai_responses:
            if resp in text:
                text = text.replace(resp, random.choice(["行", "懂了", "啧", "嗯", "……"]))

        # 在连续对话中插入动作打断
        dialogue_markers = list(re.finditer(r'[""「」]([^""「」]{10,60})[""「」]', text))
        if len(dialogue_markers) >= 3:
            # 在第2句对话后插入动作描述
            for i in range(1, len(dialogue_markers) - 1, 3):
                pos = dialogue_markers[i].end()
                action = random.choice(
                    [
                        "他顿了顿，",
                        "她抬眼看过去，",
                        "沉默片刻，",
                        "他摆摆手，",
                        "她转过身，",
                    ]
                )
                text = text[:pos] + action + text[pos:]

        return text


# ═══════════════════════════════════════════════════════
# 策略3：检测反馈闭环 — 迭代精修
# ═══════════════════════════════════════════════════════


class FeedbackLoop:
    """
    检测反馈闭环策略

    原理：改写→检测→定位问题段落→针对性重写→再检测
    持续迭代直到AI得分降至阈值以下或达到最大迭代次数。

    这是 humanize-text 方案三的核心思路，重构为独立闭环引擎。
    """

    def __init__(
        self,
        target_score: float = 0.25,
        max_iterations: int = 5,
    ):
        self.target_score = target_score
        self.max_iterations = max_iterations
        self._fingerprint = text_fingerprint
        self._detector = ai_mode_detector

    async def rewrite(
        self,
        text: str,
        llm_caller=None,
    ) -> RewriteResult:
        """
        执行检测反馈闭环

        Args:
            text: 原始文本
            llm_caller: LLM调用函数

        Returns:
            RewriteResult
        """
        if not text or len(text) < 50:
            return RewriteResult(original=text, rewritten=text, strategy="feedback_loop")

        before_fp = self._fingerprint.analyze(text)
        before_markers = self._detector.detect(text)

        current = text
        iterations = 0

        for i in range(self.max_iterations):
            # 1. 检测当前文本
            fp = self._fingerprint.analyze(current)
            detection = self._detector.detect(current)

            # 2. 检查是否已达到目标
            if fp.ai_likelihood <= self.target_score:
                logger.info(f"FeedbackLoop: 第{i + 1}轮达到目标 ({fp.ai_likelihood:.2f})")
                break

            # 3. 定位问题段落
            problem_segments = self._identify_problem_segments(current, fp, detection)

            # 4. 针对性重写
            if problem_segments and llm_caller:
                current = await self._targeted_rewrite(current, problem_segments, llm_caller)
            else:
                # 无LLM时使用规则处理
                current = self._rule_targeted_fix(current, fp, detection)

            iterations += 1

        after_fp = self._fingerprint.analyze(current)
        after_markers = self._detector.detect(current)

        reduction = 0.0
        if before_fp.ai_likelihood > 0:
            reduction = (
                (before_fp.ai_likelihood - after_fp.ai_likelihood) / before_fp.ai_likelihood * 100
            )

        return RewriteResult(
            original=text,
            rewritten=current,
            strategy=f"feedback_loop ({iterations} iterations)",
            passes=iterations,
            fingerprint_before={
                "perplexity": round(before_fp.perplexity_score, 2),
                "burstiness": round(before_fp.burstiness, 3),
                "ai_likelihood": round(before_fp.ai_likelihood, 3),
            },
            fingerprint_after={
                "perplexity": round(after_fp.perplexity_score, 2),
                "burstiness": round(after_fp.burstiness, 3),
                "ai_likelihood": round(after_fp.ai_likelihood, 3),
            },
            markers_before=before_markers.total_markers,
            markers_after=after_markers.total_markers,
            ai_score_before=before_fp.ai_likelihood,
            ai_score_after=after_fp.ai_likelihood,
            reduction_pct=round(reduction, 1),
            changes_summary=f"反馈闭环 {iterations} 轮迭代: "
            f"AI得分 {before_fp.ai_likelihood:.2f}→{after_fp.ai_likelihood:.2f}",
        )

    def _identify_problem_segments(self, _text: str, fp, detection) -> list[dict]:
        """识别问题段落"""
        problems: list[dict] = []

        # 从统计指纹中获取可疑句子
        if fp.flagged_segments:
            problems.extend(
                {
                    "text": seg,
                    "reason": "统计指纹异常（低困惑度/低突发性）",
                    "severity": "high",
                }
                for seg in fp.flagged_segments[:3]
            )

        # 从模式检测中获取
        for marker in detection.markers:
            if marker.severity > 0.7 and marker.examples:
                problems.extend(
                    {
                        "text": ex,
                        "reason": f"AI模式: {marker.name}",
                        "severity": "high" if marker.severity > 0.8 else "medium",
                    }
                    for ex in marker.examples[:2]
                )

        return problems[:5]  # 最多5个问题段落

    async def _targeted_rewrite(self, text: str, problems: list[dict], llm_caller) -> str:
        """针对问题段落的重写"""
        result = text
        for problem in problems:
            problem_text = problem["text"]
            if problem_text in result:
                prompt = (
                    f"改写以下文本片段，使其更自然。\n"
                    f"问题: {problem['reason']}\n\n"
                    f"原文: {problem_text}\n\n"
                    f"改写后（保持原意，只改表达方式）:"
                )
                try:
                    rewritten = await llm_caller(
                        prompt, "你是文字编辑，只改写表达方式，不改原意。直接输出改写结果。"
                    )
                    if rewritten and len(rewritten) > len(problem_text) * 0.5:
                        result = result.replace(problem_text, rewritten, 1)
                except Exception as e:
                    logger.warning(f"针对性重写失败: {e}")

        return result

    def _rule_targeted_fix(self, text: str, _fp, detection) -> str:
        """基于规则的问题修复"""
        result = text
        processor = RulePostProcessor()
        result = processor.process(result, detection)
        # 统计优化
        result, _ = text_fingerprint.optimize(result)
        return result


# ═══════════════════════════════════════════════════════
# 策略4：规则后处理 — 零LLM成本，快速去AI味
# ═══════════════════════════════════════════════════════


class RulePostProcessor:
    """
    规则后处理器

    零LLM成本，纯规则替换 + 结构变换。
    与现有的 style/refiner.py 和 style/engineer.py 互补：
    - refiner.py: 去套路词、过度描写
    - engineer.py: 句式CV调整、连接词替换、句首多样性
    - 本模块: 去AI模式标记、统计指纹优化、对话自然化

    网文特化规则：
    - AI词汇替换表（30+ 英文信号词 + 11+ 中文套话短语）
    - 句子节奏打乱（合并短句、打破均匀长度模式）
    - 连接词自然化
    - 成语堆砌检测
    """

    def __init__(self):
        self._fingerprint = text_fingerprint

    def process(self, text: str, detection=None) -> str:
        """
        执行规则后处理

        Args:
            text: 原始文本
            detection: 可选的检测报告，用于针对性处理

        Returns:
            处理后文本
        """
        if not text or len(text) < 50:
            return text

        result = text

        # 1. 去AI模式标记（基于检测结果或默认规则）
        result = self._remove_ai_markers(result, detection)

        # 2. 连接词自然化
        result = self._naturalize_conjunctions(result)

        # 3. 成语堆砌检测与替换
        result = self._reduce_idiom_clusters(result)

        # 4. 统计指纹优化
        result, _ = self._fingerprint.optimize(result, target_burstiness=0.45, target_cv=0.55)

        # 5. 后处理清理
        return self._cleanup(result)

    def _remove_ai_markers(self, text: str, detection) -> str:
        """移除AI模式标记"""
        result = text

        # 基础替换：无论检测结果如何都执行
        basic_replacements = [
            # 内容模式
            (r"标志着", "说明"),
            (r"见证了", "经历了"),
            (r"奠定了", "打下了"),
            (r"重塑了", "改变了"),
            # 语言模式
            (r"此外，", "另外，"),
            (r"至关重要", "很重要"),
            (r"深入探讨", "讨论"),
            (r"格局", "局面"),
            (r"织锦", "画面"),
            (r"画卷", "景象"),
            # 填充模式
            (r"值得注意的是，", ""),
            (r"需要指出的是，", ""),
            (r"不可否认的是，", "确实，"),
            (r"总而言之，", ""),
            (r"综上所述，", ""),
        ]

        for pattern, replacement in basic_replacements:
            if pattern in result:
                result = result.replace(pattern, replacement)

        # 基于检测结果的针对性替换
        if detection:
            for marker in detection.markers:
                if marker.name == "AI词汇过度" and marker.examples:
                    for ex in marker.examples:
                        if ex in result and len(ex) > 1:
                            # 不直接删除，而是标记（保留内容）
                            pass

        return result

    def _naturalize_conjunctions(self, text: str) -> str:
        """连接词自然化"""
        # 每次出现的连接词随机选择一个替换
        replacements = {
            "然而": ["可", "不过", "但偏偏", "谁知", "哪料"],
            "因此": ["所以", "于是乎", "这下", "这么一来"],
            "于是": ["接着", "然后", "便", ""],
            "此外": ["另外", "还有", "再说", "况且"],
            "与此同时": ["此刻", "另一边", "这时候", "同一时间"],
            "显而易见": ["明摆着", "谁都看得出来", "不用说了"],
            "毋庸置疑": ["没得说", "毫无疑问", "肯定"],
        }

        result = text
        for word, alternatives in replacements.items():
            while word in result:
                replacement = random.choice(alternatives)
                result = result.replace(word, replacement, 1)

        return result

    def _reduce_idiom_clusters(self, text: str) -> str:
        """减少成语堆砌"""
        # 检测连续2个以上四字成语
        idiom_pattern = re.compile(
            r"[\u4e00-\u9fff]{4}[，、\s]*[\u4e00-\u9fff]{4}[，、\s]*[\u4e00-\u9fff]{4}"
        )
        matches = idiom_pattern.findall(text)

        for match in matches:
            # 保留第一个成语，将后续成语替换为具体描述
            if len(match) >= 12:  # 至少3个四字词
                # 提取成语部分
                idioms = re.findall(r"[\u4e00-\u9fff]{4}", match)
                if len(idioms) >= 3:
                    # 保留第一个，标记后续需要替换
                    replacement = idioms[0]
                    if len(idioms) > 1:
                        replacement += "，" + "很" + random.choice(["厉害", "惊人", "可怕", "强势"])
                    text = text.replace(match, replacement, 1)

        return text

    def _cleanup(self, text: str) -> str:
        """后处理清理"""
        # 清理连续标点
        text = re.sub(r"[，,]{2,}", "，", text)
        text = re.sub(r"[。.]{2,}", "。", text)
        # 清理多余空格
        text = re.sub(r" {2,}", " ", text)
        # 清理空括号
        text = text.replace("（）", "")
        return text.replace("()", "")


# 全局单例
translation_chain = TranslationChain()
multi_pass_rewriter = MultiPassRewriter()
feedback_loop = FeedbackLoop()
rule_post_processor = RulePostProcessor()

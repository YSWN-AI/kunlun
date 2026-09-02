"""
文风指纹系统 — 统计指纹提取 + 风格注入

对应 inkos style analyze / style import 命令

核心流程:
  1. StyleAnalyzer.analyze(text) → StyleFingerprint (统计指纹)
  2. StyleAnalyzer.generate_style_guide(fp) → LLM 生成风格指南
  3. StyleInjector.build_style_prompt(fp) → 注入到 Writer prompt

使用方式:
    from kunlun.style.fingerprint import style_analyzer, style_injector

    # 分析参考文本
    fp = style_analyzer.analyze(reference_text, name="名家风格")
    await style_analyzer.generate_style_guide(fp)

    # 保存/加载
    style_analyzer.save_fingerprint(fp, "my_book")
    fp_loaded = style_analyzer.load_fingerprint("my_book")

    # 注入到创作
    style_prompt = style_injector.build_style_prompt(fp)
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from loguru import logger

from kunlun.config import settings


@dataclass
class StyleFingerprint:
    """文风统计指纹

    包含全文的统计特征,用于:
    - 风格分析: 句长/词频/节奏/对话等维度的量化描述
    - 风格注入: 将特征转化为创作提示词
    - 风格对比: 两个指纹之间的相似度计算
    """

    name: str = ""
    source: str = ""  # 参考文本来源/作者

    # ── 句长分布 ──
    avg_sentence_length: float = 0.0
    sentence_length_std: float = 0.0
    sentence_length_histogram: list[int] = field(default_factory=lambda: [0] * 10)
    # 桶: 0-10, 10-20, 20-30, ..., 80-90, 90-100, 100+

    # ── 词频特征 ──
    top_words: list[tuple[str, int]] = field(default_factory=list)  # top-20词
    word_diversity: float = 0.0  # 独特词数 / 总词数

    # ── 节奏模式 ──
    paragraph_length_pattern: list[int] = field(default_factory=list)  # 连续段落长度序列
    avg_paragraph_length: float = 0.0
    paragraph_length_cv: float = 0.0  # 变异系数

    # ── 对话特征 ──
    dialogue_ratio: float = 0.0  # 对话字数 / 总字数
    avg_dialogue_length: float = 0.0  # 平均每句对话长度

    # ── 标点偏好 ──
    punctuation_distribution: dict = field(default_factory=dict)

    # ── LLM生成 ──
    style_guide: str = ""  # 由LLM生成的风格描述


class StyleAnalyzer:
    """文风分析器 — 从参考文本提取统计指纹

    分析维度:
    1. 句长分布 (平均、标准差、直方图)
    2. 词汇特征 (高频词、词汇多样性)
    3. 段落节奏 (平均长度、变异系数、序列模式)
    4. 对话特征 (占比、平均长度)
    5. 标点偏好 (逗号、句号、感叹号等的使用频率)
    """

    def analyze(self, text: str, name: str = "reference") -> StyleFingerprint:
        """分析文本,提取统计指纹

        Args:
            text: 参考文本
            name: 指纹名称

        Returns:
            StyleFingerprint 对象
        """
        fp = StyleFingerprint(name=name, source=text[:100])

        # ── 1. 句长分析 ──
        sentences = re.split(r"[。！？.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            lengths = [len(s) for s in sentences]
            fp.avg_sentence_length = sum(lengths) / len(lengths)
            if len(lengths) > 1:
                variance = sum((v - fp.avg_sentence_length) ** 2 for v in lengths) / len(lengths)
                fp.sentence_length_std = math.sqrt(variance)
            else:
                fp.sentence_length_std = 0.0

            # 直方图: 每10字一个桶
            for v in lengths:
                bucket = min(v // 10, 9)
                fp.sentence_length_histogram[bucket] += 1

        # ── 2. 词汇特征 ──
        # 多字词（用于 top_words 和多样性计算）
        multi_words = re.findall(r"[一-鿿]{2,}", text)
        # 单字词（补充）
        single_words = re.findall(r"[一-鿿]", text)
        all_words = multi_words + single_words
        if all_words:
            word_counts = Counter(all_words)
            fp.top_words = word_counts.most_common(20)
            fp.word_diversity = len(word_counts) / max(len(all_words), 1)

        # ── 3. 段落节奏 ──
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            para_lens = [len(p) for p in paragraphs]
            fp.paragraph_length_pattern = para_lens[:20]  # 前20段
            fp.avg_paragraph_length = sum(para_lens) / len(para_lens)
            if len(para_lens) > 1 and fp.avg_paragraph_length > 0:
                variance = sum((v - fp.avg_paragraph_length) ** 2 for v in para_lens) / len(
                    para_lens
                )
                fp.paragraph_length_cv = math.sqrt(variance) / fp.avg_paragraph_length
            else:
                fp.paragraph_length_cv = 0.0

        # ── 4. 对话特征 ──
        dialogues = re.findall(r'[「「""]([^」」""]+)[」」""]', text)
        all_text_len = max(len(text), 1)
        dialogue_chars = sum(len(d) for d in dialogues)
        fp.dialogue_ratio = dialogue_chars / all_text_len
        fp.avg_dialogue_length = dialogue_chars / len(dialogues) if dialogues else 0

        # ── 5. 标点分布 ──
        puncts = [
            ",",
            "，",
            "。",
            "！",
            "？",
            "、",
            "…",
            "；",
            "：",
            '"',
            "「",
            "」",
            "——",
            "《",
            "》",
        ]
        fp.punctuation_distribution = {p: text.count(p) for p in puncts}

        logger.info(
            f'[StyleAnalyzer] 指纹"{name}"提取完成: '
            f"句长{int(fp.avg_sentence_length)}字, "
            f"段长{int(fp.avg_paragraph_length)}字, "
            f"对话{fp.dialogue_ratio:.0%}, "
            f"词多样性{fp.word_diversity:.2f}"
        )
        return fp

    async def generate_style_guide(self, fp: StyleFingerprint) -> str:
        """通过LLM生成风格指南

        将统计指纹发送给LLM,生成人类可读的写作风格描述。
        这个描述会被注入到Writer的prompt中,指导风格模仿。

        使用 gacha_engine.generate() 调用真实模型,不使用mock数据。

        Args:
            fp: 统计指纹

        Returns:
            风格指南文本
        """
        from kunlun.gacha.engine import gacha_engine

        stats = f"""文风统计:
- 平均句长: {fp.avg_sentence_length:.1f}字 (标准差: {fp.sentence_length_std:.1f})
- 句长直方图(10字桶): {fp.sentence_length_histogram}
- 平均段长: {fp.avg_paragraph_length:.1f}字 (变异系数: {fp.paragraph_length_cv:.2f})
- 对话占比: {fp.dialogue_ratio:.1%}
- 平均对话长度: {fp.avg_dialogue_length:.1f}字
- 词汇多样性: {fp.word_diversity:.2%}
- 高频词Top10: {dict(fp.top_words[:10])}
- 标点分布: {fp.punctuation_distribution}
"""

        prompt = f"""你是文风分析师。根据以下统计指纹,生成一份简洁的写作风格指南。

{stats}

请输出:
1. 风格定位（1句话概括）
2. 句式特点（2-3条建议，基于句长/标准差/直方图）
3. 段落节奏建议（基于变异系数）
4. 词汇倾向（基于高频词）
5. 对话风格（基于对话占比/平均长度）
6. 去AI味要点（对抗AI生成倾向的具体建议）

格式：直接输出，每条一行，总字数不超过200字。"""

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            fp.style_guide = result.get("best_text", "")
            if not fp.style_guide:
                logger.warning("[StyleAnalyzer] LLM风格指南生成返回空")
            else:
                logger.info(f"[StyleAnalyzer] 风格指南生成完成: {fp.style_guide[:50]}...")
            return fp.style_guide
        except Exception as e:
            logger.error(f"[StyleAnalyzer] LLM风格指南生成失败: {e}")
            # 回退：基于统计数据生成简单的规则指南
            fp.style_guide = self._fallback_style_guide(fp)
            return fp.style_guide

    def _fallback_style_guide(self, fp: StyleFingerprint) -> str:
        """LLM不可用时的回退风格指南（基于统计规则生成）"""
        lines = ["风格指南(规则生成):"]

        # 句长
        if fp.avg_sentence_length < 20:
            lines.append("- 短句风格,简洁有力,适合快节奏叙事")
        elif fp.avg_sentence_length > 40:
            lines.append("- 长句风格,细腻丰富,适合深度描写")
        else:
            lines.append("- 长短结合,叙事节奏均衡")

        # 段落节奏
        if fp.paragraph_length_cv > 0.5:
            lines.append("- 段落长短交替,节奏感强")
        else:
            lines.append("- 段落结构稳定,适合平缓叙事")

        # 对话
        if fp.dialogue_ratio > 0.3:
            lines.append("- 对话驱动,角色互动丰富")
        elif fp.dialogue_ratio < 0.1:
            lines.append("- 叙述为主,对话精简")

        # 词汇
        if fp.word_diversity > 0.3:
            lines.append("- 词汇丰富,表达多元")
        else:
            lines.append("- 词汇集中,风格统一")

        return "\n".join(lines)

    def save_fingerprint(self, fp: StyleFingerprint, book_id: str):
        """保存指纹到 data/style/{book_id}/fingerprint.json

        Args:
            fp: 风格指纹
            book_id: 作品ID
        """
        path = settings.DATA_DIR / "style" / book_id
        path.mkdir(parents=True, exist_ok=True)

        data = {k: v for k, v in fp.__dict__.items() if not k.startswith("_")}
        # 序列化 tuple 为 list (JSON不支持tuple)
        if "top_words" in data:
            data["top_words"] = [[w, c] for w, c in data["top_words"]]

        (path / "fingerprint.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"[StyleAnalyzer] 指纹已保存: {path / 'fingerprint.json'}")

    def load_fingerprint(self, book_id: str) -> StyleFingerprint | None:
        """加载已保存的指纹

        Args:
            book_id: 作品ID

        Returns:
            StyleFingerprint 或 None
        """
        path = settings.DATA_DIR / "style" / book_id / "fingerprint.json"
        if not path.exists():
            logger.info(f"[StyleAnalyzer] 未找到已保存的指纹: {path}")
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fp = StyleFingerprint()
            for k, v in data.items():
                if hasattr(fp, k):
                    # 还原 tuple
                    if k == "top_words" and isinstance(v, list):
                        v = [(item[0], item[1]) for item in v if isinstance(item, list)]  # noqa: PLW2901
                    setattr(fp, k, v)
            logger.info(f"[StyleAnalyzer] 指纹已加载: {path}")
            return fp
        except Exception as e:
            logger.error(f"[StyleAnalyzer] 指纹加载失败: {e}")
            return None

    def compare(self, fp1: StyleFingerprint, fp2: StyleFingerprint) -> float:
        """比较两个指纹的相似度 (0.0 ~ 1.0)

        用于评估生成文本与参考风格的匹配程度。

        Args:
            fp1: 指纹1
            fp2: 指纹2

        Returns:
            相似度分数
        """
        scores = []

        # 句长相似度
        if fp1.avg_sentence_length > 0 and fp2.avg_sentence_length > 0:
            ratio = min(fp1.avg_sentence_length, fp2.avg_sentence_length) / max(
                fp1.avg_sentence_length, fp2.avg_sentence_length
            )
            scores.append(ratio * 0.25)

        # 段长CV相似度
        cv_diff = abs(fp1.paragraph_length_cv - fp2.paragraph_length_cv)
        scores.append(max(0, 1 - cv_diff) * 0.15)

        # 对话占比相似度
        diag_diff = abs(fp1.dialogue_ratio - fp2.dialogue_ratio)
        scores.append(max(0, 1 - diag_diff * 2) * 0.25)

        # 词汇多样性相似度
        div_diff = abs(fp1.word_diversity - fp2.word_diversity)
        scores.append(max(0, 1 - div_diff * 3) * 0.15)

        # 句长标准差相似度
        if fp1.sentence_length_std > 0 and fp2.sentence_length_std > 0:
            std_ratio = min(fp1.sentence_length_std, fp2.sentence_length_std) / max(
                fp1.sentence_length_std, fp2.sentence_length_std
            )
            scores.append(std_ratio * 0.20)

        similarity = sum(scores) / sum([0.25, 0.15, 0.25, 0.15, 0.20])
        return round(min(1.0, max(0.0, similarity)), 3)


class StyleInjector:
    """风格注入器 — 将指纹注入到 Writer prompt 中

    将统计数据转化为自然语言创作约束,注入到 Writer 的系统提示中,
    使生成文本朝参考风格靠拢。
    """

    def build_style_prompt(self, fp: StyleFingerprint) -> str:
        """从指纹构建风格提示词

        生成的提示词可直接注入到 Writer 的 system prompt 中。

        Args:
            fp: 风格指纹

        Returns:
            风格提示词字符串
        """
        if not fp:
            return ""

        parts = ["## 文风要求\n"]

        # LLM生成的风格指南优先
        if fp.style_guide:
            parts.append(fp.style_guide + "\n")

        # 句式特征
        if fp.avg_sentence_length > 0:
            if fp.avg_sentence_length < 20:
                parts.append(
                    f"- 句式: 短句为主（平均{int(fp.avg_sentence_length)}字/句），"
                    f"简洁有力，避免冗长修饰"
                )
            elif fp.avg_sentence_length > 40:
                parts.append(
                    f"- 句式: 长句为主（平均{int(fp.avg_sentence_length)}字/句），"
                    f"细腻丰富，注重细节展开"
                )
            else:
                parts.append(
                    f"- 句式: 长短结合（平均{int(fp.avg_sentence_length)}字/句），"
                    f"根据场景需求灵活切换"
                )

            # 句长标准差
            if fp.sentence_length_std > 15:
                parts.append(
                    f"- 句长变化: 大（标准差{fp.sentence_length_std:.0f}），长短句交替使用"
                )
            elif fp.sentence_length_std < 5 and fp.avg_sentence_length > 10:
                parts.append(f"- 句长变化: 小（标准差{fp.sentence_length_std:.0f}），句长保持稳定")

        # 段落节奏
        if fp.paragraph_length_cv > 0.5:
            parts.append(
                f"- 段落: 长短交替（CV={fp.paragraph_length_cv:.2f}），避免均匀段落（AI特征）"
            )
        elif fp.paragraph_length_cv > 0.01 and fp.paragraph_length_cv <= 0.5:
            parts.append(f"- 段落: 结构稳定（CV={fp.paragraph_length_cv:.2f}），适合平缓叙事")

        # 对话特征
        if fp.dialogue_ratio > 0.3:
            parts.append(f"- 对话: 占比高({fp.dialogue_ratio:.0%})，用人物对话推动剧情和体现性格")
        elif fp.dialogue_ratio < 0.1:
            parts.append(
                f"- 对话: 精简({fp.dialogue_ratio:.0%})，以叙述为主，对话只用于关键信息传递"
            )
        else:
            parts.append(f"- 对话: 适中({fp.dialogue_ratio:.0%})，叙述与对话平衡")

        # 词汇倾向
        if fp.top_words:
            top_words_list = [w for w, _ in fp.top_words[:5]]
            parts.append(f"- 核心词汇倾向: {', '.join(top_words_list)}")

        if fp.word_diversity > 0.5:
            parts.append("- 词汇: 高度多样化,避免重复用词")
        elif fp.word_diversity < 0.2:
            parts.append("- 词汇: 集中统一,保持术语一致性")

        # 去AI味建议（通用，适用于所有风格）
        parts.append("\n## 反AI痕迹要求\n")
        parts.append("- 禁用AI高频套话: 突然、仿佛、似乎、总的来说、通过这件事")
        parts.append('- 变化句式开头，避免连续3句以上以"他/她/它"开头')
        parts.append('- 禁止总结性结尾（"从此以后""这次经历"等）')
        parts.append("- 段落长短交替，不得全部段落长度相近")
        parts.append("- 避免过度使用连接词（然而/因此/于是/随后）")
        parts.append("- 对话需有个性化差异，不同角色说话风格不同")

        return "\n".join(parts)


# ── 全局单例 ──
style_analyzer = StyleAnalyzer()
style_injector = StyleInjector()

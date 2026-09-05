"""
dialogue 对话解析器 — 对话提取、语言特征标注与数据结构
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ============================================================================
# 枚举定义
# ============================================================================


class DialogueStyle(StrEnum):
    """对话语体风格"""

    NATURAL = "natural"  # 自然口语
    LITERARY = "literary"  # 偏书面
    SLANG = "slang"  # 俚语/方言
    FORMAL = "formal"  # 正式
    INTIMATE = "intimate"  # 亲密
    COLD = "cold"  # 冷淡/疏离
    AGGRESSIVE = "aggressive"  # 攻击性
    COMIC = "comic"  # 搞笑/吐槽


class DistinctivenessLevel(StrEnum):
    """角色辨识度等级"""

    HIGH = "high"  # 一眼能认出是谁在说话
    MEDIUM = "medium"  # 有一定区分度
    LOW = "low"  # 换谁都能说
    NONE = "none"  # 完全无法区分


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class SpeakerProfile:
    """角色语音指纹"""

    character_id: str
    character_name: str

    # 口头禅与高频词
    catchphrases: list[str] = field(default_factory=list)  # 口头禅
    high_freq_words: Counter = field(default_factory=Counter)  # 高频实词
    sentence_enders: Counter = field(default_factory=Counter)  # 句末语气词（啊/呢/吧/吗/哦）

    # 句式特征
    avg_sentence_length: float = 0.0  # 平均句长
    question_ratio: float = 0.0  # 疑问句占比
    exclamation_ratio: float = 0.0  # 感叹句占比
    ellipsis_ratio: float = 0.0  # 省略号使用频率
    dash_ratio: float = 0.0  # 破折号使用频率

    # 语体
    dominant_style: DialogueStyle = DialogueStyle.NATURAL
    style_distribution: dict[str, float] = field(default_factory=dict)

    # 统计
    total_dialogue_lines: int = 0
    total_words: int = 0

    def fingerprint(self) -> dict[str, Any]:
        """生成角色语音指纹摘要"""
        return {
            "character": self.character_name,
            "catchphrases": self.catchphrases[:5],
            "top_words": self.high_freq_words.most_common(10),
            "sentence_enders": self.sentence_enders.most_common(5),
            "avg_sentence_length": round(self.avg_sentence_length, 1),
            "question_ratio": round(self.question_ratio, 3),
            "dominant_style": self.dominant_style.value,
        }


@dataclass
class DialogueLine:
    """单句对话"""

    speaker_id: str
    speaker_name: str
    text: str
    line_number: int
    paragraph_index: int

    # 语言特征（自动计算）
    word_count: int = 0
    has_question: bool = False
    has_exclamation: bool = False
    ellipsis_count: int = 0
    dash_count: int = 0
    sentence_ender: str = ""  # 句末语气词
    style_hint: DialogueStyle = DialogueStyle.NATURAL

    def __post_init__(self):
        self.word_count = len(self.text)
        self.has_question = "?" in self.text or "？" in self.text
        self.has_exclamation = "!" in self.text or "！" in self.text
        self.ellipsis_count = self.text.count("...") + self.text.count("……")
        self.dash_count = self.text.count("——") + self.text.count("--")

        # 提取句末语气词
        ender_match = re.search(r"[啊呢吧吗哦呀哟嘛啦哈呵嘿噢](?:[？?！!。.]|$)", self.text)
        if ender_match:
            self.sentence_ender = ender_match.group()[0]

        # 粗判语体
        self._detect_style()

    def _detect_style(self) -> None:
        """基于语言特征判定语体风格"""
        text = self.text
        # 俚语/方言特征词
        slang_words = {"俺", "咋", "啥", "甭", "嘞", "哩", "嘛", "呗", "咋滴", "整啥", "干哈"}
        slang_count = sum(1 for w in slang_words if w in text)
        if slang_count >= 2:
            self.style_hint = DialogueStyle.SLANG
            return

        # 攻击性特征
        aggressive_words = {"滚", "找死", "混蛋", "闭嘴", "废物", "放肆", "岂有此理"}
        if any(w in text for w in aggressive_words):
            self.style_hint = DialogueStyle.AGGRESSIVE
            return

        # 搞笑/吐槽特征
        comic_words = {"哈哈哈哈", "笑死", "吐槽", "无语", "绝了", "太真实了"}
        if any(w in text for w in comic_words):
            self.style_hint = DialogueStyle.COMIC
            return

        # 正式
        formal_indicators = {"请", "您", "务必", "可否", "谨", "兹"}
        if sum(1 for w in formal_indicators if w in text) >= 2:
            self.style_hint = DialogueStyle.FORMAL
            return

        # 冷淡
        if self.word_count <= 3 and not self.has_question and not self.has_exclamation:
            self.style_hint = DialogueStyle.COLD
            return

        # 默认自然口语
        self.style_hint = DialogueStyle.NATURAL


@dataclass
class DialogueMetrics:
    """对话统计指标"""

    total_lines: int = 0
    total_words: int = 0
    dialogue_ratio: float = 0.0  # 对话占总字数比例
    avg_line_length: float = 0.0
    avg_lines_per_exchange: float = 0.0  # 平均每轮对话行数
    speaker_count: int = 0
    speaker_balance: float = 0.0  # 对话分配均衡度（0-1）
    question_ratio: float = 0.0
    exclamation_ratio: float = 0.0
    distinctiveness: DistinctivenessLevel = DistinctivenessLevel.MEDIUM
    longest_monologue: int = 0  # 最长独白字数


@dataclass
class DialogueReport:
    """对话质量报告"""

    book_id: str
    chapter_id: str = ""
    metrics: DialogueMetrics = field(default_factory=DialogueMetrics)
    speaker_profiles: dict[str, SpeakerProfile] = field(default_factory=dict)
    distinctiveness_issues: list[str] = field(default_factory=list)
    style_warnings: list[str] = field(default_factory=list)
    overall_score: float = 0.0  # 0-100

    def summary(self) -> str:
        return (
            f"对话报告 [{self.chapter_id or self.book_id}]: "
            f"得分{self.overall_score:.0f}/100, "
            f"{self.metrics.total_lines}句对话, "
            f"{self.metrics.speaker_count}个角色, "
            f"辨识度: {self.metrics.distinctiveness.value}"
        )


# ============================================================================
# 对话解析器
# ============================================================================


class DialogueParser:
    """从文本中提取对话行"""

    # 中文对话模式
    DIALOGUE_PATTERN = re.compile(
        r'(?:[""\u201c\u201d\u300c\u300d])([^""\u201c\u201d\u300c\u300d]+?)(?:[""\u201c\u201d\u300c\u300d])'
        r'|(?:[：:]\s*)([""\u201c\u201d\u300c\u300d]?)([^，。！？\n,\.!\?\n]{2,50}?)\2(?=[\n，。！？,\.!\?]|$)'
        r"|(?:^|\n)\s*([^\n]{3,60})[说问道喊叫嚷吼骂喊嚷]"
    )

    # 角色名提取模式
    SPEAKER_PATTERN = re.compile(
        r'([^\s""\u201c\u201d\u300c\u300d：:]{1,6})'
        r"(?:说道|问道|喊道|叫道|嚷道|吼道|骂道|笑道|哭道|怒道|冷声道|淡淡道|"
        r"低声道|大声道|小声说|轻声说|说|问|道|喊|叫|嚷|吼|骂|答|回应|回答|"
        r"开口|开口说|出声|出声说|冷冷说|淡淡说|低声说|大声说)"
    )

    @classmethod
    def extract_dialogue_lines(cls, text: str) -> list[str]:
        """从文本中提取所有对话内容（不含说话人）"""
        lines = []
        for match in cls.DIALOGUE_PATTERN.finditer(text):
            content = match.group(1) or match.group(3) or match.group(4) or ""
            content = content.strip()
            if content and len(content) >= 2:
                lines.append(content)
        return lines

    @classmethod
    def extract_with_speakers(
        cls, text: str, known_characters: dict[str, str] | None = None
    ) -> list[DialogueLine]:
        """提取对话并尝试标注说话人"""
        results: list[DialogueLine] = []
        known = known_characters or {}
        paragraphs = text.split("\n")
        line_counter = 0

        for para_idx, para in enumerate(paragraphs):
            # 尝试找到"XX说/道/问"模式
            speaker_matches = list(cls.SPEAKER_PATTERN.finditer(para))
            raw_dialogues = cls.DIALOGUE_PATTERN.findall(para)

            if not raw_dialogues:
                continue

            # 配对说话人和对话
            for _d_idx, d_match in enumerate(cls.DIALOGUE_PATTERN.finditer(para)):
                content = d_match.group(1) or d_match.group(3) or d_match.group(4) or ""
                content = content.strip()
                if not content or len(content) < 2:
                    continue

                # 找最近的说话人
                speaker_name = "未知"
                speaker_id = "unknown"
                d_start = d_match.start()

                for sm in speaker_matches:
                    if sm.end() <= d_start:
                        speaker_name = sm.group(1)
                        break

                # 匹配已知角色
                if speaker_name in known:
                    speaker_id = speaker_name
                elif speaker_name != "未知":
                    # 尝试模糊匹配
                    for cid, cname in known.items():
                        if speaker_name in cname or cname in speaker_name:
                            speaker_id = cid
                            speaker_name = cname
                            break

                line_counter += 1
                results.append(
                    DialogueLine(
                        speaker_id=speaker_id,
                        speaker_name=speaker_name,
                        text=content,
                        line_number=line_counter,
                        paragraph_index=para_idx,
                    )
                )

        return results

"""
格式适配器 — 跨平台格式转换

支持:
- HTML → 纯文本 (去标签)
- HTML → Markdown
- Markdown → HTML (各平台所需格式)
- 字数统计
- 章节分割/合并

用法:
    formatter = FormatAdapter()
    html = formatter.markdown_to_html("# 标题\n\n正文内容")
    stats = formatter.get_stats(content)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextStats:
    """文本统计信息"""

    char_count: int = 0
    word_count: int = 0  # 中文字数（含标点）
    word_count_en: int = 0  # 英文词数
    line_count: int = 0
    paragraph_count: int = 0
    avg_sentence_length: float = 0.0
    reading_time_minutes: float = 0.0  # 估计阅读时间


class FormatAdapter:
    """格式适配器

    在不同平台所需的格式之间进行转换。

    用法:
        adapter = FormatAdapter()
        html = adapter.markdown_to_html(content)
        plain = adapter.strip_html(html_content)
    """

    # 各平台 HTML 包装模板
    PLATFORM_TEMPLATES = {
        "qidian": '<div class="content">{content}</div>',
        "fanqie": "<article>{content}</article>",
        "jinjiang": '<div class="noveltext" id="content">{content}</div>',
        "zongheng": '<div class="content">{content}</div>',
        "feilu": '<div class="novel-content">{content}</div>',
    }

    def markdown_to_html(self, markdown_text: str) -> str:
        """Markdown → HTML 基础转换"""
        html = markdown_text

        # 标题
        html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # 粗体和斜体
        html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # 段落
        paragraphs = html.split("\n\n")
        return "\n".join(
            f"<p>{p.replace(chr(10), '<br>')}</p>"
            if not p.startswith("<h") and not p.startswith("<p")
            else p
            for p in paragraphs
            if p.strip()
        )

    def html_to_plaintext(self, html: str) -> str:
        """HTML → 纯文本"""
        # 替换换行相关标签
        text = re.sub(r"<br\s*/?>", "\n", html)
        text = re.sub(r"</p>", "\n\n", text)
        text = re.sub(r"</h[1-6]>", "\n\n", text)
        text = re.sub(r"</div>", "\n", text)
        # 移除所有标签
        text = re.sub(r"<[^>]+>", "", text)
        # 清理多余空白
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def wrap_for_platform(self, content: str, platform_id: str) -> str:
        """为指定平台包装 HTML"""
        template = self.PLATFORM_TEMPLATES.get(platform_id, "<div>{content}</div>")
        return template.format(content=content)

    def get_stats(self, text: str) -> TextStats:
        """获取文本统计"""
        # 中文字数（含中文标点）
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", text))
        # 英文词数
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        # 总字符数
        char_count = len(text)
        # 行数
        lines = text.split("\n")
        line_count = len(lines)
        # 段落数
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        para_count = len(paragraphs)

        # 估计阅读时间 (中文 ~400字/分钟, 英文 ~250词/分钟)
        reading_minutes = chinese_chars / 400 + english_words / 250

        return TextStats(
            char_count=char_count,
            word_count=chinese_chars + english_words,
            word_count_en=english_words,
            line_count=line_count,
            paragraph_count=para_count,
            reading_time_minutes=round(reading_minutes, 1),
        )

    def split_chapter(self, content: str, max_words: int) -> list[str]:
        """将超长章节拆分为多个部分"""
        paragraphs = content.split("\n\n")
        parts: list[str] = []
        current: list[str] = []
        current_words = 0

        for para in paragraphs:
            para_words = len(para)
            if current_words + para_words > max_words and current:
                parts.append("\n\n".join(current))
                current = []
                current_words = 0
            current.append(para)
            current_words += para_words

        if current:
            parts.append("\n\n".join(current))

        return parts or [content]

    def estimate_word_count(self, content: str) -> int:
        """估算字数"""
        stats = self.get_stats(content)
        return stats.word_count

    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """自动生成摘要（截取前 N 个字符）"""
        plain = content
        if "<" in content:
            plain = self.html_to_plaintext(content)
        if len(plain) <= max_length:
            return plain
        return plain[:max_length].rsplit("。", 1)[0] + "。"

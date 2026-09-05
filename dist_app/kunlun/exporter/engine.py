"""
昆仑创作引擎 — 导出引擎核心实现

支持 7 种导出格式：TXT / EPUB / MOBI / PDF / HTML / DOCX / Markdown + 投稿包。
设计原则：LBYL — 每步操作先检查依赖再执行，清晰反馈缺失的依赖。
"""

from __future__ import annotations

import html as html_mod
import json
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from kunlun.config import settings
from kunlun.kg.client import kg_client


class ExportFormat(StrEnum):
    """导出格式枚举"""

    TXT = "txt"
    EPUB = "epub"
    MOBI = "mobi"
    PDF = "pdf"
    HTML = "html"
    DOCX = "docx"
    MARKDOWN = "md"
    SUBMISSION = "submission"  # 投稿包 (ZIP)


class ExportLayout(StrEnum):
    """全书导出排版风格"""

    STANDARD = "standard"
    COMPACT = "compact"
    BEAUTIFUL = "beautiful"


@dataclass
class ChapterData:
    """章节数据容器"""

    number: int
    title: str = ""
    content: str = ""
    word_count: int = 0
    status: str = "written"


@dataclass
class ExportResult:
    """导出结果"""

    success: bool
    format: str = ""
    path: str = ""
    chapters: int = 0
    total_words: int = 0
    missing_deps: list[str] = field(default_factory=list)
    error: str = ""


# ─── HTML 排版模板 ────────────────────────────────────────────────


def _css_for_layout(layout: ExportLayout) -> str:
    """根据排版风格生成 CSS"""
    base = (
        "max-width:720px;margin:2rem auto;"
        'font-family:"Noto Serif SC",serif;font-size:18px;line-height:2;color:#333;'
    )
    if layout == ExportLayout.COMPACT:
        base = (
            "max-width:680px;margin:1.5rem auto;"
            'font-family:"Noto Serif SC",serif;font-size:16px;line-height:1.8;color:#333;'
        )
    elif layout == ExportLayout.BEAUTIFUL:
        base = (
            "max-width:760px;margin:3rem auto;"
            'font-family:"Noto Serif SC","Source Han Serif SC",serif;font-size:19px;'
            "line-height:2.2;color:#2c2c2c;background:#fdfbf7;padding:2rem 3rem;"
        )
    return base


def _chapter_html(num: int, title: str, content: str, layout: ExportLayout) -> str:
    """生成单章 HTML 片段"""
    chapter_title = title or f"第{num}章"
    paragraphs = "".join(
        f"<p>{html_mod.escape(p.strip())}</p>\n" for p in content.split("\n\n") if p.strip()
    )
    if layout == ExportLayout.BEAUTIFUL:
        return (
            f'<h1 style="text-align:center;margin:3rem 0 1.5rem;'
            f'font-size:24px;color:#4a3728;">{html_mod.escape(chapter_title)}</h1>\n'
            f"{paragraphs}\n"
            f'<hr style="border:none;border-top:2px dotted #d4c5b2;margin:2.5rem 0;">\n'
        )
    return (
        f"<h1>{html_mod.escape(chapter_title)}</h1>\n"
        f"{paragraphs}\n"
        f'<hr style="border:none;border-top:1px solid #eee;margin:2rem 0;">\n'
    )


def _build_html(title: str, chapters: list[ChapterData], layout: ExportLayout) -> str:
    """构建全书 HTML 文档"""
    css = _css_for_layout(layout)
    parts = [
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n'
        f"<title>{html_mod.escape(title)}</title>\n"
        f"<style>body{{{css}}}h1{{text-align:center;}}p{{text-indent:2em}}</style>\n"
        "</head>\n<body>\n",
    ]
    parts.extend(_chapter_html(ch.number, ch.title, ch.content, layout) for ch in chapters)
    parts.append("</body>\n</html>")
    return "".join(parts)


# ─── 核心导出器 ────────────────────────────────────────────────────


class Exporter:
    """多格式导出器。

    用法:
        exporter = Exporter()
        result = exporter.export_book(book_id, chapters, ExportFormat.EPUB, output_dir)
    """

    def __init__(self):
        self._epub_available: bool | None = None
        self._pdf_available: bool | None = None
        self._docx_available: bool | None = None

    # ── 依赖检测 ──────────────────────────────────────────────

    def _check_epub(self) -> bool:
        if self._epub_available is None:
            import importlib.util

            self._epub_available = importlib.util.find_spec("ebooklib") is not None
        return self._epub_available

    def _check_pdf(self) -> bool:
        """检测 weasyprint 是否可用。

        weasyprint 在 Windows 上需要 GTK3 运行时（libgobject-2.0-0.dll），
        若缺少系统库，import 阶段会抛出 OSError。
        """
        if self._pdf_available is None:
            import importlib.util

            self._pdf_available = importlib.util.find_spec("weasyprint") is not None
        return self._pdf_available

    def _check_docx(self) -> bool:
        if self._docx_available is None:
            import importlib.util

            self._docx_available = importlib.util.find_spec("docx") is not None
        return self._docx_available

    def _get_missing_deps(self, fmt: ExportFormat) -> list[str]:
        """返回指定格式缺失的依赖"""
        missing = []
        if fmt == ExportFormat.EPUB and not self._check_epub():
            missing.append("ebooklib (pip install ebooklib)")
        if fmt == ExportFormat.PDF and not self._check_pdf():
            missing.append("weasyprint (pip install weasyprint)")
        if fmt == ExportFormat.DOCX and not self._check_docx():
            missing.append("python-docx (pip install python-docx)")
        if fmt == ExportFormat.MOBI:
            missing.append("calibre (需要独立安装 calibre 软件，用 ebook-convert 命令行)")
        return missing

    # ── 章节查询 ──────────────────────────────────────────────

    def _query_chapter(self, book_id: str, chapter: int) -> ChapterData | None:
        """从 KG 查询单章内容"""
        rows = kg_client.query_cypher(
            """MATCH (ch:Chapter {uid: $uid})
               RETURN ch.contentPreview AS content, ch.wordCount AS word_count,
                      ch.chapterNumber AS num, ch.title AS title""",
            {"uid": f"{book_id}_ch{chapter}"},
        )
        if not rows or not rows[0].get("content"):
            return None
        r = rows[0]
        return ChapterData(
            number=r.get("num", chapter),
            title=r.get("title", f"第{chapter}章"),
            content=r["content"],
            word_count=r.get("word_count", 0),
        )

    def _query_chapters(self, book_id: str) -> list[ChapterData]:
        """从 KG 查询已写章节列表"""
        rows = kg_client.query_cypher(
            """MATCH (ch:Chapter)
               WHERE ch.book_id = $book_id AND ch.status = 'written'
               RETURN ch.chapterNumber AS num, ch.contentPreview AS content,
                      ch.wordCount AS word_count, ch.title AS title
               ORDER BY ch.chapterNumber""",
            {"book_id": book_id},
        )
        return [
            ChapterData(
                number=r.get("num", 0),
                title=r.get("title", f"第{r['num']}章"),
                content=r.get("content", ""),
                word_count=r.get("word_count", 0),
            )
            for r in rows
        ]

    # ── 安全路径 ──────────────────────────────────────────────

    def _get_export_dir(self, book_id: str) -> Path:
        export_dir = settings.get_book_safe_path(book_id, "export")
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir

    # ── TXT ───────────────────────────────────────────────────

    def _export_txt(
        self,
        book_id: str,
        chapters: list[ChapterData],
        output_dir: Path,
        single_chapter: bool = False,
    ) -> Path:
        if single_chapter and len(chapters) == 1:
            ch = chapters[0]
            path = output_dir / f"ch{ch.number:04d}.txt"
            path.write_text(f"{ch.title}\n{'=' * 40}\n\n{ch.content}", encoding="utf-8")
        else:
            path = output_dir / f"{book_id}_full.txt"
            parts = [f"{book_id}\n", "=" * 50, "\n\n"]
            parts.extend(
                f"\n\n{'=' * 50}\n{ch.title}\n{'=' * 50}\n\n{ch.content}" for ch in chapters
            )
            path.write_text("".join(parts), encoding="utf-8")
        return path

    # ── HTML ──────────────────────────────────────────────────

    def _export_html(
        self,
        book_id: str,
        chapters: list[ChapterData],
        output_dir: Path,
        layout: ExportLayout = ExportLayout.STANDARD,
        single_chapter: bool = False,
    ) -> Path:
        if single_chapter and len(chapters) == 1:
            ch = chapters[0]
            html_str = _build_html(ch.title, [ch], layout)
            path = output_dir / f"ch{ch.number:04d}.html"
        else:
            html_str = _build_html(book_id, chapters, layout)
            path = output_dir / f"{book_id}_full.html"
        path.write_text(html_str, encoding="utf-8")
        return path

    # ── Markdown ──────────────────────────────────────────────

    def _export_md(
        self,
        book_id: str,
        chapters: list[ChapterData],
        output_dir: Path,
        single_chapter: bool = False,
    ) -> Path:
        if single_chapter and len(chapters) == 1:
            ch = chapters[0]
            path = output_dir / f"ch{ch.number:04d}.md"
            path.write_text(f"# {ch.title}\n\n{ch.content}", encoding="utf-8")
        else:
            path = output_dir / f"{book_id}_full.md"
            parts = [f"# {book_id}\n\n"]
            parts.extend(f"\n---\n\n## {ch.title}\n\n{ch.content}\n" for ch in chapters)
            path.write_text("".join(parts), encoding="utf-8")
        return path

    # ── EPUB ──────────────────────────────────────────────────

    def _export_epub(
        self,
        book_id: str,
        chapters: list[ChapterData],
        output_dir: Path,
        layout: ExportLayout = ExportLayout.STANDARD,
    ) -> Path:
        if not self._check_epub():
            raise ImportError("缺少 ebooklib 依赖。安装: pip install ebooklib")

        from ebooklib import epub

        css = _css_for_layout(layout)
        book = epub.EpubBook()
        book.set_identifier(book_id)
        book.set_title(book_id)
        book.set_language("zh-CN")
        book.add_author("昆仑创作引擎")

        # 默认样式
        default_css = epub.EpubItem(
            uid="style",
            file_name="style/default.css",
            media_type="text/css",
            content=f"body {{{css}}} p {{text-indent: 2em}} h1 {{text-align: center}}\n".encode(),
        )
        book.add_item(default_css)

        spine = ["nav"]
        epub_chapters = []
        for ch in chapters:
            c = epub.EpubHtml(
                title=ch.title,
                file_name=f"ch{ch.number:04d}.xhtml",
                lang="zh-CN",
            )
            c.content = _chapter_html(ch.number, ch.title, ch.content, layout).encode("utf-8")
            c.add_item(default_css)
            book.add_item(c)
            spine.append(c)
            epub_chapters.append(c)

        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine

        path = output_dir / f"{book_id}.epub"
        epub.write_epub(str(path), book)
        return path

    # ── PDF ───────────────────────────────────────────────────

    def _export_pdf(
        self,
        book_id: str,
        chapters: list[ChapterData],
        output_dir: Path,
        layout: ExportLayout = ExportLayout.STANDARD,
    ) -> Path:
        if not self._check_pdf():
            raise ImportError("缺少 weasyprint 依赖。安装: pip install weasyprint")

        import weasyprint

        html_str = _build_html(book_id, chapters, layout)
        path = output_dir / f"{book_id}.pdf"
        weasyprint.HTML(string=html_str).write_pdf(str(path))
        return path

    # ── DOCX ──────────────────────────────────────────────────

    def _export_docx(self, book_id: str, chapters: list[ChapterData], output_dir: Path) -> Path:
        if not self._check_docx():
            raise ImportError("缺少 python-docx 依赖。安装: pip install python-docx")

        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Cm, Pt

        doc = Document()

        # 设置默认字体
        style = doc.styles["Normal"]
        font = style.font
        font.name = "宋体"
        font.size = Pt(12)
        style.paragraph_format.first_line_indent = Cm(0.74)
        style.paragraph_format.line_spacing = 1.5

        # 标题页
        title = doc.add_heading(book_id, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        for ch in chapters:
            doc.add_page_break()
            heading = doc.add_heading(ch.title, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

            for para_text in ch.content.split("\n\n"):
                p = para_text.strip()
                if p:
                    doc.add_paragraph(p)

        path = output_dir / f"{book_id}.docx"
        doc.save(str(path))
        return path

    # ── MOBI ──────────────────────────────────────────────────

    def _export_mobi(
        self,
        book_id: str,
        chapters: list[ChapterData],
        output_dir: Path,
        layout: ExportLayout = ExportLayout.STANDARD,
    ) -> Path:
        """MOBI 导出需要 calibre 的 ebook-convert 命令行工具。

        策略：先导出 EPUB，再调用 ebook-convert 转换。
        """
        # 先确保 EPUB 存在
        epub_path = self._export_epub(book_id, chapters, output_dir, layout)
        mobi_path = output_dir / f"{book_id}.mobi"

        import shutil
        import subprocess

        ebook_convert = shutil.which("ebook-convert")
        if ebook_convert is None:
            raise RuntimeError(
                "MOBI 导出需要 calibre 的 ebook-convert 工具。"
                "请安装 calibre: https://calibre-ebook.com/download"
            )

        result = subprocess.run(
            [ebook_convert, str(epub_path), str(mobi_path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"MOBI 转换失败: {result.stderr}")

        return mobi_path

    # ── SUBMISSION 投稿包 ─────────────────────────────────────

    def _export_submission(
        self, book_id: str, chapters: list[ChapterData], output_dir: Path
    ) -> Path:
        """生成投稿包 ZIP (txt正文 + 大纲 + 角色设定 + 统计摘要)"""
        zip_path = output_dir / f"{book_id}_投稿包.zip"

        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            # 正文 txt
            txt_path = self._export_txt(book_id, chapters, output_dir)
            zf.write(str(txt_path), f"{book_id}_正文.txt")

            # 大纲 (从 KG 查询)
            outline_rows = kg_client.query_cypher(
                """MATCH (o:Outline)
                   WHERE o.book_id = $book_id
                   RETURN o.content AS content, o.volume AS volume
                   ORDER BY o.volume""",
                {"book_id": book_id},
            )
            if outline_rows:
                outline_md = "# 大纲\n\n" + "\n\n".join(
                    f"## 第{r.get('volume', '?')}卷\n\n{r.get('content', '')}" for r in outline_rows
                )
                zf.writestr(f"{book_id}_大纲.md", outline_md)

            # 角色设定 (从 KG 查询)
            char_rows = kg_client.query_cypher(
                """MATCH (c:Character)
                   WHERE c.book_id = $book_id
                   RETURN c.name AS name, c.description AS description,
                          c.role AS role
                   ORDER BY c.role""",
                {"book_id": book_id},
            )
            if char_rows:
                char_md = "# 角色设定\n\n" + "\n\n".join(
                    f"## {r.get('name', '未知')} ({r.get('role', '未知')})\n\n"
                    f"{r.get('description', '')}"
                    for r in char_rows
                )
                zf.writestr(f"{book_id}_角色设定.md", char_md)

            # 统计摘要
            total_words = sum(ch.word_count for ch in chapters)
            summary = {
                "book_id": book_id,
                "total_chapters": len(chapters),
                "total_words": total_words,
                "avg_words_per_chapter": round(total_words / max(len(chapters), 1)),
                "exported_at": "",
            }
            zf.writestr(f"{book_id}_统计.json", json.dumps(summary, ensure_ascii=False, indent=2))

        return zip_path

    # ── 公共 API ──────────────────────────────────────────────

    def export_chapter(
        self,
        book_id: str,
        chapter: int,
        fmt: ExportFormat,
        layout: ExportLayout = ExportLayout.STANDARD,
    ) -> ExportResult:
        """导出单章。

        Args:
            book_id: 书籍 ID
            chapter: 章节编号
            fmt: 导出格式
            layout: 排版风格 (仅 HTML/EPUB/PDF 有效)

        Returns:
            ExportResult — 成功或失败详情
        """
        ch_data = self._query_chapter(book_id, chapter)
        if ch_data is None:
            return ExportResult(
                success=False, format=fmt.value, error=f"第{chapter}章未找到或未生成"
            )

        missing = self._get_missing_deps(fmt)
        if missing:
            return ExportResult(
                success=False,
                format=fmt.value,
                missing_deps=missing,
                error=f"{fmt.value} 导出需要安装依赖: {', '.join(missing)}",
            )

        output_dir = self._get_export_dir(book_id)
        try:
            if fmt == ExportFormat.TXT:
                p = self._export_txt(book_id, [ch_data], output_dir, single_chapter=True)
            elif fmt == ExportFormat.HTML:
                p = self._export_html(book_id, [ch_data], output_dir, layout, single_chapter=True)
            elif fmt == ExportFormat.MARKDOWN:
                p = self._export_md(book_id, [ch_data], output_dir, single_chapter=True)
            elif fmt == ExportFormat.EPUB:
                p = self._export_epub(book_id, [ch_data], output_dir, layout)
            elif fmt == ExportFormat.PDF:
                p = self._export_pdf(book_id, [ch_data], output_dir, layout)
            elif fmt == ExportFormat.DOCX:
                p = self._export_docx(book_id, [ch_data], output_dir)
            elif fmt == ExportFormat.MOBI:
                p = self._export_mobi(book_id, [ch_data], output_dir, layout)
            else:
                return ExportResult(
                    success=False, format=fmt.value, error=f"不支持的格式: {fmt.value}"
                )
        except Exception as e:
            return ExportResult(success=False, format=fmt.value, error=str(e))

        return ExportResult(
            success=True,
            format=fmt.value,
            path=str(p),
            chapters=1,
            total_words=ch_data.word_count,
        )

    def export_book(
        self,
        book_id: str,
        fmt: ExportFormat,
        layout: ExportLayout = ExportLayout.STANDARD,
    ) -> ExportResult:
        """导出全书。

        Args:
            book_id: 书籍 ID
            fmt: 导出格式
            layout: 排版风格

        Returns:
            ExportResult
        """
        chapters = self._query_chapters(book_id)
        if not chapters:
            return ExportResult(success=False, format=fmt.value, error="无已写章节")

        missing = self._get_missing_deps(fmt)
        if missing:
            return ExportResult(
                success=False,
                format=fmt.value,
                missing_deps=missing,
                error=f"{fmt.value} 导出需要安装依赖: {', '.join(missing)}",
            )

        output_dir = self._get_export_dir(book_id)
        try:
            if fmt == ExportFormat.TXT:
                p = self._export_txt(book_id, chapters, output_dir)
            elif fmt == ExportFormat.HTML:
                p = self._export_html(book_id, chapters, output_dir, layout)
            elif fmt == ExportFormat.MARKDOWN:
                p = self._export_md(book_id, chapters, output_dir)
            elif fmt == ExportFormat.EPUB:
                p = self._export_epub(book_id, chapters, output_dir, layout)
            elif fmt == ExportFormat.PDF:
                p = self._export_pdf(book_id, chapters, output_dir, layout)
            elif fmt == ExportFormat.DOCX:
                p = self._export_docx(book_id, chapters, output_dir)
            elif fmt == ExportFormat.MOBI:
                p = self._export_mobi(book_id, chapters, output_dir, layout)
            else:
                return ExportResult(
                    success=False, format=fmt.value, error=f"不支持的格式: {fmt.value}"
                )
        except Exception as e:
            return ExportResult(success=False, format=fmt.value, error=str(e))

        total_words = sum(ch.word_count for ch in chapters)
        return ExportResult(
            success=True,
            format=fmt.value,
            path=str(p),
            chapters=len(chapters),
            total_words=total_words,
        )

    def export_submission(self, book_id: str) -> ExportResult:
        """导出投稿包 (ZIP)。

        Args:
            book_id: 书籍 ID

        Returns:
            ExportResult
        """
        chapters = self._query_chapters(book_id)
        if not chapters:
            return ExportResult(success=False, format="submission", error="无已写章节")

        output_dir = self._get_export_dir(book_id)
        try:
            p = self._export_submission(book_id, chapters, output_dir)
        except Exception as e:
            return ExportResult(success=False, format="submission", error=str(e))

        total_words = sum(ch.word_count for ch in chapters)
        return ExportResult(
            success=True,
            format="submission",
            path=str(p),
            chapters=len(chapters),
            total_words=total_words,
        )

    def check_dependencies(self) -> dict[str, bool]:
        """检测各格式依赖是否就绪。

        Returns:
            {"epub": True/False, "pdf": True/False, "docx": True/False, "mobi": True/False}
        """
        mobi_available = False
        import shutil

        if shutil.which("ebook-convert"):
            mobi_available = True

        return {
            "epub": self._check_epub(),
            "pdf": self._check_pdf(),
            "docx": self._check_docx(),
            "mobi": mobi_available,
        }


# 模块级单例
exporter = Exporter()

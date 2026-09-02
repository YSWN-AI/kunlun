"""
昆仑创作引擎 — 发布引擎 (真实实现)

替代占位实现，提供多平台发布格式化和计划管理。

核心能力:
  1. 平台格式化 — 自动适配各平台格式要求
  2. 章节打包 — 批量发布前的章节准备
  3. 发布计划 — 定时发布/每日更新计划
  4. 发布记录 — 历史发布追踪
  5. 多平台矩阵 — 一本书 → 多个平台同时管理
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 数据类型
# ══════════════════════════════════════════════════════


class Platform(Enum):
    """发布平台"""

    QIDIAN = "qidian"  # 起点中文网
    FANQIE = "fanqie"  # 番茄小说
    QIMAO = "qimao"  # 七猫小说
    FEILU = "feilu"  # 飞卢小说网
    JJWXC = "jjwxc"  # 晋江文学城
    CUSTOM = "custom"  # 自定义


class PublishMode(Enum):
    """发布模式"""

    MANUAL = "manual"  # 手动 — 用户自己发布
    SCHEDULED = "scheduled"  # 定时 — 按计划发布
    BATCH = "batch"  # 批量 — 一次性发布多章


class PublishStatus(Enum):
    """发布状态"""

    DRAFT = "draft"  # 草稿
    FORMATTED = "formatted"  # 已格式化
    READY = "ready"  # 待发布
    PUBLISHED = "published"  # 已发布
    FAILED = "failed"  # 发布失败


@dataclass
class PlatformConfig:
    """平台发布配置"""

    platform: Platform
    platform_name: str = ""
    author_name: str = ""
    pen_name: str = ""  # 笔名 (可不同于作者名)
    book_title: str = ""
    book_id_on_platform: str = ""  # 平台上的书ID
    # 格式要求
    chapter_title_format: str = "第{chapter}章 {title}"  # 章节标题模板
    min_chapter_words: int = 2000
    max_chapter_words: int = 5000
    requires_summary: bool = False  # 是否需要章节摘要
    requires_keywords: bool = False  # 是否需要标签
    # 发布计划
    publish_schedule: str = ""  # cron 或 daily/hourly
    daily_chapter_limit: int = 2
    # 其他
    notes: str = ""


@dataclass
class PublishRecord:
    """单条发布记录"""

    chapter: int
    platform: Platform
    status: PublishStatus
    published_at: float = 0.0
    formatted_text: str = ""
    word_count: int = 0
    error: str = ""
    notes: str = ""


@dataclass
class PublishSchedule:
    """发布计划"""

    book_id: str
    platform: Platform
    mode: PublishMode
    next_chapter: int  # 下一章编号
    total_chapters: int  # 总章节数
    daily_count: int  # 每日发布数
    scheduled_for: list[int] = field(default_factory=list)  # 待发布章节列表
    history: list[PublishRecord] = field(default_factory=list)


# ══════════════════════════════════════════════════════
# 平台格式化器
# ══════════════════════════════════════════════════════


class PlatformFormatter:
    """平台格式化器 — 将章节内容适配到各平台格式"""

    # 平台格式模板
    FORMAT_SPECS: dict[Platform, dict[str, Any]] = {
        Platform.QIDIAN: {
            "name": "起点中文网",
            "title_template": "第{chapter}章 {title}",
            "add_chapter_header": True,
            "add_author_note": False,
            "preface_text": "",  # 章节前附加
            "appendix_text": "",  # 章节后附加
            "line_break": "\n\n",
            "replace_smart_quotes": False,
        },
        Platform.FANQIE: {
            "name": "番茄小说",
            "title_template": "第{chapter}章 {title}",
            "add_chapter_header": True,
            "add_author_note": False,
            "preface_text": "",
            "appendix_text": "",
            "line_break": "\n\n",
            "replace_smart_quotes": True,  # 番茄建议用 "" 替代 「」
        },
        Platform.QIMAO: {
            "name": "七猫小说",
            "title_template": "第{chapter}章 {title}",
            "add_chapter_header": True,
            "add_author_note": False,
            "line_break": "\n\n",
        },
        Platform.FEILU: {
            "name": "飞卢小说网",
            "title_template": "{chapter}. {title}",
            "add_chapter_header": False,
            "add_author_note": True,  # 飞卢允许作者说
            "line_break": "\n",
        },
        Platform.JJWXC: {
            "name": "晋江文学城",
            "title_template": "{title}",
            "add_chapter_header": False,
            "add_author_note": True,  # 晋江支持"作者有话说"
            "line_break": "\n\n",
            "replace_smart_quotes": True,
        },
        Platform.CUSTOM: {
            "name": "自定义",
            "title_template": "第{chapter}章 {title}",
            "line_break": "\n\n",
        },
    }

    @classmethod
    def format_chapter(
        cls,
        text: str,
        chapter_number: int,
        platform: Platform,
        chapter_title: str = "",
        author_note: str = "",
    ) -> str:
        """格式化章节为平台就绪文本"""
        spec = cls.FORMAT_SPECS.get(platform, cls.FORMAT_SPECS[Platform.CUSTOM])

        title = spec["title_template"].format(chapter=chapter_number, title=chapter_title)

        parts: list[str] = []

        # 标题
        if spec.get("add_chapter_header", True):
            parts.append(title)
            parts.append("")

        # 前言
        if spec.get("preface_text"):
            parts.append(spec["preface_text"])
            parts.append("")

        # 正文
        # 智能引号替换
        if spec.get("replace_smart_quotes", False):
            text = PlatformFormatter._replace_smart_quotes(text)

        parts.append(text)

        # 作者的话
        if spec.get("add_author_note") and author_note:
            parts.append("")
            parts.append(f"——\n作者有话说：{author_note}")

        # 附录
        if spec.get("appendix_text"):
            parts.append("")
            parts.append(spec["appendix_text"])

        lb = spec.get("line_break", "\n\n")
        return lb.join(parts)

    @classmethod
    def _replace_smart_quotes(cls, text: str) -> str:
        """将中文智能引号替换为直引号 (部分平台偏好)"""
        return (
            text.replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u300c", '"')
            .replace("\u300d", '"')
        )

    @classmethod
    def get_platform_specs(cls) -> dict[str, dict]:
        """获取所有平台格式规格 (供前端展示)"""
        return {
            p.value: {
                "name": s["name"],
                "title_template": s.get("title_template", ""),
                "features": {
                    "header": s.get("add_chapter_header", True),
                    "author_note": s.get("add_author_note", False),
                    "smart_quotes": s.get("replace_smart_quotes", False),
                },
            }
            for p, s in cls.FORMAT_SPECS.items()
        }

    @classmethod
    def batch_format(
        cls,
        chapters: dict[int, str],
        platform: Platform,
        titles: dict[int, str] | None = None,
    ) -> dict[int, str]:
        """批量格式化多章"""
        titles = titles or {}
        return {
            ch: cls.format_chapter(text, ch, platform, titles.get(ch, ""))
            for ch, text in chapters.items()
        }


# ══════════════════════════════════════════════════════
# 发布引擎
# ══════════════════════════════════════════════════════


class PublishProxy:
    """发布代理 — 管理多平台发布"""

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.publish_dir = settings.DATA_DIR / "publish" / book_id
        self.publish_dir.mkdir(parents=True, exist_ok=True)

        # 平台配置
        self._platform_configs: dict[Platform, PlatformConfig] = {}
        self._schedules: dict[Platform, PublishSchedule] = {}
        self._history: list[PublishRecord] = []

        self._load_state()

    def _load_state(self):
        """加载发布状态"""
        config_path = self.publish_dir / "configs.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                for p_str, cfg in data.get("platforms", {}).items():
                    platform = Platform(p_str)
                    self._platform_configs[platform] = PlatformConfig(platform=platform, **cfg)
            except Exception as e:
                logger.warning(f"加载发布配置失败: {e}")

        history_path = self.publish_dir / "history.json"
        if history_path.exists():
            try:
                data = json.loads(history_path.read_text(encoding="utf-8"))
                self._history = [PublishRecord(**r) for r in data]
            except Exception as e:
                logger.warning(f"加载发布历史失败: {e}")

    def _save_state(self):
        """保存发布状态"""
        config_path = self.publish_dir / "configs.json"
        config_data = {
            "platforms": {
                p.value: {
                    "platform_name": cfg.platform_name,
                    "author_name": cfg.author_name,
                    "pen_name": cfg.pen_name,
                    "book_title": cfg.book_title,
                    "book_id_on_platform": cfg.book_id_on_platform,
                    "chapter_title_format": cfg.chapter_title_format,
                    "min_chapter_words": cfg.min_chapter_words,
                    "max_chapter_words": cfg.max_chapter_words,
                    "requires_summary": cfg.requires_summary,
                    "requires_keywords": cfg.requires_keywords,
                    "publish_schedule": cfg.publish_schedule,
                    "daily_chapter_limit": cfg.daily_chapter_limit,
                    "notes": cfg.notes,
                }
                for p, cfg in self._platform_configs.items()
            }
        }
        config_path.write_text(
            json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        history_path = self.publish_dir / "history.json"
        history_data = [
            {
                "chapter": r.chapter,
                "platform": r.platform.value,
                "status": r.status.value,
                "published_at": r.published_at,
                "word_count": r.word_count,
                "error": r.error,
                "notes": r.notes,
            }
            for r in self._history
        ]
        history_path.write_text(
            json.dumps(history_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── 平台配置管理 ──────────────────────────────────

    def register_platform(self, platform: Platform, config: PlatformConfig) -> None:
        """注册平台配置"""
        config.platform = platform
        self._platform_configs[platform] = config
        self._save_state()

    def get_platform_config(self, platform: Platform) -> PlatformConfig | None:
        """获取平台配置"""
        return self._platform_configs.get(platform)

    def list_platforms(self) -> list[dict[str, Any]]:
        """列出所有配置的平台"""
        return [
            {
                "platform": p.value,
                "name": cfg.platform_name
                or PlatformFormatter.FORMAT_SPECS.get(p, {}).get("name", p.value),
                "author": cfg.author_name,
                "book_title": cfg.book_title,
                "daily_limit": cfg.daily_chapter_limit,
            }
            for p, cfg in self._platform_configs.items()
        ]

    # ── 格式化发布 ──────────────────────────────────

    def prepare_chapter(
        self,
        chapter: int,
        text: str,
        platform: Platform,
        chapter_title: str = "",
        author_note: str = "",
    ) -> str:
        """准备单章 — 格式化并保存"""
        formatted = PlatformFormatter.format_chapter(
            text=text,
            chapter_number=chapter,
            platform=platform,
            chapter_title=chapter_title,
            author_note=author_note,
        )

        # 保存格式化后的文本
        out_dir = self.publish_dir / platform.value
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"ch_{chapter:04d}.md"
        out_path.write_text(formatted, encoding="utf-8")

        # 记录
        self._record(chapter, platform, PublishStatus.FORMATTED, len(text))
        self._save_state()

        return formatted

    def prepare_batch(
        self,
        chapters: dict[int, str],
        platform: Platform,
        titles: dict[int, str] | None = None,
    ) -> dict[int, str]:
        """批量准备多章"""
        titles = titles or {}
        results: dict[int, str] = {}
        for ch, text in sorted(chapters.items()):
            results[ch] = self.prepare_chapter(ch, text, platform, titles.get(ch, ""))
        return results

    def _record(
        self,
        chapter: int,
        platform: Platform,
        status: PublishStatus,
        word_count: int,
        error: str = "",
        notes: str = "",
    ):
        """记录发布事件"""
        record = PublishRecord(
            chapter=chapter,
            platform=platform,
            status=status,
            published_at=time.time(),
            word_count=word_count,
            error=error,
            notes=notes,
        )
        self._history.append(record)

    # ── 发布计划 ─────────────────────────────────────

    def create_schedule(
        self,
        platform: Platform,
        next_chapter: int,
        total_chapters: int,
        daily_count: int = 2,
    ) -> PublishSchedule:
        """创建发布计划"""
        schedule = PublishSchedule(
            book_id=self.book_id,
            platform=platform,
            mode=PublishMode.SCHEDULED,
            next_chapter=next_chapter,
            total_chapters=total_chapters,
            daily_count=daily_count,
            scheduled_for=list(range(next_chapter, min(next_chapter + 10, total_chapters + 1))),
        )
        self._schedules[platform] = schedule
        return schedule

    def get_schedule(self, platform: Platform) -> PublishSchedule | None:
        """获取发布计划"""
        return self._schedules.get(platform)

    def advance_schedule(self, platform: Platform) -> PublishSchedule | None:
        """推进发布计划 (发布了一章后)"""
        schedule = self._schedules.get(platform)
        if schedule and schedule.scheduled_for:
            schedule.next_chapter = schedule.scheduled_for.pop(0)
            if schedule.next_chapter < schedule.total_chapters:
                next_ch = schedule.next_chapter + schedule.daily_count
                schedule.scheduled_for = list(
                    range(schedule.next_chapter + 1, min(next_ch + 1, schedule.total_chapters + 1))
                )
        return schedule

    # ── 历史与统计 ───────────────────────────────────

    def get_history(
        self, platform: Platform | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取发布历史"""
        records = self._history
        if platform:
            records = [r for r in records if r.platform == platform]

        return [
            {
                "chapter": r.chapter,
                "platform": r.platform.value,
                "status": r.status.value,
                "published_at": r.published_at,
                "word_count": r.word_count,
                "error": r.error,
                "notes": r.notes,
            }
            for r in sorted(records[-limit:], key=lambda x: x.published_at, reverse=True)
        ]

    def get_statistics(self) -> dict[str, Any]:
        """发布统计"""
        platform_stats: dict[str, dict] = {}
        for r in self._history:
            p = r.platform.value
            if p not in platform_stats:
                platform_stats[p] = {"total": 0, "published": 0, "total_words": 0}
            platform_stats[p]["total"] += 1
            if r.status == PublishStatus.PUBLISHED:
                platform_stats[p]["published"] += 1
                platform_stats[p]["total_words"] += r.word_count

        return {
            "total_records": len(self._history),
            "platforms": platform_stats,
        }

    # ── 导出 ──────────────────────────────────────────

    def export_for_platform(
        self, platform: Platform, chapters: list[int] | None = None
    ) -> dict[int, str]:
        """导出指定平台的格式化章节"""
        out_dir = self.publish_dir / platform.value
        if not out_dir.exists():
            return {}

        result: dict[int, str] = {}
        for f in sorted(out_dir.glob("ch_*.md")):
            ch = int(f.stem.split("_")[1])
            if chapters is None or ch in chapters:
                result[ch] = f.read_text(encoding="utf-8")

        return result


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_proxies: dict[str, PublishProxy] = {}


def get_publish_proxy(book_id: str) -> PublishProxy:
    """获取发布代理实例"""
    if book_id not in _proxies:
        _proxies[book_id] = PublishProxy(book_id)
    return _proxies[book_id]


__all__ = [
    "Platform",
    "PlatformConfig",
    "PlatformFormatter",
    "PublishMode",
    "PublishProxy",
    "PublishRecord",
    "PublishSchedule",
    "PublishStatus",
    "get_publish_proxy",
]

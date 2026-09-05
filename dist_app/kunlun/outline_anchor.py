"""
昆仑创作引擎 — 大纲锚点/进度配额约束

设计来源: novel-creator-skill 的 Outline Anchors

核心功能:
  1. 定义每章必须推进的情节进度范围（min_progress ~ max_progress）
  2. 如果生成内容超出配额范围，触发门禁警告
  3. 确保故事不会"拖戏"或"跳进度"

配额示例:
  - 第1-5章: 开篇铺垫, 每章推进 2-4%
  - 第6-15章: 发展期, 每章推进 3-6%
  - 第16-25章: 冲突升级, 每章推进 4-8%
  - 最后5章: 收尾, 每章推进 8-15%
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from loguru import logger

from kunlun.config import settings


@dataclass
class ChapterQuota:
    """单章进度配额"""

    chapter: int
    min_progress: float  # 最小推进进度 (0.0-1.0)
    max_progress: float  # 最大推进进度
    description: str = ""  # 建议内容

    def validate(self, actual_progress: float) -> list[str]:
        """验证实际进度是否在配额范围内"""
        warnings = []
        if actual_progress < self.min_progress:
            warnings.append(
                f"进度不足: 实际{actual_progress:.1%} < 最低{self.min_progress:.1%}，"
                f"建议增加情节推进"
            )
        if actual_progress > self.max_progress:
            warnings.append(
                f"进度过快: 实际{actual_progress:.1%} > 最高{self.max_progress:.1%}，"
                f"建议放缓节奏增加细节"
            )
        return warnings


@dataclass
class ArcDefinition:
    """弧段定义"""

    name: str
    start_chapter: int
    end_chapter: int
    description: str = ""
    chapter_quotas: list[ChapterQuota] = field(default_factory=list)

    @property
    def total_chapters(self) -> int:
        return self.end_chapter - self.start_chapter + 1


class OutlineAnchor:
    """
    大纲锚点管理器

    使用方式:
        anchor = OutlineAnchor(book_id)
        anchor.set_total_chapters(100)
        anchor.add_arc(ArcDefinition("开篇", 1, 10, "世界观引入", [...]))
        quota = anchor.get_quota(15)        # 获取第15章的配额
        warnings = quota.validate(0.05)     # 验证实际进度5%
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.total_chapters: int = 0
        self.arcs: list[ArcDefinition] = []
        self._data_dir = settings.DATA_DIR / "outline" / book_id
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def set_total_chapters(self, total: int):
        """设置总章节数"""
        self.total_chapters = total
        self._auto_generate_quotas()
        self._save()

    def add_arc(self, arc: ArcDefinition):
        """添加弧段定义"""
        self.arcs.append(arc)
        self.arcs.sort(key=lambda a: a.start_chapter)
        self._auto_generate_quotas()
        self._save()

    def get_quota(self, chapter: int) -> ChapterQuota | None:
        """获取指定章节的进度配额"""
        for arc in self.arcs:
            if arc.start_chapter <= chapter <= arc.end_chapter:
                for q in arc.chapter_quotas:
                    if q.chapter == chapter:
                        return q
                # 如果弧段内没有精确到每章的配额，自动生成
                q = self._generate_quota_for_chapter(arc, chapter)
                arc.chapter_quotas.append(q)
                return q
        return None

    def validate_chapter(self, chapter: int, actual_progress: float) -> list[str]:
        """验证一章的进度是否在配额内"""
        quota = self.get_quota(chapter)
        if quota:
            return quota.validate(actual_progress)
        return []

    def get_overall_progress(self, current_chapter: int) -> float:
        """获取整体进度百分比"""
        if self.total_chapters <= 0:
            return 0.0
        return current_chapter / self.total_chapters

    def build_quota_prompt(self, chapter: int) -> str:
        """生成配额提示，注入 Writer prompt"""
        quota = self.get_quota(chapter)
        if not quota:
            return ""

        overall = self.get_overall_progress(chapter)
        current_arc = ""
        for arc in self.arcs:
            if arc.start_chapter <= chapter <= arc.end_chapter:
                current_arc = arc.name
                break

        return (
            f"【大纲锚点】\n"
            f"整体进度: {overall:.0%} ({chapter}/{self.total_chapters}章)\n"
            f"当前弧段: {current_arc}\n"
            f"本章进度配额: {quota.min_progress:.0%} - {quota.max_progress:.0%}\n"
            f"建议内容: {quota.description}\n"
            f"约束: 进度不足或超速都会触发门禁警告"
        )

    # ─── 自动生成配额 ─────────────────────────────

    def _auto_generate_quotas(self):
        """自动生成所有章节的进度配额"""
        if self.total_chapters <= 0:
            return

        # 如果没有显式定义的弧段，创建默认的三段式结构
        if not self.arcs:
            self.arcs = self._default_arcs()

        for arc in self.arcs:
            # 如果弧段内已有精确配额则跳过
            existing_chapters = {q.chapter for q in arc.chapter_quotas}
            for ch in range(arc.start_chapter, arc.end_chapter + 1):
                if ch not in existing_chapters:
                    q = self._generate_quota_for_chapter(arc, ch)
                    arc.chapter_quotas.append(q)

    def _default_arcs(self) -> list[ArcDefinition]:
        """创建默认的三段式弧段"""
        if self.total_chapters <= 0:
            return []

        # 开篇(20%) / 发展(60%) / 收尾(20%)
        split1 = max(1, int(self.total_chapters * 0.2))
        split2 = max(split1 + 1, int(self.total_chapters * 0.8))

        return [
            ArcDefinition("开篇铺垫", 1, split1, "世界观引入+主角出场"),
            ArcDefinition("剧情发展", split1 + 1, split2, "冲突升级+角色成长"),
            ArcDefinition("高潮收尾", split2 + 1, self.total_chapters, "核心冲突解决"),
        ]

    def _generate_quota_for_chapter(self, arc: ArcDefinition, chapter: int) -> ChapterQuota:
        """为弧段内的一个章节生成进度配额"""

        # 根据弧段位置决定每章推进速度
        arc_progress = (chapter - arc.start_chapter) / max(arc.total_chapters, 1)

        if "开篇" in arc.name:
            min_p, max_p = 0.02, 0.04
            desc = "推进主线剧情，适量世界观展示"
        elif "收尾" in arc.name or "高潮" in arc.name:
            min_p, max_p = 0.06, 0.12
            desc = "加快节奏，解决冲突和伏笔"
        else:
            # 发展期：中间快两头慢
            mid_factor = 1.0 - abs(arc_progress - 0.5) * 0.6
            min_p = 0.03 * mid_factor
            max_p = 0.06 * mid_factor
            desc = "保持节奏，深化角色和冲突"

        return ChapterQuota(
            chapter=chapter,
            min_progress=round(min_p, 3),
            max_progress=round(max_p, 3),
            description=desc,
        )

    # ─── 持久化 ──────────────────────────────────────

    def _save(self):
        data = {
            "book_id": self.book_id,
            "total_chapters": self.total_chapters,
            "arcs": [
                {
                    "name": a.name,
                    "start_chapter": a.start_chapter,
                    "end_chapter": a.end_chapter,
                    "description": a.description,
                    "chapter_quotas": [
                        {
                            "chapter": q.chapter,
                            "min_progress": q.min_progress,
                            "max_progress": q.max_progress,
                            "description": q.description,
                        }
                        for q in a.chapter_quotas
                    ],
                }
                for a in self.arcs
            ],
        }
        path = self._data_dir / "outline_anchor.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self):
        path = self._data_dir / "outline_anchor.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_chapters = data.get("total_chapters", 0)
            for ad in data.get("arcs", []):
                quotas = [ChapterQuota(**q) for q in ad.get("chapter_quotas", [])]
                self.arcs.append(
                    ArcDefinition(
                        name=ad["name"],
                        start_chapter=ad["start_chapter"],
                        end_chapter=ad["end_chapter"],
                        description=ad.get("description", ""),
                        chapter_quotas=quotas,
                    )
                )
        except Exception as e:
            logger.warning(f"[OutlineAnchor] 加载失败: {e}")


# ─── 工厂函数 ──────────────────────────────────────

_anchors: dict[str, OutlineAnchor] = {}


def get_outline_anchor(book_id: str) -> OutlineAnchor:
    if book_id not in _anchors:
        _anchors[book_id] = OutlineAnchor(book_id)
    return _anchors[book_id]

"""
pleasure 爽点引擎 — 爽点弧线规划器
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kunlun.pleasure.types import PleasureType, get_pleasure_config


@dataclass
class ArcPhase:
    """爽点弧线的一个阶段"""

    name: str  # 阶段名
    chapter_range: tuple[int, int]  # 章节范围 (start, end)
    target_density: float  # 目标密度 (每千字爽点数)
    primary_types: list[PleasureType]  # 推荐主要爽点类型
    description: str = ""


@dataclass
class PleasureArcPlan:
    """爽点弧线规划"""

    book_id: str
    total_chapters: int
    chapters_per_act: int  # 每幕章节数
    phases: list[ArcPhase] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    HIGH_DENSITY = 3.5  # 高密度
    MEDIUM_DENSITY = 2.5  # 中密度
    LOW_DENSITY = 1.5  # 低密度


class PleasureArcPlanner:
    """爽点弧线规划器 — 规划跨章节爽点分布

    基于竞品研究的网文爽点节奏规律:
      - 开头黄金三章: 高密度 (≥3/千字)
      - 发展期: 中密度 + 多样性
      - 高潮前: 低密度蓄力
      - 高潮幕: 极高密度爆发
      - 收尾/过渡: 中低密度 + 情感爽点
    """

    @classmethod
    def plan_default_arc(cls, book_id: str, total_chapters: int) -> PleasureArcPlan:
        """生成默认爽点弧线 — 经典五幕式"""
        c = total_chapters
        plan = PleasureArcPlan(
            book_id=book_id,
            total_chapters=c,
            chapters_per_act=max(1, c // 5),
        )

        intro_end = max(1, c // 10)
        development_end = max(intro_end + 1, c * 35 // 100)
        build_up_end = max(development_end + 1, c * 60 // 100)
        climax_end = max(build_up_end + 1, c * 85 // 100)

        plan.phases = [
            ArcPhase(
                name="开场引爆期（黄金三章）",
                chapter_range=(1, intro_end),
                target_density=PleasureArcPlan.HIGH_DENSITY,
                primary_types=[
                    PleasureType.FACE_SLAP,
                    PleasureType.LEVEL_UP,
                    PleasureType.SHOW_OFF,
                ],
                description="高频强爽点抓住读者，每2000字至少1个打脸/装逼/升级",
            ),
            ArcPhase(
                name="发展铺陈期",
                chapter_range=(intro_end + 1, development_end),
                target_density=PleasureArcPlan.MEDIUM_DENSITY,
                primary_types=[
                    PleasureType.LEVEL_UP,
                    PleasureType.ACQUISITION,
                    PleasureType.HOT_BLOOD,
                    PleasureType.ROMANCE,
                    PleasureType.FORTUNATE,
                ],
                description="爽点密度适中，注重类型多样性，引入升级/奇遇/感情线",
            ),
            ArcPhase(
                name="蓄力酝酿期",
                chapter_range=(development_end + 1, build_up_end),
                target_density=PleasureArcPlan.LOW_DENSITY,
                primary_types=[PleasureType.REVEAL, PleasureType.TWIST, PleasureType.TOUCHING],
                description="降低爽点频率，为高潮蓄力，穿插揭秘/反转/感动",
            ),
            ArcPhase(
                name="高潮爆发期",
                chapter_range=(build_up_end + 1, climax_end),
                target_density=PleasureArcPlan.HIGH_DENSITY + 1.0,
                primary_types=[
                    PleasureType.OVERWHELM,
                    PleasureType.REVENGE,
                    PleasureType.LEVEL_UP,
                    PleasureType.AWAKENING,
                    PleasureType.HOT_BLOOD,
                ],
                description="极高密度爽点爆发，碾压/复仇/觉醒/热血全面释放",
            ),
            ArcPhase(
                name="收尾过渡期",
                chapter_range=(climax_end + 1, c),
                target_density=PleasureArcPlan.MEDIUM_DENSITY,
                primary_types=[
                    PleasureType.ROMANCE,
                    PleasureType.TOUCHING,
                    PleasureType.PROTECT,
                    PleasureType.SYSTEM_REWARD,
                    PleasureType.FORTUNATE,
                ],
                description="爽点适中过渡，以感情/感动/收获为主，为下一卷埋钩子",
            ),
        ]

        plan.notes = [
            "每幕内部也应有微观波浪式节奏（爽点 → 铺垫 → 爽点）",
            "高潮幕前3章建议蓄力（降低密度），后3章全力爆发",
            "收尾幕末尾2章需为下一卷埋设钩子",
            "同类型爽点连续不超过3次，超过需穿插其他类型",
        ]

        return plan

    @classmethod
    def plan_for_genre(cls, book_id: str, total_chapters: int, genre: str) -> PleasureArcPlan:
        """根据题材生成定制化爽点弧线"""
        base = cls.plan_default_arc(book_id, total_chapters)

        genre_lower = genre.lower()

        if any(k in genre_lower for k in ["系统", "sys"]):
            base.phases[0].primary_types.insert(0, PleasureType.SYSTEM_REWARD)
            base.phases[1].target_density = PleasureArcPlan.MEDIUM_DENSITY + 0.5
            base.phases[1].primary_types.append(PleasureType.SYSTEM_REWARD)
            base.notes.insert(0, "系统流: 每5-10章安排一次系统升级/新功能解锁")
        elif any(k in genre_lower for k in ["重生", "reborn"]):
            base.phases[0].primary_types.insert(0, PleasureType.REVEAL)
            base.phases[1].primary_types.extend([PleasureType.FORTUNATE, PleasureType.REVENGE])
            base.notes.insert(0, "重生流: 前期利用前世信息制造信息差爽点")
        elif any(k in genre_lower for k in ["悬疑", "推理"]):
            for phase in base.phases:
                phase.primary_types = [
                    p
                    for p in phase.primary_types
                    if p not in (PleasureType.HOT_BLOOD, PleasureType.HAREM)
                ]
            base.phases[1].primary_types.extend([PleasureType.REVEAL, PleasureType.TWIST])
            base.phases[3].primary_types.append(PleasureType.REVEAL)
            base.notes.insert(0, "悬疑: 每10-15章揭晓一个小谜题，保持悬念张力")
        elif any(k in genre_lower for k in ["言情", "恋爱"]):
            base.phases[1].primary_types = [
                PleasureType.ROMANCE,
                PleasureType.TOUCHING,
                PleasureType.PROTECT,
                PleasureType.HAREM,
            ]
            base.phases[4].primary_types = [
                PleasureType.ROMANCE,
                PleasureType.TOUCHING,
                PleasureType.HAREM,
            ]
            base.phases[3].primary_types.append(PleasureType.ROMANCE)
            base.notes.insert(0, "言情: 感情线为主，爽点以为情爱推进为主")

        return base

    @classmethod
    def get_phase_for_chapter(cls, plan: PleasureArcPlan, chapter_number: int) -> ArcPhase | None:
        """获取指定章节对应的弧线阶段"""
        for phase in plan.phases:
            start, end = phase.chapter_range
            if start <= chapter_number <= end:
                return phase
        return None

    @classmethod
    def generate_chapter_guidance(
        cls, plan: PleasureArcPlan, chapter_number: int, chapter_word_count: int = 3000
    ) -> dict[str, Any]:
        """生成单章爽点写作指导"""
        phase = cls.get_phase_for_chapter(plan, chapter_number)
        if not phase:
            return {"phase": "unknown", "guidance": "未在弧线范围内"}

        target_event_count = max(1, int(phase.target_density * chapter_word_count / 1000))
        type_names = [get_pleasure_config(p).name_cn for p in phase.primary_types[:4]]

        return {
            "phase": phase.name,
            "phase_description": phase.description,
            "target_density": phase.target_density,
            "target_event_count": target_event_count,
            "recommended_types": type_names,
            "guidance": f"当前处于「{phase.name}」，目标每千字{phase.target_density:.1f}个爽点，"
            f"本章建议{target_event_count}个。推荐类型: {' / '.join(type_names)}",
        }

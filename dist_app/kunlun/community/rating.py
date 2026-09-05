"""
评分/打赏系统 — 作品评分与读者互动

支持:
- 作品评分 (1-10 分)
- 多维评分 (文笔/情节/角色/世界观/节奏)
- 打赏 (虚拟货币)
- 催更票
- 评分排行榜

用法:
    rs = RatingSystem()
    rs.rate_book("book_001", "user_001", {
        "overall": 8,
        "writing": 9,
        "plot": 7,
        "characters": 8,
        "worldbuilding": 6,
        "pacing": 7,
    })
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BookRating:
    """作品评分"""

    book_id: str = ""
    user_id: str = ""
    overall: int = 0  # 综合评分 (1-10)
    writing: int = 0  # 文笔
    plot: int = 0  # 情节
    characters: int = 0  # 角色
    worldbuilding: int = 0  # 世界观
    pacing: int = 0  # 节奏
    comment: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def average_dimension(self) -> float:
        """各维度平均分"""
        dims = [self.writing, self.plot, self.characters, self.worldbuilding, self.pacing]
        valid = [d for d in dims if d > 0]
        return sum(valid) / len(valid) if valid else 0.0


@dataclass
class Tip:
    """打赏"""

    id: str = ""
    book_id: str = ""
    from_user: str = ""
    to_user: str = ""
    amount: int = 0  # 虚拟货币
    message: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class BoostTicket:
    """催更票"""

    id: str = ""
    book_id: str = ""
    chapter_num: int = 0
    from_user: str = ""
    amount: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class RatingSummary:
    """评分汇总"""

    book_id: str = ""
    total_ratings: int = 0
    average_overall: float = 0.0
    average_writing: float = 0.0
    average_plot: float = 0.0
    average_characters: float = 0.0
    average_worldbuilding: float = 0.0
    average_pacing: float = 0.0


class RatingSystem:
    """评分/打赏系统

    管理作品评分、打赏、催更票等读者互动功能。

    用法:
        rs = RatingSystem()
        rs.rate_book("book_001", "user_001", {"overall": 8, "writing": 9})
        rs.tip_book("book_001", "user_001", "user_002", 100, "加油！")
    """

    # 评分维度
    DIMENSIONS = ["writing", "plot", "characters", "worldbuilding", "pacing"]

    def __init__(self):
        self._ratings: dict[str, list[BookRating]] = {}  # book_id -> ratings
        self._tips: list[Tip] = []
        self._boost_tickets: list[BoostTicket] = []
        self._summaries: dict[str, RatingSummary] = {}

    def rate_book(
        self,
        book_id: str,
        user_id: str,
        scores: dict[str, int],
        comment: str = "",
    ) -> BookRating:
        """评分"""
        # 限制评分范围
        overall = max(1, min(10, scores.get("overall", 0)))

        rating = BookRating(
            book_id=book_id,
            user_id=user_id,
            overall=overall,
            writing=max(1, min(10, scores.get("writing", 0))),
            plot=max(1, min(10, scores.get("plot", 0))),
            characters=max(1, min(10, scores.get("characters", 0))),
            worldbuilding=max(1, min(10, scores.get("worldbuilding", 0))),
            pacing=max(1, min(10, scores.get("pacing", 0))),
            comment=comment,
        )

        self._ratings.setdefault(book_id, []).append(rating)

        # 清除缓存
        self._summaries.pop(book_id, None)

        return rating

    def get_summary(self, book_id: str) -> RatingSummary:
        """获取评分汇总"""
        cached = self._summaries.get(book_id)
        if cached:
            return cached

        ratings = self._ratings.get(book_id, [])
        total = len(ratings)

        if total == 0:
            return RatingSummary(book_id=book_id)

        summary = RatingSummary(
            book_id=book_id,
            total_ratings=total,
            average_overall=sum(r.overall for r in ratings) / total,
            average_writing=sum(r.writing for r in ratings if r.writing > 0)
            / max(sum(1 for r in ratings if r.writing > 0), 1),
            average_plot=sum(r.plot for r in ratings if r.plot > 0)
            / max(sum(1 for r in ratings if r.plot > 0), 1),
            average_characters=sum(r.characters for r in ratings if r.characters > 0)
            / max(sum(1 for r in ratings if r.characters > 0), 1),
            average_worldbuilding=sum(r.worldbuilding for r in ratings if r.worldbuilding > 0)
            / max(sum(1 for r in ratings if r.worldbuilding > 0), 1),
            average_pacing=sum(r.pacing for r in ratings if r.pacing > 0)
            / max(sum(1 for r in ratings if r.pacing > 0), 1),
        )

        self._summaries[book_id] = summary
        return summary

    def get_ratings(self, book_id: str, limit: int = 50) -> list[BookRating]:
        """获取评分列表"""
        ratings = self._ratings.get(book_id, [])
        return sorted(ratings, key=lambda r: -r.created_at)[:limit]

    def get_user_rating(
        self,
        book_id: str,
        user_id: str,
    ) -> BookRating | None:
        """获取用户对某书的评分"""
        for r in self._ratings.get(book_id, []):
            if r.user_id == user_id:
                return r
        return None

    def tip_book(
        self,
        book_id: str,
        from_user: str,
        to_user: str,
        amount: int,
        message: str = "",
    ) -> Tip:
        """打赏"""
        import uuid

        tip = Tip(
            id=str(uuid.uuid4())[:12],
            book_id=book_id,
            from_user=from_user,
            to_user=to_user,
            amount=amount,
            message=message,
        )
        self._tips.append(tip)
        return tip

    def boost_chapter(
        self,
        book_id: str,
        chapter_num: int,
        from_user: str,
        amount: int,
    ) -> BoostTicket:
        """催更"""
        import uuid

        ticket = BoostTicket(
            id=str(uuid.uuid4())[:12],
            book_id=book_id,
            chapter_num=chapter_num,
            from_user=from_user,
            amount=amount,
        )
        self._boost_tickets.append(ticket)
        return ticket

    def get_tip_total(self, book_id: str) -> int:
        """获取某书的总打赏额"""
        return sum(t.amount for t in self._tips if t.book_id == book_id)

    def get_boost_total(self, book_id: str) -> dict[str, Any]:
        """获取催更统计"""
        tickets = [t for t in self._boost_tickets if t.book_id == book_id]
        return {
            "total_tickets": len(tickets),
            "total_amount": sum(t.amount for t in tickets),
            "unique_users": len({t.from_user for t in tickets}),
        }

    def get_top_rated(self, limit: int = 20) -> list[RatingSummary]:
        """获取评分排行榜"""
        summaries = []
        for book_id in self._ratings:
            summary = self.get_summary(book_id)
            if summary.total_ratings >= 3:  # 至少 3 人评分
                summaries.append(summary)
        summaries.sort(key=lambda s: -s.average_overall)
        return summaries[:limit]

    def get_stats(self) -> dict[str, Any]:
        return {
            "rated_books": len(self._ratings),
            "total_ratings": sum(len(v) for v in self._ratings.values()),
            "total_tips": len(self._tips),
            "total_boosts": len(self._boost_tickets),
        }

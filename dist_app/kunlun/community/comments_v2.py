"""
评论系统 V2 — 增强版评论系统

支持:
- 星级评分 (1-5 星)
- 评论点赞/踩
- 评论回复嵌套
- 评论举报
- 作者置顶评论
- 评论统计

用法:
    cs = CommentSystemV2()
    review = cs.add_review(
        book_id="book_001",
        author_id="user_001",
        rating=4,
        content="文笔细腻，情节紧凑",
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CommentSort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_LIKED = "most_liked"
    HIGHEST_RATED = "highest_rated"


@dataclass
class ReviewComment:
    """评论/书评"""

    id: str = ""
    book_id: str = ""
    chapter_num: int = 0
    author_id: str = ""
    content: str = ""
    rating: int = 0  # 1-5 星
    parent_id: str = ""  # 父评论 ID（回复）
    created_at: float = field(default_factory=time.time)
    edited_at: float = 0.0
    like_count: int = 0
    dislike_count: int = 0
    is_pinned: bool = False
    is_spoiler: bool = False
    report_count: int = 0
    deleted: bool = False

    @property
    def is_reply(self) -> bool:
        return bool(self.parent_id)

    @property
    def net_score(self) -> int:
        return self.like_count - self.dislike_count


@dataclass
class RatingStats:
    """评分统计"""

    book_id: str = ""
    total_reviews: int = 0
    average_rating: float = 0.0
    rating_distribution: dict[int, int] = field(
        default_factory=lambda: {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
        }
    )


class CommentSystemV2:
    """评论系统 V2

    增强版评论系统，支持评分、回复嵌套、点赞/踩、举报等功能。

    用法:
        cs = CommentSystemV2()
        cs.add_review("book_001", "user_001", rating=5, content="好书！")
        stats = cs.get_rating_stats("book_001")
    """

    def __init__(self):
        self._reviews: dict[str, list[ReviewComment]] = {}  # book_id -> reviews
        self._rating_stats: dict[str, RatingStats] = {}

    def add_review(
        self,
        book_id: str,
        author_id: str,
        content: str,
        rating: int = 0,
        chapter_num: int = 0,
        parent_id: str = "",
        is_spoiler: bool = False,
    ) -> ReviewComment:
        """添加评论/评分"""
        import uuid

        # 限制评分范围
        rating = max(0, min(5, rating))

        comment = ReviewComment(
            id=str(uuid.uuid4())[:12],
            book_id=book_id,
            chapter_num=chapter_num,
            author_id=author_id,
            content=content,
            rating=rating,
            parent_id=parent_id,
            is_spoiler=is_spoiler,
        )

        self._reviews.setdefault(book_id, []).append(comment)

        if rating > 0:
            self._update_rating_stats(book_id)

        return comment

    def get_reviews(
        self,
        book_id: str,
        sort: CommentSort = CommentSort.NEWEST,
        chapter_num: int = 0,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReviewComment]:
        """获取评论列表"""
        reviews = self._reviews.get(book_id, [])

        # 过滤已删除和回复
        reviews = [r for r in reviews if not r.deleted and not r.is_reply]

        if chapter_num > 0:
            reviews = [r for r in reviews if r.chapter_num == chapter_num]

        # 排序
        if sort == CommentSort.NEWEST:
            reviews.sort(key=lambda r: -r.created_at)
        elif sort == CommentSort.OLDEST:
            reviews.sort(key=lambda r: r.created_at)
        elif sort == CommentSort.MOST_LIKED:
            reviews.sort(key=lambda r: -r.like_count)
        elif sort == CommentSort.HIGHEST_RATED:
            reviews.sort(key=lambda r: (-r.rating, -r.like_count))

        return reviews[offset : offset + limit]

    def get_replies(self, book_id: str, parent_id: str) -> list[ReviewComment]:
        """获取某评论的回复"""
        reviews = self._reviews.get(book_id, [])
        return [r for r in reviews if r.parent_id == parent_id and not r.deleted]

    def like_review(self, book_id: str, review_id: str) -> bool:
        return self._vote(book_id, review_id, like=True)

    def dislike_review(self, book_id: str, review_id: str) -> bool:
        return self._vote(book_id, review_id, like=False)

    def _vote(self, book_id: str, review_id: str, like: bool) -> bool:
        for review in self._reviews.get(book_id, []):
            if review.id == review_id:
                if like:
                    review.like_count += 1
                else:
                    review.dislike_count += 1
                return True
        return False

    def pin_review(self, book_id: str, review_id: str) -> bool:
        """置顶评论"""
        for review in self._reviews.get(book_id, []):
            if review.id == review_id:
                review.is_pinned = True
                return True
        return False

    def report_review(self, book_id: str, review_id: str) -> bool:
        """举报评论"""
        for review in self._reviews.get(book_id, []):
            if review.id == review_id:
                review.report_count += 1
                return True
        return False

    def delete_review(self, book_id: str, review_id: str) -> bool:
        """软删除评论"""
        for review in self._reviews.get(book_id, []):
            if review.id == review_id:
                review.deleted = True
                self._update_rating_stats(book_id)
                return True
        return False

    def get_rating_stats(self, book_id: str) -> RatingStats:
        """获取评分统计"""
        stats = self._rating_stats.get(book_id)
        if not stats:
            # 计算评分统计
            stats = RatingStats(book_id=book_id)
            reviews = [
                r
                for r in self._reviews.get(book_id, [])
                if not r.deleted and not r.is_reply and r.rating > 0
            ]
            stats.total_reviews = len(reviews)
            if reviews:
                stats.average_rating = sum(r.rating for r in reviews) / len(reviews)
            for r in reviews:
                bucket = min(max(r.rating, 1), 5)
                stats.rating_distribution[bucket] += 1
            self._rating_stats[book_id] = stats
        return stats

    def _update_rating_stats(self, book_id: str) -> None:
        """更新评分统计缓存"""
        self._rating_stats.pop(book_id, None)

    def get_user_reviews(self, author_id: str) -> list[ReviewComment]:
        """获取用户的所有评论"""
        results: list[ReviewComment] = []
        for reviews in self._reviews.values():
            results.extend(r for r in reviews if r.author_id == author_id and not r.deleted)
        results.sort(key=lambda r: -r.created_at)
        return results

    def get_stats(self) -> dict[str, Any]:
        total_reviews = sum(len(v) for v in self._reviews.values())
        return {
            "total_books": len(self._reviews),
            "total_reviews": total_reviews,
            "total_replies": sum(
                1 for reviews in self._reviews.values() for r in reviews if r.is_reply
            ),
        }

"""
社区引擎 — 读者社区核心

整合论坛、评论、评分、书签等模块，提供统一的社区功能入口。

用法:
    from kunlun.community import CommunityEngine, community_engine

    engine = CommunityEngine()
    book = engine.get_book_community("book_001")
    print(book.rating_summary.average_overall)
"""

from __future__ import annotations

from typing import Any

from kunlun.community.bookmark import BookmarkManager
from kunlun.community.comments_v2 import CommentSystemV2
from kunlun.community.forum import ForumEngine
from kunlun.community.rating import RatingSystem


class CommunityEngine:
    """社区引擎

    整合所有社区功能，提供统一的接口。

    用法:
        engine = CommunityEngine()

        # 论坛
        thread = engine.forum.create_thread("general", "user_001", "标题", "内容")

        # 评论
        engine.comments.add_review("book_001", "user_001", "好书！", rating=5)

        # 评分
        engine.ratings.rate_book("book_001", "user_001", {"overall": 8})

        # 书签
        engine.bookmarks.add_bookmark("user_001", "book_001")
    """

    def __init__(self):
        self._forum = ForumEngine()
        self._comments = CommentSystemV2()
        self._ratings = RatingSystem()
        self._bookmarks = BookmarkManager()

    @property
    def forum(self) -> ForumEngine:
        return self._forum

    @property
    def comments(self) -> CommentSystemV2:
        return self._comments

    @property
    def ratings(self) -> RatingSystem:
        return self._ratings

    @property
    def bookmarks(self) -> BookmarkManager:
        return self._bookmarks

    def get_book_community(self, book_id: str) -> dict[str, Any]:
        """获取书籍社区全景数据"""
        return {
            "book_id": book_id,
            "rating": {
                "summary": self._ratings.get_summary(book_id),
                "total": len(self._ratings._ratings.get(book_id, [])),
            },
            "comments": {
                "total": len(self._comments._reviews.get(book_id, [])),
                "stats": self._comments.get_rating_stats(book_id),
            },
            "tips": {
                "total": self._ratings.get_tip_total(book_id),
            },
            "boosts": self._ratings.get_boost_total(book_id),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "forum": self._forum.get_stats(),
            "comments": self._comments.get_stats(),
            "ratings": self._ratings.get_stats(),
            "bookmarks": self._bookmarks.get_stats(),
        }


# 全局单例
community_engine = CommunityEngine()

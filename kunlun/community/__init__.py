"""
社区模块 — 读者社区与互动系统

功能:
- 论坛 (ForumEngine) — 版块/主题/回复
- 评论 V2 (CommentSystemV2) — 评分/回复/点赞/举报
- 评分系统 (RatingSystem) — 多维评分/打赏/催更
- 书签管理 (BookmarkManager) — 书架/阅读进度/历史

用法:
    from kunlun.community import CommunityEngine, community_engine

    engine = community_engine
    engine.ratings.rate_book("book_001", "user_001", {"overall": 8})
"""

from __future__ import annotations

from kunlun.community.bookmark import (
    Bookmark,
    BookmarkManager,
    ReadingHistory,
    ReadingProgress,
    ShelfCategory,
)
from kunlun.community.comments_v2 import (
    CommentSort,
    CommentSystemV2,
    RatingStats,
    ReviewComment,
)
from kunlun.community.engine import CommunityEngine, community_engine
from kunlun.community.forum import (
    ForumBoard,
    ForumEngine,
    ForumPost,
    ForumThread,
    ThreadStatus,
)
from kunlun.community.rating import (
    BookRating,
    BoostTicket,
    RatingSummary,
    RatingSystem,
    Tip,
)

__all__ = [
    "BookRating",
    "Bookmark",
    "BookmarkManager",
    "BoostTicket",
    "CommentSort",
    "CommentSystemV2",
    "CommunityEngine",
    "ForumBoard",
    "ForumEngine",
    "ForumPost",
    "ForumThread",
    "RatingStats",
    "RatingSummary",
    "RatingSystem",
    "ReadingHistory",
    "ReadingProgress",
    "ReviewComment",
    "ShelfCategory",
    "ThreadStatus",
    "Tip",
    "community_engine",
]

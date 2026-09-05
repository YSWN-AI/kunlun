"""
昆仑创作引擎 — 书架作品管理

增强现有书籍管理能力，支持书籍分组、回收站、快速操作等功能。
书籍信息从 data/books/ 目录扫描获取，分组和回收站数据存储在 data/bookshelf/。
"""

from kunlun.bookshelf.models import (
    BookCard,
    CreateGroupRequest,
    GroupInfo,
    MoveToGroupRequest,
    QuickActions,
)
from kunlun.bookshelf.service import (
    create_group,
    delete_group,
    get_book,
    get_quick_actions,
    get_recycle_bin,
    list_books,
    list_groups,
    move_to_group,
    move_to_recycle,
    permanently_delete,
    restore_from_recycle,
)

__all__ = [
    "BookCard",
    "CreateGroupRequest",
    "GroupInfo",
    "MoveToGroupRequest",
    "QuickActions",
    "create_group",
    "delete_group",
    "get_book",
    "get_quick_actions",
    "get_recycle_bin",
    "list_books",
    "list_groups",
    "move_to_group",
    "move_to_recycle",
    "permanently_delete",
    "restore_from_recycle",
]

__version__ = "0.1.0"

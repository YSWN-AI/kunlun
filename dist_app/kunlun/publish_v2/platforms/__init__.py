"""发布平台适配器集合"""

from __future__ import annotations

from kunlun.publish_v2.platforms.base import (
    BasePlatformAdapter,
    ChapterData,
    PlatformInfo,
    PublishResult,
    PublishStatus,
)
from kunlun.publish_v2.platforms.fanqie import FanqieAdapter
from kunlun.publish_v2.platforms.feilu import FeiluAdapter
from kunlun.publish_v2.platforms.jinjiang import JinjiangAdapter
from kunlun.publish_v2.platforms.qidian import QidianAdapter
from kunlun.publish_v2.platforms.zongheng import ZonghengAdapter

__all__ = [
    "BasePlatformAdapter",
    "ChapterData",
    "FanqieAdapter",
    "FeiluAdapter",
    "JinjiangAdapter",
    "PlatformInfo",
    "PublishResult",
    "PublishStatus",
    "QidianAdapter",
    "ZonghengAdapter",
]

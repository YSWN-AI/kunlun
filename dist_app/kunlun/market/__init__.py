"""
市场情报系统 — 扫榜拆书 + 热搜热点辅助决策

功能:
  - 热点趋势分析: 通过LLM分析当前网文市场趋势
  - 拆书: 分析优秀作品的叙事结构、爽点布局、角色设计
  - 热搜关联: 将社会热点与创作方向关联
"""

from kunlun.market.engine import MarketIntelligence, market_intel

__all__ = [
    "MarketIntelligence",
    "market_intel",
]

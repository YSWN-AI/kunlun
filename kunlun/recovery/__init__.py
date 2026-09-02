"""
昆仑创作引擎 — 断更恢复引擎

检测断更状态 → 自动生成恢复报告，包含：
- 当前位置（最后完成章节 + 下一章蓝图状态）
- 故事现状（N 章递进摘要）
- 活跃伏笔（逾期/即将到期/安全）
- 角色位置速查
- 待办建议

设计来源：昆仑_剩余功能补全设计.md §断更恢复
"""

from kunlun.recovery.engine import RecoveryEngine

__all__ = ["RecoveryEngine"]

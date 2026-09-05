"""
昆仑创作引擎 — 规划/行动双模式系统

对标灵蟹创作规划/行动模式，为每本书提供两种写作模式：
- planning（规划模式）：只输出计划，不执行实际写作
- action（行动模式）：执行实际写作，自动批准
"""

from kunlun.writing_mode.manager import ModeManager, WritingMode

__all__ = ["ModeManager", "WritingMode"]

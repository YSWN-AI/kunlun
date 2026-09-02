"""
昆仑创作引擎 — 插件系统

提供可扩展的插件架构，支持热加载/卸载/钩子事件。
第三方可通过继承 PluginBase 并注册到 PluginManager 来扩展昆仑功能。

用法:
    from kunlun.plugins import PluginBase, PluginManager, plugin_manager

    class MyPlugin(PluginBase):
        name = "my_plugin"
        version = "1.0.0"

        async def on_chapter_generated(self, chapter):
            # 章节生成后自动触发
            print(f"New chapter: {chapter.title}")

    plugin_manager.register(MyPlugin())
"""

from __future__ import annotations

from kunlun.plugins.base import PluginBase, PluginEvent, PluginHook
from kunlun.plugins.manager import PluginManager, plugin_manager

__all__ = [
    "PluginBase",
    "PluginEvent",
    "PluginHook",
    "PluginManager",
    "plugin_manager",
]

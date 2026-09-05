"""
插件管理器 — 注册/卸载/热加载/事件分发
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from kunlun.plugins.base import PluginBase, PluginEvent, PluginHook

logger = logging.getLogger(__name__)


class PluginManager:
    """插件管理器

    职责:
    - 注册/卸载插件
    - 按钩子分组管理
    - 事件分发到所有匹配的插件
    - 从目录热加载插件
    - 插件生命周期管理

    用法:
        from kunlun.plugins import plugin_manager

        # 注册插件
        plugin_manager.register(MyPlugin())

        # 触发事件
        await plugin_manager.emit(PluginEvent(
            hook=PluginHook.CHAPTER_GENERATED,
            book_id="book_001",
            data={"chapter_num": 42},
        ))

        # 热加载插件目录
        plugin_manager.load_from_dir("plugins/")
    """

    def __init__(self):
        self._plugins: dict[str, PluginBase] = {}
        self._hook_index: dict[PluginHook, list[PluginBase]] = defaultdict(list)
        self._started = False

    # ── 注册与卸载 ─────────────────────────────────

    def register(self, plugin: PluginBase) -> None:
        """注册插件到管理器"""
        if not plugin.name:
            logger.warning("Plugin has no name, skipping registration")
            return

        if plugin.name in self._plugins:
            logger.warning("Plugin '%s' already registered, replacing", plugin.name)
            self.unregister(plugin.name)

        self._plugins[plugin.name] = plugin
        for hook in plugin.hooks:
            self._hook_index[hook].append(plugin)

        logger.info("Plugin registered: %s (hooks: %s)", plugin.name, plugin.hooks)

        # 如果系统已启动，立即触发启动事件
        if self._started:
            _task = asyncio.create_task(  # noqa: RUF006
                plugin.on_event(PluginEvent(hook=PluginHook.SYSTEM_STARTUP))
            )

    def unregister(self, name: str) -> None:
        """卸载插件"""
        plugin = self._plugins.pop(name, None)
        if plugin:
            for hook in plugin.hooks:
                self._hook_index[hook] = [p for p in self._hook_index[hook] if p.name != name]
            # 清理空的 hook 索引
            empty_hooks = [h for h, p in self._hook_index.items() if not p]
            for h in empty_hooks:
                del self._hook_index[h]
            logger.info("Plugin unregistered: %s", name)

    def get_plugin(self, name: str) -> PluginBase | None:
        """获取已注册的插件"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginBase]:
        """列出所有已注册的插件"""
        return list(self._plugins.values())

    # ── 事件分发 ───────────────────────────────────

    async def emit(self, event: PluginEvent) -> None:
        """向所有匹配的插件分发事件"""
        plugins = self._hook_index.get(event.hook, [])
        if not plugins:
            return

        tasks = [p.on_event(event) for p in plugins]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for plugin, result in zip(plugins, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(
                    "Plugin '%s' failed on hook %s: %s",
                    plugin.name,
                    event.hook,
                    result,
                )

    # ── 热加载 ─────────────────────────────────────

    def load_from_dir(self, directory: str | Path) -> int:
        """从目录加载所有 Python 插件

        扫描目录中的 .py 文件，查找 PluginBase 的子类并自动注册。
        返回加载的插件数量。
        """
        dir_path = Path(directory) if isinstance(directory, str) else directory
        if not dir_path.is_dir():
            logger.warning("Plugin directory not found: %s", dir_path)
            return 0

        loaded = 0
        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, str(py_file))
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, PluginBase)
                        and attr is not PluginBase
                    ):
                        self.register(attr())
                        loaded += 1
            except Exception as e:
                logger.warning("Failed to load plugin from %s: %s", py_file, e)

        logger.info("Loaded %d plugins from %s", loaded, dir_path)
        return loaded

    # ── 生命周期 ───────────────────────────────────

    async def startup(self) -> None:
        """启动所有插件"""
        self._started = True
        event = PluginEvent(hook=PluginHook.SYSTEM_STARTUP)
        await self.emit(event)
        logger.info("Plugin system started (%d plugins)", len(self._plugins))

    async def shutdown(self) -> None:
        """关闭所有插件"""
        event = PluginEvent(hook=PluginHook.SYSTEM_SHUTDOWN)
        await self.emit(event)
        self._plugins.clear()
        self._hook_index.clear()
        self._started = False
        logger.info("Plugin system shut down")

    # ── 统计 ───────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """获取插件系统统计信息"""
        return {
            "total_plugins": len(self._plugins),
            "active_hooks": len(self._hook_index),
            "plugins": [
                {
                    "name": p.name,
                    "version": p.version,
                    "description": p.description,
                    "hooks": [h.value for h in p.hooks],
                }
                for p in self._plugins.values()
            ],
        }


# 全局单例
plugin_manager = PluginManager()

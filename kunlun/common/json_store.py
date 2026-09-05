"""
昆仑创作引擎 — 轻量 JSON 持久化工具

跨模块复用: cooldown / cost_tracker / aigc_detect / reflector / marginal_efficiency 等多处
重复的 JSON save/load 模式，统一为类型安全的工具函数。

用法:
    from kunlun.common.json_store import load_json, save_json, JsonStore

    data = load_json(path, default={})
    save_json(path, data, pretty=True)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generic, TypeVar

from loguru import logger

T = TypeVar("T")


def load_json(path: Path, *, default: T | None = None) -> T | None:
    """从磁盘加载 JSON，失败时返回默认值。

    Args:
        path: JSON 文件路径
        default: 加载失败或文件不存在时的默认返回值

    Returns:
        反序列化的对象，或 default
    """
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.debug(f"[JsonStore] 加载失败 {path}: {e}")
        return default


def save_json(path: Path, data: Any, *, pretty: bool = False, mkdir: bool = True) -> bool:
    """将数据以 JSON 格式持久化到磁盘。

    Args:
        path: 目标文件路径
        data: 要序列化的数据
        pretty: 是否使用缩进格式化
        mkdir: 是否自动创建父目录

    Returns:
        成功返回 True，失败返回 False
    """
    try:
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        indent = 2 if pretty else None
        path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
        return True
    except OSError as e:
        logger.debug(f"[JsonStore] 保存失败 {path}: {e}")
        return False


class JsonStore(Generic[T]):
    """带类型约束的 JSON 持久化容器。

    使用方式:
        from dataclasses import dataclass
        from kunlun.common.json_store import JsonStore

        @dataclass
        class Config:
            key: str = "default"

        store = JsonStore(Path("data/config.json"), Config)
        cfg = store.load()
        cfg.key = "new_value"
        store.save(cfg)
    """

    def __init__(self, path: Path, factory: type[T], *, pretty: bool = False):
        self.path = path
        self.factory = factory
        self.pretty = pretty

    def load(self) -> T:
        data: dict[str, Any] | None = load_json(self.path, default={})
        try:
            if isinstance(data, dict):
                return self.factory(**data)
            return self.factory()
        except (TypeError, ValueError) as e:
            logger.debug(f"[JsonStore] 数据反序列化失败: {e}")
            return self.factory()

    def save(self, obj: T) -> bool:
        if hasattr(obj, "__dict__"):
            data: Any = obj.__dict__
        else:
            data = obj
        return save_json(self.path, data, pretty=self.pretty)

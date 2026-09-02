"""
昆仑创作引擎 — 扩展模块统一基类

为 21+ 扩展模块提供标准生命周期：
  __init__(book_id) → 自动创建 _data_dir
  save() / _load() → JSON 持久化
  get_factory() → 工厂单例模式

所有扩展模块应继承此类以减少重复代码。"""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from kunlun.config import settings


class BaseExtensionModule:
    """扩展模块基类 — 标准持久化 + 工厂模式"""

    # 子类覆盖：data_dir 下的子目录名
    SUBDIR: str = "extensions"

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self._data_dir: Path | None = None
        self._data: dict = {}
        if book_id:
            self._data_dir = settings.DATA_DIR / self.SUBDIR / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ── 持久化 ────────────────────────────────────────

    @property
    def _state_path(self) -> Path:
        if self._data_dir:
            return self._data_dir / "state.json"
        return Path("/dev/null")

    def save(self):
        """持久化到磁盘"""
        if not self._data_dir:
            return
        try:
            self._state_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2))
        except (OSError, TypeError, ValueError) as e:
            # 磁盘满、权限不足、JSON序列化失败 → 记录告警但不崩溃
            logger.warning(f"[{self.__class__.__name__}] 保存失败 (数据可能丢失): {e}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] 保存发生未预期异常: {e}", exc_info=True)

    def _load(self):
        """从磁盘恢复"""
        if not self._data_dir or not self._state_path.exists():
            return
        try:
            self._data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[{self.__class__.__name__}] 加载失败 (将使用空状态): {e}")
            self._data = {}
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] 加载发生未预期异常: {e}", exc_info=True)
            self._data = {}

    # ── 数据访问 ──────────────────────────────────────

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def update(self, data: dict):
        self._data.update(data)
        self.save()

    # ── 工厂模式 ──────────────────────────────────────

    _instances: dict[str, BaseExtensionModule] = {}

    @classmethod
    def get_factory(cls, book_id: str = "") -> BaseExtensionModule:
        """获取/创建模块实例（工厂单例模式）"""
        key = f"{cls.__name__}:{book_id}"
        if key not in cls._instances:
            cls._instances[key] = cls(book_id)
        return cls._instances[key]

    @classmethod
    def clear_factory(cls):
        """清空工厂缓存（主要用于测试）"""
        cls._instances = {}

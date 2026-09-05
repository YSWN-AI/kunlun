"""
昆仑创作引擎 — 规划/行动双模式管理器

支持模式切换、模式配置（模型/温度/最大token/自动批准）、持久化、Prompt 后缀生成。
模式状态存入 data/books/book_<id>/mode_config.json
"""

from __future__ import annotations

import json
import time
from enum import StrEnum
from typing import Any

from loguru import logger

from kunlun.config import settings


class WritingMode(StrEnum):
    """写作模式枚举。"""

    PLANNING = "planning"
    ACTION = "action"


# 默认模式配置
_DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "planning": {
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 2048,
        "auto_approve": False,
    },
    "action": {
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 2048,
        "auto_approve": True,
    },
}

# 模式对应的 Prompt 后缀
_PLANNING_SUFFIX = (
    "\n\n【规划模式】当前处于规划模式，只输出计划、大纲、步骤和分析，"
    "不要执行实际写作、不要生成正文内容、不要调用写作管线。"
    "所有输出以可执行的计划文档形式呈现。"
)

_ACTION_SUFFIX = (
    "\n\n【行动模式】当前处于行动模式，可以执行实际写作操作。"
    "按照计划直接生成内容，无需等待额外确认。"
)


class ModeManager:
    """写作模式管理器。

    每本书独立维护当前模式和模式配置，持久化到 mode_config.json。
    """

    def __init__(self, book_id: str) -> None:
        self.book_id = book_id
        self.book_dir = settings.DATA_DIR / "books" / book_id
        self.config_path = self.book_dir / "mode_config.json"

    # ─── 持久化 ────────────────────────────────────

    def _ensure_dir(self) -> None:
        self.book_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        """加载模式配置文件，不存在则返回默认结构。"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                # 合并默认配置，确保字段完整
                for mode in ("planning", "action"):
                    if mode not in data.get("configs", {}):
                        data.setdefault("configs", {})[mode] = dict(_DEFAULT_CONFIG[mode])
                    else:
                        merged = dict(_DEFAULT_CONFIG[mode])
                        merged.update(data["configs"][mode])
                        data["configs"][mode] = merged
                return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"[ModeManager] 读取 mode_config.json 失败，使用默认配置: {e}")
        return {
            "current_mode": WritingMode.ACTION.value,
            "configs": {
                "planning": dict(_DEFAULT_CONFIG["planning"]),
                "action": dict(_DEFAULT_CONFIG["action"]),
            },
            "last_switch_at": None,
            "created_at": time.time(),
        }

    def _save(self, data: dict[str, Any]) -> None:
        self._ensure_dir()
        self.config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ─── 模式查询与切换 ────────────────────────────

    def get_mode(self, book_id: str) -> WritingMode:  # noqa: ARG002
        """获取当前写作模式。"""
        data = self._load()
        mode_str = data.get("current_mode", WritingMode.ACTION.value)
        try:
            return WritingMode(mode_str)
        except ValueError:
            return WritingMode.ACTION

    def set_mode(self, book_id: str, mode: WritingMode) -> bool:
        """切换写作模式。

        Args:
            book_id: 作品 ID
            mode: 目标模式

        Returns:
            是否切换成功
        """
        data = self._load()
        old_mode = data.get("current_mode")
        data["current_mode"] = mode.value
        data["last_switch_at"] = time.time()
        data["last_switch_datetime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save(data)
        logger.info(f"[ModeManager] {book_id} 模式切换: {old_mode} → {mode.value}")
        return True

    # ─── 模式配置 ──────────────────────────────────

    def get_mode_config(self, book_id: str) -> dict[str, Any]:  # noqa: ARG002
        """获取完整模式配置（含两种模式的配置和当前模式）。"""
        data = self._load()
        return {
            "current_mode": data.get("current_mode", WritingMode.ACTION.value),
            "configs": data.get("configs", dict(_DEFAULT_CONFIG)),
            "last_switch_at": data.get("last_switch_at"),
            "last_switch_datetime": data.get("last_switch_datetime"),
        }

    def update_mode_config(self, book_id: str, mode: WritingMode, config: dict[str, Any]) -> bool:
        """更新指定模式的配置。

        Args:
            book_id: 作品 ID
            mode: 目标模式
            config: 配置字典，支持字段：model, temperature, max_tokens, auto_approve

        Returns:
            是否更新成功
        """
        data = self._load()
        mode_key = mode.value
        if mode_key not in data.get("configs", {}):
            data.setdefault("configs", {})[mode_key] = dict(_DEFAULT_CONFIG[mode_key])

        # 只更新允许的字段
        allowed_fields = {"model", "temperature", "max_tokens", "auto_approve"}
        for key, value in config.items():
            if key in allowed_fields:
                data["configs"][mode_key][key] = value

        data["config_updated_at"] = time.time()
        self._save(data)
        logger.info(f"[ModeManager] {book_id} 模式 {mode_key} 配置已更新")
        return True

    # ─── 执行判断 ──────────────────────────────────

    def should_execute(self, book_id: str) -> bool:
        """当前模式是否允许执行实际写作。

        planning 模式返回 False，action 模式返回 True。
        """
        mode = self.get_mode(book_id)
        return mode == WritingMode.ACTION

    # ─── Prompt 后缀 ───────────────────────────────

    def get_system_prompt_suffix(self, book_id: str) -> str:
        """根据当前模式返回 System Prompt 后缀。"""
        mode = self.get_mode(book_id)
        if mode == WritingMode.PLANNING:
            return _PLANNING_SUFFIX
        return _ACTION_SUFFIX

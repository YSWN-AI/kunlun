"""
昆仑创作引擎 — 配置包 (Config Domain Splitting)

字段定义分布在各子模块中，Settings 通过多继承组合。
所有配置对象从此处统一导出，保持向后兼容。
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from pydantic_settings import BaseSettings, SettingsConfigDict

from kunlun.config.base import BOOK_ID_PATTERN, BaseConfig
from kunlun.config.database import DatabaseConfig
from kunlun.config.llm import LLMConfig
from kunlun.config.pipeline import PipelineConfig
from kunlun.config.thresholds import ThresholdsConfig


class Settings(
    BaseConfig,
    DatabaseConfig,
    LLMConfig,
    PipelineConfig,
    ThresholdsConfig,
    BaseSettings,
):
    """全局配置，所有字段从 .env / 环境变量自动加载。
    字段定义分布在各 config/ 子模块中，通过多继承组合。
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    def model_post_init(self, __context) -> None:
        """初始化后补全路径依赖的默认值。"""
        super().model_post_init(__context)
        if not self.qdrant_path:
            self.qdrant_path = str(self.DATA_DIR / "qdrant")
        if not self.sqlite_path:
            self.sqlite_path = str(self.DATA_DIR / "kunlun_search.db")


_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings


def _reset_settings() -> None:
    global _settings  # noqa: PLW0603
    _settings = None


settings: Settings = _get_settings()


__all__ = [
    "BOOK_ID_PATTERN",
    "BaseConfig",
    "DatabaseConfig",
    "LLMConfig",
    "PipelineConfig",
    "Settings",
    "ThresholdsConfig",
    "settings",
]

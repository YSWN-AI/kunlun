"""
昆仑创作引擎 — 基础配置 (路径、应用环境、日志、守护进程、API认证、速率限制、通知)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel

from kunlun.config.defaults import DEFAULT_KUNLUN_MODE

BOOK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


class BaseConfig(BaseModel):
    # ── 运行模式 ──────────────────────────────────
    kunlun_mode: str = DEFAULT_KUNLUN_MODE  # "personal" | "enterprise"

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Path(os.environ.get("KUNLUN_DATA_DIR", str(PROJECT_ROOT / "data")))
    SKILLS_DIR: Path = PROJECT_ROOT / "skills"
    PROMPTS_DIR: Path = PROJECT_ROOT / "kunlun" / "prompts"

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_env: str = "development"
    log_level: str = "INFO"
    LOG_FORMAT: str = "text"

    nats_url: str = "nats://localhost:4222"

    daemon_default_chapters: int = 10
    daemon_chapter_interval: int = 3
    daemon_max_retries: int = 3
    daemon_max_consecutive_failures: int = 5
    daemon_retry_backoff_base: float = 5.0

    writer_context_budget: int = 8000

    api_auth_enabled: bool = False
    api_auth_key: str = ""

    rate_limit_per_minute: int = 30
    rate_limit_generate_per_minute: int = 3
    rate_limit_export_per_minute: int = 5

    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "kunlun-engine"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    feishu_webhook_url: str = ""
    feishu_webhook_secret: str = ""
    wecom_webhook_url: str = ""
    webhook_url: str = ""
    webhook_secret: str = ""

    model_config = {"extra": "ignore"}

    def is_production(self) -> bool:
        return self.app_env == "production"

    def is_development(self) -> bool:
        return self.app_env == "development"

    def is_personal_mode(self) -> bool:
        return self.kunlun_mode == "personal"

    def get_project_dir(self, *subdirs: str) -> Path:
        p = self.PROJECT_ROOT.joinpath(*subdirs)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_book_safe_path(self, book_id: str, *subdirs: str) -> Path:
        if not book_id or not BOOK_ID_PATTERN.match(book_id):
            raise ValueError(f"book_id 格式不合法: '{book_id}'。仅允许字母、数字、下划线和短横线。")
        if book_id in (".", "..") or book_id.startswith("."):
            raise ValueError(f"book_id 不允许以 '.' 开头: '{book_id}'")
        p = self.DATA_DIR.joinpath(*subdirs, book_id).resolve()
        data_root = self.DATA_DIR.resolve()
        if not str(p).startswith(str(data_root)):
            raise ValueError(f"路径穿越检测: '{p}' 不在 '{data_root}' 内")
        return p

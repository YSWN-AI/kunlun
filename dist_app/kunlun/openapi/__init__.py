"""
昆仑创作引擎 — 开放API平台

为第三方开发者提供公开REST API、SDK和API密钥管理。

用法:
    from kunlun.openapi import OpenAPIManager, openapi_manager

    # 创建API密钥
    key = openapi_manager.create_api_key("my-app", permissions=["read", "write"])

    # 验证请求
    app = openapi_manager.authenticate("api-key-xxx")
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class APIPermission(StrEnum):
    """API 权限"""

    READ = "read"
    WRITE = "write"
    PUBLISH = "publish"
    ADMIN = "admin"


class RateLimitTier(StrEnum):
    """限流等级"""

    FREE = "free"  # 100 req/hour
    BASIC = "basic"  # 1,000 req/hour
    PRO = "pro"  # 10,000 req/hour
    ENTERPRISE = "enterprise"  # unlimited


@dataclass
class RateLimit:
    """限流配置"""

    tier: RateLimitTier = RateLimitTier.FREE
    requests_per_hour: int = 100
    requests_per_day: int = 1000
    concurrent_requests: int = 1


RATE_LIMITS: dict[RateLimitTier, RateLimit] = {
    RateLimitTier.FREE: RateLimit(
        tier=RateLimitTier.FREE, requests_per_hour=100, requests_per_day=1000, concurrent_requests=1
    ),
    RateLimitTier.BASIC: RateLimit(
        tier=RateLimitTier.BASIC,
        requests_per_hour=1000,
        requests_per_day=10000,
        concurrent_requests=5,
    ),
    RateLimitTier.PRO: RateLimit(
        tier=RateLimitTier.PRO,
        requests_per_hour=10000,
        requests_per_day=100000,
        concurrent_requests=20,
    ),
    RateLimitTier.ENTERPRISE: RateLimit(
        tier=RateLimitTier.ENTERPRISE,
        requests_per_hour=100000,
        requests_per_day=1000000,
        concurrent_requests=100,
    ),
}


@dataclass
class AppRegistration:
    """API应用注册信息"""

    app_id: str
    app_name: str
    api_key: str
    permissions: list[APIPermission] = field(default_factory=lambda: [APIPermission.READ])
    rate_limit_tier: RateLimitTier = RateLimitTier.FREE
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0
    is_active: bool = True
    owner: str = ""
    description: str = ""


@dataclass
class UsageStats:
    """用量统计"""

    app_id: str
    total_requests: int = 0
    requests_this_hour: int = 0
    requests_today: int = 0
    tokens_used: int = 0
    last_reset: float = field(default_factory=time.time)


class OpenAPIManager:
    """开放API平台管理器

    职责:
    - API密钥生成与管理
    - 权限控制
    - 限流
    - 用量统计
    - SDK生成

    用法:
        manager = OpenAPIManager()
        key = manager.create_api_key("MyApp", [APIPermission.READ, APIPermission.WRITE])
    """

    def __init__(self, data_dir: str = "data/openapi"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._apps: dict[str, AppRegistration] = {}
        self._usage: dict[str, UsageStats] = {}
        self._load_apps()

    # ── 密钥管理 ───────────────────────────────────

    def create_api_key(
        self,
        app_name: str,
        permissions: list[APIPermission] | None = None,
        tier: RateLimitTier = RateLimitTier.FREE,
        owner: str = "",
        description: str = "",
    ) -> AppRegistration:
        """创建新的API密钥"""
        app_id = secrets.token_hex(8)
        api_key = "kl_" + secrets.token_urlsafe(32)

        app = AppRegistration(
            app_id=app_id,
            app_name=app_name,
            api_key=api_key,
            permissions=permissions or [APIPermission.READ],
            rate_limit_tier=tier,
            owner=owner,
            description=description,
        )

        self._apps[app_id] = app
        self._usage[app_id] = UsageStats(app_id=app_id)
        self._save_apps()

        logger.info("API key created: %s (%s)", app_name, app_id)
        return app

    def revoke_api_key(self, app_id: str) -> bool:
        """撤销API密钥"""
        app = self._apps.get(app_id)
        if app:
            app.is_active = False
            self._save_apps()
            logger.info("API key revoked: %s", app_id)
            return True
        return False

    def list_apps(self) -> list[AppRegistration]:
        """列出所有应用"""
        return list(self._apps.values())

    # ── 认证与授权 ─────────────────────────────────

    def authenticate(self, api_key: str) -> AppRegistration | None:
        """认证API密钥，返回应用注册信息"""
        for app in self._apps.values():
            if app.api_key == api_key and app.is_active:
                app.last_used = time.time()
                return app
        return None

    def check_permission(
        self,
        app: AppRegistration,
        permission: APIPermission,
    ) -> bool:
        """检查权限"""
        if APIPermission.ADMIN in app.permissions:
            return True
        return permission in app.permissions

    # ── 限流 ───────────────────────────────────────

    def check_rate_limit(self, app_id: str) -> tuple[bool, str]:
        """检查限流

        返回:
            (是否通过, 失败原因)
        """
        limit = RATE_LIMITS.get(
            self._apps.get(
                app_id, AppRegistration(app_id="", app_name="", api_key="")
            ).rate_limit_tier,
            RATE_LIMITS[RateLimitTier.FREE],
        )

        usage = self._usage.get(app_id)
        if usage is None:
            usage = UsageStats(app_id=app_id)
            self._usage[app_id] = usage

        # 重置计数器
        now = time.time()
        if now - usage.last_reset > 3600:
            usage.requests_this_hour = 0
            usage.last_reset = now

        if usage.requests_this_hour >= limit.requests_per_hour:
            return False, f"Rate limit exceeded: {limit.requests_per_hour} req/hour"

        usage.requests_this_hour += 1
        usage.total_requests += 1
        return True, "OK"

    def get_rate_limit_for_key(self, api_key: str) -> RateLimit | None:
        """获取指定密钥的限流配置"""
        app = self.authenticate(api_key)
        if app:
            return RATE_LIMITS.get(app.rate_limit_tier)
        return None

    # ── 用量统计 ───────────────────────────────────

    def get_usage(self, app_id: str) -> UsageStats | None:
        """获取应用用量统计"""
        return self._usage.get(app_id)

    def record_usage(self, app_id: str, tokens: int) -> None:
        """记录用量"""
        usage = self._usage.get(app_id)
        if usage:
            usage.tokens_used += tokens

    def get_all_usage(self) -> dict[str, UsageStats]:
        """获取所有应用的用量统计"""
        return dict(self._usage)

    # ── SDK生成 ────────────────────────────────────

    def generate_sdk(self, language: str, output_dir: str | Path) -> Path:
        """生成SDK代码骨架

        Args:
            language: 目标语言 (python, javascript, typescript)
            output_dir: 输出目录

        Returns:
            生成的SDK目录路径
        """
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        if language == "python":
            return self._generate_python_sdk(output)
        if language == "javascript":
            return self._generate_js_sdk(output)
        if language == "typescript":
            return self._generate_ts_sdk(output)
        raise ValueError(f"Unsupported language: {language}")

    def _generate_python_sdk(self, output_dir: Path) -> Path:
        sdk_code = '''
"""昆仑创作引擎 Python SDK"""

from __future__ import annotations

import httpx
from typing import Any


class KunlunClient:
    """昆仑API客户端"""

    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    # ── 书籍 ────────────────────

    def list_books(self) -> list[dict[str, Any]]:
        resp = self._client.get(f"{self.base_url}/api/v1/books")
        resp.raise_for_status()
        return resp.json()

    def create_book(self, title: str, genre: str = "", description: str = "") -> dict[str, Any]:
        resp = self._client.post(
            f"{self.base_url}/api/v1/books",
            json={"title": title, "genre": genre, "description": description},
        )
        resp.raise_for_status()
        return resp.json()

    # ── 生成 ────────────────────

    def generate_chapter(self, book_id: str, outline: str = "") -> dict[str, Any]:
        resp = self._client.post(
            f"{self.base_url}/api/v1/books/{book_id}/generate",
            json={"outline": outline},
        )
        resp.raise_for_status()
        return resp.json()

    # ── 审计 ────────────────────

    def audit_chapter(self, book_id: str, content: str) -> dict[str, Any]:
        resp = self._client.post(
            f"{self.base_url}/api/v1/books/{book_id}/audit",
            json={"content": content},
        )
        resp.raise_for_status()
        return resp.json()

    # ── TTS ─────────────────────

    def generate_audio(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes:
        resp = self._client.post(
            f"{self.base_url}/api/v1/tts",
            json={"text": text, "voice": voice},
        )
        resp.raise_for_status()
        return resp.content

    # ── 图像 ────────────────────

    def generate_cover(self, title: str, genre: str, style: str = "realistic") -> bytes:
        resp = self._client.post(
            f"{self.base_url}/api/v1/images/cover",
            json={"title": title, "genre": genre, "style": style},
        )
        resp.raise_for_status()
        return resp.content

    def close(self):
        self._client.close()
'''
        sdk_file = output_dir / "kunlun_client.py"
        sdk_file.write_text(sdk_code.strip() + "\n", encoding="utf-8")
        return sdk_file

    def _generate_js_sdk(self, output_dir: Path) -> Path:
        sdk_code = """
/**
 * 昆仑创作引擎 JavaScript SDK
 */
class KunlunClient {
  constructor(apiKey, baseUrl = "http://localhost:8000") {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\\/$/, "");
  }

  async _request(method, path, body = null) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  async listBooks() { return this._request("GET", "/api/v1/books"); }
  async createBook(title, genre = "", description = "") {
    return this._request("POST", "/api/v1/books", { title, genre, description });
  }
  async generateChapter(bookId, outline = "") {
    return this._request("POST", `/api/v1/books/${bookId}/generate`, { outline });
  }
}

module.exports = { KunlunClient };
"""
        sdk_file = output_dir / "kunlun_client.js"
        sdk_file.write_text(sdk_code.strip() + "\n", encoding="utf-8")
        return sdk_file

    def _generate_ts_sdk(self, output_dir: Path) -> Path:
        sdk_code = """
/**
 * 昆仑创作引擎 TypeScript SDK
 */

export interface Book {
  book_id: string;
  title: string;
  genre: string;
  description: string;
  chapter_count: number;
}

export interface ChapterResult {
  chapter_num: number;
  title: string;
  content: string;
}

export interface AuditResult {
  score: number;
  issues: Array<{ gate: string; level: string; message: string }>;
}

export class KunlunClient {
  private apiKey: string;
  private baseUrl: string;

  constructor(apiKey: string, baseUrl: string = "http://localhost:8000") {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\\/$/, "");
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json() as Promise<T>;
  }

  async listBooks(): Promise<Book[]> {
    return this.request<Book[]>("GET", "/api/v1/books");
  }

  async createBook(title: string, genre?: string, description?: string): Promise<Book> {
    return this.request<Book>("POST", "/api/v1/books", { title, genre, description });
  }

  async generateChapter(bookId: string, outline?: string): Promise<ChapterResult> {
    return this.request<ChapterResult>("POST", `/api/v1/books/${bookId}/generate`, { outline });
  }

  async auditChapter(bookId: string, content: string): Promise<AuditResult> {
    return this.request<AuditResult>("POST", `/api/v1/books/${bookId}/audit`, { content });
  }
}
"""
        sdk_file = output_dir / "kunlun_client.ts"
        sdk_file.write_text(sdk_code.strip() + "\n", encoding="utf-8")
        return sdk_file

    # ── 持久化 ─────────────────────────────────────

    def _save_apps(self) -> None:
        import json

        apps_file = self.data_dir / "apps.json"
        data = {
            app_id: {
                "app_id": app.app_id,
                "app_name": app.app_name,
                "api_key": app.api_key,
                "permissions": [p.value for p in app.permissions],
                "rate_limit_tier": app.rate_limit_tier.value,
                "created_at": app.created_at,
                "last_used": app.last_used,
                "is_active": app.is_active,
                "owner": app.owner,
                "description": app.description,
            }
            for app_id, app in self._apps.items()
        }
        apps_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_apps(self) -> None:
        import json

        apps_file = self.data_dir / "apps.json"
        if apps_file.exists():
            data = json.loads(apps_file.read_text(encoding="utf-8"))
            for app_id, app_data in data.items():
                self._apps[app_id] = AppRegistration(
                    app_id=app_data["app_id"],
                    app_name=app_data["app_name"],
                    api_key=app_data["api_key"],
                    permissions=[APIPermission(p) for p in app_data["permissions"]],
                    rate_limit_tier=RateLimitTier(app_data["rate_limit_tier"]),
                    created_at=app_data["created_at"],
                    last_used=app_data.get("last_used", 0),
                    is_active=app_data.get("is_active", True),
                    owner=app_data.get("owner", ""),
                    description=app_data.get("description", ""),
                )
                self._usage[app_id] = UsageStats(app_id=app_id)


# ── 全局单例 ───────────────────────────────────────

openapi_manager = OpenAPIManager()

"""
昆仑创作引擎 — 默认配置中心

所有配置项的默认值集中管理，用户无需修改 .env 即可运行。
自用场景下，只需配置 LLM_MODE 和 API Key 即可启动。

配置优先级: .env 环境变量 > 本文件默认值
"""

from __future__ import annotations

# ── 运行模式 ──────────────────────────────────
# "personal" — 自用模式（零外部服务，启动快）
# "enterprise" — 企业模式（需要 Docker 全套服务）
DEFAULT_KUNLUN_MODE = "personal"

# ── LLM 默认值 ──────────────────────────────────
# LLM_MODE: "local" (Ollama 免费) | "api" (DeepSeek/OpenAI 付费) | "auto" (自动检测)
DEFAULT_LLM_MODE = "local"

# 本地模型推荐（中文小说写作）
DEFAULT_LOCAL_MODEL = "qwen3:14b"  # Qwen3 14B — 中文写作最佳
DEFAULT_LOCAL_MODELS = {
    "qwen3:14b": "Qwen3 14B — 中文写作最佳，支持长文本",
    "qwen3:8b": "Qwen3 8B — 轻量级，8GB 显存可运行",
    "deepseek-r1:8b": "DeepSeek R1 8B — 推理能力强，适合大纲/审计",
    "llama3.1:8b": "Llama 3.1 8B — 通用型，英文写作好",
    "qwen2.5:14b": "Qwen2.5 14B — 稳定可靠，中文创作",
}

# ── 审计默认值 ──────────────────────────────────
# 本地模式下审计维度自动降级
DEFAULT_AUDIT_DIMENSIONS_LOCAL = 15  # 本地模式核心维度
DEFAULT_AUDIT_DIMENSIONS_FULL = 53  # API 模式完整维度

# ── 数据库默认值 ──────────────────────────────────
DEFAULT_SQLITE_PATH = "data/kunlun.db"
DEFAULT_QDRANT_PATH = "data/qdrant"

# ── API 默认值 ──────────────────────────────────
DEFAULT_APP_HOST = "127.0.0.1"
DEFAULT_APP_PORT = 8000

# ── 速率限制默认值 ──────────────────────────────────
DEFAULT_RATE_LIMIT_PER_MINUTE = 30
DEFAULT_RATE_LIMIT_GENERATE = 3
DEFAULT_RATE_LIMIT_EXPORT = 5

# ── 日志默认值 ──────────────────────────────────
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "text"

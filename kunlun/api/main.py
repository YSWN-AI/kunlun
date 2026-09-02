"""
昆仑创作引擎 — FastAPI 入口
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time as _time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from kunlun import __version__  # noqa: E402
from kunlun.config import settings  # noqa: E402

# ── 提前 monkey-patch starlette Config._read_file，确保 UTF-8 编码读取 .env ──
# 必须在任何 router 导入之前执行，因为 router 的 slowapi Limiter 初始化会
# 创建 Config() 从而调用 _read_file
_rate_limit_enabled = settings.rate_limit_per_minute > 0
if _rate_limit_enabled:
    try:
        from starlette.config import Config as _StarletteConfig

        def _utf8_read_file(file_name):
            file_values = {}
            with Path(file_name).open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()  # noqa: PLW2901
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip("\"'")
                        file_values[key] = value
            return file_values

        _StarletteConfig._read_file = staticmethod(_utf8_read_file)  # type: ignore[method-assign, assignment]
    except (ImportError, AttributeError) as e:
        logger.debug(f"[Startup] starlette Config monkey-patch 跳过: {e}")

from kunlun.api.routes import router  # noqa: E402

_startup_timings: dict[str, float] = {}


def _time_phase(phase_name: str) -> Callable:
    """启动阶段计时装饰器，记录各阶段耗时并汇总输出。"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = _time.perf_counter()
            try:
                result = await func(*args, **kwargs)
            finally:
                elapsed = _time.perf_counter() - start
                _startup_timings[phase_name] = elapsed
                logger.debug(f"[Startup] {phase_name}: {elapsed:.3f}s")
            return result

        return wrapper

    return decorator


def _log_timing_summary():
    total = sum(_startup_timings.values())
    phases = sorted(_startup_timings.items(), key=lambda x: x[1], reverse=True)
    lines = [f"\n{'=' * 50}", "启动阶段耗时汇总:", f"{'=' * 50}"]
    for name, elapsed in phases:
        pct = (elapsed / total * 100) if total > 0 else 0
        lines.append(f"  {name:<30} {elapsed:>7.3f}s ({pct:>5.1f}%)")
    lines.append(f"  {'─' * 40}")
    lines.append(f"  {'总计':<30} {total:>7.3f}s")
    lines.append(f"{'=' * 50}")
    logger.info("\n".join(lines))


async def _init_neo4j_constraints():
    """初始化 Neo4j 约束（异步并行中执行）"""
    try:
        from kunlun.kg.client import kg_client

        kg_client.init_constraints()
    except Exception as e:
        logger.warning(f"Neo4j 约束初始化失败 (不影响启动): {e}")


async def _init_seed_data():
    """填充领域知识图谱种子数据"""
    try:
        from kunlun.kg.seed_data import init_seed_data_if_empty

        seeded = init_seed_data_if_empty()
        if seeded:
            logger.info(f"KG种子数据已初始化: {seeded}")
    except Exception as e:
        logger.warning(f"种子数据初始化跳过 (不影响启动): {e}")


async def _init_autosync():
    """初始化自动文件同步系统"""
    try:
        from kunlun import autosync

        n = sum(len(v) for v in autosync.AutoSync._handlers.values())
        logger.info(f"AutoSync就绪 ({n}个处理器)")
    except Exception as e:
        logger.debug(f"AutoSync初始化跳过: {e}")


async def _init_skills():
    """加载 SKILL.md 技能体系"""
    try:
        from kunlun.skills import skill_loader

        loaded = skill_loader.load_all()
        logger.info(f"技能体系: {len(loaded)} 个")
    except Exception as e:
        logger.warning(f"技能加载失败: {e}")


async def _init_alembic():
    """数据库迁移"""
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig

        _alembic_ini = settings.PROJECT_ROOT / "migrations" / "alembic.ini"
        if _alembic_ini.exists():
            alembic_cfg = AlembicConfig(str(_alembic_ini))
            alembic_cfg.set_main_option(
                "sqlalchemy.url", f"sqlite:///{settings.DATA_DIR / 'kunlun_search.db'}"
            )
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic迁移完成")
    except Exception as e:
        logger.warning(f"Alembic跳过: {e}")


async def _init_observability():
    """可观测性初始化"""
    try:
        from kunlun.observability import init_otel

        init_otel()
    except Exception as e:
        logger.debug(f"OTel初始化跳过: {e}")


async def _init_quality_selfcheck():
    """质量模块启动自检"""
    try:
        from kunlun.audit.ai_features import AI_FEATURES
        from kunlun.audit.output_contract import OUTPUT_SCHEMAS
        from kunlun.gacha.param_variator import AGENT_PARAM_RANGES
        from kunlun.style.refiner import REFINEMENT_RULES

        logger.info(
            f"质量自检: "
            f"{len(AI_FEATURES)}AI特征, "
            f"{len(OUTPUT_SCHEMAS)}契约, "
            f"{len(REFINEMENT_RULES)}精炼规则, "
            f"{len(AGENT_PARAM_RANGES)}Agent参数"
        )
    except Exception as e:
        logger.warning(f"质量模块异常: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期 — 并行初始化各子系统并追踪耗时。"""
    _t0 = _time.perf_counter()
    logger.info(f"昆仑 v{__version__} 启动 | 环境:{settings.app_env} | Neo4j:{settings.neo4j_uri}")

    missing_keys = settings.validate_api_keys()
    if missing_keys:
        logger.warning(f"API密钥未配置: {', '.join(missing_keys)} — 使用模拟模式")

    if settings.LOG_FORMAT == "json":
        logger.remove(0)
        logger.add(
            sys.stderr,
            format=lambda record: json.dumps(
                {
                    "time": record["time"].isoformat(),
                    "level": record["level"].name,
                    "message": record["message"],
                    "module": record["module"],
                    "function": record["function"],
                    "line": record["line"],
                },
                ensure_ascii=False,
            ),
            level="INFO",
        )

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # Neo4j 约束初始化改为后台延迟执行，不阻塞启动
    _neo4j_task = asyncio.create_task(_init_neo4j_constraints())  # noqa: RUF006

    # I/O绑定阶段 → 并行执行
    async def _init_autosync_timeout():
        try:
            await asyncio.wait_for(_init_autosync(), timeout=3.0)
        except TimeoutError:
            logger.warning("AutoSync 初始化超时 (3s)，跳过")

    await asyncio.gather(
        _time_phase("seed_data")(_init_seed_data)(),
        _time_phase("autosync")(_init_autosync_timeout)(),
        _time_phase("skills")(_init_skills)(),
        _time_phase("alembic")(_init_alembic)(),
        _time_phase("otel")(_init_observability)(),
        _time_phase("quality_selfcheck")(_init_quality_selfcheck)(),
    )

    _startup_timings["_total"] = _time.perf_counter() - _t0
    if settings.log_level.upper() == "DEBUG":
        _log_timing_summary()
    else:
        logger.info(f"启动完成 ({_startup_timings['_total']:.2f}s)")

    yield

    logger.info("昆仑创作引擎 关闭")


app = FastAPI(
    title="昆仑创作引擎",
    description="开源 AI 辅助网文创作引擎 — 结构化事实层 + 去AI味流水线 + 多Agent协作",
    version=__version__,
    lifespan=lifespan,
)

_rate_limit_enabled = settings.rate_limit_per_minute > 0
if _rate_limit_enabled:
    try:
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware

        from kunlun.api.rate_limit import get_limiter

        _storage_uri = "memory://"
        try:
            import redis as _redis

            _test_conn = _redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                socket_connect_timeout=1,
            )
            _test_conn.ping()
            _test_conn.close()
            _storage_uri = (
                f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            )
            logger.info(f"RateLimit: Redis ({_storage_uri})")
        except Exception:
            logger.info("RateLimit: memory (单进程)")

        limiter = get_limiter()
        if limiter:
            limiter._storage_uri = _storage_uri
            limiter._default_limits = [f"{settings.rate_limit_per_minute}/minute"]
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)

        async def _rate_limit_handler(_request: Request, exc: RateLimitExceeded):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "请求过于频繁，请稍后再试",
                    "retry_after": getattr(exc, "retry_after", 60),
                },
            )

        app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_handler))
        logger.info(f"速率限制: {settings.rate_limit_per_minute}/分钟")
    except ImportError:
        logger.debug("slowapi未安装，跳过速率限制")

if settings.app_env == "development":
    _allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "tauri://localhost",
    ]
else:
    _allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
    _allowed_origins = (
        [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
        if _allowed_origins_env
        else []
    )

_production_default = ["http://127.0.0.1:8000", "http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins if _allowed_origins else _production_default,
    allow_credentials=bool(_allowed_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next) -> Response:
    import hmac

    from kunlun.api.auth import _is_whitelisted

    if request.method == "OPTIONS":
        return await call_next(request)

    if not settings.api_auth_enabled:
        return await call_next(request)

    if _is_whitelisted(request.url.path):
        return await call_next(request)

    if not settings.api_auth_key:
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": "API 认证配置错误，请联系管理员"},
        )

    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "缺少 API Key，请在 X-API-Key 请求头中提供"},
        )

    if not hmac.compare_digest(api_key, settings.api_auth_key):
        logger.warning(
            f"API 认证失败: {request.method} {request.url.path} (来源: {request.client})"
        )
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "API Key 无效"},
        )

    return await call_next(request)


@app.middleware("http")
async def book_id_validation_middleware(request: Request, call_next) -> Response:
    from kunlun.safety.validators import validate_book_id as _validate

    book_id = request.path_params.get("book_id")
    if book_id:
        try:
            _validate(book_id)
        except ValueError as e:
            logger.warning(f"[Security] 非法 book_id: '{book_id}' @ {request.url.path}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"book_id 格式不合法: {e}"},
            )
    return await call_next(request)


try:
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(app, endpoint="/metrics")
    logger.debug("Prometheus /metrics 已启用")
except ImportError:
    logger.debug("prometheus_fastapi_instrumentator 未安装")

_log_dir = settings.DATA_DIR / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logger.add(
    str(_log_dir / "app.log"),
    rotation="10 MB",
    retention=3,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
)
logger.info("日志系统就绪")


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    _start = _time.time()
    response = await call_next(request)
    duration = _time.time() - _start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    if response.status_code < 400 and request.method in ("POST", "PUT", "DELETE"):
        path = request.url.path
        try:
            sync_data = getattr(request.state, "sync_data", {})
            if not sync_data and "book_id" in request.path_params:
                sync_data = {"book_id": request.path_params["book_id"]}
            from kunlun.autosync import AutoSync

            if "/generate" in path or "/daemon" in path:
                await AutoSync.trigger("chapter_generated", sync_data)
            elif "/feedback" in path or "/preferences" in path:
                await AutoSync.trigger("feedback_given", sync_data)
            elif "/export" in path:
                await AutoSync.trigger("chapter_exported", sync_data)
            elif "/book" in path or "/novel" in path:
                await AutoSync.trigger("book_updated", sync_data)
        except Exception as e:
            logger.debug(f"[AutoSync] 触发失败: {e}")
    return response


# 全局异常处理 — 使用精确类型映射
from kunlun.api.error_handlers import register_exception_handlers  # noqa: E402

register_exception_handlers(app)

# v2 → /api/v1 先挂载（精确路由优先）
try:
    from kunlun.api.routers import api_router as v2_router_for_v1

    app.include_router(v2_router_for_v1, prefix="/api/v1")
    logger.debug("v2路由 → /api/v1")
except Exception as e:
    logger.debug(f"v2→v1跳过: {e}")

app.include_router(router, prefix="/api/v1")
from kunlun.api.routes_health import router as health_router  # noqa: E402

app.include_router(health_router, prefix="/api/v1")
logger.debug("v1路由+健康检查 /api/v1")

# 流式生成 + 扩展路由（agents/orchestrate/truth-status/auto-fix）
from kunlun.api.routers.stream import router as stream_router  # noqa: E402

app.include_router(stream_router, prefix="/api/v1")
logger.debug("流式/扩展路由 /api/v1")

try:
    from kunlun.api.routers import api_router

    app.include_router(api_router, prefix="/api/v2")
    logger.debug("模块化路由 /api/v2")
except Exception as e:
    logger.debug(f"v2路由跳过: {e}")

from kunlun.api.routers.admin import router as admin_router  # noqa: E402

app.include_router(admin_router)

_frontend_dist = settings.PROJECT_ROOT / "frontend" / "dist"
if _frontend_dist.is_dir() and (_frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
    logger.debug("Vue桌面版 → /")
else:
    _web_dir = settings.PROJECT_ROOT / "web"
    if _web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
        logger.debug("Web UI (降级) → /")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )

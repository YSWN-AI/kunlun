"""
昆仑创作引擎 — API 路由模块

将原 routes.py 按领域拆分为子路由模块。
每个子模块包含该领域的所有路由、Pydantic 模型和辅助函数。

目录结构:
    routers/
        _shared.py        # 公共工具（缓存导入、限流器、共享模型）
        admin.py          # /health, /status
        chat.py           # /chat, /editor/chat
        daemon.py         # /daemon/start, /daemon/stop
        books.py          # /books/*
        chapters.py       # 批量生成章节
        audit.py          # /audit/run
        quality.py        # /quality/*
        vibe.py           # /vibe/*
        usage_routes.py   # /usage/*
        prompts.py        # /prompts/*
        params.py         # /params/*
        config_routes.py  # /config/*
        genres.py         # /genres/*
        export_routes.py  # 导出
        ws.py             # WebSocket
        stream.py         # SSE+扩展
        gacha.py          # /gacha/models
        kg.py             # KG查询+实体+快照
        search.py         # /search
        api_providers.py  # API配置
        humanize.py       # 去AI人性化
        pipeline.py       # 全管线创作
        marginal_efficiency.py  # 边际收益优化
        optimization.py   # 成本优化
        story_bible.py    # Story Bible (7 routes) — v2 新增
        publish_routes.py # 发布引擎 (6 routes) — v2 新增
        dashboard.py      # 仪表盘 v2 (6 routes) — v2 新增
        compliance.py     # 平台合规 (3 routes) — v2 新增
        aigc_detect.py    # AIGC检测 (2 routes) — v2 新增
        continuity.py     # 连续性检查 (2 routes) — v2 新增
        fanfic.py         # 同人创作 (3 routes) — v2 新增
        cover.py          # 封面生成 (2 routes) — v2 新增
        rules.py          # 规则系统 (2 routes) — v2 新增
        notify.py         # 通知系统 (2 routes) — v2 新增
        model_routing.py  # 模型路由 (2 routes) — v2 新增
        branch_plot.py    # 分支剧情 (6 routes) — v2 新增
        interactive.py    # 交互式小说 (10 routes) — v2 新增
        genres_v2.py      # 题材 v2 (3 routes) — v2 新增
        quality_v2.py     # 质量 v2 (3 routes) — v2 新增
        writer_context.py # 上下文压缩 (3 routes) — v2 新增
        retention.py      # 追读率 (1 route) — v2 新增
        write_routes.py   # 创作辅助 (1 route) — v2 新增
        stats.py          # 全书统计 (1 route) — v2 新增
        learn.py          # 偏好学习 (2 routes) — v2 新增

使用方式:
    from kunlun.api.routers import api_router
    app.include_router(api_router, prefix="/api/v2")
"""

from fastapi import APIRouter

from kunlun.api.routers.admin import router as admin_router
from kunlun.api.routers.aigc_detect import router as aigc_detect_router
from kunlun.api.routers.api_providers import router as api_providers_router
from kunlun.api.routers.audit import router as audit_router
from kunlun.api.routers.books import router as books_router
from kunlun.api.routers.branch_plot import router as branch_plot_router
from kunlun.api.routers.chapters import router as chapters_router
from kunlun.api.routers.chat import router as chat_router
from kunlun.api.routers.compliance import router as compliance_router
from kunlun.api.routers.config_routes import router as config_router
from kunlun.api.routers.continuity import router as continuity_router
from kunlun.api.routers.cover import router as cover_router
from kunlun.api.routers.daemon import router as daemon_router
from kunlun.api.routers.dashboard import router as dashboard_router
from kunlun.api.routers.export_routes import router as export_router
from kunlun.api.routers.fanfic import router as fanfic_router
from kunlun.api.routers.gacha import router as gacha_router
from kunlun.api.routers.genres import router as genres_router
from kunlun.api.routers.genres_v2 import router as genres_v2_router
from kunlun.api.routers.golden_triple import router as golden_triple_router
from kunlun.api.routers.humanize import router as humanize_router
from kunlun.api.routers.interactive import router as interactive_router
from kunlun.api.routers.kg import router as kg_router
from kunlun.api.routers.learn import router as learn_router
from kunlun.api.routers.marginal_efficiency import router as marginal_router
from kunlun.api.routers.model_routing import router as model_routing_router
from kunlun.api.routers.notify import router as notify_router
from kunlun.api.routers.optimization import router as optimization_router
from kunlun.api.routers.orchestrator import router as orchestrator_router
from kunlun.api.routers.params import router as params_router
from kunlun.api.routers.pipeline import router as pipeline_router
from kunlun.api.routers.prompts import router as prompts_router
from kunlun.api.routers.publish_routes import router as publish_router
from kunlun.api.routers.quality import router as quality_router
from kunlun.api.routers.quality_v2 import router as quality_v2_router
from kunlun.api.routers.retention import router as retention_router
from kunlun.api.routers.rules import router as rules_router
from kunlun.api.routers.search import router as search_router
from kunlun.api.routers.stats import router as stats_router

# v2 新增路由模块
from kunlun.api.routers.story_bible import router as story_bible_router
from kunlun.api.routers.stream import router as stream_router
from kunlun.api.routers.usage_routes import router as usage_router
from kunlun.api.routers.vibe import router as vibe_router
from kunlun.api.routers.write_routes import router as write_router
from kunlun.api.routers.writer_context import router as writer_context_router
from kunlun.api.routers.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(chat_router)
api_router.include_router(daemon_router)
api_router.include_router(books_router)
api_router.include_router(chapters_router)
api_router.include_router(audit_router)
api_router.include_router(quality_router)
api_router.include_router(vibe_router)
api_router.include_router(usage_router)
api_router.include_router(prompts_router)
api_router.include_router(params_router)
api_router.include_router(config_router)
api_router.include_router(genres_router)
api_router.include_router(export_router)
api_router.include_router(ws_router)
api_router.include_router(stream_router)
api_router.include_router(gacha_router)
api_router.include_router(kg_router)
api_router.include_router(search_router)
api_router.include_router(api_providers_router)
api_router.include_router(humanize_router)
api_router.include_router(pipeline_router)
api_router.include_router(marginal_router)
# v2 新增路由
api_router.include_router(story_bible_router)
api_router.include_router(publish_router)
api_router.include_router(dashboard_router)
api_router.include_router(compliance_router)
api_router.include_router(aigc_detect_router)
api_router.include_router(continuity_router)
api_router.include_router(fanfic_router)
api_router.include_router(cover_router)
api_router.include_router(rules_router)
api_router.include_router(notify_router)
api_router.include_router(model_routing_router)
api_router.include_router(genres_v2_router)
api_router.include_router(quality_v2_router)
api_router.include_router(writer_context_router)
api_router.include_router(retention_router)
api_router.include_router(write_router)
api_router.include_router(stats_router)
api_router.include_router(learn_router)
api_router.include_router(golden_triple_router)
api_router.include_router(branch_plot_router)
api_router.include_router(interactive_router)
api_router.include_router(optimization_router)
api_router.include_router(orchestrator_router)

__all__ = [
    "admin_router",
    "aigc_detect_router",
    "api_providers_router",
    "api_router",
    "audit_router",
    "books_router",
    "branch_plot_router",
    "chapters_router",
    "chat_router",
    "compliance_router",
    "config_router",
    "continuity_router",
    "cover_router",
    "daemon_router",
    "dashboard_router",
    "export_router",
    "fanfic_router",
    "gacha_router",
    "genres_router",
    "genres_v2_router",
    "golden_triple_router",
    "humanize_router",
    "kg_router",
    "learn_router",
    "marginal_router",
    "model_routing_router",
    "notify_router",
    "optimization_router",
    "orchestrator_router",
    "params_router",
    "pipeline_router",
    "prompts_router",
    "publish_router",
    "quality_router",
    "quality_v2_router",
    "retention_router",
    "rules_router",
    "search_router",
    "stats_router",
    "story_bible_router",
    "stream_router",
    "usage_router",
    "vibe_router",
    "write_router",
    "writer_context_router",
    "ws_router",
]

---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: c8f6d92f871b3a4904b940a0905d8b83_060807075fe511f1b0435254007bceed
    ReservedCode1: AA7er48UuONaqHNh2hP/OcLrwaKW96NixaFs84SatoR27z4Yd+31KAg+mckdGnAiVgl5KUZRwDACQVBptg/4eJ/KiqnfviVs49MwSv0xYCCPwglnmeQZIP8Bw8duQQKis2qOfCILUHHCHNlRTE7cnspGV8Ny/c2RtGJ+g/UKZFeQAyXEAqIGEwr0tv8=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: c8f6d92f871b3a4904b940a0905d8b83_060807075fe511f1b0435254007bceed
    ReservedCode2: AA7er48UuONaqHNh2hP/OcLrwaKW96NixaFs84SatoR27z4Yd+31KAg+mckdGnAiVgl5KUZRwDACQVBptg/4eJ/KiqnfviVs49MwSv0xYCCPwglnmeQZIP8Bw8duQQKis2qOfCILUHHCHNlRTE7cnspGV8Ny/c2RtGJ+g/UKZFeQAyXEAqIGEwr0tv8=
---

# 昆仑创作引擎 — 本地部署 & 桌面版

> v0.4.0 | Windows 11 / Python 3.11+ | Vibe Writing | MIT

**昆仑引擎 = AI 网文创作伙伴。** 不说参数，只说感受。通过 Vibe Writing 对话式创作，一句话完成从开书到完结导出的全流程。

## 快速开始

```bash
# 1. 安装 Python 依赖
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 启动昆仑（Web 模式）
python -m uvicorn kunlun.api.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 http://localhost:8000 使用 Vibe Writing 总调度界面。
打开 http://localhost:8000/docs 查看 API 文档。

## 目录结构

> **📖 完整文档体系见 [`docs/索引.md`](docs/索引.md)** — 模块化组织，按编号局部更新。
>
> 快速入口: [01-项目概览](docs/01-项目概览.md) · [02-Agent与管线](docs/02-Agent与管线.md) · [03-引擎与知识图谱](docs/03-引擎与知识图谱.md) · [04-API与前端](docs/04-API与前端.md) · [05-扩展模块](docs/05-扩展模块与宪法.md) · [06-版本与问题](docs/06-版本与问题.md) · [07-统计与检查清单](docs/07-统计与检查清单.md) · [08-修复报告](docs/08-修复报告.md)

```
kunlun/                      # Python 包（155 个 .py 文件, 39 子包, ~44,000 行）
├── vibe_writer/             # ★ Vibe Writing: 总调度(VibeOrchestrator) + 单章伙伴(VibeWriter)
├── conflict/                # ★ 冲突引擎: ConflictManager + TensionManager + 热力图
├── agents/                  # Agent 体系（10 + 1 个 Agent）
│   ├── makefile.py          # 调度员 (10步旧管线，兼容保留)
│   ├── architect.py         # 总规划师 (大纲→蓝图含冲突/氛围/爽点)
│   ├── writer.py            # 写手 (Gacha + TokenBudget + VibePrompt)
│   ├── auditor.py           # 审计员 (8门禁/33维/后写验证)
│   ├── editor.py            # 主编 Agent (对话式总调度)
│   ├── scheduler.py         # Agent 集群调度器
│   ├── publisher.py         # 发布 Agent
│   ├── sociologist.py       # 社会学家 Agent (44维)
│   └── message_bus.py       # Agent 消息总线
├── api/                     # FastAPI 入口
│   ├── main.py              # 应用入口 (lifespan/中间件/全局异常)
│   ├── routes.py            # 68路由 (66 API端点+健康检查+指标, 含7个Vibe Writing端点)
│   ├── ws_manager.py        # WebSocket 连接管理
│   └── streaming.py         # SSE 流式输出
├── audit/                   # 53维审计体系 + 番茄门禁 + 输出契约
│   ├── gates.py             # 8道门禁 (G1-G8, 纯规则, 零LLM)
│   ├── audit33.py           # 33维连续性审计 (6组维度)
│   ├── icu.py               # 连载ICU (7维质量+LLM自动修复)
│   ├── ai_features.py       # 36+ AI写作特征 (F/G组)
│   ├── fanqie_gates.py      # 番茄流量门禁(全生命周期+反作弊)
│   ├── post_write_validator.py # 11条零LLM后写检查
│   └── output_contract.py   # Schema输出校验(SpecForge风格)
├── kg/                      # 四层知识图谱
│   ├── ontology.py          # KG 本体 (9实体/22关系)
│   ├── client.py            # KG 统一客户端
│   ├── embedder.py          # 实体向量嵌入 (BGE)
│   ├── snapshot.py          # KG 快照管理
│   └── seed_data.py         # 种子数据
├── gacha/                   # 多模型抽卡引擎
│   ├── engine.py            # 4模式/9维评分/chat()/单例
│   └── param_variator.py    # 7维参数随机化+章节类型感知
├── context/                 # 上下文Token预算(6段,WenShape/SAGA)
├── quality/                 # 质量看板(聚合+可执行结果)+质量趋势
├── pipeline/                # NovelPipeline(4模式)+管线干预
├── style/                   # 文风引擎: Engineer+Fingerprint+Vibe+Refiner(304规则)
│   ├── engineer.py          # 去AI味规则 (句式CV/连词/段落/开头)
│   └── fingerprint.py       # 文风指纹 (统计+LLM注入)
├── truth/                   # 真相文件系统 (7个JSON)
├── pipeline/                # 管线干预系统 (人工暂停/审批)
├── prompts/                 # Prompt 模板
│   ├── pipeline.py          # 四阶段模板 (idea→outline→volume→draft)
│   ├── society.py           # 社会推演主 Prompt (44维)
│   └── society_ext[1-9].py  # 9种扩展变体
├── skills/                  # 技能加载器 (.md→system prompt)
├── common/                  # Alerter + NATS mock
│
│   # ── 扩展模块 (21个, 全实现在 __init__.py) ──
├── pleasure/                # 爽点检测 (12种+疲劳度)
├── dialogue/                # 对话质量评估 (5维+说话人画像)
├── arc/                     # 角色弧线追踪 (成长+情感线)
├── worlds/                  # 世界观一致性 (16维检查)
├── spacetime/               # 时空一致性引擎
├── state/                   # 角色状态机 (情感/体能/社会)
├── intel/                   # 情报追踪 (上帝视角检测)
├── ripple/                  # 涟漪效应检测
├── retention/               # 读者留存预测 (10维+弃书风险)
├── dashboard/               # 写作仪表盘 (字数/质量雷达/热力图)
├── ab_test/                 # A/B 测试框架 (10指标+统计检验)
├── emosupport/              # 情感支持引擎
├── comments/                # 读者评论分析
├── publish/                 # 发布代理 (7平台+定时)
├── safety/                  # 内容安全审查 (5类词库)
├── watermark/               # 智能水印 (零宽编码+签名)
├── market/                  # 市场情报 (热点+拆书)
├── shortform/               # 短篇生成引擎
├── outline/                 # 大纲管理
├── draft/                   # 草稿版本管理
├── versions/                # Git 版本管理器
│
│   # ── 顶层模块 ──
├── recovery/                # 断更恢复 + 版本回滚
├── exporter/                # 多格式导出 (7种: TXT/HTML/MD/EPUB/MOBI/PDF/DOCX)
├── config.py                # 全局配置 (pydantic-settings)
├── model_router.py          # 多模型路由 (9 agent配置)
├── token_tracker.py         # Token 用量+预算追踪
├── daemon.py                # 守护进程 (后台循环写章)
├── filesync.py              # 文件联动同步
├── autosync.py              # AutoSync 自动同步 (13个处理器)
├── auto_fix.py              # 自动修复 (Python语法)
├── import_engine.py         # 章节导入引擎 (+同人初始化)
├── book_config.py           # 作品配置管理
├── prompt_manager.py        # Prompt 管理 (3级覆盖)
├── outline_anchor.py        # 大纲锚点配额 (三段式弧段)
├── length_gov.py            # AI字数治理器
├── model_params.py          # 模型参数预设 (8参数)
├── modifier.py              # 定向修改引擎 (只改指定段落)
├── cooldown.py              # 事件冷却矩阵 (8种剧情事件)
├── brake.py                 # 反向刹车机制 (终章悬念检测)
├── genres.py                # 体裁定义 (10种)
├── spoiler.py               # 剧透筛选器 (按章节进度)
└── rag.py                   # 两阶段RAG (BM25粗排+语义精排)

frontend/                    # Tauri 桌面端 (Vue 3 + TypeScript)
├── src/
│   ├── main.ts              # Vue 应用挂载
│   ├── App.vue              # 主界面 (深色主题)
│   ├── api/index.ts         # API 封装 (47+方法)
│   ├── types/api.ts         # 完整类型定义
│   ├── router/index.ts      # 17路由 (4组)
│   ├── stores/              # 3个 Pinia store (book/config/ui)
│   ├── layouts/MainLayout.vue  # 主布局 (侧栏+顶栏)
│   ├── views/               # 17个视图页面
│   │   ├── CreateCenter.vue # 创作中心 (主编+编辑器+审计)
│   │   ├── BookManager.vue  # 作品管理
│   │   ├── EditorChat.vue   # 主编对话
│   │   ├── AuditView.vue    # 独立审计
│   │   ├── KGView.vue       # 知识图谱浏览器
│   │   └── ...              # +12个视图
│   └── components/          # 5个共享组件
├── package.json
└── vite.config.ts

data/                        # 运行时数据
├── published/               # 发布内容
├── learn/                   # 学习数据
├── snapshots/               # KG 快照
├── qdrant/                  # 向量存储
├── truth/                   # 真相文件
└── logs/                    # 运行日志

docs/                        # 📚 模块化文档体系 (25文件)
├── 索引.md                  # → 入口 · 从这里开始
├── 01-项目概览.md           # 定位/安装/架构
├── 02-Agent与管线.md        # 10 Agent + 17步管线(NovelPipeline) / 10步(Makefile)
├── 03-引擎与知识图谱.md     # Gacha/审计/风格/KG
├── 04-API与前端.md          # 68路由 + Vue + Tauri
├── 05-扩展模块与宪法.md     # 35+模块 + 项目宪法
├── 06-版本与问题.md         # 版本历史 + 已知Bug
├── 07-统计与检查清单.md     # 统计数字 + 更新清单
└── 08-修复报告.md           # 2026-06-07 全面检查 73问题追踪

skills/                      # 技能 Markdown 文件
├── 黄金三章模板.md
├── 过签审核清单.md
├── 口语化改写规则.md
└── 内容引擎创作体系.md
tests/                       # 32个测试文件, 415/415通过 (0失败)
scripts/                     # Windows 启动/安装脚本
.github/workflows/           # CI 配置
```

## API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | Docker 健康检查 |
| GET | `/api/v1/status` | 系统状态 + 组件健康 |
| POST | `/api/v1/chat` | AI 聊天 |
| POST | `/api/v1/editor/chat` | 主编对话 |
| POST | `/api/v1/daemon/start` | 启动守护进程 |
| POST | `/api/v1/daemon/stop` | 停止守护进程 |
| POST | `/api/v1/books/{book_id}/chapters/{chapter}/generate` | 章节生成 (17步完整管线) |
| POST | `/api/v1/books/{book_id}/chapters/batch-generate` | 批量生成 |
| POST | `/api/v1/audit/run` | 独立审计 |
| POST | `/api/v1/kg/query` | Cypher 知识图谱查询 |
| GET | `/api/v1/kg/entities/{entity_type}` | 按类型列出实体 |
| GET | `/api/v1/kg/foreshadowing/overdue` | 逾期伏笔查询 |
| GET | `/api/v1/search` | FTS5 全文搜索 |
| GET | `/api/v1/gacha/models` | 可用抽卡模型列表 |
| GET | `/api/v1/books/{book_id}/stats` | 书籍统计 |
| GET | `/api/v1/books/{book_id}/preferences` | 偏好向量查询 |
| POST | `/api/v1/books/{book_id}/preferences/feedback` | 偏好反馈录入 |
| GET | `/api/v1/books/{book_id}/snapshots/latest` | 最新 KG 快照 |
| GET | `/api/v1/books/{book_id}/snapshots/{snapshot_id}` | 指定 KG 快照 |
| GET | `/api/v1/export/chapter` | 单章导出 |
| GET | `/api/v1/export/book` | 全书导出 |
| WS | `/api/v1/ws/{book_id}/{chapter}` | WebSocket 实时进度推送 |
| GET | `/api/v1/stream/generate` | SSE 流式生成 |
| POST | `/api/orchestrate` | 编排 Agent |
| GET | `/api/agents` | Agent 列表 |
| GET | `/api/truth-status` | 真相文件快照 |
| POST | `/api/auto-fix` | 自动语法修复 |
| POST | `/api/v1/books/create` | 创建作品 |
| GET | `/api/v1/books/list` | 作品列表 |
| GET | `/api/v1/books/{book_id}` | 作品详情 |
| DELETE | `/api/v1/books/{book_id}` | 删除作品 |
| POST | `/api/v1/books/{book_id}/initialize` | 开书44维推演 |
| GET | `/api/v1/books/{book_id}/chapters/{chapter}/content` | 章节内容 |
| GET | `/api/v1/usage/{book_id}` | Token 用量统计 |

## 依赖服务

| 服务 | 用途 | 降级方案 |
|------|------|---------|
| Neo4j Community | 知识图谱主存储 | SQLite 图自动激活 |
| Redis | KG 快照缓存 | 缓存关闭 |
| NATS | Agent 消息总线 | 进程内 InProcessMessageBus |
| Qdrant | 向量检索 | 嵌入式本地模式 |
| SQLite FTS5 | 全文搜索 | Python 内置 (始终可用) |

所有依赖服务可选 — 缺失任意服务不影响核心功能，降级自动触发。

## 环境变量

```env
# --- LLM API Keys ---
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# --- Neo4j ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# --- Redis ---
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# --- NATS ---
NATS_URL=nats://localhost:4222

# --- 应用 ---
APP_HOST=127.0.0.1
APP_PORT=8000
APP_ENV=development
LOG_LEVEL=INFO
# --- 安全与成本控制（自用建议全部启用）---
API_AUTH_ENABLED=true
API_AUTH_KEY=<python -c "import secrets; print(secrets.token_urlsafe(32))">
RATE_LIMIT_PER_MINUTE=30
LLM_DAILY_TOKEN_BUDGET=500000
# --- 备用Key（逗号分隔，自动轮换）---
OPENAI_API_KEYS_BACKUP=
```

## 内存预估

| 组件 | 内存 |
|------|------|
| Neo4j Community | ~800MB |
| Redis | ~100MB |
| NATS | ~50MB |
| Qdrant (嵌入式) | ~200MB |
| FastAPI 应用 | ~300MB |
| **总计** | **~1.5GB** |

推荐 16GB 内存 (剩余供 LLM 上下文和系统使用)。

> ✅ **修复完成**: 2026-06-07 全面审计发现 38 个问题已全部修复（10致命+20严重+8中等），详见 [`docs/08-修复报告.md`](docs/08-修复报告.md)。

[memory_id: memory_01_CUiTnEV1YbpcI3PptbRl4903]
*（内容由AI生成，仅供参考）*

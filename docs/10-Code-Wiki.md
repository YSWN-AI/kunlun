# 昆仑创作引擎 (Kunlun Creation Engine) — Code Wiki

> **版本**: v0.3.0 | **Python**: >= 3.11 | **许可证**: MIT | **文档生成日期**: 2026-06-13

---

## 目录

1. [项目概览](#1-项目概览)
2. [项目目录结构](#2-项目目录结构)
3. [系统架构](#3-系统架构)
4. [核心模块详解](#4-核心模块详解)
   - [4.1 配置系统 (config/)](#41-配置系统-config)
   - [4.2 核心抽象层 (core/)](#42-核心抽象层-core)
   - [4.3 Agent 体系 (agents/)](#43-agent-体系-agents)
   - [4.4 管线系统 (pipeline/)](#44-管线系统-pipeline)
   - [4.5 抽卡引擎 (gacha/)](#45-抽卡引擎-gacha)
   - [4.6 审计系统 (audit/)](#46-审计系统-audit)
   - [4.7 知识图谱 (kg/)](#47-知识图谱-kg)
   - [4.8 文风工程 (style/)](#48-文风工程-style)
   - [4.9 Vibe Writing (vibe_writer/)](#49-vibe-writing-vibe_writer)
   - [4.10 矛盾引擎 (conflict/)](#410-矛盾引擎-conflict)
   - [4.11 API 层 (api/)](#411-api-层-api)
   - [4.12 扩展模块总览](#412-扩展模块总览)
   - [4.13 顶层功能模块](#413-顶层功能模块)
5. [前端系统 (frontend/)](#5-前端系统-frontend)
6. [关键类与接口](#6-关键类与接口)
7. [数据流与管线执行流程](#7-数据流与管线执行流程)
8. [依赖关系](#8-依赖关系)
9. [项目运行方式](#9-项目运行方式)
10. [配置与环境变量](#10-配置与环境变量)
11. [部署架构](#11-部署架构)

---

## 1. 项目概览

**昆仑创作引擎**是一个 AI 驱动的中文网络文学创作平台。核心理念是 **Vibe Writing**（氛围写作）—— 用户用自然语言表达意图，AI 负责从世界观构建、章节写作、质量审计到多格式导出的全流程。

### 关键特性

| 特性 | 说明 |
|------|------|
| **六大驱动力** | 爽点驱动、情节驱动、角色驱动、矛盾驱动、情绪驱动、氛围驱动 |
| **多 Agent 协作** | 10+ 个专业 Agent（主编调度、写手、审计员、社会学家等） |
| **多模型抽卡** | 4 种抽卡模式，9 维文本质量评分（零 LLM 成本） |
| **53 维审计体系** | 8 门禁 + 33 维审计 + 连载 ICU + AI 特征检测 |
| **四层知识图谱** | Neo4j (图) + Qdrant (向量) + SQLite FTS5 (全文) + SQLite 图 (降级) |
| **自动降级** | 所有外部服务（Neo4j/Redis/NATS/Qdrant）缺失时自动降级 |
| **17 步完整管线** | 4 种执行模式（full/standard/quick/editor）|
| **桌面端** | Tauri 2.0 + Vue 3 + Naive UI，支持 NSIS 安装包 |
| **纯规则审计** | 所有审计门禁零 LLM 调用，快速且确定性输出 |

---

## 2. 项目目录结构

```
昆仑最新版/
├── .env.example                 # 环境变量模板
├── .github/workflows/ci.yml     # GitHub Actions CI 配置
├── README.md                    # 项目说明
├── CLAUDE.md                    # AI 助手上下文文件
├── pyproject.toml               # Python 项目配置（ruff/mypy/pytest）
├── requirements.txt             # Python 依赖
├── requirements-export.txt      # 导出扩展依赖
├── Dockerfile                   # Docker 镜像构建
├── docker-compose.yml           # Docker 服务编排
├── kunlun.json                  # 项目配置文件
├── kunlun_cli.py                # CLI 命令行入口
├── launch.py                    # 启动脚本
├── run.bat / start.bat          # Windows 启动脚本
├── build_app.py                 # 构建打包脚本
├── build-kunlun.bat             # 构建批处理
├── deploy.bat                   # 部署批处理
├── desktop.py                   # 桌面端入口
│
├── kunlun/                      # ★ 核心 Python 包 (155+ .py, 39子包, ~44,000行)
│   ├── __init__.py              # 包初始化 + 版本号
│   ├── config/                  # 配置系统（pydantic-settings）
│   ├── core/                    # 核心抽象层（Agent协议/管线步骤/错误分类）
│   ├── agents/                  # Agent 体系（12个Agent）
│   ├── pipeline/                # 管线系统（NovelPipeline + 17步骤）
│   ├── gacha/                   # 多模型抽卡引擎
│   ├── audit/                   # 53维审计体系
│   ├── kg/                      # 四层知识图谱
│   ├── style/                   # 文风工程
│   ├── vibe_writer/             # Vibe Writing 总调度
│   ├── conflict/                # 冲突引擎
│   ├── api/                     # FastAPI 入口 + 路由
│   ├── prompts/                 # Prompt 模板（管线+社会推演）
│   ├── learn/                   # 自学习（偏好/反思/进化）
│   ├── quality/                 # 质量看板
│   ├── context/                 # 上下文 Token 预算
│   ├── truth/                   # 真相文件系统
│   ├── common/                  # 通用基础设施
│   ├── skills/                  # 技能加载器
│   ├── recovery/                # 断更恢复 + 版本回滚
│   ├── exporter/                # 多格式导出
│   ├── pleasure/                # 爽点检测
│   ├── dialogue/                # 对话质量评估
│   ├── arc/                     # 角色弧线追踪
│   ├── worlds/                  # 世界观一致性
│   ├── spacetime/               # 时空一致性
│   ├── state/                   # 角色状态机
│   ├── intel/                   # 情报追踪
│   ├── ripple/                  # 涟漪效应
│   ├── rules/                   # 规则引擎
│   ├── retention/               # 读者留存预测
│   ├── dashboard/               # 写作仪表盘
│   ├── ab_test/                 # A/B 测试
│   ├── emosupport/              # 情感支持
│   ├── comments/                # 读者评论
│   ├── publish/                 # 发布代理
│   ├── safety/                  # 内容安全
│   ├── watermark/               # 智能水印
│   ├── market/                  # 市场情报
│   ├── shortform/               # 短篇生成
│   ├── outline/                 # 大纲引擎
│   ├── draft/                   # 草稿版本
│   ├── versions/                # Git 版本管理
│   ├── humanize/                # 去 AI 化引擎
│   ├── plot/                    # 情节引擎
│   ├── character/               # 角色引擎
│   ├── structure/               # 结构分析
│   ├── coherence/               # 连贯性检查
│   ├── continuity/              # 连续性检查
│   ├── fanfic/                  # 同人创作
│   ├── genre/                   # 体裁定义
│   ├── interactive/             # 交互式引擎
│   ├── notify/                  # 通知推送
│   ├── platform_compliance/     # 平台合规
│   ├── proofread/               # 校对引擎
│   ├── cover/                   # 封面生成
│   ├── story_bible/             # 故事圣经
│   ├── golden_triple/           # 黄金三章
│   ├── search/                  # 搜索功能
│   ├── branch_plot/             # 分支情节
│   ├── writer_context/          # 写手上下文
│   ├── aigc_detect/             # AIGC 检测
│   │
│   ├── exceptions.py            # 统一异常体系（20+类）
│   ├── observability.py         # 可观测性（OTel）
│   ├── model_router.py          # 多模型路由
│   ├── token_tracker.py         # Token 用量追踪
│   ├── cost_tracker.py          # 成本追踪
│   ├── daemon.py                # 守护进程（后台自动写作）
│   ├── auto_fix.py              # 自动修复
│   ├── autosync.py              # 自动文件同步
│   ├── filesync.py              # 文件联动同步
│   ├── import_engine.py         # 章节导入
│   ├── book_config.py           # 作品配置
│   ├── prompt_manager.py        # Prompt 管理
│   ├── prompt_compressor.py     # Prompt 压缩
│   ├── outline_anchor.py        # 大纲锚点
│   ├── length_gov.py            # 字数治理
│   ├── model_params.py          # 模型参数预设
│   ├── modifier.py              # 定向修改
│   ├── cooldown.py              # 事件冷却
│   ├── brake.py                 # 反向刹车
│   ├── genres.py                # 体裁定义
│   ├── spoiler.py               # 剧透筛选
│   ├── rag.py                   # RAG 检索
│   ├── llm_cache.py             # LLM 缓存
│   ├── precheck.py              # 预检查
│   ├── doctor.py                # 环境诊断
│   ├── status_cmd.py            # 状态命令
│   ├── project_config.py        # 项目配置管理
│   ├── marginal_efficiency.py   # 边际效率
│   └── api_providers.py         # API 供应商管理
│
├── frontend/                    # ★ Tauri 桌面端 (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── main.ts              # Vue 应用入口
│   │   ├── App.vue              # 根组件
│   │   ├── api/index.ts         # API 封装层
│   │   ├── types/api.ts         # API 类型定义
│   │   ├── types/write.ts       # 创作类型定义
│   │   ├── router/index.ts      # 路由配置（15个路由）
│   │   ├── stores/              # Pinia 状态管理
│   │   │   ├── book.ts          # 书籍状态
│   │   │   ├── config.ts        # 配置状态
│   │   │   └── ui.ts            # UI 状态
│   │   ├── layouts/             # 布局组件
│   │   │   ├── AppShell.vue     # 应用外壳
│   │   │   ├── ActivityBar.vue  # 活动栏
│   │   │   ├── SidePanel.vue    # 侧边面板
│   │   │   └── StatusBar.vue    # 状态栏
│   │   ├── views/               # 15 个视图页面
│   │   ├── components/          # 共享组件
│   │   ├── composables/         # 组合式函数
│   │   ├── styles/tokens.css    # 样式令牌
│   │   └── constants/index.ts   # 常量定义
│   ├── src-tauri/               # Tauri 原生端
│   │   ├── src/main.rs          # Rust 主入口
│   │   ├── Cargo.toml           # Rust 依赖
│   │   └── tauri.conf.json      # Tauri 配置
│   ├── package.json             # 前端依赖
│   ├── vite.config.ts           # Vite 构建配置
│   └── index.html               # HTML 入口
│
├── tests/                       # 测试目录（50+ 测试文件）
├── docs/                        # 文档体系（25+ 文件）
├── skills/                      # 运行时技能 Markdown 文件
│   └── kunlun-engine/           # 昆仑引擎技能
│       ├── SKILL.md
│       └── references/          # 参考文档
├── scripts/                     # 工具脚本 (Windows)
│   ├── setup.bat                # 环境安装
│   ├── start-services-full.bat # 全服务启动
│   └── ...
├── migrations/                  # Alembic 数据库迁移
├── k8s/                         # Kubernetes 部署配置
├── web/                         # 降级静态 Web UI
│   ├── index.html               # Vibe Writing 主界面
│   └── config.html              # 配置页面
└── data/                        # 运行时数据目录
    ├── books/                   # 书籍数据
    ├── truth/                   # 真相文件
    ├── snapshots/               # KG 快照
    ├── qdrant/                  # 向量存储
    ├── logs/                    # 运行日志
    └── ...
```

---

## 3. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Tauri 桌面端  │  │  Web UI     │  │  CLI (命令行)  │      │
│  │ (Vue 3 + TS) │  │ (降级静态页) │  │ (kunlun_cli) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
├─────────┼─────────────────┼─────────────────┼───────────────┤
│         ▼                 ▼                 ▼               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                API 网关层 (FastAPI)                    │   │
│  │  • 认证/鉴权中间件  • 速率限制 (slowapi)              │   │
│  │  • CORS 跨域支持   • Prometheus 指标                   │   │
│  │  • WebSocket (实时推送)  • SSE (流式输出)             │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
├─────────────────────────┼───────────────────────────────────┤
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Vibe Orchesrator (总调度)                 │   │
│  │       "一句话 → 开书 → 写作 → 审计 → 导出"            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │              NovelPipeline (17步管线)                  │   │
│  │  Snapshot → Planner → Architect → Society → Writer    │   │
│  │  → Conflict → Vibe → PostWrite → Audit → Revise       │   │
│  │  → ICU → Quality → Polish → KG Update → Truth Sync    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────┬───────────┼───────────┬──────────┐           │
│  ▼          ▼           ▼           ▼          ▼           │
│ ┌────┐  ┌──────┐  ┌────────┐  ┌──────┐  ┌────────┐       │
│ │Gacha│  │Audit │  │ Style  │  │ Agent│  │ 扩展   │       │
│ │引擎 │  │系统  │  │ 工程   │  │ 集群 │  │ 模块   │       │
│ └──┬─┘  └──┬───┘  └───┬────┘  └──┬───┘  └───┬────┘       │
│    │       │          │          │          │             │
│    ▼       ▼          ▼          ▼          ▼             │
│ ┌──────────────────────────────────────────────────────┐   │
│  │           数据层 (四层知识图谱 + 真相文件)             │   │
│  │  Neo4j ─→ SQLite Graph   Qdrant   SQLite FTS5       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            基础设施层                                 │   │
│  │  Redis (缓存)  NATS (消息总线)  文件系统 (持久化)    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 架构设计原则

| 原则 | 说明 |
|------|------|
| **优雅降级** | 所有外部服务（Neo4j/Redis/NATS/Qdrant）缺失时自动降级到内置方案 |
| **单例模式** | 所有核心系统（Settings/KGClient/GachaEngine/Alerter等）为模块级单例 |
| **纯规则审计** | 所有审计门禁零 LLM 调用，使用正则、Counter、jieba 分词 |
| **异步管线** | asyncio 驱动，步骤间插入 `asyncio.sleep` 避免事件循环阻塞 |
| **Dataclass 结果** | 审计/管线/KG 实体统一使用 `@dataclass` + `field(default_factory=...)` |
| **中文优先** | 所有注释、提示词、错误消息、UI 均使用中文 |
| **声明式管线** | PipelineStepDef 声明式定义步骤，支持重试/超时/降级/条件跳过 |

---

## 4. 核心模块详解

### 4.1 配置系统 (config/)

**职责**: 全局配置管理，基于 pydantic-settings 从 `.env` 文件和环境变量加载。

**文件**: [kunlun/config/__init__.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/config/__init__.py)

**关键类**: `Settings` — 通过多继承组合 5 个配置域：

| 配置域 | 文件 | 职责 |
|--------|------|------|
| `BaseConfig` | [base.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/config/base.py) | 基础路径、应用环境、日志级别 |
| `DatabaseConfig` | [database.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/config/database.py) | Neo4j/Redis/NATS/Qdrant 连接配置 |
| `LLMConfig` | [llm.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/config/llm.py) | OpenAI/DeepSeek/Anthropic API Key、Token 预算 |
| `PipelineConfig` | [pipeline.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/config/pipeline.py) | 管线模式、上下文预算、体裁默认值 |
| `ThresholdsConfig` | [thresholds.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/config/thresholds.py) | 审计门禁阈值、AI 检测阈值 |

**使用方式**:
```python
from kunlun.config import settings
# settings 是模块级单例，自动从 .env 加载
```

---

### 4.2 核心抽象层 (core/)

**职责**: 定义 Agent 协议、管线步骤声明、错误分类器等核心接口。

**文件**: [kunlun/core/agent_interface.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/core/agent_interface.py)

**关键类/接口**:

| 名称 | 类型 | 说明 |
|------|------|------|
| `AgentProtocol` | ABC | Agent 抽象基类，定义 `execute/validate_input/pre_execute/post_execute` 生命周期 |
| `AgentCapability` | StrEnum | Agent 能力枚举（16 种能力类型）|
| `PipelineStepDef` | dataclass | 声明式管线步骤定义（name/handler/required/retry/timeout/degrade）|
| `StepResult` | dataclass | 统一的步骤执行结果（status/data/errors/warnings/duration）|
| `StepStatus` | StrEnum | 步骤状态（PENDING/RUNNING/SUCCESS/FAILED/SKIPPED/DEGRADED）|
| `PipelineResult` | dataclass | 管线执行结果汇总（steps/degraded_steps/failed_steps）|
| `ErrorClassifier` | class | 错误分类器 — 将异常映射为 RETRYABLE/DEGRADABLE/FATAL |
| `ErrorDecision` | dataclass | 错误处理决策（severity/action/message/retry_after_ms）|
| `ErrorSeverity` | StrEnum | 错误严重程度（RETRYABLE/DEGRADABLE/FATAL）|

**扩展基类**: [kunlun/core/extension_base.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/core/extension_base.py) — `BaseExtensionModule`，21+ 扩展模块统一基类。

---

### 4.3 Agent 体系 (agents/)

**职责**: 10+ 专业 Agent 通过消息总线协作完成创作全流程。

**Agent 列表**:

| Agent | 文件 | 角色 | 输入 | 输出 |
|-------|------|------|------|------|
| `EditorInChief` | [editor.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/editor.py) | 主编/总调度 | 自然语言指令 | 创作任务分发 |
| `MakefileAgent` | [makefile.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/makefile.py) | 管线调度员 (10步旧管线) | book_id + chapter | 完整管线执行结果 |
| `Architect` | [architect.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/architect.py) | 蓝图规划师 | 章节意图 | 含冲突/氛围/爽点的蓝图 |
| `Writer` | [writer.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/writer.py) | 写手 | 蓝图 + TokenBudget | 正文草稿 |
| `Auditor` | [auditor.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/auditor.py) | 审计员 | 草稿 | 审计报告 |
| `Scheduler` | [scheduler.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/scheduler.py) | 集群调度器 | 任务列表 | 并行任务分配 |
| `Publisher` | [publisher.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/publisher.py) | 发布 Agent | 完成章节 | 多平台发布 |
| `Sociologist` | [sociologist.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/sociologist.py) | 社会学家 | 当前世界状态 | 44维社会推演结果 |
| `Observer` | [observer.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/observer.py) | 观察者 Agent | 管线事件 | 事件日志 |
| `ReflectorAgent` | [reflector_agent.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/reflector_agent.py) | 反思 Agent | 写后数据 | 反思报告 |

**基类**: `BaseAgent` ([base.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/agents/base.py))
- 属性: `agent_name`, `capabilities`, `status`
- 核心方法: `execute(task)` → dict, `post_message(to, type, payload)`, `on_message(msg)`
- 消息传递: 优先 NATS（真实消息队列）→ 回退进程内 `InProcessMessageBus`

**消息总线**: `message_bus.py` — Agent 间通信枢纽，支持 NATS（分布式）和进程内（单机降级）两种模式。

---

### 4.4 管线系统 (pipeline/)

**职责**: 核心创作管线，定义章节生成的完整步骤序列。

**主文件**: [kunlun/pipeline/novel_pipeline.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/pipeline/novel_pipeline.py)

**管线步骤 (17步)**:

```
SNAPSHOT → PLANNER → ARCHITECT → SOCIETY → WRITER → CONFLICT
  → VIBE → POST_WRITE → AUDIT → REVISE → ICU → QUALITY
  → POLISH → KG_UPDATE → PLEASURE → TRUTH_SYNC → REFLECT
```

**4 种执行模式**:

| 模式 | 步骤数 | 说明 |
|------|--------|------|
| `full` | 17 步 | 六大驱动力全覆盖，用于新书或关键章节 |
| `standard` | 14 步 | 含冲突+Vibe 追踪，用于常规更新 |
| `quick` | 10 步 | 快速生成，跳过规划反思 |
| `editor` | 12 步 | 主编对话式，支持人工干预 |

**管线干预**: [kunlun/pipeline/__init__.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/pipeline/__init__.py) — `PipelineInterventionManager`，人在环中（Human-in-the-loop）系统，每个步骤可暂停等待审批。

**步骤实现目录**: [kunlun/pipeline/steps/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/pipeline/steps/)

| 步骤文件 | 对应步骤 |
|----------|----------|
| `snapshot.py` | KG 快照 |
| `blueprint.py` | 蓝图生成 |
| `society_rag.py` | 社会推演 |
| `draft.py` | 正文生成 |
| `audit.py` | 审计 |
| `icu.py` | 连载 ICU |
| `polish.py` | 去 AI 味润色 |
| `quality_check.py` | 质量看板 |
| `kg_update.py` | KG 更新 |
| `revise_loop.py` | 修订循环 |
| `post_write_validate.py` | 后写验证 |
| `reflector.py` | 写后反思 |
| `truth_and_fingerprint.py` | 真相文件同步 |
| `style_drift.py` | 文风漂移检测 |
| `state_update.py` | 状态更新 |
| `learner_record.py` | 学习记录 |
| `publish.py` | 发布 |
| `observer.py` | 观察者 |

---

### 4.5 抽卡引擎 (gacha/)

**职责**: 多模型并行调用 + 质量评分 + 最优文本选择。

**主文件**: [kunlun/gacha/engine.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/gacha/engine.py)

**4 种模式**:

| 模式 | 说明 |
|------|------|
| `single_fix` | 单模型修复/生成（审计修复、配置推断等）|
| `gacha_parallel_3` | 3 个模型并行抽卡 → 9 维评分 → 选最优 |
| `gacha_cheap_2` | 2 个随机模型抽卡（成本优先）|
| `gacha_ultimate_5` | 5 个模型段落级混合（质量优先）|

**9 维评分体系** (纯文本统计，零 LLM 成本):
1. 多样性 (Diversity)
2. 连贯性 (Coherence)
3. 信息密度 (Information Density)
4. 情感波动 (Emotional Fluctuation)
5. 节奏感 (Rhythm)
6. 创新度 (Innovation)
7. 流畅度 (Fluency)
8. 完整性 (Completeness)
9. 人味度 (Human-likeness)

**关键类**:

| 类 | 说明 |
|------|------|
| `GachaEngine` | 抽卡引擎主类（单例）|
| `ModelCandidate` | 模型候选配置（provider/model/api_key/priority）|
| `CircuitBreaker` | API Key 熔断器（[circuit_breaker.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/gacha/circuit_breaker.py)）|
| `KeyRotator` | API Key 轮换器 |
| `ParamVariator` | 7 维参数随机化 + 章节类型感知（[param_variator.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/gacha/param_variator.py)）|

---

### 4.6 审计系统 (audit/)

**职责**: 53 维审计体系，纯规则（零 LLM 成本）+ LLM 修复兜底。

**目录**: [kunlun/audit/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/)

**审计层次**:

| 系统 | 文件 | 维度 | LLM 使用 |
|------|------|------|----------|
| **8 门禁 (G1-G8)** | [gates/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/) | G1 弧线/G2 信息/G3 AI味/G4 爽点间隔/G5 爽点多样性/G6 情绪/G7 对话/G8 战斗 | 纯规则 |
| **33 维审计** | [audit33.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/audit33.py) | 6 组 × 33 维 (A角色/B情节/C结构/D风格/E读者/F AI) | 纯规则 |
| **连载 ICU** | [icu.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/icu.py) | 7 维 (爽点/情绪/信息/节奏/钩子/OOC/对话) | 规则 + LLM 修复 |
| **AI 特征库** | [ai_features.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/ai_features.py) | 36+ AI 写作特征 (F/G 组) | 纯规则 |
| **后写验证** | [post_write_validator.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/post_write_validator.py) | 11 条零 LLM 检查 | 纯规则 |
| **输出契约** | [output_contract.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/output_contract.py) | Schema 校验 (SpecForge 风格) | 纯规则 |
| **番茄门禁** | [fanqie_gates.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/fanqie_gates.py) | 番茄平台流量适配 + 全生命周期 + 反作弊 | 纯规则 |
| **Jieba 分析器** | [jieba_analyzer.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/jieba_analyzer.py) | 关键词精确匹配 | jieba 分词 |
| **文风漂移** | [style_drift.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/style_drift.py) | 文风一致性检测 | 统计 |

**8 门禁说明**:

| 门禁 | 文件 | 检查内容 |
|------|------|----------|
| G1 角色弧线 | [gate_g1_arc.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g1_arc.py) | 角色成长轨迹偏差 |
| G2 信息密度 | [gate_g2_info.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g2_info.py) | 新概念引入频率 |
| G3 AI 痕迹 | [gate_g3_ai.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g3_ai.py) | 句式 CV/连词密度/开头多样性 |
| G4 爽点间隔 | [gate_g4_pleasure_interval.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g4_pleasure_interval.py) | 爽点间最大段落数 |
| G5 爽点多样性 | [gate_g5_pleasure_diversity.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g5_pleasure_diversity.py) | 同类爽点连续出现 |
| G6 情绪 | [gate_g6_emotion.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g6_emotion.py) | 情绪波动幅度 |
| G7 对话 | [gate_g7_dialogue.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g7_dialogue.py) | 无用对话占比 |
| G8 战斗 | [gate_g8_battle.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/audit/gates/gate_g8_battle.py) | 战斗力/境界一致性 |

---

### 4.7 知识图谱 (kg/)

**职责**: 四层知识图谱存储与检索，支持优雅降级。

**主文件**: [kunlun/kg/client.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/kg/client.py)

**四层架构**:

| 层级 | 技术 | 用途 | 降级方案 |
|------|------|------|----------|
| 图数据库 | Neo4j (Bolt) | 主图存储，关系查询 | SQLite 图模式 |
| 向量检索 | Qdrant (BGE 嵌入) | 语义搜索 | 嵌入式本地模式 |
| 全文搜索 | SQLite FTS5 | 关键词搜索 | 内置（始终可用）|
| 图降级 | SQLite 图 | Neo4j 不可用时的替代 | — |

**关键类**:

| 类 | 文件 | 说明 |
|------|------|------|
| `KGClient` | [client.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/kg/client.py) | 统一 KG 客户端（单例），聚合四路检索 |
| `Embedder` | [embedder.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/kg/embedder.py) | BGE 向量嵌入（sentence-transformers，单例）|
| `SnapshotManager` | [snapshot.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/kg/snapshot.py) | KG 快照管理（自动管理，追踪 continuity）|

**本体定义** ([ontology.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/kg/ontology.py)):
- **9 实体类型**: Character, Location, Item, Organization, Skill, Event, Foreshadowing, Knowledge, ChapterSnapshot
- **22 关系类型**: APPEARS_IN, KNOWS, OWNS, LOCATED_AT, etc.
- **属性**: 使用 Pydantic v2 模型，`extra_data` 别名避免 `metadata` 冲突

**仓库模式** ([repositories/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/kg/repositories/)):
- `base.py` — 仓库基类
- `neo4j_repo.py` — Neo4j 实现
- `qdrant_repo.py` — Qdrant 实现
- `sqlite_fts.py` — SQLite FTS5 实现
- `sqlite_graph.py` — SQLite 图实现
- `factory.py` — 仓库工厂

---

### 4.8 文风工程 (style/)

**职责**: 文风指纹、去 AI 味、Vibe 氛围、文本精炼。

**目录**: [kunlun/style/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/style/)

| 模块 | 文件 | 说明 |
|------|------|------|
| **文风指纹** | [fingerprint.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/style/fingerprint.py) | 统计 + LLM 文风分析，生成风格指南 |
| **去 AI 味** | [engineer.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/style/engineer.py) | 句式 CV/连词密度/段落 CV/开头多样性检测 |
| **Vibe 引擎** | [vibe.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/style/vibe.py) | 14 种氛围类型（压抑/轻松/紧张/浪漫/史诗/神秘...）|
| **文本精炼** | [refiner.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/style/refiner.py) | 304 条高频套路词替换规则 |

---

### 4.9 Vibe Writing (vibe_writer/)

**职责**: Vibe Writing 最高抽象层 — "一句话完成从开书到完结导出"。

**目录**: [kunlun/vibe_writer/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/vibe_writer/)

| 类 | 文件 | 说明 |
|------|------|------|
| `VibeOrchestrator` | [orchestrator.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/vibe_writer/orchestrator.py) | 总调度（Supreme Agent），解析自然语言意图 → 调用完整管线 |
| `VibeWriter` | [engine.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/vibe_writer/engine.py) | 单章 Vibe 写作伙伴，VibePrompt 注入 |

---

### 4.10 矛盾引擎 (conflict/)

**职责**: 冲突追踪、张力管理、冲突热力图。

**目录**: [kunlun/conflict/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/conflict/)

| 类 | 说明 |
|------|------|
| `ConflictManager` | 6 种冲突类型管理 + 张力追踪 |
| `TensionManager` | 叙事张力曲线管理 |
| 热力图 | 跨章节冲突分布可视化 |

---

### 4.11 API 层 (api/)

**职责**: FastAPI 应用入口，路由管理，中间件。

**主文件**: [kunlun/api/main.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/main.py)

**关键组件**:

| 组件 | 文件 | 说明 |
|------|------|------|
| `FastAPI app` | [main.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/main.py) | 应用创建 + 生命周期管理 |
| `lifespan` | [main.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/main.py) | 启动时并行初始化（Neo4j/种子/技能/AutoSync/Alembic/OTel）|
| 认证中间件 | [main.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/main.py) + [auth.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/auth.py) | X-API-Key 认证（HMAC 恒定时间比较）|
| 速率限制 | [rate_limit.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/rate_limit.py) | slowapi 限流（内存/Redis）|
| CORS | [main.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/main.py) | 跨域支持（开发模式: localhost:5173/8000/tauri://）|
| WebSocket | [ws_manager.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/ws_manager.py) | WebSocket 连接池管理 |
| SSE 流 | [streaming.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/streaming.py) | SSE 流式输出 |
| 全局异常 | [error_handlers.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/error_handlers.py) | KunlunError → 友好响应，未知异常 → traceback |
| 安全中间件 | [security_middleware.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/security_middleware.py) | book_id 路径遍历保护 |

**路由体系** ([routers/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/api/routers/)):

| 路由文件 | 前缀 | 功能 |
|----------|------|------|
| `books.py` | `/api/v1/books` | 作品 CRUD + 初始化 |
| `chapters.py` | `/api/v1/books/{book_id}/chapters` | 章节生成 + 批量生成 |
| `orchestrator.py` | `/api/v1/orchestrator` | 编排 Agent |
| `chat.py` | `/api/v1/chat` | AI 聊天 |
| `audit.py` | `/api/v1/audit` | 独立审计 |
| `kg.py` | `/api/v1/kg` | 知识图谱查询 |
| `write_routes.py` | `/api/v1/write` | 写作接口 |
| `stream.py` | `/api/v1/stream` | SSE 流式生成 |
| `ws.py` | `/api/v1/ws` | WebSocket 进度推送 |
| `dashboard.py` | `/api/v1/dashboard` | 仪表盘数据 |
| `export_routes.py` | `/api/v1/export` | 多格式导出 |
| `prompts.py` | `/api/v1/prompts` | 提示词管理 |
| `publish_routes.py` | `/api/v1/publish` | 发布管理 |
| `gacha.py` | `/api/v1/gacha` | 模型列表 |
| `config_routes.py` | `/api/v1/config` | 配置管理 |
| `rules.py` | `/api/v1/rules` | 规则引擎 |
| `stats.py` | `/api/v1/stats` | 统计数据 |
| `usage_routes.py` | `/api/v1/usage` | Token 用量 |
| `pipeline.py` | `/api/v1/pipeline` | 管线状态 |
| `admin.py` | `/admin` | 管理接口 |
| `health` | `/api/v1/health` | 健康检查 |
| ... | ... | 40+ 路由文件 |

---

### 4.12 扩展模块总览

以下 30+ 个扩展模块基于 `BaseExtensionModule` 统一基类，各自独立完成特定功能：

#### 写作辅助

| 模块 | 目录 | 功能 |
|------|------|------|
| **爽点检测** | [pleasure/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/pleasure/) | 12 种爽点类型检测 + 疲劳度追踪 |
| **对话评估** | [dialogue/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/dialogue/) | 5 维对话质量 + 说话人画像 |
| **角色弧线** | [arc/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/arc/) | 7 维 × 6 种角色弧线追踪 |
| **大纲管理** | [outline/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/outline/) | 大纲创建/编辑/版本管理 |
| **草稿管理** | [draft/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/draft/) | 草稿版本存储 |
| **短篇生成** | [shortform/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/shortform/) | 短篇/中篇独立生成 |

#### 世界与一致性

| 模块 | 目录 | 功能 |
|------|------|------|
| **世界观** | [worlds/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/worlds/) | 16 维世界观一致性检查 + 体裁感知建议 |
| **时空一致性** | [spacetime/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/spacetime/) | 时间线/地理位置一致性 |
| **角色状态机** | [state/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/state/) | 情感/体能/社会三维状态机 + 持久化 |
| **情报追踪** | [intel/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/intel/) | 上帝视角检测 + 情报边界 |
| **涟漪效应** | [ripple/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/ripple/) | 事件因果链追踪 |
| **真相文件** | [truth/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/truth/) | 7 个 JSON 真相文件自动同步 |

#### 质量与分析

| 模块 | 目录 | 功能 |
|------|------|------|
| **质量看板** | [quality/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/quality/) | 聚合质量评分 + 可执行结果 |
| **质量趋势** | [quality/tracker.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/quality/tracker.py) | 跨章质量趋势 + 持久化 |
| **A/B 测试** | [ab_test/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/ab_test/) | 10 指标 + 统计检验 |
| **写作仪表盘** | [dashboard/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/dashboard/) | 字数/质量雷达/热力图 |
| **读者留存** | [retention/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/retention/) | 10 维读者留存预测 + 弃书风险 |
| **读者评论** | [comments/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/comments/) | 读者评论分析 |

#### 发布与安全

| 模块 | 目录 | 功能 |
|------|------|------|
| **发布代理** | [publish/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/publish/) | 7 平台发布 + 定时发布 |
| **内容安全** | [safety/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/safety/) | 5 类词库审查 |
| **智能水印** | [watermark/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/watermark/) | 零宽编码 + 数字签名 |
| **AIGC 检测** | [aigc_detect/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/aigc_detect/) | AI 生成内容检测 |
| **平台合规** | [platform_compliance/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/platform_compliance/) | 各平台内容规则适配 |

#### 学习与进化

| 模块 | 目录 | 功能 |
|------|------|------|
| **偏好学习** | [learn/learner.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/learn/learner.py) | 50 维偏好学习（EMA + 衰减）|
| **写后反思** | [learn/reflector.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/learn/reflector.py) | 章节后自动反思 |
| **自主进化** | [learn/evolve.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/learn/evolve.py) | 作者画像 + 自动技能生成 |
| **市场情报** | [market/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/market/) | 热点追踪 + 拆书分析 |

---

### 4.13 顶层功能模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **守护进程** | [daemon.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/daemon.py) | 后台自动写作（可配置章数）|
| **多格式导出** | [exporter/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/exporter/) | 7 种格式: TXT/HTML/MD/EPUB/MOBI/PDF/DOCX |
| **断更恢复** | [recovery/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/recovery/) | 断更恢复引擎 + 章回滚 |
| **版本管理** | [versions/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/versions/) | Git 版本管理 |
| **章节导入** | [import_engine.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/import_engine.py) | TXT/MD/EPUB 导入 + 同人初始化 |
| **文件同步** | [filesync.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/filesync.py) + [autosync.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/autosync.py) | 控制文档自动同步（13 个处理器）|
| **模型路由** | [model_router.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/model_router.py) | 9 种 Agent 模型配置 + 3 层任务分层 |
| **Token 追踪** | [token_tracker.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/token_tracker.py) + [cost_tracker.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/cost_tracker.py) | 用量 + 预算 + 成本 |
| **LLM 缓存** | [llm_cache.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/llm_cache.py) | LLM 响应缓存 |
| **Prompt 管理** | [prompt_manager.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/prompt_manager.py) | 3 级覆盖 Prompt 管理 |
| **Prompt 压缩** | [prompt_compressor.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/prompt_compressor.py) | Prompt 长度优化 |
| **技能加载** | [skills/loader.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/skills/loader.py) | .md 文件 → system prompt |
| **上下文预算** | [context/budget.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/context/budget.py) | 6 段 Token 预算 + 距离衰减 (WenShape/SAGA) |
| **字数治理** | [length_gov.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/length_gov.py) | AI 生成字数控制 |
| **冷却管理** | [cooldown.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/cooldown.py) | 8 种剧情事件冷却矩阵 |
| **反向刹车** | [brake.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/brake.py) | 终章悬念检测 |
| **大纲锚点** | [outline_anchor.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/outline_anchor.py) | 三段式弧段配额 |
| **定向修改** | [modifier.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/modifier.py) | 只改指定段落的定向修改引擎 |
| **RAG 检索** | [rag.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/rag.py) | 两阶段 RAG: BM25 粗排 + 语义精排 |
| **去 AI 化** | [humanize/](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/humanize/) | 去 AI 化引擎（检测器 + 重写器 + 指纹）|
| **环境诊断** | [doctor.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/doctor.py) | 系统健康检查 |
| **异常体系** | [exceptions.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/exceptions.py) | 20+ 自定义异常类 |
| **可观测性** | [observability.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/observability.py) | OpenTelemetry 追踪 + 生成步骤计时 |
| **体裁定义** | [genres.py](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/kunlun/genres.py) | 10 种体裁定义 |

---

## 5. 前端系统 (frontend/)

### 5.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.4.0 | UI 框架 |
| TypeScript | ^5.3.0 | 类型系统 |
| Tauri | ^2.0.0 | 桌面端框架 |
| Vite | ^5.4.0 | 构建工具 |
| Naive UI | ^2.38.0 | 组件库 |
| Pinia | ^2.1.0 | 状态管理 |
| Vue Router | ^4.3.0 | 路由管理 |
| ECharts | ^6.1.0 | 数据可视化 |
| Tiptap | ^3.26.0 | 富文本编辑器 |

### 5.2 路由与视图

| 路由 | 视图 | 说明 |
|------|------|------|
| `/write` | `WriteView.vue` | 创作中心（主编对话 + 编辑器 + 审计）|
| `/books` | `BooksView.vue` | 作品管理 |
| `/books/:id` | `BookDetailView.vue` | 作品详情 |
| `/dashboard` | `DashboardView.vue` | 仪表盘（统计数据 + 图表）|
| `/world` | `WorldView.vue` | 世界设定管理 |
| `/audit` | `AuditView.vue` | 审计中心 |
| `/analysis` | `AnalysisView.vue` | 分析中心 |
| `/abtest` | `ABTestView.vue` | A/B 测试 |
| `/drafts` | `DraftView.vue` | 草稿管理 |
| `/pipeline` | `PipelineView.vue` | 管线监控 |
| `/settings` | `SettingsView.vue` | 设置 |
| `/export` | `ExportView.vue` | 导出中心 |
| `/prompts` | `PromptsView.vue` | 提示词管理 |
| `/import` | `ImportView.vue` | 导入中心 |
| `/orchestrator` | `OrchestratorView.vue` | 智能创作（Vibe Writing 入口）|

### 5.3 状态管理 (Pinia)

| Store | 文件 | 职责 |
|-------|------|------|
| `useBookStore` | [book.ts](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/frontend/src/stores/book.ts) | 当前书籍/章节/蓝图文稿状态 |
| `useConfigStore` | [config.ts](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/frontend/src/stores/config.ts) | 全局配置（持久化到 localStorage）|
| `useUIStore` | [ui.ts](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/frontend/src/stores/ui.ts) | UI 状态（活动栏/侧面板/主题/命令面板）|

### 5.4 布局组件

| 组件 | 说明 |
|------|------|
| `AppShell.vue` | 应用外壳布局（活动栏 + 侧面板 + 主内容区 + 状态栏）|
| `ActivityBar.vue` | 左侧活动栏（15 个功能入口图标）|
| `SidePanel.vue` | 侧边面板容器 |
| `StatusBar.vue` | 底部状态栏 |

### 5.5 共享组件

| 组件 | 说明 |
|------|------|
| `ChapterTree.vue` | 章节树形目录 |
| `CommandPalette.vue` | 命令面板（Ctrl+K）|
| `GlobalProgress.vue` | 全局进度指示器 |
| `InlineNotice.vue` | 内联通知 |
| `SkeletonLoader.vue` | 骨架屏加载 |
| `TiptapEditor.vue` | Tiptap 富文本编辑器封装 |
| `AiGenerationToolbar.vue` | AI 生成工具栏 |
| `WriteToolbar.vue` | 写作工具栏 |

---

## 6. 关键类与接口

### 6.1 核心单例列表

以下所有模块级单例可直接 import 使用：

```python
from kunlun.config import settings              # 全局配置 (pydantic-settings)
from kunlun.model_router import model_router    # 多模型路由
from kunlun.kg.client import kg_client           # KG 统一客户端
from kunlun.kg.embedder import embedder          # BGE 嵌入器
from kunlun.kg.snapshot import snapshot_manager  # KG 快照管理
from kunlun.gacha.engine import gacha_engine     # 抽卡引擎
from kunlun.gacha.param_variator import param_variator  # 参数随机化器
from kunlun.audit.icu import icu_system          # 连载 ICU
from kunlun.audit.output_contract import output_contract  # 输出契约校验
from kunlun.audit.fanqie_gates import fanqie_optimizer   # 番茄流量优化
from kunlun.pipeline import pipeline_intervention # 管线干预管理
from kunlun.common.alerter import alerter         # 告警器
from kunlun.token_tracker import token_tracker   # Token 追踪
from kunlun.skills.loader import skill_loader    # 技能加载器
from kunlun.quality import quality_dashboard     # 质量看板
from kunlun.context.budget import ContextBudgetAllocator  # 上下文预算
from kunlun.style.refiner import text_refiner    # 文本精炼器
from kunlun.style.vibe import get_vibe_engine    # Vibe 引擎
from kunlun.conflict import get_conflict_manager # 冲突管理器
from kunlun.vibe_writer.orchestrator import get_orchestrator  # Vibe 总调度
from kunlun.exceptions import KunlunError        # 异常基类
```

### 6.2 异常体系

所有异常继承自 `KunlunError`，按模块分层：

```
KunlunError
├── WriterError / WriterBudgetError / WriterRevisionError / WriterGenerationError
├── PipelineError / PipelineStepError / PipelineTimeoutError
├── GachaError / GachaModelError / GachaKeyExhaustedError / GachaRateLimitError
├── KGError / KGConnectionError / KGEntityNotFoundError
├── ExportError / ExportFormatError / ExportDependencyError
├── AuditError / AuditGateError
└── ConfigError / ConfigValidationError
```

### 6.3 Agent 消息格式

```python
@dataclass
class AgentMessage:
    msg_id: str           # 消息唯一 ID
    from_agent: str       # 发送方 Agent
    to_agent: str         # 接收方 Agent
    msg_type: str         # 消息类型 (BLUEPRINT_READY, AUDIT_RESULT 等)
    payload: dict         # 消息载荷
    correlation_id: str   # 关联任务 ID
    kg_snapshot_id: str   # KG 快照 ID
    timestamp: float      # 时间戳
```

### 6.4 管线步骤定义

```python
@dataclass
class PipelineStepDef:
    name: str                     # 步骤名称
    handler: str                  # 处理器名称
    required: bool = True         # 失败是否阻断管线
    retry_count: int = 0          # 重试次数
    retry_delay: float = 1.0      # 重试延迟
    timeout: float = 120.0        # 超时秒数
    degrade_on_failure: bool = False  # 失败是否降级
    skip_conditions: list[str]    # 跳过条件
```

### 6.5 知识图谱本体

```python
# 9 实体类型
EntityType: Character, Location, Item, Organization, Skill, Event, 
            Foreshadowing, Knowledge, ChapterSnapshot

# 22 关系类型
RelationshipType: APPEARS_IN, KNOWS, OWNS, LOCATED_AT, BELONGS_TO,
                  HAS_SKILL, PARTICIPATES_IN, CAUSES, FORESHADOWS,
                  RESOLVES, CONFLICTS_WITH, ALLIES_WITH, etc.
```

---

## 7. 数据流与管线执行流程

### 7.1 完整创作流程

```
用户意图 (自然语言)
    │
    ▼
VibeOrchestrator (解析意图)
    │
    ├── "创建新书" → EditorInChief → 44维社会推演 → 世界观初始化
    │
    ├── "写一章" → NovelPipeline (17步)
    │       │
    │       ├── 1. KG Snapshot (保存当前知识图谱状态)
    │       ├── 2. Planner (章节意图规划)
    │       ├── 3. Architect (蓝图: 冲突/氛围/爽点规划)
    │       ├── 4. Society (社会推演，44维 RAG)
    │       ├── 5. Writer (Gacha 多模型抽卡 + VibePrompt 注入)
    │       ├── 6. Conflict (冲突驱动追踪 #4)
    │       ├── 7. Vibe (Vibe Writing 氛围追踪 #6)
    │       ├── 8. PostWrite (11条零LLM后写验证)
    │       ├── 9. Audit (33维审计 / 8门禁)
    │       ├── 10. Revise (最多3轮修订循环)
    │       ├── 11. ICU (7维连载ICU检查 + LLM自动修复)
    │       ├── 12. Quality (质量看板，可执行结果)
    │       ├── 13. Polish (StyleEngineer 304规则去AI味)
    │       ├── 14. KG Update (知识图谱更新 + 爽点标记)
    │       ├── 15. Pleasure (爽点追踪)
    │       ├── 16. Truth Sync (7份真相文件同步 + Schema校验)
    │       └── 17. Reflect (写后反思)
    │
    ├── "导出" → Exporter (7种格式)
    │
    └── "发布" → Publisher (7平台)
```

### 7.2 消息总线数据流

```
Agent A ──post_message(to="Agent B", type, payload)──→ MessageBus
                                                           │
                                          ┌────────────────┼────────────────┐
                                          ▼                ▼                ▼
                                      NATS (分布式)    进程内消息总线    降级模式
                                          │                │
                                          ▼                ▼
                                      Agent B ──on_message(msg)──→ 处理 → 响应
```

### 7.3 优雅降级流程

```
外部服务检测
    │
    ├── Neo4j: 可用? ──Yes──→ 使用 Neo4j
    │              ──No───→ 自动切换到 SQLite 图模式
    │
    ├── Redis:  可用? ──Yes──→ 使用 Redis 缓存
    │              ──No───→ 禁用缓存，直接读写
    │
    ├── NATS:   可用? ──Yes──→ 使用 NATS 消息队列
    │              ──No───→ 使用进程内 InProcessMessageBus
    │
    └── Qdrant: 可用? ──Yes──→ 使用独立 Qdrant 服务
                   ──No───→ 使用嵌入式本地模式
```

---

## 8. 依赖关系

### 8.1 Python 后端核心依赖

| 类别 | 包名 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | fastapi | 0.115.0 | API 框架 |
| | uvicorn | 0.34.0 | ASGI 服务器 |
| | websockets | 14.1 | WebSocket 支持 |
| | slowapi | 0.1.9 | 速率限制 |
| **数据库** | neo4j | 5.28.0 | 图数据库驱动 |
| | redis | 5.2.1 | 缓存 |
| | qdrant-client | 1.11.3 | 向量数据库 |
| | sqlalchemy | 2.0.35 | ORM |
| | alembic | 1.13.2 | 数据库迁移 |
| **消息** | nats-py | 2.9.0 | 消息总线 |
| **LLM** | openai | 1.68.2 | OpenAI 客户端 |
| | anthropic | 0.49.0 | Anthropic 客户端 |
| **嵌入** | sentence-transformers | 3.4.0 | 向量嵌入 |
| | torch | >=2.1.0 | 深度学习（BGE 模型）|
| **数据** | pydantic | 2.9.2 | 数据验证 |
| | pydantic-settings | 2.5.2 | 配置管理 |
| | python-dotenv | 1.0.1 | 环境变量 |
| **文本** | jieba | 0.42.1 | 中文分词 |
| | numpy | >=2.0.0 | 数值计算 |
| **异步** | httpx | 0.27.2 | HTTP 客户端 |
| | aiofiles | 24.1.0 | 异步文件 |
| **日志** | loguru | 0.7.2 | 日志 |
| **工具** | tqdm | 4.66.5 | 进度条 |
| | pyyaml | 6.0.2 | YAML 解析 |
| **代码质量** | ruff | >=0.11.0 | Linter + Formatter |
| | mypy | >=1.14.0 | 类型检查 |
| | pre-commit | >=4.0.0 | Git hooks |

### 8.2 导出扩展依赖 (可选)

| 包名 | 用途 |
|------|------|
| ebooklib | EPUB 导出 |
| weasyprint | PDF 导出 |
| python-docx | DOCX 导出 |

### 8.3 前端核心依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| vue | ^3.4.0 | UI 框架 |
| naive-ui | ^2.38.0 | 组件库 |
| pinia | ^2.1.0 | 状态管理 |
| vue-router | ^4.3.0 | 路由 |
| echarts | ^6.1.0 | 图表 |
| @tiptap/vue-3 | ^3.26.0 | 富文本编辑器 |
| @vueuse/core | ^14.3.0 | 组合式工具 |
| @tauri-apps/api | ^2.0.0 | Tauri API |

---

## 9. 项目运行方式

### 9.1 环境要求

- **操作系统**: Windows 11 / macOS / Linux
- **Python**: >= 3.11
- **Node.js**: >= 18 (前端开发)
- **内存**: 推荐 16GB
- **Docker** (可选): 用于 Neo4j/Redis/NATS/Qdrant 服务

### 9.2 本地开发启动

```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
cp .env.example .env
# 编辑 .env 填入 API Key

# 4. 启动后端 (Web 模式)
python -m uvicorn kunlun.api.main:app --host 127.0.0.1 --port 8000 --reload

# 5. 启动前端 (桌面端，另一个终端)
cd frontend
npm install
npm run dev              # Vite 开发服务器 (http://localhost:5173)
# npm run tauri dev      # Tauri 桌面端
```

### 9.3 CLI 命令行使用

```bash
# 环境检查
python kunlun_cli.py doctor

# 创建新书
python kunlun_cli.py book create --title "我的第一本小说" --genre 都市修真

# 写下一章
python kunlun_cli.py write next --book-id my_novel

# 后台自动写作
python kunlun_cli.py up --book-id my_novel --chapters 10

# 质量检查
python kunlun_cli.py quality --file chapter.txt

# 文本精炼
python kunlun_cli.py refine --file chapter.txt

# 番茄流量检查
python kunlun_cli.py fanqie --file chapter.txt
```

### 9.4 Docker 部署

```bash
# 启动依赖服务 (Neo4j + Redis + NATS + Qdrant + 昆仑应用)
docker compose up -d

# 自定义构建
docker build -t kunlun .
docker run -p 8000:8000 --env-file .env kunlun
```

### 9.5 测试运行

```bash
# 全部测试
pytest tests/

# 单个测试文件
pytest tests/test_gacha.py -v

# 覆盖率报告
pytest --cov=kunlun tests/ --cov-report=html
```

### 9.6 代码质量检查

```bash
# Ruff (Lint + Format)
ruff check .           # 代码检查
ruff format .          # 代码格式化

# MyPy
mypy kunlun/           # 类型检查

# Pre-commit
pre-commit run --all-files  # 提交前检查
```

### 9.7 Tauri 桌面端构建

```bash
cd frontend
npm run tauri build     # 生成 NSIS 安装包
```

---

## 10. 配置与环境变量

### 10.1 核心配置项

#### LLM API

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | — |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | — |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | — |
| `OPENAI_API_KEYS_BACKUP` | 备用 Key (逗号分隔) | — |

#### 成本控制

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_MAX_TOKENS_PER_REQUEST` | 单次最大 Token | 4096 |
| `LLM_MAX_CALLS_PER_HOUR` | 每小时最大调用 | 60 |
| `LLM_DAILY_TOKEN_BUDGET` | 每日 Token 预算 | 500000 |

#### 数据库

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NEO4J_URI` | Neo4j Bolt 地址 | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j 用户 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密码 | — |
| `REDIS_HOST` | Redis 主机 | `localhost` |
| `REDIS_PORT` | Redis 端口 | 6379 |
| `NATS_URL` | NATS 地址 | `nats://localhost:4222` |

#### 应用

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_HOST` | 主机 | `127.0.0.1` |
| `APP_PORT` | 端口 | 8000 |
| `APP_ENV` | 环境 | `development` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `API_AUTH_ENABLED` | 启用 API 认证 | `false` |
| `RATE_LIMIT_PER_MINUTE` | 每分钟限制 | 30 |

#### 管线配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PIPELINE_AUTO_PROOFREAD` | 自动校对 | `true` |
| `PIPELINE_CONTEXT_BUDGET` | 上下文预算 | 8000 |
| `PIPELINE_DEFAULT_GENRE` | 默认体裁 | `xuanhuan` |
| `PIPELINE_MAX_PARALLEL_AGENTS` | 最大并行 Agent | 5 |

---

## 11. 部署架构

### 11.1 Docker Compose 架构

```
┌─────────────────────────────────────────────────┐
│                  Docker Network                   │
│                                                   │
│  ┌─────────┐  ┌────────┐  ┌──────┐  ┌────────┐ │
│  │  Neo4j  │  │ Redis  │  │ NATS │  │ Qdrant │ │
│  │ :7474   │  │ :6379  │  │:4222 │  │ :6333  │ │
│  │ :7687   │  │        │  │:8222 │  │        │ │
│  └────┬────┘  └───┬────┘  └──┬───┘  └───┬────┘ │
│       │           │          │           │       │
│       └───────────┼──────────┼───────────┘       │
│                   │          │                   │
│              ┌────▼──────────▼──────┐            │
│              │    kunlun (昆仑应用)   │            │
│              │       :8000           │            │
│              └───────────────────────┘            │
└─────────────────────────────────────────────────┘
```

### 11.2 Kubernetes 部署 (k8s/)

| 文件 | 说明 |
|------|------|
| [deployment.yaml](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/k8s/deployment.yaml) | 昆仑应用 Deployment |
| [service.yaml](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/k8s/service.yaml) | Service 暴露 |
| [configmap.yaml](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/k8s/configmap.yaml) | 配置注入 |
| [secret.yaml](file:///c:/Users/hhj/OneDrive/Desktop/昆仑最新版/k8s/secret.yaml) | 密钥管理 |

### 11.3 内存预估

| 组件 | 内存 |
|------|------|
| Neo4j Community | ~800MB |
| Redis | ~100MB |
| NATS | ~50MB |
| Qdrant (嵌入式) | ~200MB |
| FastAPI 应用 | ~300MB |
| **总计** | **~1.5GB** |

---

> **文档说明**: 本文档通过静态代码分析生成，仅对项目结构、模块职责、关键类和依赖关系进行说明，不包含任何代码修改。项目版本 v0.3.0，代码行数约 44,000 行（Python），39 个子包。
>
> 详细 API 文档请启动服务后访问 `http://localhost:8000/docs` 查看 Swagger UI。
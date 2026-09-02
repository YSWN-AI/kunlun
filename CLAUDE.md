# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**昆仑创作引擎 (Kunlun Creation Engine)** — v0.3.0. AI-assisted Chinese web novel creation platform. Built on **Vibe Writing** philosophy — you express intent in natural language, the AI handles everything from world-building to chapter writing to quality assurance to export. Local-first, supports multiple LLM providers, knowledge graph backbone, 6 driving forces (power fantasy, plot, character, conflict, emotion, vibe).

> 📖 **文档体系见 [`docs/索引.md`](docs/索引.md)** — 模块化组织，按编号局部更新。
> 更新统计数字 → [`docs/07-统计与检查清单.md`](docs/07-统计与检查清单.md)
> 记录版本历史 → [`docs/06-版本与问题.md`](docs/06-版本与问题.md)
> 更新API端点 → [`docs/04-API与前端.md`](docs/04-API与前端.md)
> 更新修复进度 → [`docs/08-修复报告.md`](docs/08-修复报告.md)（含附录A-F：85项目调研+源码分析+实现路径）

## Commands

```bash
# Setup
python -m venv venv && source venv/Scripts/activate  # or venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # then edit API keys
scripts\setup.bat     # full Windows setup

# Run server
uvicorn kunlun.api.main:app --host 127.0.0.1 --port 8000 --reload
scripts\start.bat     # or start_api.bat (Windows launcher)

# CLI
python kunlun_cli.py book create --title "小说名" --genre 都市修真
python kunlun_cli.py write next --book-id my_novel
python kunlun_cli.py model set --agent writer --model claude-opus-4-6
python kunlun_cli.py audit check --book-id my_novel --chapter 1

# Run tests
pytest tests/                          # all tests
pytest tests/test_xxx.py               # single test file
pytest tests/test_xxx.py -k "test_yyy" # single test
pytest --cov=kunlun tests/             # with coverage

# Docker (dependency services: Neo4j, Redis, NATS, Qdrant)
docker compose up -d
docker build -t kunlun .

# Tauri desktop
cd frontend && npm install && npm run tauri dev
cd frontend && npm run tauri build      # build NSIS installer
```

## Core Architecture

### Pipeline (orchestrated by `kunlun/pipeline/novel_pipeline.py`)

```
KG Snapshot → Architect (含冲突+Vibe规划) → SocietyDeduce → Writer (Gacha+Vibe注入)
  → Conflict追踪 → Vibe氛围追踪 → PostWrite验证(11条零LLM)
  → Auditor (33维/8 Gates hybrid) → [up to 3 revision loops] → ICU 7维检查
  → QualityDashboard(可执行结果) → StyleEngineer(304规则) → KG Update (+ PleasurePoint)
  → TruthFile Sync (+ Schema校验) → Reflect
```

17 steps total across 6 driving forces. Two unified pipeline modes:
- **NovelPipeline** (`kunlun/pipeline/novel_pipeline.py`): 4 modes (full 17步/standard 14步/quick 10步/editor 12步)
- **VibeOrchestrator** (`kunlun/vibe_writer/orchestrator.py`): Supreme agent — one sentence completes entire workflow
- Token budget control via `ContextBudgetAllocator` (WenShape 6-segment allocation)
- Parameter randomization via `param_variator` (7 dimensions + chapter-type awareness)

### Agent System (`kunlun/agents/` + new)

| Agent | File | Role |
|-------|------|------|
| **VibeOrchestrator** ★ | `vibe_writer/orchestrator.py` | Supreme agent — Vibe Writing entry, one sentence completes everything |
| MakefileAgent | `agents/makefile.py` | Pipeline orchestrator (17-step coordinator) |
| EditorInChief | `agents/editor.py` | Dialog-based chief editor (8-step chat pipeline) |
| Scheduler | `agents/scheduler.py` | Task decomposer + parallel agent cluster |
| Architect | `agents/architect.py` | Chapter blueprint + conflict/vibe/pleasure planning |
| Writer | `agents/writer.py` | Draft via Gacha + TokenBudget + VibePrompt injection |
| Auditor | `agents/auditor.py` | Delegates to 8 audit gates or 33维 audit |
| Sociologist | `agents/sociologist.py` | Societal/reader profile simulation (44 dims → RAG) |
| StyleEngineer | `style_engineer.py` | De-AI-ification + VibeEngine (delegates to `style/`) |
| **ConflictEngine** ★ | `conflict/__init__.py` | Conflict tracking + TensionManager + heatmap |
| Publisher | `publishere.py` | Platform publication agent |

All agents communicate via the message bus (`agents/message_bus.py`) with optional NATS fallback.

### Gacha Engine (`kunlun/gacha/engine.py`)

Multi-model parallel generation. 4 modes: `single_fix`, `gacha_parallel_3` (3 models), `gacha_cheap_2` (2 random), `gacha_ultimate_5` (5 → paragraph-level mix). Scores on **9 dimensions** (hook, pleasure, anti_ai, emotion, information, rhythm, character, style, dialogue) via pure text statistics — no LLM in scoring. Uses `deepseek-chat`/`deepseek-reasoner` with varying temperatures as the model pool. Includes a `chat()` method for direct LLM calls (used by AI chat endpoint).

### Audit System (`kunlun/audit/`)

| System | File | Scope | LLM |
|--------|------|-------|-----|
| **8 Gates (G1-G8)** | `gates.py` | Arc/info/AI味/爽点/情绪/对话/战斗 | ❌ Pure rules |
| **33维 Audit** | `audit33.py` | 6 groups × 33 dims (A:角色/F:AI痕迹) | ❌ Pure rules |
| **连载ICU** | `icu.py` | 7 dims (爽点/情绪/信息/节奏/钩子/OOC/对话) | ✅ Auto-fix uses LLM |

Pipeline auto-adopts 33维 audit first, falls back to 8 gates. All 8 gate implementations live in `gates.py` (delegated through `auditor.py`). G4-G5 use `jieba` segmentation for keyword counting.

### Knowledge Graph (`kunlun/kg/`)

4-layer storage with graceful degradation:
- **Neo4j** (primary graph DB) → **SQLite graph** (fallback) → unified via `KGClient`
- **Qdrant** (vector embeddings via BGE) for semantic search
- **SQLite FTS5** (full-text search, built-in, always on)

**Ontology** (`ontology.py`): 9 entity types (Character, Location, Item, Organization, Skill, Event, Foreshadowing, Knowledge, ChapterSnapshot) + 22 relationship types. Properties use Pydantic v2 models with `extra_data` alias (avoids collision with Pydantic's reserved `metadata` field). CultivationRealm enum provides a sample cultivation system (斗之力 → 斗帝). Constraints defined as module-level constants with human-readable rules.

**Snapshots** (`snapshot.py`): Auto-managed, tracks `last_pleasure_chapter` for continuity.

**Embedder** (`embedder.py`): BGE model via `sentence-transformers`, with singleton instance.

### Model Router (`kunlun/model_router.py`)

Per-agent model configuration via `ModelRouter` singleton. Supports OpenAI, Anthropic, DeepSeek, or any OpenAI-compatible API. 9 default agent configs (architect/writer/auditor/reviser/stylist/planner/radar/sociologist/market). Persisted to `data/model_routing.json`. Configurable via API (`POST /model/configure`) or CLI (`python kunlun_cli.py model set/list`).

### Key Global Singletons

All are module-level instances, importable directly:

```python
from kunlun.config import settings              # Settings (pydantic-settings, loads from .env)
from kunlun.model_router import model_router     # Per-agent LLM model config + TASK_TIERS
from kunlun.kg.client import kg_client           # KGClient (Neo4j → SQLite graph)
from kunlun.kg.embedder import embedder          # Embedder (BGE via sentence-transformers)
from kunlun.kg.snapshot import snapshot_manager  # SnapshotManager
from kunlun.gacha.engine import gacha_engine     # GachaEngine (singleton, multi-model pool)
from kunlun.gacha.param_variator import param_variator  # 7-dim parameter randomization
from kunlun.audit.icu import icu_system          # ICUSystem (7-dim quality)
from kunlun.audit.output_contract import output_contract  # SpecForge-style schema validation
from kunlun.audit.fanqie_gates import fanqie_optimizer # Fanqie traffic optimizer
from kunlun.pipeline import pipeline_intervention # PipelineInterventionManager
from kunlun.common.alerter import alerter         # Alerter (error recording)
from kunlun.token_tracker import token_tracker   # TokenTracker (usage + budget)
from kunlun.skills.loader import skill_loader    # SkillLoader (skills/ .md files)
from kunlun.quality import quality_dashboard     # QualityDashboard (aggregated + actionable)
from kunlun.context.budget import ContextBudgetAllocator  # WenShape 6-segment budget
from kunlun.style.refiner import text_refiner    # TextRefiner (304 rules)
from kunlun.style.vibe import get_vibe_engine    # VibeEngine (14 atmosphere types)
from kunlun.conflict import get_conflict_manager # ConflictManager (6 types + tension)
from kunlun.vibe_writer.orchestrator import get_orchestrator  # VibeOrchestrator (supreme agent)
from kunlun.exceptions import KunlunError        # Unified exception hierarchy (20 classes)
from kunlun.observability import record_generation_step  # Per-step generation timing
```

### Truth Files (`kunlun/truth/`)

7 machine-readable JSON files auto-updated per chapter for cross-chapter consistency:
1. `character_matrix.json` — interaction matrix + info boundaries
2. `emotional_arcs.json` — per-character emotional arcs
3. `current_state.json` — character current state (location/realm/relationships)
4. `pending_hooks.json` — unresolved foreshadowing
5. `subplot_board.json` — side-plot progress
6. `chapter_summaries.json` — chapter summary index
7. `book_rules.json` — hard world-building rules

Files are stored as JSON. Used by 33维 audit as the ground truth for continuity checks.

### Pipeline Intervention (`kunlun/pipeline/__init__.py`)

Human-in-the-loop system: each pipeline step (snapshot/blueprint/draft/audit/polish/publish) can pause for approval. Features: timeout auto-approval, WebSocket notifications, state persistence to `data/pipeline_states/`, retry/skip/modify actions. Managed via `PipelineInterventionManager` singleton. State machine: PENDING → RUNNING → WAITING_APPROVAL → APPROVED/REJECTED/SKIPPED/FAILED.

### API (`kunlun/api/`)

FastAPI with 46+ REST endpoints + WebSocket + SSE. Routes at `/api/v1/*`.
- `main.py`: App lifecycle (Neo4j constraints init, seed data, skills loading via `skill_loader`, JSON log format, CORS, Prometheus metrics, rotating file logs, request middleware with AutoSync triggers, global exception handler)
- `routes.py`: All endpoints — AI chat, editor chat, daemon control, book CRUD, chapter generation (sync + batch), audit, KG queries, full-text search, gacha model listing, preferences, snapshots, rollback, token usage, export, streaming (SSE)
- `ws_manager.py`: WebSocket connection pool management
- `streaming.py`: SSE streaming support for chapter generation

### Prompts (`kunlun/prompts/`)
- `pipeline.py`: 4-stage pipeline templates (idea → outline → volume → draft)
- `society.py`: Societal simulation prompt (44 dimensions)
- `society_ext.py`(1-9): 9 extended societal simulation variations
- Custom skills from `skills/` directory loaded at app startup via `kunlun.skills.loader.SkillLoader`

### Extended Modules (50+)

| Module | File(s) | Purpose |
|--------|---------|---------|
| **★ Vibe总调度** | `vibe_writer/orchestrator.py` | Supreme agent — one sentence creates/writes/exports entire book |
| **★ VibeWriter** | `vibe_writer/__init__.py` | Vibe Writing — express intent in natural language, AI writes |
| **★ 冲突引擎** | `conflict/__init__.py` | Conflict driven — 6 types, TensionManager, heatmap |
| **★ Vibe氛围** | `style/vibe.py` | Vibe Writing — 14 atmosphere types, scene vibe tracking |
| 文风指纹 | `style/fingerprint.py` | Statistical + LLM style analysis |
| 去AI味规则 | `style/engineer.py` | Sentence CV, conjunction density, paragraph CV, opening diversity |
| 自主进化 | `learn/evolve.py` | Author profiling + auto skill generation |
| 偏好学习 | `learn/learner.py` | 50-dim preference learning (EMA + decay) |
| 写后反思 | `learn/reflector.py` | Post-chapter reflection |
| 市场情报 | `market/__init__.py` | Trend analysis |
| 情报追踪 | `intel/tracker.py` | God-view detection |
| 守护进程 | `daemon.py` | Background auto-writing with configurable chapter count |
| 文件同步 | `filesync.py` | Control doc auto-sync |
| 导入引擎 | `import_engine.py` | Chapter import + fanfic init |
| 多格式导出 | `exporter/engine.py` | 7 export formats |
| 回复断更 | `recovery/engine.py` | Recovery engine for dropped series |
| 版本回滚 | `recovery/rollback.py` | Chapter version rollback |
| 时空一致性 | `spacetime/engine.py` | Space-time consistency engine |
| 角色状态机 | `state/machine.py` | Character state machine (+ save/load persistence) |
| 涟漪效应 | `ripple/detector.py` | Ripple effect detection |
| 世界观 | `worlds/` | World-building consistency (16 dims + genre-aware suggestions) |
| 短篇生成 | `shortform/` | Short-form generation |
| 读者留存 | `retention/` | Reader retention prediction |
| A/B测试 | `ab_test/` | A/B testing framework |
| 内容安全 | `safety/` | Content safety review |
| 智能水印 | `watermark/` | Smart watermarking |
| 大纲管理 | `outline/` | Outline management |
| 草稿版本 | `draft/` | Draft version management |
| 对话评估 | `dialogue/` | Dialogue quality assessment |
| 爽点检测 | `pleasure/` | Pleasure point detection (12 types + fatigue) |
| 角色弧线 | `arc/` | Character arc tracking (7 dims × 6 arcs) |
| 读者评论 | `comments/` | Reader comment analysis |
| 写作仪表盘 | `dashboard/` | Writing dashboard |
| 情感支持 | `emosupport/` | Emotional support engine |
| 版本管理 | `versions/manager.py` | Git-based version management |
| 技能加载 | `skills/loader.py` | Runtime skill .md → system prompt injection |
| 大图检索 | `rag.py` | RAG query utility |
| 🔥后写验证 | `audit/post_write_validator.py` | 11条零LLM后写质量检查 |
| 🔥AI特征库 | `audit/ai_features.py` | 36+ AI写作特征检测(F/G组) |
| 🔥输出契约 | `audit/output_contract.py` | Schema输出校验(SpecForge风格) |
| 🔥Jieba分词 | `audit/jieba_analyzer.py` | jieba精确关键词匹配 |
| 🔥番茄门禁 | `audit/fanqie_gates.py` | 番茄平台流量适配+全生命周期策略+反作弊 |
| 🔥文本精炼 | `style/refiner.py` | 304条高频套路词替换(Humanizer/TextHumanize) |
| 🔥参数随机化 | `gacha/param_variator.py` | 7维生成参数随机+章节类型感知+历史防重复 |
| 🔥上下文预算 | `context/budget.py` | 6段Token预算+距离衰减(WenShape/SAGA) |
| 🔥质量看板 | `quality/__init__.py` | 聚合质量评分+可执行结果 |
| 🔥质量趋势 | `quality/tracker.py` | 跨章质量趋势+持久化 |
| 🔥共享管线 | `pipeline/novel_pipeline.py` | 4模式(full 17/standard 14/quick 10/editor 12) |
| 🔥扩展基类 | `core/extension_base.py` | 21扩展统一基类 |


### Frontend (`frontend/`)

Tauri 2.0 + Vue 3 + Naive UI + Pinia + Vue Router + TypeScript (vite build + vue-tsc). 17 views + 5 components:
- **CreateCenter**: Main writing view with generation, editing, audit, save/export/TTS
- **BookManager**: Book CRUD + 44-dim initialization
- **EditorChat**: Dialog-based chief editor interface
- **AuditView**: Standalone audit with 8-gate visualization
- **KGView**: Knowledge graph browser (entities, Cypher console, foreshadowing)
- **+12 more views** (Outline, Characters, World, Search, Export, Preferences, Daemon, Snapshots, Usage, Settings, Config, BookWizard)

API layer in `src/api/index.ts`. Desktop build produces NSIS installer.

Web fallback: `web/index.html` + `config.html` — single-page dark-theme HTML UI served statically by FastAPI.

### Key Design Patterns

- **Graceful degradation**: Every external service (Neo4j→SQLite graph, NATS→in-process bus, Redis→cache disabled, Qdrant→embedded Python) has a fallback. The app starts and works without any external dependencies. Verified on startup via `lifespan` hooks with `try/except` around each init.
- **Singleton pattern**: All major systems (`settings`, `kg_client`, `model_router`, `gacha_engine`, `alerter`, `icu_system`, `skill_loader`) are module-level singleton instances. Tests reset key singletons after each test via `conftest.py`'s `reset_singletons()` autouse fixture.
- **Dataclass-heavy results**: Audit results, pipeline state, ICU reports, KG entities all use `@dataclass` with `field(default_factory=...)` for clean defaults.
- **All audit gates are rule-based**: Zero LLM calls in G1-G8 or 33维 — fast deterministic quality gates using regex, `Counter`, and statistics via `jieba` for Chinese segmentation.
- **Chinese-first**: All comments, docstrings, prompts, error messages, and UI are in Chinese. Text processing uses `jieba` for word segmentation.
- **Async pipeline with yield**: `asyncio.sleep(yield_interval)` between steps prevents event loop starvation in async mode.
- **Config**: `Settings` class in `config.py` uses `pydantic-settings` (v2) loading from `.env`. All fields have defaults. `extra="ignore"` to tolerate undefined env vars.
- **Global exception handler**: `main.py` catches all unhandled exceptions, logs them with traceback, records via `alerter.record_error()`, and returns sanitized error messages in production.
- **Test pattern**: No test DB. `conftest.py` resets `KGClient` instance and `Embedder` singleton + clears embedding cache after each test via autouse fixture.

### Dependency Services

| Service | Port | Purpose | Graceful Degradation |
|---------|------|---------|---------------------|
| Neo4j | 7687 | Graph storage | SQLite graph fallback |
| Redis | 6379 | KG snapshot cache | Cache disabled |
| NATS | 4222 | Agent message bus | In-process message bus |
| Qdrant | 6333 | Vector search | Built-in Python mode |
| SQLite FTS5 | — | Full-text search | Built-in (always on) |

### Project Structure

```
kunlun/                     # Core Python package (124 .py files, 39 subpackages)
├── vibe_writer/            # ★ Vibe Writing: VibeOrchestrator(总调度) + VibeWriter(单章伙伴)
├── conflict/               # ★ 冲突引擎: ConflictManager + TensionManager + 热力图
├── agents/                 # 10 agents + message_bus.py (base.py → ABC)
├── api/                    # FastAPI (main.py, routes.py, ws_manager.py, streaming.py)
├── audit/                  # 8 gates + 33维 + ICU + AI特征(36维) + 番茄门禁 + 输出契约
├── kg/                     # KG client, ontology, embedder, snapshot, seed_data
├── gacha/                  # GachaEngine(4模式9维评分) + param_variator(7维随机化)
├── style/                  # Fingerprint + Engineer + VibeEngine + Refiner(304规则)
├── context/                # Token budget allocator (6段, WenShape/SAGA)
├── quality/                # QualityDashboard + 质量趋势 + 可执行结果
├── pipeline/               # NovelPipeline(4模式) + PipelineIntervention
├── learn/                  # 偏好学习(50维) + 写后反思 + 自主进化
├── truth/                  # 7 truth files + schema校验(InkOS Zod风格)
├── prompts/                # Pipeline 4-stage + society 9-extended prompts
├── core/                   # Extension base class (21统一基类)
├── common/                 # Alerter, NATS mock
├── recovery/               # Recovery engine + rollback system
├── ripple/                 # Ripple effect detector
├── spacetime/              # Space-time consistency engine
├── state/                  # Character state machine (+ save/load)
├── intel/                  # Intel/situation tracker (+ persistence)
├── pleasure/               # Pleasure point detection (12种+疲劳度)
├── arc/                    # Character arc tracking
├── dialogue/               # Dialogue quality assessment
├── exporter/               # Multi-format export
├── publish/                # Platform publication
├── market/                 # Trend analysis
├── comments/               # Reader comment analysis
├── dashboard/              # Writing dashboard
├── outline/                # Outline management
├── draft/                  # Draft version management
├── ab_test/                # A/B testing framework
├── safety/                 # Content safety review
├── watermark/              # Smart watermarking
├── emosupport/             # Emotional support engine
├── retention/              # Reader retention prediction
├── worlds/                 # World-building consistency (16 dims)
├── shortform/              # Short-form generation
├── versions/               # Git version manager
├── config.py               # Global config (pydantic-settings)
├── exceptions.py            # Unified exception hierarchy (20 classes)
├── observability.py         # Per-step generation timing + OTel
├── model_router.py         # Per-agent LLM model routing (+ TASK_TIERS 3层)
├── token_tracker.py        # Token usage + budget control
├── daemon.py               # Background auto-writing daemon
├── filesync.py             # Control doc auto-sync
├── autosync.py             # Auto-sync trigger system
├── import_engine.py        # Chapter import engine
├── book_config.py          # Book configuration
├── prompt_manager.py       # Prompt management
├── length_gov.py           # Chapter length governor
├── model_params.py         # Model parameter presets
├── modifier.py             # Text modifier
├── cooldown.py             # Cooldown management
├── brake.py                # Circuit breaker / rate limiter
├── genres.py               # Genre definitions
├── spoiler.py              # Spoiler detection
└── rag.py                  # RAG query utility
web/                        # Static web UI (index.html, config.html) + Vibe总调度
frontend/                   # Tauri 2.0 + Vue 3 + Naive UI desktop app
tests/                      # 31 test files + conftest.py (415 tests, 0 failures)
docs/                       # Documentation (14 files: 8核心 + 2审计报告 + design + superpowers)
skills/                     # Runtime skill definitions (.md)
scripts/                    # Windows setup/start/cleanup scripts
data/                       # Runtime data (24子目录: conflict/ vibe/ truth/ pleasure/ ...)
```

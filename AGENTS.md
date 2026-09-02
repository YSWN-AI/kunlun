# 昆仑创作引擎 — 项目协作指南

> 本文件面向 AI 编码助手与开发者，提供项目架构、常用命令和关键约束的快速参考。

## 项目概述

- **名称**：昆仑创作引擎 (kunlun)
- **版本**：0.4.0
- **定位**：AI 驱动的网络文学创作平台，支持 Vibe Writing 对话式创作、多模型抽卡、53 维质量审计、知识图谱、全管线自动写作
- **语言**：Python >= 3.11
- **许可证**：MIT
- **规模**：kunlun 包 383 个 .py 文件，tests 下 49 个测试文件

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 数据校验 | Pydantic / pydantic_settings |
| 图数据库 | Neo4j |
| 缓存 | Redis |
| 向量检索 | Qdrant |
| LLM SDK | OpenAI / Anthropic / DeepSeek (兼容 OpenAI 协议) |
| 中文处理 | jieba |
| 向量嵌入 | sentence-transformers (BGE) |
| 日志 | loguru |
| 异步文件 | aiofiles |
| 限流 | slowapi |
| 代码规范 | Ruff (Linter + Formatter，替代 flake8/isort/black) |
| 测试 | pytest + pytest-asyncio + coverage |
| 类型检查 | mypy (渐进式严格模式) |
| 打包 | PyInstaller (桌面版) / Docker |

## 目录结构

```
昆仑最新版/
├── kunlun/                  # 核心包（383 个 .py，~80 子包）
│   ├── api/                 # FastAPI 入口（main.py / routes.py / ws_manager / streaming）
│   ├── agents/              # Agent 体系（architect/writer/auditor/editor/scheduler 等）
│   ├── vibe_writer/         # Vibe Writing 总调度 + 单章伙伴
│   ├── audit/               # 53 维审计 + 8 门禁 + 番茄流量门禁 + 后写验证
│   ├── kg/                  # 四层知识图谱（本体/客户端/嵌入/快照）
│   ├── gacha/               # 多模型抽卡引擎（4 模式/9 维评分）
│   ├── conflict/            # 冲突引擎（ConflictManager + TensionManager）
│   ├── context/             # 上下文 Token 预算（6 段 WenShape/SAGA）
│   ├── quality/             # 质量看板 + 质量趋势
│   ├── pipeline/            # 创作管线（steps/ 子模块）
│   ├── character/           # 人物管理
│   ├── plot/                # 情节管理
│   ├── story_bible/         # 故事圣经
│   ├── truth/               # 真相/伏笔管理
│   ├── worlds/              # 世界观管理
│   ├── exporter/            # 导出（TXT/MD/EPUB）
│   ├── publish/             # 发布 Agent
│   ├── safety/              # 内容安全
│   ├── humanize/            # 去 AI 味
│   ├── monetize/            # 商业化
│   ├── versions/            # 版本管理与回滚
│   ├── cost_tracker.py      # Token 成本追踪
│   ├── daemon.py            # 后台守护进程
│   ├── doctor.py            # 环境健康检查
│   └── ...                  # 其余子包（见 docs/01-项目概览.md）
├── tests/                   # 测试套件（49 个 test_*.py）
├── docs/                    # 模块化文档（01-13 编号 + 专项调研）
├── scripts/                 # 构建/打包/清理/种子数据脚本
├── config/                  # 配置文件目录（当前为空，运行时生成）
├── data/                    # 运行时数据（已 gitignore，含书籍/数据库/缓存）
├── frontend/                # 前端源码
├── web/                     # Web 静态资源
├── migrations/              # 数据库迁移
├── skills/                  # 内置技能
├── output/                  # 输出目录
├── k8s/                     # Kubernetes 部署配置
├── .github/                 # GitHub Actions 配置
├── kunlun_cli.py            # CLI 主入口（argparse，~30 个子命令）
├── launch.py                # Web 启动入口
├── desktop.py               # 桌面 GUI 壳入口
├── build_app.py             # PyInstaller 构建脚本
├── pyproject.toml           # 项目元数据 + Ruff/pytest/mypy 配置
├── requirements.txt         # 运行时依赖
├── requirements-dev.txt     # 开发依赖
├── Dockerfile               # Docker 镜像构建
├── docker-compose.yml       # 服务编排（Neo4j/Redis/Qdrant 等）
├── Makefile                 # 常用命令快捷方式
├── .pre-commit-config.yaml  # pre-commit 钩子配置
├── .env.example             # 环境变量模板
├── .env                     # 本地环境变量（已 gitignore，含 API Key）
└── 通用小说创作模板/          # 小说创作项目模板（含 AGENTS.md/大纲/人物/正文模板）
```

## 常用命令

### 环境初始化

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt   # 开发依赖

# 配置环境变量
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
# 编辑 .env 填入 API Key

# 交互式配置向导
python kunlun_cli.py setup
```

### 运行

```bash
# Web 模式（开发，热重载）
python -m uvicorn kunlun.api.main:app --host 127.0.0.1 --port 8000 --reload

# CLI 模式
python kunlun_cli.py doctor          # 环境健康检查
python kunlun_cli.py status          # 项目状态
python kunlun_cli.py book create     # 创建新书
python kunlun_cli.py write next      # 写下一章
python kunlun_cli.py up              # 启动后台守护进程
python kunlun_cli.py down            # 停止守护进程

# 桌面版
python desktop.py
```

### 代码质量

```bash
# Ruff 代码检查
ruff check kunlun/ tests/

# Ruff 自动修复
ruff check --fix kunlun/ tests/

# Ruff 格式化
ruff format kunlun/ tests/

# mypy 类型检查
mypy kunlun/

# 运行测试（含覆盖率，门槛 30%）
pytest

# 运行单个测试文件
pytest tests/test_writer.py -v

# 跳过慢速测试
pytest -m "not slow"
```

### 构建与打包

```bash
# PyInstaller 桌面版构建
python build_app.py
# 或
scripts\build_exe.bat

# Docker 构建
docker build -t kunlun .

# Docker Compose 启动全部依赖服务
docker-compose up -d
```

## 关键约束

### 代码规范

- **行宽**：100 字符（与 Black 兼容）
- **引号**：双引号
- **import 排序**：Ruff I 规则，已知第三方包在 pyproject.toml 中声明
- **print 语句**：允许（T201 忽略），但生产代码优先使用 loguru
- **延迟导入**：大量使用 lazy import 优化启动速度和避免循环依赖（PLC0415 忽略）
- **魔法数字**：创作引擎中字数/评分/阈值等合理魔法数字允许（PLR2004 忽略）
- **全角/半角字符**：中文项目中 RUF001/2/3 忽略
- **异常命名**：后缀 `Error` 比 `Exception` 更语义化（N818 忽略）

### 配置管理

- **环境变量**：`.env` 文件（已 gitignore），模板见 `.env.example`
- **配置加载**：pydantic_settings，支持环境变量覆盖
- **LLM 配置**：支持 OpenAI/DeepSeek/Anthropic 多提供商，通过 `kunlun model set` 管理
- **项目配置**：每本书独立 `project.json`，位于 `data/books/book_<id>/`

### 数据目录

- `data/` 已加入 `.gitignore`，包含：
  - `books/` — 用户书籍数据（章节/大纲/人物/世界观）
  - `*.db` — SQLite 数据库（图谱/搜索/缓存/商业化）
  - `llm_cache.db` — LLM 响应缓存
  - `redis.zip` — Redis 便携版
  - `truth/`、`versions/`、`vibe/` 等运行时状态
- **绝不**将 `data/` 提交到 git，其中包含用户创作内容和 API 缓存

### 测试

- 测试目录：`tests/`，文件名 `test_*.py`
- 异步测试：pytest-asyncio auto 模式
- 覆盖率门槛：当前 30%（渐进式，目标逐步提升到 50→70→80）
- 测试标记：`slow`（慢速）、`integration`（集成）、`unit`（单元）
- Mock 工具：`tests/mocks.py`、`tests/conftest.py`

### Git 提交

- 仓库已初始化，主分支 `main`
- `.gitignore` 已覆盖：Python 缓存、虚拟环境、`.env`、`data/`、构建产物、IDE 配置
- 提交前建议运行：`ruff check` + `pytest`
- pre-commit 钩子配置见 `.pre-commit-config.yaml`

## 开发注意事项

1. **延迟导入模式**：项目大量使用函数内 import 来优化启动速度和避免循环依赖。新增模块时如遇循环依赖，优先考虑延迟导入而非重构。
2. **Agent 消息总线**：Agent 间通信通过 `kunlun/agents/message_bus.py`，新增 Agent 时应接入总线而非直接调用。
3. **审计门禁**：所有生成内容必须通过 8 道门禁（G1-G8，纯规则零 LLM）和 33 维连续性审计。修改生成逻辑时需同步检查审计规则。
4. **多模型抽卡**：LLM 调用统一通过 `kunlun/gacha/engine.py` 的 `chat()` 方法，不直接调用 OpenAI SDK，以支持模型路由、成本控制和缓存。
5. **知识图谱**：实体/关系操作通过 `kunlun/kg/client.py` 统一客户端，支持 Neo4j 和本地 SQLite 双模式。
6. **Vibe Writing**：新的对话式创作入口在 `kunlun/vibe_writer/`，旧的 10 步管线在 `kunlun/agents/makefile.py`（兼容保留）。
7. **中文编码**：所有文件使用 UTF-8 编码，Windows 下读取文件时显式指定 `-Encoding utf8`。
8. **版本号**：`pyproject.toml` 中为 0.4.0，README 中可能滞后，发版时需同步更新。

## 相关文档

- 完整文档索引：[`docs/索引.md`](docs/索引.md)
- 项目概览：[`docs/01-项目概览.md`](docs/01-项目概览.md)
- Agent 与管线：[`docs/02-Agent与管线.md`](docs/02-Agent与管线.md)
- 引擎与知识图谱：[`docs/03-引擎与知识图谱.md`](docs/03-引擎与知识图谱.md)
- API 与前端：[`docs/04-API与前端.md`](docs/04-API与前端.md)
- 扩展模块与宪法：[`docs/05-扩展模块与宪法.md`](docs/05-扩展模块与宪法.md)
- 代码 Wiki：[`docs/10-Code-Wiki.md`](docs/10-Code-Wiki.md)
- 小说创作模板：[`通用小说创作模板/README.md`](通用小说创作模板/README.md)

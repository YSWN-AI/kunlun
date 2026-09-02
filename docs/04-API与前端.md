# 04 API 与前端

> **更新最频繁的文档**。新增端点或前端改动后必须更新。

## API 层 — 46 端点

### AI 与对话 (2)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | AI 聊天 (gacha_engine.chat) |
| POST | `/api/v1/editor/chat` | 主编对话 (EditorInChief) |

### 创作生成 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/books/{id}/chapters/{n}/generate` | 全流程13步管线 |
| POST | `/api/v1/books/{id}/chapters/batch-generate` | 批量生成 |
| POST | `/api/v1/daemon/start` | 启动守护进程 |
| POST | `/api/v1/daemon/stop` | 停止守护进程 |

### 审计与质量 (1)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/audit/run` | 独立审计 (8门禁+33维) |

### 知识图谱 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/kg/query` | Cypher 查询 (含注入防护) |
| GET | `/api/v1/kg/entities/{entity_type}` | 按类型列出实体 |
| GET | `/api/v1/kg/foreshadowing/overdue` | 逾期伏笔 |
| GET | `/api/v1/search` | FTS5 全文搜索 |

### 快照 (2)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/books/{id}/snapshots/latest` | 最新 KG 快照 |
| GET | `/api/v1/books/{id}/snapshots/{sid}` | 指定 KG 快照 |

### 作品管理 (7)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/books/create` | 创建作品 |
| GET | `/api/v1/books/list` | 作品列表 |
| GET | `/api/v1/books/{id}` | 作品详情+统计 |
| DELETE | `/api/v1/books/{id}` | 删除作品 |
| POST | `/api/v1/books/{id}/initialize` | 开书44维全量推演 |
| GET | `/api/v1/books/{id}/chapters/{n}/content` | 章节内容 |
| GET | `/api/v1/usage/{id}` | Token 用量统计 |

### 偏好学习 (2)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/books/{id}/preferences` | 偏好向量查询 |
| POST | `/api/v1/books/{id}/preferences/feedback` | 偏好反馈录入 |

### 导出 (2)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/export/chapter` | 单章导出 |
| GET | `/api/v1/export/book` | 全书导出 |

### 模型与参数 (8)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/gacha/models` | 可用抽卡模型列表 |
| GET | `/api/v1/genres` | 体裁列表 |
| GET | `/api/v1/genres/{name}` | 体裁详情 |
| GET | `/api/v1/params/defs` | 参数定义列表 |
| GET | `/api/v1/params/{book_id}` | 作品参数 |
| GET/POST | `/api/v1/params/{book_id}/{agent}` | Agent 参数 CRUD |
| GET/POST | `/api/v1/prompts/{book_id}` | Prompt 管理 |
| GET/POST/DELETE | `/api/v1/prompts/{book_id}/{agent}` | Agent Prompt CRUD |

### 配置 (3)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/v1/config/{book_id}` | 作品配置 CRUD |
| POST | `/api/v1/config/{book_id}/auto-deduce` | 单字段自动推断 |
| POST | `/api/v1/config/{book_id}/auto-deduce-all` | 全字段自动推断 |

### 实时推送 (2)

| 方法 | 路径 | 说明 |
|------|------|------|
| WS | `/api/v1/ws/{book_id}/{chapter}` | WebSocket 进度推送 |
| GET | `/api/v1/stream/generate` | SSE 流式生成 |

### 扩展端点 (4)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/orchestrate` | 编排 Agent |
| GET | `/api/agents` | Agent 列表 |
| GET | `/api/truth-status` | 真相文件快照 |
| POST | `/api/auto-fix` | 自动语法修复 |

### 基础设施 (3)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/status` | 系统状态 + 组件健康 |
| GET | `/health` | Docker 健康检查 |
| GET | `/metrics` | Prometheus 指标 |

### 额外端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/ripple/check` | 涟漪检测 |
| POST | `/api/v1/safety/check` | 安全审查 |

### 中间件

CORS / 请求日志 + AutoSync 触发 / 全局异常处理 `{success, error, traceback}` / Prometheus `/metrics` / 回滚日志轮转 (10MB×3)

---

## 前端 UI

**技术栈**: Vue 3 + TypeScript + Naive UI + Vite 5 + Pinia + Vue Router

```
frontend/src/
├── main.ts                  # Vue 应用挂载
├── App.vue                  # 根组件 (深色主题 NConfigProvider)
├── api/index.ts             # API 封装 (47+ 方法)
├── types/api.ts             # 完整 TypeScript 类型 (218行)
├── router/index.ts          # 17 路由 (4组, 懒加载)
├── stores/                  # Pinia 状态管理
│   ├── book.ts              # 作品/章节状态
│   ├── config.ts            # 模型参数/配置状态
│   └── ui.ts                # UI 状态 (连接/提示/侧栏)
├── layouts/
│   └── MainLayout.vue       # 主布局 (侧栏17项+顶栏+内容区)
├── views/                   # 17 个视图页面
│   ├── CreateCenter.vue     # 创作中心 (生成/编辑/审计/保存)
│   ├── BookManager.vue      # 作品管理 (CRUD+开书推演)
│   ├── EditorChat.vue       # 主编对话
│   ├── BookWizard.vue       # 作品向导
│   ├── OutlineView.vue      # 大纲管理
│   ├── WorldView.vue        # 世界观设定
│   ├── CharacterView.vue    # 角色管理
│   ├── AuditView.vue        # 独立审计 (8门禁+分数)
│   ├── KGView.vue           # 知识图谱浏览器 (实体/Cypher/伏笔)
│   ├── SearchView.vue       # 全文搜索
│   ├── ExportView.vue       # 多格式导出
│   ├── PreferencesView.vue  # 偏好设置
│   ├── DaemonView.vue       # 守护进程控制
│   ├── SnapshotView.vue     # KG 快照浏览
│   ├── UsageView.vue        # Token 用量统计
│   ├── SettingsView.vue     # 模型路由设置
│   └── ConfigCenter.vue     # 作品配置中心
└── components/              # 5 个共享组件
    ├── ChapterEditor.vue    # [已废弃] → 迁移至 CreateCenter
    ├── AuditReport.vue      # 审计报告面板
    ├── KGBrowser.vue        # 知识图谱浏览器
    ├── OutlinePanel.vue     # 大纲面板
    └── SettingsDialog.vue   # 设置对话框
```

## 桌面端 (Tauri 2.0)

```
Tauri 窗口 (1280x860)
  ├── Vue 3 前端 (完整 SPA)
  └── Tauri API (@tauri-apps/api v2)
      └── 窗口管理 / 系统通知 / 文件系统
```

开发: `cd frontend && npm run tauri dev`
打包: `cd frontend && npm run tauri build` → NSIS 安装包

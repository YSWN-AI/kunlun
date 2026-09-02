# 昆仑创作引擎 — 生产级全量深度审计报告

> **审计日期**: 2026-06-07  
> **审计范围**: 124 `.py` 文件，39 子包，~42,000 行代码  
> **测试结果**: 379 通过，36 失败，1 跳过  
> **审计方法**: 全量代码阅读 + 静态分析 + 测试运行 + 架构审查

---

## 执行摘要

本次审计对昆仑创作引擎 v0.1.0-alpha 进行了全面的生产级代码审计。发现了 **7 个 P0 致命问题**、**13 个 P1 严重问题**。36 个异步测试因缺少 `pytest-asyncio` 全部失败。整体架构设计优秀，降级策略完善，但存在若干影响生产稳定性的关键缺陷需立即修复。

---

## 一、项目理解

### 1.1 核心架构确认

- **Web框架**: FastAPI + Uvicorn，46+ REST端点 + WebSocket + SSE
- **Agent体系**: 10个专业Agent + 1个消息总线（InProcessMessageBus + NATS降级）
- **创作管线**: 17步完整管线（4模式：full/standard/quick/editor）
- **知识图谱**: 4层存储（Neo4j → SQLite图降级 → Qdrant向量 → FTS5全文）
- **多模型引擎**: GachaEngine（4模式：single/cheap_2/parallel_3/ultimate_5）+ 9维评分
- **审计体系**: 53维（8门禁 + 33维 + ICU 7维 + 后写验证11条）+ 番茄门禁 + 输出契约
- **前端**: Tauri 2.0 + Vue 3 + TypeScript（17视图）+ Web UI 降级
- **导出**: 7种格式（TXT/HTML/MD/EPUB/MOBI/PDF/DOCX）

### 1.2 模块识别

| 分类 | 模块 | 状态 |
|------|------|------|
| 文本导入导出 | `exporter/engine.py`, `import_engine.py`, `recovery/engine.py` | ✅ 正常 |
| 大文本分块 | `context/budget.py` (ContextBudgetAllocator) | ⚠️ 有Bug |
| 上下文管理 | `context/budget.py`, `token_tracker.py` | ⚠️ 有Bug |
| 模型API调用 | `gacha/engine.py`, `model_router.py` | ⚠️ 有Bug |
| 进度保存 | `daemon.py`, `filesync.py`, `autosync.py` | 🔴 致命Bug |
| 多线程调度 | `agents/makefile.py`, `pipeline/novel_pipeline.py` | ⚠️ 有Bug |

---

## 二、P0 致命问题（7个）

### 🔴 P0-1: AutoSync 自动文件同步完全失效
**文件**: `kunlun/api/main.py:151-185`  
**严重程度**: 🔴 致命  
**影响**: 所有写操作（POST/PUT/DELETE）完成后无法触发自动文件同步。用户创作进度、偏好反馈、导出结果的数据一致性机制完全瘫痪。

**根因分析**:
```python
# main.py:154 — call_next 已消费请求体
response = await call_next(request)

# main.py:166 — 此时 body 已被 FastAPI 消费，await request.json() 永远失败
body = await request.json()
```

FastAPI 的 `call_next(request)` 在路由处理器内部将请求体反序列化为 Pydantic 模型，请求体流已被消费。后续的 `await request.json()` 必定失败（Starlette `request.body()` 只能读一次），被空的 `except Exception: pass` 静默吞噬。所有端点均未设置 `request.state.sync_data`，导致 fallback 路径也无效。

**修复建议**:
```python
# 方案A: 在路由处理器内部显式设置 sync_data
request.state.sync_data = {"book_id": book_id, "chapter": chapter}

# 方案B: 使用 FastAPI BackgroundTasks 替代中间件二次读取
# 方案C: 在路由处理器内直接调用 AutoSync.trigger()
```

---

### 🔴 P0-2: 36个异步测试全部因缺少 pytest-asyncio 而失败
**文件**: 测试套件全局  
**严重程度**: 🔴 致命  
**影响**: 所有异步测试（Gacha生成、消息总线端到端、Makefile管线、WebSocket广播、Society推演）均失败，错误信息: `"async def functions are not natively supported"`。这意味着核心功能（多模型抽卡、管线同步、消息通信）**从未在 CI 中真正运行过**。

**根因**: `pytest-asyncio` 未安装在 `requirements.txt` 中，异步测试需要此插件来支持 `@pytest.mark.asyncio` 装饰器。

**修复**:
```bash
pip install pytest-asyncio
# 并在 requirements.txt 中添加: pytest-asyncio>=0.24.0
```

---

### 🔴 P0-3: 守护进程任务泄漏（内存泄漏）
**文件**: `kunlun/api/routes.py:78, 89-90`  
**严重程度**: 🔴 致命  
**影响**: 守护进程崩溃后 `_daemon_tasks` 字典中的引用永远不会被清理。后台任务异常退出后，引擎对象残留内存，且 `/daemon/start` 会错误报告"守护进程已在运行"，导致用户无法重启。

**代码**:
```python
_daemon_tasks: dict[str, dict] = {}

@router.post("/daemon/start", ...)
async def daemon_start(...):
    if req.book_id in _daemon_tasks:
        return {"success": False, "error": "守护进程已在运行"}
    task = asyncio.create_task(engine.start())
    _daemon_tasks[req.book_id] = {"engine": engine, "task": task}
```

**问题**: 
1. 当 `engine.start()` 因异常退出时，task 完成但 `_daemon_tasks[req.book_id]` 仍保留
2. 没有 `task.add_done_callback()` 来自动清理
3. 没有定期健康检查机制

**修复**:
```python
task = asyncio.create_task(engine.start())
task.add_done_callback(lambda t: _daemon_tasks.pop(req.book_id, None))
```

---

### 🔴 P0-4: TokenTracker 死代码（不可达代码）
**文件**: `kunlun/token_tracker.py:130-134`  
**严重程度**: 🔴 致命  
**影响**: 代码逻辑错误 — `suggest_tier()` 方法中存在不可达代码，表明该方法可能未完成实现。更重要的是，`_chapter_budgets` 重复声明在不可达位置，提示可能缺少对特定情况的处理。

**代码**:
```python
def suggest_tier(self, mode, chapter_type, is_first_chapter):
    if is_first_chapter or ...:
        return "premium"
    if mode in ("gacha_parallel_3", "gacha_cascade"):
        return "standard"
    return "economy"
    # ⬇️ 以下代码永远不可达 —— 复制粘贴错误
    # 每章预算控制（运行期状态）
    self._chapter_budgets: dict[str, dict] = {}
```

---

### 🔴 P0-5: GachaEngine 客户端缓存无限增长（资源泄漏）
**文件**: `kunlun/gacha/engine.py:127, 175-188`  
**严重程度**: 🔴 致命  
**影响**: `_client_cache` 字典以 `(base_url, api_key)` 为键缓存 `AsyncOpenAI` 客户端。在长期运行的守护进程中，如果用户频繁切换模型配置，缓存无上限增长且无 TTL 过期机制，最终导致内存耗尽。

**代码**:
```python
self._client_cache: dict[tuple, AsyncOpenAI] = {}  # 无限的，无淘汰

async def _get_client_for_config(self, cfg):
    cache_key = (base_url, api_key)
    if cache_key not in self._client_cache:
        # 每次新配置都会新增，从不删除
        self._client_cache[cache_key] = AsyncOpenAI(...)
```

**修复**: 使用 `functools.lru_cache(maxsize=16)` 或定期清理旧的客户端连接。

---

### 🔴 P0-6: 导出模块中字符串 `replace` 误用导致 MOBI 路径错误
**文件**: `kunlun/exporter/engine.py:497`  
**严重程度**: 🔴 致命  
**影响**: MOBI 格式导出时，如果书名包含 `.epub` 字符串（如 `黑暗.epub传奇`），`str.replace()` 会错误替换书名中的 `.epub`，导致输出路径异常。

**代码**:
```python
mobi_path = epub_path.replace(".epub", ".mobi")  # 🔴 字符串替换，可能匹配书名中的.epub
```

**修复**:
```python
mobi_path = str(epub_path).rsplit(".epub", 1)[0] + ".mobi"
# 或使用 Path:
mobi_path = str(Path(epub_path).with_suffix(".mobi"))
```

---

### 🔴 P0-7: 管线上下文数据竞态（Polished Draft 空值传播）
**文件**: `kunlun/pipeline/novel_pipeline.py:306-308`  
**严重程度**: 🔴 致命  
**影响**: `_step_writer` 设置 `ctx.draft` 后，`_step_conflict` 和 `_step_vibe` 使用 `ctx.polished_draft or ctx.draft`。但如果 POLISH 步骤失败/跳过，`ctx.polished_draft` 保持空字符串 `""`，导致 fallback 到 `ctx.draft`。但如果 WRITER 未正确执行（draft 仍为 `""`），后续步骤（后写验证、审计、ICU）会在空输入上运行，产生错误报告并污染质量趋势数据。

**代码**:
```python
# _step_writer: ctx.draft = result.get("draft", "")
# _step_post_write: if not ctx.draft: return  # ✅ 有保护
# _step_audit: if not ctx.draft: return       # ✅ 有保护
# But:
# _step_conflict: draft = ctx.polished_draft or ctx.draft  # "" or "" = ""
```

**修复**: 在每个步骤开头统一检查 `ctx.polished_draft or ctx.draft` 非空。

---

## 三、P1 严重问题（13个）

### 🟠 P1-1: 管线步骤依赖顺序问题（Conflict在Writer之后但先检查polished）
**文件**: `kunlun/pipeline/novel_pipeline.py:309-342`  
**严重程度**: 🟠 严重  
**问题**: `_step_conflict` 在 `_step_writer` 之后、`_step_polish` 之前执行。此时检查 `ctx.polished_draft or ctx.draft`，其中 `polished_draft` 必然为空（尚未执行 POLISH）。虽然 fallback 到 draft 能正常工作，但这暴露了设计意图不清晰 — 冲突追踪应该在写后运行但使用原始草稿还是润色后草稿？

---

### 🟠 P1-2: 预算系统 token/character 单位混淆
**文件**: `kunlun/context/budget.py:106-131` 和 `kunlun/agents/writer.py:322-323`  
**严重程度**: 🟠 严重  
**问题**: Writer 中将 `budget * 1.5` 作为字符上限 (`char_limit`)，但 `ContextBudgetAllocator` 的 `get_segment_budget()` 返回的是 token 预算。中文约 1.5 char/token 的假设在混合英文、代码、特殊符号时严重不准确。过度截断会导致蓝图信息丢失。

**代码**:
```python
# writer.py:322
budget = allocator.get_segment_budget("current_blueprint")
char_limit = int(budget * 1.5)  # 🔴 1.5 对混合内容不准确
```

---

### 🟠 P1-3: API 导出端点返回类型不一致
**文件**: `kunlun/api/routes.py:811-812`  
**严重程度**: 🟠 严重  
**问题**: `export_chapter` 和 `export_book` 在错误情况下绕过 FastAPI 响应模型直接返回 `JSONResponse`，导致 OpenAPI 文档中的响应模型与实际不匹配，前端类型定义出现未预期的数据格式。

**代码**:
```python
if not rows or not rows[0].get("content"):
    return JSONResponse({"error": f"第{chapter}章未找到或未生成"}, status_code=404)
    # 🔴 应该 raise HTTPException(status_code=404, ...)
```

---

### 🟠 P1-4: SQLite 图存储缺少连接池和超时
**文件**: `kunlun/kg/client.py:193-210`  
**严重程度**: 🟠 严重  
**问题**: `_get_graph_conn()` 仅捕获 `sqlite3.ProgrammingError` 但未捕获 `sqlite3.OperationalError`（如 database is locked）。在高并发写入场景下，多个协程同时操作 SQLite 图可能导致 "database is locked" 错误。

**代码**:
```python
try:
    self._graph_conn.execute("SELECT 1")
except sqlite3.ProgrammingError:  # 🔴 未捕获 OperationalError
    ...
```

---

### 🟠 P1-5: 管线步骤处理器异常处理不一致
**文件**: `kunlun/pipeline/novel_pipeline.py:204-209`  
**严重程度**: 🟠 严重  
**问题**: `run()` 方法中只有 WRITER 和 AUDIT 步骤的失败会导致管线中止（return error）。ARCHITECT/PLANNER/SOCIETY 等步骤的失败被静默跳过（logged but continue）。这意味着蓝图生成失败后，Writer 会在空蓝图上生成，产生不可用的垃圾文本。

---

### 🟠 P1-6: 模型调用失败返回占位文本导致下游污染
**文件**: `kunlun/gacha/engine.py:386-389`  
**严重程度**: 🟠 严重  
**问题**: API 调用失败时返回 `"[deepseek-chat 生成失败]"` 作为占位文本。此文本会流入草稿 → 审计 → 润色 → 发布流程，且审计门禁将此文本视为正常内容评分。更严重的是，`_paragraph_mix` 会在此"文本"上运行 n-gram 评分并可能将其选为最优段落。

**修复**: 应在生成方法返回前检查是否为占位文本，并触发重试或向上传播异常。

---

### 🟠 P1-7: 大文本处理缺乏分页和流式保护
**文件**: `kunlun/gacha/engine.py:446-449`  
**严重程度**: 🟠 严重  
**问题**: `chat.completions.create(**api_kwargs)` 的 `max_tokens` 设置为 4096，但对于 60 万字的小说全文上下文，单次 API 调用可能因 prompt 过长而失败。上下文预算分配器仅为 Writer 预留 8000 token 的预算，对于长篇创作严重不足。

---

### 🟠 P1-8: WebSocket 连接无心跳超时机制
**文件**: `kunlun/api/ws_manager.py`（通过 routes.py:914-937）  
**严重程度**: 🟠 严重  
**问题**: WebSocket 端点接受 `ping` 消息并回复 `pong`，但服务端没有主动心跳检测。死连接（客户端断网但 TCP 未超时）会永久保留在连接池中。若 100+ 客户端连接后断网，`ws_manager` 的连接字典会堆积僵尸对象。

---

### 🟠 P1-9: 审核失败修订循环存在无限循环风险
**文件**: `kunlun/agents/makefile.py:397-429`  
**严重程度**: 🟠 严重  
**问题**: 修订循环的条件判断中存在 bug — 第399行检查 `auditor is None` 后才进入 while 循环，但如果 33维审计失败降级到 8门禁后 `auditor` 被赋值，而第一个 if 条件 `auditor is None` 为 False，导致不创建 Auditor。while 循环内调用 `auditor.execute()` 时 `auditor` 可能为 None。

**代码**:
```python
# 379: auditor = Auditor()
# 399: if auditor is None and not audit_result.get("passed"):  # auditor 不为 None
# 400:     auditor = Auditor()
# 401: while not audit_result.get("passed") and revision_count < 3:
# 411:     audit_result = await auditor.execute(...)  # auditor 可能是 None!
```

---

### 🟠 P1-10: 知识图谱入口 Cypher 注入保护不完整
**文件**: `kunlun/api/routes.py:402-408`  
**严重程度**: 🟠 严重  
**问题**: `/kg/query` 端点的写操作黑名单检查使用了 `kw in cypher_upper` 的简单子串匹配。攻击者可以通过在关键字之间插入注释 `CREATE /*comment*/ (n:Node)` 或使用 Unicode 同形异义字符绕过检查。

**修复**: 使用正则而非子串匹配，增加注释过滤。
```python
# 当前: "CREATE " in cypher_upper  # 可被 CREATE/*...*/绕过
# 应: re.search(r'\bCREATE\b', cypher_without_comments, re.IGNORECASE)
```

---

### 🟠 P1-11: Param Variator 存在历史重复检测碰撞
**文件**: `kunlun/gacha/param_variator.py`（通过 engine.py:207-213 调用）  
**严重程度**: 🟠 严重  
**问题**: `param_variator.get_params()` 使用 `hash(prompt) % 10000` 作为 chapter 参数。由于 Python 的 `hash()` 函数在每次进程重启后产生不同的值（PYTHONHASHSEED），重启后同样的 prompt 会产生不同的"章节号"，导致参数随机化不可复现。

**修复**: 使用 `hashlib.md5(prompt.encode()).hexdigest()` 或确定性哈希。

---

### 🟠 P1-12: Empty Draft 导致 33维审计崩溃
**文件**: `kunlun/audit/audit33.py`（通过 `novel_pipeline.py:429` 调用）  
**严重程度**: 🟠 严重  
**问题**: `_step_audit` 调用的 `auditor33.run_audit()` 在 `ctx.draft` 为空字符串时缺少保护（与 `_step_post_write` 不同，后者有 `if not ctx.draft: return`）。Pipeline 依赖 `PipelineStep.AUDIT` 作为中断条件，但如果 draft 为空，审计返回垃圾评分并错误标记为"通过"。

---

### 🟠 P1-13: ContextBudgetAllocator 截断逻辑在边界条件下静默丢失数据
**文件**: `kunlun/context/budget.py:124-131`  
**严重程度**: 🟠 严重  
**问题**: `truncate_to_budget()` 方法在 `effective_budget * 0.5` 范围内找不到句号时，不添加截断标记直接返回。对于全英文内容（无中文句号），所有句子边界都不会被检测到，截断变得不可预测。

---

## 四、中等问题（8个）

### 🟡 M-1: `validate_api_keys()` 已实现但从未被调用
**文件**: `kunlun/config.py:54-65`  
**问题**: 方法实现完整，但在 `main.py` 的 `lifespan` 中未调用。API 密钥缺失时只有静默警告（模拟模式），用户无从得知配置不完整。

### 🟡 M-2: 导出引擎 MOBI 章节统计可能为 0
**文件**: `kunlun/exporter/engine.py:482-527`  
**问题**: `_export_mobi` 在 calibre 不可用时返回 `chapter_count=0, total_words=0`，但实际章节存在。调用者无法区分"无章节"和"转换工具缺失"。

### 🟡 M-3: `WordCountGovernor` 的字数范围硬编码
**文件**: `kunlun/daemon.py:250-257`  
**问题**: `WORD_TARGET_RANGES` 仅覆盖 1000-6000 字，对于 8000+ 字的大章使用 `get_range()` 的 ±20% 推导。但 `get_range()` 和硬编码表逻辑不一致。

### 🟡 M-4: InProcessMessageBus 缺少背压保护
**文件**: `kunlun/agents/message_bus.py:48-71`  
**问题**: `publish()` 对所有匹配订阅者使用 `asyncio.gather()` 并发通知，无并发限制。在大量 Agent 场景下可导致协程爆炸。

### 🟡 M-5: Exporter._export_pdf 临时文件清理不可靠
**文件**: `kunlun/exporter/engine.py:598-601`  
**问题**: `finally` 块中的临时 HTML 清理仅删除成功生成的文件。若 `weasyprint.HTML.write_pdf()` 抛出异常，临时文件残留。

### 🟡 M-6: 测试 conftest 不重置 GachaEngine 单例
**文件**: `tests/conftest.py:15-29`  
**问题**: `reset_singletons()` 只重置了 `kg_client` 和 `embedder`，未重置 `gacha_engine`、`token_tracker`、`model_router` 等单例，导致测试间状态污染风险。

### 🟡 M-7: AgentMessage 使用 `time.time()` 作为默认工厂
**文件**: `kunlun/agents/base.py:32`  
**问题**: `timestamp: float = field(default_factory=time.time)` — 使用 `time.time()` 而非 `time.monotonic()`。系统时间调整会导致消息时间戳跳跃。

### 🟡 M-8: 错误消息中暴露内部路径
**文件**: 多处  
**问题**: 全局异常处理器在 `development` 模式下返回完整 traceback，其中包含用户文件系统路径。虽然开发模式可接受，但需要确认生产环境正确切换。

---

## 五、测试套件状态

| 指标 | 值 |
|------|-----|
| 总测试数 | 416 |
| 通过 | 379 (91.1%) |
| 失败 | 36 (8.7%) |
| 跳过 | 1 |
| 所有失败根因 | `pytest-asyncio` 缺失 |

### 建议操作
1. 安装 `pytest-asyncio` 并重新运行全部测试
2. 将 `pytest-asyncio` 加入 `requirements.txt`
3. 在 `conftest.py` 中重置 `gacha_engine` 和 `token_tracker` 等单例
4. 为 CI 配置 GitHub Actions 异步测试矩阵

---

## 六、架构问题总结

| 分类 | 问题数 | 最高严重度 |
|------|--------|------------|
| 数据一致性（AutoSync失效） | 1 | 🔴 致命 |
| 资源管理（内存泄漏） | 2 | 🔴 致命 |
| 测试基础设施 | 1 | 🔴 致命 |
| 并发安全 | 2 | 🟠 严重 |
| API/输入验证 | 2 | 🟠 严重 |
| 错误处理不一致 | 3 | 🟠 严重 |
| Token/上下文管理 | 2 | 🟠 严重 |
| 大文本处理 | 1 | 🟠 严重 |
| 代码质量 | 2 | 🔴 致命 |

---

## 七、修复优先级

### 立即修复（本周）
1. ✅ **[P0-2]** 安装 `pytest-asyncio` 并验证所有异步测试通过
2. ✅ **[P0-1]** 修复 AutoSync 中间件 — 改为在端点内显式调用
3. ✅ **[P0-4]** 删除 token_tracker.py 死代码
4. ✅ **[P0-3]** 为守护进程任务添加 `done_callback` 清理

### 高优先级（本月）
5. ✅ **[P1-9]** 修复 Makefile 修订循环中的 auditor None 问题
6. ✅ **[P0-5]** 为 `_client_cache` 添加 LRU 淘汰
7. ✅ **[P0-6]** 修复 MOBI 导出路径 `replace` 问题
8. ✅ **[P1-10]** 加固 KG Cypher 注入保护
9. ✅ **[P1-12]** 为 `auditor33.run_audit()` 添加空输入保护

### 中优先级（下个版本）
10. [P1-2] 上下文预算使用更准确的 token 计数
11. [P1-3] 统一 API 端点错误响应格式
12. [P1-7] 大文本处理的流式优化
13. [P1-8] WebSocket 添加心跳超时

---

## 八、正面发现

1. **降级策略完善**: 所有外部服务（Neo4j、Redis、NATS、Qdrant）都有完整的降级方案，核心功能不依赖任何外部服务
2. **审计体系完整**: 53 维多层审计 + 后写验证 + 质量看板，零 LLM 成本
3. **单例模式规范**: 全局单例使用模块级实例，避免了常见的 `__new__` 陷阱
4. **API 安全基础好**: Cypher 注入防护、参数验证、速率限制框架已就位
5. **文档完善**: 8 个文档文件覆盖架构/API/Agent/统计，中英文混合注释清晰
6. **Pipeline 设计优雅**: `PipelineMode` 枚举 + `PipelineContext` 数据类 + 步骤处理器映射的模式清晰可扩展
7. **代码风格一致**: dataclass、类型注解、loguru 日志在所有模块中一致使用

---

> **审计者**: Claude Code 自动化审计  
> **审计时间**: 2026-06-07  
> **总问题数**: 28 (7 P0 + 13 P1 + 8 M)

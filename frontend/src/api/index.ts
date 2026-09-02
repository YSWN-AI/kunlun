/**
 * 昆仑创作引擎 — API 客户端
 * 覆盖 47 个 v1 端点 + 50+ 个 v2 端点，统一错误处理
 *
 * 未来重构方向: 按领域拆分为独立模块
 *   src/api/
 *     index.ts      → 基础工具 (request/get/post/del/connectWS)
 *     books.ts      → 作品管理
 *     chapters.ts   → 章节/生成
 *     audit.ts      → 审计/质量
 *     kg.ts         → 知识图谱
 *     export.ts     → 导出
 *     config.ts     → 配置/参数/Prompt
 *     story-bible.ts → Story Bible
 *     publish.ts    → 发布引擎
 *     ...
 *
 * ═══════════════════════════════════════════════════════════════════
 * 方法清单 (47 端点, 含 v1 + v2)
 * ═══════════════════════════════════════════════════════════════════
 *
 * ✅ 活跃 (21) — 已在至少一个视图/Store 中调用:
 *   health   createBook   listBooks   deleteBook   initializeBook
 *   generateChapter   runAudit   listEntities   getBookStats
 *   exportChapter   exportBook   exportSubmission
 *   getUsage   getBookConfig   updateBookConfig   listGenres
 *   listPrompts   getParamDefs   getAllParams   setParam   rawRequest
 *
 * 📋 预留 (22) — 端点就绪，前端暂未接入:
 *   chat   editorChat   getBook   batchGenerate   getChapterContent
 *   kgQuery   getOverdueForeshadowing   getLatestSnapshot
 *   getSnapshot   getGachaModels   search   getPreferences
 *   recordFeedback   autoDeduceConfig   autoDeduceAllConfig
 *   getGenre   getPrompt   setPrompt   resetPrompt   getAgentParams
 *   daemonStart   daemonStop   orchestrate   listAgents
 *   getTruthStatus   autoFix   streamGenerateURL
 *
 * 🔧 工具函数:  request  get  post  del  connectWS
 * ═══════════════════════════════════════════════════════════════════
 */
import type {
  ApiResponse, Book, CreateBookRequest, Chapter, GenerateChapterResponse,
  BatchGenerateResponse, AuditResult, KGEntity, KGSnapshot,
  OverdueForeshadowing, BookConfig, Genre, PromptStatus, ModelParamDef,
  AgentParams, Preferences, UsageSummary, SystemStatus, ChatMessage,
  EditorChatResponse, SearchResult, AgentInfo, TruthStatus, AutoFixReport,
} from '../types/api'
import { API_BASE_URL, API_DEFAULT_TIMEOUT_MS } from '../constants'

const BASE = API_BASE_URL

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

type QueryValue = string | number | boolean
type QueryParams = Record<string, QueryValue>

async function request<T>(
  method: string,
  path: string,
  body?: Record<string, unknown>,
  queryParams?: QueryParams,
  timeoutMs: number = API_DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    let url = `${BASE}${path}`
    if (queryParams) {
      const qs = Object.entries(queryParams)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
      if (qs) url += `?${qs}`
    }
    const res = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
    const data = await res.json()
    if (!res.ok) throw new ApiError(res.status, data.detail || data.error || `请求失败: ${res.status}`)
    return data as T
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiError(408, `请求超时 (${timeoutMs / 1000}s)`)
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

function get<T>(path: string, params?: QueryParams) {
  return request<T>('GET', path, undefined, params)
}

function post<T>(path: string, body?: Record<string, unknown>, queryParams?: QueryParams) {
  return request<T>('POST', path, body, queryParams)
}

function del<T>(path: string) {
  return request<T>('DELETE', path)
}

export const api = {
  // ─── 健康检查 ───────────────────────────
  // ✅ 已在 AppShell/ABTest/Analysis/Drafts 中使用
  health: () => get<ApiResponse<SystemStatus>>('/status'),

  // ─── AI 对话 ───────────────────────────
  // 📋 预留: AI聊天接口 (前端AI对话面板待接入)
  chat: (messages: ChatMessage[], model = 'deepseek-chat', temperature = 0.7, maxTokens = 2048) =>
    post<ApiResponse<{ content: string; model: string; usage: Record<string, number> }>>('/chat', { messages, model, temperature, max_tokens: maxTokens }),

  // 📋 预留: 主编对话
  editorChat: (bookId: string, message: string, context?: Record<string, unknown>) =>
    post<EditorChatResponse>('/editor/chat', { book_id: bookId, message, context }),

  // ─── 作品管理 ───────────────────────────
  // ✅ book store/ImportView 使用
  createBook: (req: CreateBookRequest) =>
    post<ApiResponse>('/books/create', req as unknown as Record<string, unknown>),

  // ✅ book store/ExportView/ImportView 使用
  listBooks: () =>
    get<ApiResponse & { books: Book[] }>('/books/list'),

  // 📋 预留: 单作品查询
  getBook: (bookId: string) =>
    get<ApiResponse & { book: Book }>(`/books/${bookId}`),

  // ✅ book store 使用
  deleteBook: (bookId: string) =>
    del<ApiResponse>(`/books/${bookId}`),

  // ✅ book store 使用
  initializeBook: (bookId: string, baselineParams?: Record<string, unknown>) =>
    post<ApiResponse & { dimensions: string[] }>(`/books/${bookId}/initialize`, { baseline_params: baselineParams || {} }),

  // ─── 章节 ───────────────────────────────
  // ✅ book store 使用
  generateChapter: (bookId: string, chapter: number, mode = 'gacha_parallel_3', chapterType = 'normal') =>
    post<GenerateChapterResponse>(`/books/${bookId}/chapters/${chapter}/generate`, { mode, chapter_type: chapterType }),

  // 📋 预留: 批量生成
  batchGenerate: (bookId: string, start: number, end: number, mode = 'gacha_cascade', chapterType = 'normal') =>
    post<BatchGenerateResponse>(`/books/${bookId}/chapters/batch-generate`, undefined, { start, end, mode, chapter_type: chapterType }),

  // 📋 预留: 获取章节内容
  getChapterContent: (bookId: string, chapter: number) =>
    get<ApiResponse & { content: string; word_count: number; status: string }>(`/books/${bookId}/chapters/${chapter}/content`),

  // ─── 审计 ───────────────────────────────
  // ✅ AuditView 使用
  runAudit: (draft: string, chapter = 0, chapterType = 'normal') =>
    post<ApiResponse<AuditResult>>('/audit/run', { draft, chapter, chapter_type: chapterType }),

  // ─── 知识图谱 ───────────────────────────
  // 📋 预留: Cypher查询
  kgQuery: (cypher: string, params?: Record<string, unknown>) =>
    post<ApiResponse & { count: number; results: KGEntity[] }>('/kg/query', { cypher, params }),

  // ✅ WorldView 使用
  listEntities: (entityType: string, bookId = 'default', limit = 50) =>
    get<ApiResponse & { count: number; entities: KGEntity[] }>(`/kg/entities/${entityType}`, { book_id: bookId, limit }),

  // 📋 预留: 过期伏笔
  getOverdueForeshadowing: (bookId = 'default', currentChapter = 0) =>
    get<ApiResponse & { count: number; overdue: OverdueForeshadowing[] }>('/kg/foreshadowing/overdue', { book_id: bookId, current_chapter: currentChapter }),

  // ─── 快照 ───────────────────────────────
  // 📋 预留: 最新快照
  getLatestSnapshot: (bookId: string) =>
    get<ApiResponse & { data: KGSnapshot }>(`/books/${bookId}/snapshots/latest`),

  // 📋 预留: 指定快照
  getSnapshot: (bookId: string, snapshotId: string) =>
    get<ApiResponse & { data: any }>(`/books/${bookId}/snapshots/${snapshotId}`),

  // ─── 抽卡引擎 ───────────────────────────
  // 📋 预留: 获取模型列表
  getGachaModels: () =>
    get<ApiResponse & { data: { models: any } }>('/gacha/models'),

  // ─── 搜索 ───────────────────────────────
  // 📋 预留: 全文搜索
  search: (q: string, limit = 20) =>
    get<ApiResponse & { data: SearchResult }>('/search', { q, limit }),

  // ─── 全书统计 ───────────────────────────
  // ✅ book store/DashboardView 使用
  getBookStats: (bookId: string) =>
    get<ApiResponse & { data: any }>(`/books/${bookId}/stats`),

  // ─── 偏好学习 ───────────────────────────
  // 📋 预留: 偏好查询
  getPreferences: (bookId: string) =>
    get<ApiResponse & { data: Preferences }>(`/books/${bookId}/preferences`),

  // 📋 预留: 反馈记录
  recordFeedback: (bookId: string, feedback: string, rating: number) =>
    post<ApiResponse>(`/books/${bookId}/preferences/feedback`, undefined, { feedback, rating }),

  // ─── 导出 ───────────────────────────────
  // ✅ ExportView 使用
  exportChapter: (bookId: string, chapter: number, format = 'txt') =>
    get<ApiResponse & { format: string; path: string; word_count: number }>(`/books/${bookId}/chapters/${chapter}/export`, { format }),

  // ✅ ExportView 使用
  exportBook: (bookId: string, format = 'txt', scope = 'all', layout = 'standard') =>
    get<ApiResponse & { format: string; path: string; chapters: number; total_words?: number }>(`/books/${bookId}/export`, { format, scope, layout }),

  // ✅ ExportView 使用
  exportSubmission: (bookId: string) =>
    get<ApiResponse & { path: string; file_path: string; total_words?: number }>(`/books/${bookId}/export`, { format: 'submission' }),

  // ─── Token 用量 ─────────────────────────
  // ✅ DashboardView/SettingsView 使用
  getUsage: (bookId = 'default') =>
    get<ApiResponse & UsageSummary>(`/usage/${bookId}`),

  // ─── 配置 ───────────────────────────────
  // ✅ config store 使用
  getBookConfig: (bookId: string) =>
    get<ApiResponse & { config: BookConfig }>(`/config/${bookId}`),

  // ✅ config store 使用
  updateBookConfig: (bookId: string, updates: Record<string, unknown>) =>
    post<ApiResponse>(`/config/${bookId}`, updates),

  // 📋 预留: 单字段自动推导
  autoDeduceConfig: (bookId: string, field: string, hint = '') =>
    post<ApiResponse & { field: string; result: any }>(`/config/${bookId}/auto-deduce`, undefined, { field, hint }),

  // 📋 预留: 全量自动推导
  autoDeduceAllConfig: (bookId: string) =>
    post<ApiResponse & { auto_deduced: Record<string, unknown> }>(`/config/${bookId}/auto-deduce-all`),

  // ─── 体裁 ───────────────────────────────
  // ✅ config store 使用
  listGenres: () =>
    get<ApiResponse & { genres: Genre[] }>('/genres'),

  // 📋 预留: 单体裁查询
  getGenre: (name: string) =>
    get<ApiResponse & { genre: Genre }>(`/genres/${name}`),

  // ─── Prompt 管理 ─────────────────────────
  // ✅ config store/SettingsView 使用
  listPrompts: (bookId: string) =>
    get<ApiResponse & { prompts: PromptStatus[] }>(`/prompts/${bookId}`),

  // 📋 预留: 获取Agent Prompt
  getPrompt: (bookId: string, agent: string) =>
    get<ApiResponse & { content: string; source: string; has_override: boolean }>(`/prompts/${bookId}/${agent}`),

  // 📋 预留: 设置Prompt
  setPrompt: (bookId: string, agent: string, content: string) =>
    post<ApiResponse>(`/prompts/${bookId}/${agent}`, { content }),

  // 📋 预留: 重置Prompt
  resetPrompt: (bookId: string, agent: string) =>
    del<ApiResponse>(`/prompts/${bookId}/${agent}`),

  // ─── 模型参数 ───────────────────────────
  // ✅ config store 使用
  getParamDefs: () =>
    get<ApiResponse & { params: ModelParamDef[]; agents: string[] }>('/params/defs'),

  // ✅ config store 使用
  getAllParams: (bookId = 'default') =>
    get<ApiResponse & { params: Record<string, AgentParams> }>(`/params/${bookId}`),

  // 📋 预留: 获取Agent参数
  getAgentParams: (bookId: string, agent: string) =>
    get<ApiResponse & { params: AgentParams }>(`/params/${bookId}/${agent}`),

  // ✅ SettingsView 使用
  setParam: (bookId: string, param: string, value: number, agent: string) =>
    post<ApiResponse>(`/params/${bookId}/${param}`, { value, agent }),

  // ─── 守护进程 ───────────────────────────
  // 📋 预留: 启动守护
  daemonStart: (bookId: string) =>
    post<ApiResponse>('/daemon/start', { book_id: bookId, message: '' }),

  // 📋 预留: 停止守护
  daemonStop: (bookId: string) =>
    post<ApiResponse>('/daemon/stop', { book_id: bookId, message: '' }),

  // ─── 扩展端点 ───────────────────────────
  // 📋 预留: Vibe编排
  orchestrate: (intent: string) =>
    post<ApiResponse & { plan: any }>('/orchestrate', { intent }),

  // 📋 预留: Agent列表
  listAgents: () =>
    get<{ agents: AgentInfo[] }>('/agents'),

  // 📋 预留: Truth文件状态
  getTruthStatus: (bookId = 'default') =>
    get<TruthStatus>(`/truth-status?book_id=${bookId}`),

  // 📋 预留: 自动修复
  autoFix: () =>
    post<AutoFixReport>('/auto-fix'),

  // ─── 流式生成 (SSE) ─────────────────────
  // 📋 预留: SSE流式URL
  streamGenerateURL: (bookId: string, chapter: number, prompt = '', mode = 'single_fix', agent = 'writer') =>
    `${BASE}/stream/generate?book_id=${bookId}&chapter=${chapter}&prompt=${encodeURIComponent(prompt)}&mode=${mode}&agent=${agent}`,

  // ─── 通用请求（用于新增/自定义端点）───────
  // ✅ OrchestratorView/ImportView 使用
  rawRequest: <T>(path: string, options?: RequestInit) =>
    request<T>(options?.method || 'GET', path.replace(BASE, ''), options?.body ? JSON.parse(options.body as string) : undefined),
}

// WebSocket 连接工厂
export function connectWS(bookId: string, chapter: number): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host  // Vite proxy handles the rest
  const url = `${protocol}//${host}${BASE}/ws/${bookId}/${chapter}`
  return new WebSocket(url)
}

/** 昆仑创作引擎 — API 类型定义 */

// ─── 通用 ───────────────────────
export interface ApiResponse<T = any> {
  success: boolean
  error?: string
  message?: string
  data?: T
}

// ─── 作品 ───────────────────────
export interface Book {
  uid: string
  title: string
  genre: string
  description: string
  status: string
  created_at: string
  tags: string
  chapters?: number
  characters?: number
  total_words?: number
}

export interface CreateBookRequest {
  book_id: string
  title: string
  genre?: string
  description?: string
  tags?: string[]
  target_words?: number
}

// ─── 章节 ───────────────────────
export interface Chapter {
  num: number
  status: string
  word_count: number
  title?: string
  written_at?: string
  content?: string
}

export interface GenerateChapterResponse {
  success: boolean
  pipeline_id?: string
  chapter?: number
  chapter_type?: string
  draft?: string
  audit_passed?: boolean
  revisions?: number
  style_changes?: number
  gacha_best_model?: string
  audit_summary?: string
  kg_snapshot_id?: string
  error?: string
  message?: string
}

export interface BatchGenerateResponse {
  success: boolean
  total: number
  success_count: number
  results: { chapter: number; success: boolean; word_count: number; audit_passed?: boolean; error?: string }[]
}

// ─── 审计 ───────────────────────
export interface GateResult {
  level: 'PASS' | 'WARN' | 'FAIL'
  score: number
  detail: string
}

export interface AuditResult {
  passed: boolean
  fatal_count: number
  warn_count: number
  score?: number
  gates: Record<string, GateResult>
  [key: string]: any
}

// ─── 知识图谱 ───────────────────
export interface KGEntity {
  uid: string
  name: string
  entity_type: string
  description?: string
  book_id?: string
  chapter?: number
  created_at?: string
  updated_at?: string
  properties?: Record<string, unknown>
}

export interface KGSnapshot {
  snapshot_id: string
  book_id: string
  chapter: number
  entity_count: number
  relationship_count: number
  summary?: string
}

export interface OverdueForeshadowing {
  name: string
  status: string
  priority: number
  expected_chapter: number
  planted_chapter?: number
  [key: string]: any
}

// ─── 配置 ───────────────────────
export interface BookConfig {
  book_id: string
  title: string
  genre?: string
  description?: string
  target_words_per_chapter?: number
  chapters_planned?: number
  writing_style?: string
  narrative_perspective?: string
  audience?: string
  language?: string
  extra?: Record<string, unknown>
}

export interface Genre {
  key: string
  name: string
  description: string
  words_per_chapter: number
  pacing: string
  gate_weights: Record<string, number>
  [key: string]: any
}

export interface PromptStatus {
  agent: string
  source: string
  has_override: boolean
  preview: string
  length: number
}

export interface ModelParamDef {
  key: string
  label: string
  description: string
  default: number
  min: number
  max: number
  step: number
  agent_defaults: Record<string, number>
}

export interface AgentParams {
  [param_key: string]: number
}

// ─── 偏好学习 ───────────────────
export interface Preferences {
  book_id: string
  top_preferences: [string, number][]
  groups: {
    style: Record<string, number>
    narrative: Record<string, number>
    content: Record<string, number>
    structure: Record<string, number>
    gates: Record<string, number>
  }
  prompt_hints: string
}

// ─── Token ─────────────────────
export interface UsageSummary {
  total_tokens: number
  total_cost_usd: number
  calls: number
  by_agent: Record<string, { total_tokens: number; total_cost: number; calls: number }>
}

// ─── 守护进程 ───────────────────
export interface DaemonStatus {
  running: boolean
  book_id?: string
  chapters_written?: number
}

// ─── 系统状态 ───────────────────
export interface SystemStatus {
  kg: Record<string, unknown>
  embedder: Record<string, unknown>
}

// ─── AI 对话 ────────────────────
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface EditorChatResponse {
  success: boolean
  type?: string
  content?: string
  error?: string
}

// ─── 搜索 ──────────────────────
export interface SearchResult {
  query: string
  count: number
  results: { name: string; entity_type: string; rank: number; [key: string]: any }[]
}

// ─── Agent ─────────────────────
export interface AgentInfo {
  name: string
  description: string
}

// ─── 真相文件 ───────────────────
export interface TruthStatus {
  success: boolean
  files: string[]
  consistency_report?: Record<string, unknown>
  error?: string
}

// ─── 自动修复 ───────────────────
export interface AutoFixReport {
  scanned: number
  fixed: number
  errors?: string[]
}

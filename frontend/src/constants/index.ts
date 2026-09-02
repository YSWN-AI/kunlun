/**
 * 昆仑创作引擎 — 全局常量
 * 集中管理所有硬编码数值，消除魔法数字
 */

// ─── 响应式断点 ───────────────────────
export const BREAKPOINTS = {
  xs: 600,
  sm: 900,
  md: 1200,
  lg: 1600,
} as const

// ─── 布局尺寸 ─────────────────────────
export const ACTIVITY_BAR_WIDTH = 48

export const SIDEBAR = {
  minWidth: 180,
  maxWidth: 400,
  defaultWidth: 260,
} as const

export const RIGHT_PANEL = {
  minWidth: 200,
  maxWidth: 500,
  defaultWidth: 320,
} as const

// ─── UI 时间 ──────────────────────────
export const TOAST_DURATION_MS = 3500
export const PIPELINE_STEP_DELAY_MS = 600

// ─── 管线步骤 ─────────────────────────
export const PIPELINE_STEPS = [
  '意图分析', '大纲生成', '内容创作', '质量审计', '风格打磨', '快照保存',
] as const

// ─── 图标映射（统一 Toast + InlineNotice）──
export const TOAST_ICONS: Record<string, string> = {
  success: '✓',
  error: '✗',
  warning: '!',
  info: 'i',
  loading: '⟳',
  empty: '○',
} as const

// ─── API ──────────────────────────────
export const API_BASE_URL = '/api/v1'
export const API_DEFAULT_TIMEOUT_MS = 30_000

// ─── 滚动条 ───────────────────────────
export const SCROLLBAR = {
  width: 5,
  height: 5,
  thumbRadius: 3,
} as const

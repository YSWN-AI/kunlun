/**
 * 昆仑创作引擎 — UI 状态管理
 * 管理布局、面板、活动项、反馈系统
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: number
  message: string
  type: ToastType
}

export type ActivityId = 'write' | 'books' | 'dashboard' | 'world' | 'audit' | 'analysis' | 'abtest' | 'drafts' | 'pipeline' | 'settings' | 'export' | 'prompts' | 'import' | 'orchestrator'

export interface Activity {
  id: ActivityId
  label: string
  icon: string
  route: string
  badge?: number
}

export const ACTIVITIES: Activity[] = [
  { id: 'write', label: '创作中心', icon: 'edit', route: '/write' },
  { id: 'books', label: '作品管理', icon: 'book', route: '/books' },
  { id: 'dashboard', label: '仪表盘', icon: 'dashboard', route: '/dashboard' },
  { id: 'world', label: '世界设定', icon: 'globe', route: '/world' },
  { id: 'audit', label: '审计中心', icon: 'audit', route: '/audit' },
  { id: 'analysis', label: '分析中心', icon: 'pie-chart', route: '/analysis' },
  { id: 'abtest', label: 'A/B 测试', icon: 'experiment', route: '/abtest' },
  { id: 'drafts', label: '草稿管理', icon: 'history', route: '/drafts' },
  { id: 'pipeline', label: '管线监控', icon: 'apartment', route: '/pipeline' },
  { id: 'export', label: '导出中心', icon: 'export', route: '/export' },
  { id: 'prompts', label: '提示词库', icon: 'file-text', route: '/prompts' },
  { id: 'import', label: '导入中心', icon: 'import', route: '/import' },
  { id: 'orchestrator', label: '总调度', icon: 'robot', route: '/orchestrator' },
  { id: 'settings', label: '设置', icon: 'settings', route: '/settings' },
]

/** 简洁模式：只显示核心创作活动 */
export const SIMPLE_ACTIVITIES: Activity[] = [
  { id: 'write', label: '创作中心', icon: 'edit', route: '/write' },
  { id: 'books', label: '作品管理', icon: 'book', route: '/books' },
  { id: 'world', label: '世界设定', icon: 'globe', route: '/world' },
  { id: 'audit', label: '审计中心', icon: 'audit', route: '/audit' },
  { id: 'settings', label: '设置', icon: 'settings', route: '/settings' },
]

export const useUIStore = defineStore('ui', () => {
  const backendConnected = ref(false)
  const toasts = ref<Toast[]>([])
  let toastId = 0

  // 活动栏
  const activeActivity = ref<ActivityId>('write')

  // 侧边栏
  const sidebarVisible = ref(true)
  const sidebarWidth = ref(260)

  // 右侧面板
  const rightPanelVisible = ref(false)
  const rightPanelWidth = ref(320)

  // 状态栏
  const statusBarVisible = ref(true)

  // 简洁模式（自用推荐）
  const simpleMode = ref(true)

  // 响应式：是否移动端 (≤768px)
  const isMobile = ref(false)
  if (typeof window !== 'undefined') {
    const mq = window.matchMedia('(max-width: 768px)')
    const applyMobile = () => { isMobile.value = mq.matches }
    applyMobile()
    mq.addEventListener('change', applyMobile)
  }

  // 可见活动列表
  const visibleActivities = computed(() =>
    simpleMode.value ? SIMPLE_ACTIVITIES : ACTIVITIES
  )

  function setBackendStatus(connected: boolean) {
    backendConnected.value = connected
  }

  function showToast(message: string, type: ToastType = 'info') {
    const id = ++toastId
    toasts.value.push({ id, message, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 3500)
  }

  function dismissToast(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  // --- 活动栏 ---
  function setActivity(id: ActivityId) {
    activeActivity.value = id
  }

  // --- 侧边栏 ---
  function toggleSidebar() {
    sidebarVisible.value = !sidebarVisible.value
  }

  function setSidebarWidth(w: number) {
    sidebarWidth.value = Math.min(400, Math.max(180, w))
  }

  // --- 右侧面板 ---
  function toggleRightPanel() {
    rightPanelVisible.value = !rightPanelVisible.value
  }

  // --- 状态栏 ---
  function toggleStatusBar() {
    statusBarVisible.value = !statusBarVisible.value
  }

  // --- 简洁模式 ---
  function toggleSimpleMode() {
    simpleMode.value = !simpleMode.value
  }

  // 主内容区宽度计算
  const mainContentStyle = computed(() => {
    // 移动端侧栏改为覆盖式抽屉，不挤压内容区
    const sidebarW = sidebarVisible.value && !isMobile.value ? sidebarWidth.value : 0
    const rightW = rightPanelVisible.value && !isMobile.value ? rightPanelWidth.value : 0
    return {
      marginLeft: `${48 + sidebarW}px`,
      marginRight: `${rightW}px`,
    }
  })

  return {
    backendConnected,
    toasts,
    activeActivity,
    sidebarVisible,
    sidebarWidth,
    rightPanelVisible,
    rightPanelWidth,
    statusBarVisible,
    simpleMode,
    visibleActivities,
    mainContentStyle,
    isMobile,
    setBackendStatus,
    showToast,
    dismissToast,
    setActivity,
    toggleSidebar,
    setSidebarWidth,
    toggleRightPanel,
    toggleStatusBar,
    toggleSimpleMode,
  }
}, {
  persist: {
    paths: ['sidebarWidth', 'rightPanelVisible', 'sidebarVisible', 'simpleMode'],
  },
})

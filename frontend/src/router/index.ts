/**
 * 昆仑创作引擎 — 路由配置
 * 活动栏驱动导航，按功能模块分组
 */
import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUIStore } from '../stores/ui'
import type { ActivityId } from '../stores/ui'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/write',
  },
  {
    path: '/write',
    name: 'write',
    component: () => import('../views/write/WriteView.vue'),
    meta: { title: '创作中心', activity: 'write' },
  },
  {
    path: '/books',
    name: 'books',
    component: () => import('../views/books/BooksView.vue'),
    meta: { title: '作品管理', activity: 'books' },
  },
  {
    path: '/books/:id',
    name: 'book-detail',
    component: () => import('../views/books/BookDetailView.vue'),
    meta: { title: '作品详情', activity: 'books' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/dashboard/DashboardView.vue'),
    meta: { title: '仪表盘', activity: 'dashboard' },
  },
  {
    path: '/world',
    name: 'world',
    component: () => import('../views/world/WorldView.vue'),
    meta: { title: '世界设定', activity: 'world' },
  },
  {
    path: '/audit',
    name: 'audit',
    component: () => import('../views/audit/AuditView.vue'),
    meta: { title: '审计中心', activity: 'audit' },
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('../views/analysis/AnalysisView.vue'),
    meta: { title: '分析中心', activity: 'analysis' },
  },
  {
    path: '/abtest',
    name: 'abtest',
    component: () => import('../views/abtest/ABTestView.vue'),
    meta: { title: 'A/B 测试', activity: 'abtest' },
  },
  {
    path: '/drafts',
    name: 'drafts',
    component: () => import('../views/drafts/DraftView.vue'),
    meta: { title: '草稿管理', activity: 'drafts' },
  },
  {
    path: '/pipeline',
    name: 'pipeline',
    component: () => import('../views/pipeline/PipelineView.vue'),
    meta: { title: '管线监控', activity: 'pipeline' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/settings/SettingsView.vue'),
    meta: { title: '设置', activity: 'settings' },
  },
  {
    path: '/export',
    name: 'export',
    component: () => import('../views/export/ExportView.vue'),
    meta: { title: '导出中心', activity: 'export' },
  },
  {
    path: '/prompts',
    name: 'prompts',
    component: () => import('../views/prompts/PromptsView.vue'),
    meta: { title: '提示词管理', activity: 'prompts' },
  },
  {
    path: '/import',
    name: 'import',
    component: () => import('../views/import/ImportView.vue'),
    meta: { title: '导入中心', activity: 'import' },
  },
  {
    path: '/orchestrator',
    name: 'orchestrator',
    component: () => import('../views/orchestrator/OrchestratorView.vue'),
    meta: { title: '智能创作', activity: 'orchestrator' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：更新活动栏选中项
router.afterEach((to) => {
  if (to.meta?.activity) {
    useUIStore().setActivity(to.meta.activity as ActivityId)
  }
})

export default router

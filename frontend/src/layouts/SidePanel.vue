<template>
  <Transition name="slide-left">
    <aside
      v-if="sidebarVisible"
      class="side-panel no-select"
      :style="{ width: `${sidebarWidth}px` }"
    >
      <div class="side-panel__resize-handle" @mousedown="onResizeStart" />

      <div class="side-panel__header">
        <span class="side-panel__title">{{ panelTitle }}</span>
        <div class="side-panel__actions">
          <n-button text size="tiny" @click="$emit('toggle')">
            <template #icon><n-icon :size="16"><CloseOutlined /></n-icon></template>
          </n-button>
        </div>
      </div>

      <div class="side-panel__content">
        <component :is="activePanel" v-bind="panelProps" v-on="panelEmits" />
      </div>
    </aside>
  </Transition>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, shallowRef, watchEffect, type Component } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import { CloseOutlined } from '@vicons/antd'
import type { ActivityId } from '../stores/ui'
import { SIDEBAR } from '../constants'

const props = defineProps<{
  sidebarVisible: boolean
  sidebarWidth: number
  activeActivity: ActivityId
  chapters?: { num: number; status: string; word_count: number }[]
  currentChapter?: number
  books?: { uid: string; title: string; chapters?: number; total_words?: number }[]
  currentBookId?: string
}>()

const emit = defineEmits<{
  toggle: []
  'update:sidebarWidth': [w: number]
  'select-chapter': [num: number]
  'select-book': [id: string]
  'ai-action': [action: string]
  'reorder-chapters': [fromIndex: number, toIndex: number]
}>()

const panelMap: Partial<Record<ActivityId, ReturnType<typeof defineAsyncComponent>>> = {
  write:    defineAsyncComponent(() => import('./side-panels/SidePanelWrite.vue')),
  books:    defineAsyncComponent(() => import('./side-panels/SidePanelBooks.vue')),
  dashboard: defineAsyncComponent(() => import('./side-panels/SidePanelDashboard.vue')),
  world:    defineAsyncComponent(() => import('./side-panels/SidePanelWorld.vue')),
  audit:    defineAsyncComponent(() => import('./side-panels/SidePanelAudit.vue')),
  settings: defineAsyncComponent(() => import('./side-panels/SidePanelSettings.vue')),
  analysis: defineAsyncComponent(() => import('./side-panels/SidePanelAnalysis.vue')),
  abtest:   defineAsyncComponent(() => import('./side-panels/SidePanelABTest.vue')),
  drafts:   defineAsyncComponent(() => import('./side-panels/SidePanelDrafts.vue')),
  pipeline: defineAsyncComponent(() => import('./side-panels/SidePanelPipeline.vue')),
  export:   defineAsyncComponent(() => import('./side-panels/SidePanelExport.vue')),
  import:   defineAsyncComponent(() => import('./side-panels/SidePanelImport.vue')),
  prompts:  defineAsyncComponent(() => import('./side-panels/SidePanelPrompts.vue')),
  orchestrator: defineAsyncComponent(() => import('./side-panels/SidePanelOrchestrator.vue')),
}

const activePanel = shallowRef<Component | null>(null)
watchEffect(() => { activePanel.value = panelMap[props.activeActivity] ?? null })

const panelProps = computed(() => ({
  chapters: props.chapters,
  currentChapter: props.currentChapter,
  books: props.books,
  currentBookId: props.currentBookId,
}))

const panelEmits = computed(() => ({
  'select-chapter': (n: number) => emit('select-chapter', n),
  'select-book': (id: string) => emit('select-book', id),
  'ai-action': (a: string) => emit('ai-action', a),
  'reorder-chapters': (from: number, to: number) => emit('reorder-chapters', from, to),
}))

const panelTitle = computed(() => {
  const titles: Record<ActivityId, string> = {
    write: '创作工具', books: '作品列表', dashboard: '数据筛选',
    world: '世界观', audit: '审计历史', settings: '系统设置',
    analysis: '分析筛选', abtest: 'A/B测试', drafts: '草稿管理',
    pipeline: '管线监控', export: '快速导出', import: '导入来源',
    prompts: '提示词库', orchestrator: 'Vibe指令',
  }
  return titles[props.activeActivity] || ''
})

// 拖拽调整宽度
let resizeStartX = 0
let startWidth = 0
function onResizeStart(e: MouseEvent) {
  e.preventDefault()
  resizeStartX = e.clientX
  startWidth = props.sidebarWidth
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}
function onResizeMove(e: MouseEvent) {
  const newWidth = Math.min(SIDEBAR.maxWidth, Math.max(SIDEBAR.minWidth, startWidth + e.clientX - resizeStartX))
  emit('update:sidebarWidth', newWidth)
}
function onResizeEnd() {
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<style scoped>
.side-panel {
  position: fixed;
  top: 0;
  left: var(--activity-bar-width);
  height: 100%;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sidebar);
}
.side-panel__resize-handle {
  position: absolute; top: 0; right: -3px;
  width: 6px; height: 100%; cursor: col-resize; z-index: 10;
}
.side-panel__resize-handle:hover { background: var(--color-primary); opacity: 0.3; }
.side-panel__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) var(--space-3) var(--space-2); flex-shrink: 0;
}
.side-panel__title {
  font-size: var(--text-sm); font-weight: var(--font-semibold);
  color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.5px;
}
.side-panel__content {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
  gap: var(--space-3); padding: 0 var(--space-2) var(--space-2);
}
.panel-section { display: flex; flex-direction: column; }
.panel-section__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-2) var(--space-2);
}
.panel-section__title {
  font-size: var(--text-xs); font-weight: var(--font-semibold);
  color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.8px;
}
.panel-section__body { padding: 0 var(--space-2); }
.panel-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: 6px var(--space-2); border-radius: var(--radius-sm); cursor: pointer;
  transition: background var(--transition-fast); font-size: var(--text-sm); color: var(--color-text-secondary);
}
.panel-item:hover { background: var(--color-bg-overlay); color: var(--color-text-primary); }
.panel-item.active { background: var(--color-primary-suppl); color: var(--color-primary); }
.panel-item__icon { flex-shrink: 0; width: 16px; text-align: center; font-size: var(--text-xs); }
.panel-item__label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.panel-item__extra { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.panel-item__content { flex: 1; display: flex; flex-direction: column; gap: 2px; overflow: hidden; }
.panel-item__desc { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.panel-empty {
  padding: var(--space-4); text-align: center;
  font-size: var(--text-sm); color: var(--color-text-tertiary);
}

/* 移动端：侧栏转为覆盖式抽屉 */
@media (max-width: 768px) {
  .side-panel {
    box-shadow: var(--shadow-lg);
    max-width: calc(100vw - var(--activity-bar-width));
  }
  .side-panel__resize-handle { display: none; }
}
</style>

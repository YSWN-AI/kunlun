<template>
  <div class="draft-view">
    <div class="draft-view__header">
      <h2 class="draft-view__title">草稿管理</h2>
      <n-button size="small" @click="createSnapshot" :loading="creating" secondary>
        <template #icon><n-icon :size="16"><PlusOutlined /></n-icon></template>
        创建快照
      </n-button>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端服务未连接，展示演示数据" />

    <!-- 草稿列表 -->
    <SkeletonLoader v-if="loading" type="list" :count="5" />

    <div v-else class="draft-view__list">
      <n-card
        v-for="draft in drafts"
        :key="draft.id"
        :bordered="true"
        class="draft-card"
        size="small"
        :class="{ 'draft-card--active': draft.isActive }"
      >
        <div class="draft-card__left">
          <div class="draft-card__meta">
            <n-tag :type="draft.isActive ? 'success' : 'default'" :bordered="false" size="small">
              {{ draft.isActive ? '当前' : 'v' + draft.version }}
            </n-tag>
            <span class="draft-card__time">{{ draft.timestamp }}</span>
            <span class="draft-card__length">{{ draft.wordCount }} 字</span>
          </div>
          <p class="draft-card__preview">{{ draft.preview || '(空内容)' }}</p>

          <!-- Diff 对比 -->
          <div v-if="draft.showDiff && draft.diffLines" class="draft-card__diff">
            <p v-for="(line, li) in draft.diffLines" :key="li"
               :class="{ 'diff-added': line.type === 'added', 'diff-removed': line.type === 'removed' }">
              <span class="diff-prefix">{{ line.type === 'added' ? '+' : '-' }}</span>
              {{ line.text }}
            </p>
          </div>
        </div>

        <div class="draft-card__actions">
          <n-button size="tiny" @click="toggleDiff(draft)" quaternary>{{ draft.showDiff ? '隐藏' : '对比' }}</n-button>
          <n-button size="tiny" @click="restoreDraft(draft)" quaternary type="primary">恢复</n-button>
          <n-popconfirm @positive-click="deleteDraft(draft)">
            <template #trigger>
              <n-button size="tiny" quaternary type="error">删除</n-button>
            </template>
            确认删除此草稿版本？
          </n-popconfirm>
        </div>
      </n-card>

      <n-empty v-if="!drafts.length" description="暂无草稿快照" class="draft-view__empty" />
    </div>

    <!-- 统计摘要 -->
    <n-card v-if="stats.totalDrafts" :bordered="true" title="草稿统计" size="small" class="draft-view__stats">
      <n-grid :cols="4" :x-gap="16">
        <n-grid-item>
          <span class="stat-label">总快照数</span>
          <span class="stat-value">{{ stats.totalDrafts }}</span>
        </n-grid-item>
        <n-grid-item>
          <span class="stat-label">总字数变化</span>
          <span class="stat-value" :class="stats.wordChange > 0 ? 'positive' : 'negative'">
            {{ stats.wordChange > 0 ? '+' : '' }}{{ stats.wordChange }}
          </span>
        </n-grid-item>
        <n-grid-item>
          <span class="stat-label">最近快照</span>
          <span class="stat-value small">{{ stats.lastSnapshot }}</span>
        </n-grid-item>
        <n-grid-item>
          <span class="stat-label">可恢复版本</span>
          <span class="stat-value">{{ stats.restorableCount }}</span>
        </n-grid-item>
      </n-grid>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { PlusOutlined } from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import { api } from '../../api'

const ui = useUIStore()
const backendConnected = ref(false)
const loading = ref(true)
const creating = ref(false)

interface DiffLine {
  type: 'added' | 'removed'
  text: string
}

interface Draft {
  id: number
  version: number
  timestamp: string
  wordCount: number
  preview: string
  isActive: boolean
  showDiff: boolean
  diffLines?: DiffLine[]
}

const drafts = ref<Draft[]>([])
const stats = reactive({
  totalDrafts: 0,
  wordChange: 0,
  lastSnapshot: '--',
  restorableCount: 0,
})

function loadDrafts() {
  loading.value = true
  // 演示数据
  setTimeout(() => {
    const baseText = '夜色如墨，林玄盘膝坐在青石上，双目微阖。',
      mockDrafts: Draft[] = [
        { id: 1, version: 1, timestamp: '2026-06-11 14:30', wordCount: 0, preview: '', isActive: false, showDiff: false },
        { id: 2, version: 2, timestamp: '2026-06-11 14:45', wordCount: 380, preview: '夜色如墨，林玄盘膝坐在青石上，双目微阖。一缕若有若无的灵气从丹田升起...', isActive: false, showDiff: false },
        { id: 3, version: 3, timestamp: '2026-06-11 15:20', wordCount: 1560, preview: '夜色如墨，林玄盘膝坐在青石上，双目微阖。丹田之中灵气翻涌...', isActive: true, showDiff: false,
          diffLines: [
            { type: 'removed' as const, text: '一缕若有若无的灵气从丹田升起，沿着经脉缓缓流转...' },
            { type: 'added' as const, text: '丹田之中灵气翻涌，如江河奔腾。三年了，终于触摸到了那道门槛。' },
          ] },
        { id: 4, version: 4, timestamp: '2026-06-11 16:05', wordCount: 2100, preview: '夜色如墨，林玄盘膝坐在青石上。丹田之中灵气翻涌，如江河奔腾...', isActive: false, showDiff: false },
      ]

    drafts.value = mockDrafts
    stats.totalDrafts = mockDrafts.length
    stats.wordChange = 2100
    stats.lastSnapshot = '2026-06-11 16:05'
    stats.restorableCount = mockDrafts.length - 1
    loading.value = false
  }, 400)
}

function createSnapshot() {
  creating.value = true
  setTimeout(() => {
    ui.showToast('快照已创建', 'success')
    creating.value = false
  }, 300)
}

function toggleDiff(draft: Draft) {
  draft.showDiff = !draft.showDiff
}

function restoreDraft(draft: Draft) {
  drafts.value.forEach(d => d.isActive = false)
  draft.isActive = true
  ui.showToast(`已恢复到版本 ${draft.version}`, 'success')
}

function deleteDraft(draft: Draft) {
  drafts.value = drafts.value.filter(d => d.id !== draft.id)
  stats.totalDrafts = drafts.value.length
  ui.showToast(`版本 ${draft.version} 已删除`, 'info')
}

onMounted(() => {
  loadDrafts()
  api.health().then(() => { backendConnected.value = true }).catch((e: unknown) => { console.debug('health check failed', e) })
})
</script>

<style scoped>
.draft-view {
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
}
.draft-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.draft-view__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}
.draft-view__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
.draft-view__empty {
  margin-top: 40px;
}

.draft-card {
  transition: border-color 0.2s;
}
.draft-card--active {
  border-color: var(--color-success, #52c41a);
}
.draft-card__left {
  flex: 1;
}
.draft-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.draft-card__time {
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.draft-card__length {
  font-size: 12px;
  color: var(--color-text-tertiary);
  background: var(--color-bg-secondary);
  padding: 0 6px;
  border-radius: 3px;
}
.draft-card__preview {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 600px;
}
.draft-card__diff {
  margin-top: 8px;
  padding: 8px;
  background: var(--color-bg-secondary);
  border-radius: 4px;
  font-family: var(--font-family-mono, monospace);
  font-size: 12px;
  line-height: 1.6;
}
.draft-card__diff p {
  margin: 0;
}
.diff-added {
  color: #52c41a;
}
.diff-removed {
  color: #ff4d4f;
}
.diff-prefix {
  margin-right: 4px;
  font-weight: bold;
}
.draft-card__actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.draft-view__stats {
  margin-top: 16px;
}
.stat-label {
  display: block;
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.stat-value.small {
  font-size: 14px;
  font-weight: 400;
}
.stat-value.positive {
  color: #52c41a;
}
.stat-value.negative {
  color: #ff4d4f;
}
</style>

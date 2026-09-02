<template>
  <div class="pipeline-view">
    <div class="pipeline-view__header">
      <h2 class="pipeline-view__title">管线监控</h2>
      <n-space>
        <n-button size="small" @click="refreshPipelines" :loading="refreshing">
          <template #icon><n-icon :size="16"><ReloadOutlined /></n-icon></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端服务未连接，展示演示数据" />

    <!-- 当前运行状态 -->
    <n-card v-if="activePipeline" :bordered="true" class="pipeline-view__active" :class="{ 'pipeline--running': activePipeline.status === 'running' }">
      <template #header>
        <n-space align="center">
          <n-spin v-if="activePipeline.status === 'running'" :size="16" />
          <n-tag :type="statusTagType(activePipeline.status)" :bordered="false">
            {{ statusLabel(activePipeline.status) }}
          </n-tag>
          <span class="pipeline-title">{{ activePipeline.bookTitle || '未命名管线' }}</span>
        </n-space>
      </template>

      <!-- 进度条 -->
      <div class="pipeline-progress">
        <div class="pipeline-progress__info">
          <span>步骤 {{ activePipeline.currentStep }} / {{ activePipeline.totalSteps }}</span>
          <span>{{ activePipeline.progress }}%</span>
        </div>
        <n-progress
          type="line"
          :percentage="activePipeline.progress"
          :height="8"
          :color="activePipeline.status === 'running' ? C.primary : C.success"
          :border-radius="4"
          :indicator-placement="'inside'"
        />
      </div>

      <!-- 步骤列表 -->
      <div class="pipeline-steps">
        <div
          v-for="step in activePipeline.steps"
          :key="step.id"
          class="pipeline-step"
          :class="`pipeline-step--${step.status}`"
        >
          <div class="pipeline-step__indicator">
            <n-icon v-if="step.status === 'completed'" :size="16" :color="C.success"><CheckCircleOutlined /></n-icon>
            <n-icon v-else-if="step.status === 'running'" :size="16" :color="C.primary"><LoadingOutlined /></n-icon>
            <n-icon v-else-if="step.status === 'failed'" :size="16" :color="C.error"><CloseCircleOutlined /></n-icon>
            <span v-else class="pipeline-step__dot" />
          </div>
          <div class="pipeline-step__body">
            <span class="pipeline-step__name">{{ step.name }}</span>
            <span v-if="step.duration" class="pipeline-step__duration">{{ step.duration }}</span>
            <span v-if="step.error" class="pipeline-step__error">{{ step.error }}</span>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 历史记录 -->
    <SkeletonLoader v-if="loading" type="list" :count="4" />

    <n-card v-else class="pipeline-view__history" :bordered="true" title="历史运行记录" size="small">
      <n-data-table
        :columns="historyColumns"
        :data="historyList"
        :bordered="false"
        :single-line="false"
        size="small"
        :row-class-name="rowClassName"
      />
      <n-empty v-if="!historyList.length" description="暂无运行记录" class="pipeline-view__empty" />
    </n-card>

    <!-- 统计 -->
    <n-card v-if="pipelineStats.totalRuns" class="pipeline-view__stats" :bordered="true" title="运行统计" size="small">
      <n-grid :cols="4" :x-gap="16">
        <n-grid-item>
          <span class="stat-label">总运行次数</span>
          <span class="stat-value">{{ pipelineStats.totalRuns }}</span>
        </n-grid-item>
        <n-grid-item>
          <span class="stat-label">成功率</span>
          <span class="stat-value" :class="pipelineStats.successRate >= 80 ? 'positive' : 'negative'">
            {{ pipelineStats.successRate }}%
          </span>
        </n-grid-item>
        <n-grid-item>
          <span class="stat-label">平均耗时</span>
          <span class="stat-value">{{ pipelineStats.avgDuration }}</span>
        </n-grid-item>
        <n-grid-item>
          <span class="stat-label">Token 总量</span>
          <span class="stat-value">{{ pipelineStats.totalTokens?.toLocaleString() }}</span>
        </n-grid-item>
      </n-grid>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h } from 'vue'
import { ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import type { DataTableColumn } from 'naive-ui'
import { NTag } from 'naive-ui'

// 图表色板常量（与 tokens.css 中 --color-chart-* 保持一致）
const C = { primary: '#5B8FF9', success: '#52C41A', error: '#FF4D4F' }

const ui = useUIStore()
const backendConnected = ref(false)
const loading = ref(true)
const refreshing = ref(false)

interface PipelineStep {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  duration?: string
  error?: string
}

interface ActivePipeline {
  bookTitle: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  currentStep: number
  totalSteps: number
  steps: PipelineStep[]
}

interface HistoryRecord {
  id: string
  bookTitle: string
  chapter: number
  status: 'completed' | 'failed'
  duration: string
  timestamp: string
  tokens: number
}

const activePipeline = ref<ActivePipeline | null>(null)
const historyList = ref<HistoryRecord[]>([])
const pipelineStats = reactive({
  totalRuns: 0,
  successRate: 0,
  avgDuration: '--',
  totalTokens: 0,
})

const historyColumns: DataTableColumn<HistoryRecord>[] = [
  { title: '管线ID', key: 'id', width: 180, ellipsis: { tooltip: true } },
  { title: '作品', key: 'bookTitle', width: 120 },
  { title: '章节', key: 'chapter', width: 60 },
  {
    title: '状态', key: 'status', width: 80,
    render(row) {
      return h(NTag, { type: row.status === 'completed' ? 'success' : 'error', bordered: false, size: 'small' },
        { default: () => row.status === 'completed' ? '成功' : '失败' })
    },
  },
  { title: '耗时', key: 'duration', width: 80 },
  { title: 'Token', key: 'tokens', width: 80, render: (r: HistoryRecord) => r.tokens.toLocaleString() },
  { title: '时间', key: 'timestamp', width: 150 },
]

function rowClassName(row: HistoryRecord) {
  return row.status === 'failed' ? 'row--failed' : ''
}

function statusTagType(status: string) {
  return status === 'running' ? 'info' : status === 'completed' ? 'success' : 'error'
}

function statusLabel(status: string) {
  return status === 'running' ? '运行中' : status === 'completed' ? '已完成' : '失败'
}

function loadData() {
  loading.value = true
  setTimeout(() => {
    // 演示：当前运行中的管线
    activePipeline.value = {
      bookTitle: '星辰变',
      status: 'running',
      progress: 38,
      currentStep: 3,
      totalSteps: 8,
      steps: [
        { id: 'precheck', name: 'Pre-check 前置检查', status: 'completed', duration: '0.8s' },
        { id: 'architect', name: 'Architect 大纲调整', status: 'completed', duration: '2.3s' },
        { id: 'writer', name: 'Writer 正文生成', status: 'running', duration: '进行中...' },
        { id: 'audit', name: 'Audit 8门禁审计', status: 'pending' },
        { id: 'fix', name: 'Auto Fix 自动修复', status: 'pending' },
        { id: 'retention', name: 'Retention 追读力评估', status: 'pending' },
        { id: 'continuity', name: 'Continuity 连续性检查', status: 'pending' },
        { id: 'export', name: 'Export 导出', status: 'pending' },
      ],
    }

    // 演示：历史记录
    historyList.value = [
      { id: 'xcb_ch2', bookTitle: '星辰变', chapter: 1, status: 'completed', duration: '12.4s', timestamp: '2026-06-11 16:45', tokens: 3850 },
      { id: 'xcb_ch3', bookTitle: '星辰变', chapter: 2, status: 'completed', duration: '14.1s', timestamp: '2026-06-11 16:28', tokens: 4210 },
      { id: 'xcb_ch4', bookTitle: '星辰变', chapter: 3, status: 'failed', duration: '8.3s', timestamp: '2026-06-11 16:10', tokens: 1200 },
      { id: 'xcb_ch5', bookTitle: '星辰变', chapter: 3, status: 'completed', duration: '11.2s', timestamp: '2026-06-11 15:52', tokens: 3900 },
    ]

    pipelineStats.totalRuns = 4
    pipelineStats.successRate = 75
    pipelineStats.avgDuration = '12.8s'
    pipelineStats.totalTokens = 13160

    loading.value = false
  }, 500)
}

function refreshPipelines() {
  refreshing.value = true
  setTimeout(() => {
    refreshing.value = false
    ui.showToast('已刷新', 'success')
  }, 500)
}

loadData()
</script>

<style scoped>
.pipeline-view {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
}
.pipeline-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.pipeline-view__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}
.pipeline-view__empty {
  margin-top: 20px;
}

.pipeline-view__active {
  margin-bottom: 20px;
}
.pipeline-view__active.pipeline--running {
  border-color: #5B8FF9;
}
.pipeline-title {
  font-weight: 500;
}

.pipeline-progress {
  margin-bottom: 16px;
}
.pipeline-progress__info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.pipeline-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}
.pipeline-step:hover {
  background: var(--color-bg-hover);
}
.pipeline-step__indicator {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.pipeline-step__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
}
.pipeline-step--running .pipeline-step__dot {
  background: #5B8FF9;
  animation: pulse 1.5s infinite;
}
.pipeline-step--completed {
  color: var(--color-text-primary);
}
.pipeline-step--pending {
  opacity: 0.5;
}
.pipeline-step--failed {
  background: rgba(255, 77, 79, 0.06);
}
.pipeline-step__body {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.pipeline-step__name {
  font-size: 13px;
}
.pipeline-step__duration {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}
.pipeline-step__error {
  font-size: 12px;
  color: #ff4d4f;
  width: 100%;
}

.pipeline-view__history {
  margin-bottom: 16px;
}
:deep(.row--failed) {
  background: rgba(255, 77, 79, 0.04);
}

.pipeline-view__stats {
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
.stat-value.positive {
  color: #52c41a;
}
.stat-value.negative {
  color: #ff4d4f;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>

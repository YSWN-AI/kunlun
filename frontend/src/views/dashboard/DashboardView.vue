<template>
  <div class="dashboard-view">
    <div class="dashboard-view__header">
      <h2 class="dashboard-view__title">仪表盘</h2>
      <n-space>
        <n-button size="small" @click="refreshData" :loading="loading">
          <template #icon><n-icon :size="16"><ReloadOutlined /></n-icon></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端未连接，仅展示演示数据" />

    <!-- 骨架屏 -->
    <SkeletonLoader v-if="loading" type="cards" />

    <!-- 统计卡片 -->
    <div v-else class="dashboard-view__stats">
      <n-card v-for="stat in stats" :key="stat.label" class="stat-card" :bordered="true" size="small"
        :content-style="{ display: 'flex', alignItems: 'center', gap: '16px', padding: '16px' }">
        <div class="stat-card__icon" :style="{ color: `var(--color-chart-${stat.colorIndex})` }">
          <n-icon :size="24">
            <component :is="stat.icon" />
          </n-icon>
        </div>
        <div class="stat-card__body">
          <span class="stat-card__value">{{ stat.value }}</span>
          <span class="stat-card__label">{{ stat.label }}</span>
        </div>
      </n-card>
    </div>

    <!-- 图表区 -->
    <div class="dashboard-view__charts">
      <n-card class="chart-card" :bordered="true" title="字数趋势">
        <SkeletonLoader v-if="loading" type="chart" />
        <v-chart v-else :option="wordTrendOption" :autoresize="true" class="chart-instance" />
      </n-card>
      <n-card class="chart-card" :bordered="true" title="质量雷达图">
        <SkeletonLoader v-if="loading" type="chart" />
        <v-chart v-else :option="radarOption" :autoresize="true" class="chart-instance" />
      </n-card>
    </div>

    <!-- Token 用量 -->
    <n-card class="usage-card" :bordered="true" title="Token 用量">
      <SkeletonLoader v-if="loading" type="list" :count="3" />
      <div v-else class="usage-list">
        <div class="usage-item">
          <span class="usage-item__label">总 Token 数</span>
          <span class="usage-item__value">{{ (usage.totalTokens || 0).toLocaleString() }}</span>
        </div>
        <div class="usage-item">
          <span class="usage-item__label">总成本</span>
          <span class="usage-item__value">${{ (usage.totalCost || 0).toFixed(4) }}</span>
        </div>
        <div class="usage-item">
          <span class="usage-item__label">API 调用次数</span>
          <span class="usage-item__value">{{ (usage.calls || 0).toLocaleString() }}</span>
        </div>
      </div>
    </n-card>

    <!-- Demo Mode 标识 -->
    <div v-if="demoMode" class="demo-badge">Demo Mode</div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { NIcon, NCard } from 'naive-ui'
import {
  BookOutlined, FileTextOutlined, EditOutlined, CheckCircleOutlined, ReloadOutlined,
} from '@vicons/antd'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, RadarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
} from 'echarts/components'
import { api } from '../../api'
import { useBookStore } from '../../stores/book'
import { useUIStore } from '../../stores/ui'
import SkeletonLoader from '../../components/shared/SkeletonLoader.vue'
import InlineNotice from '../../components/shared/InlineNotice.vue'
import { useChartTheme } from '../../composables/useChartTheme'

const { palette } = useChartTheme()

use([CanvasRenderer, LineChart, BarChart, RadarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const bookStore = useBookStore()
const uiStore = useUIStore()
const backendConnected = uiStore.backendConnected
const loading = ref(true)
const demoMode = ref(false)

const totalBooks = ref(0)
const totalChapters = ref(0)
const totalWords = ref(0)
const auditPassRate = ref(0)

const stats = computed(() => [
  { label: '作品总数', value: totalBooks.value.toLocaleString(), icon: BookOutlined, colorIndex: 1 },
  { label: '总章节数', value: totalChapters.value.toLocaleString(), icon: FileTextOutlined, colorIndex: 2 },
  { label: '总字数', value: totalWords.value.toLocaleString(), icon: EditOutlined, colorIndex: 3 },
  { label: '审计通过率', value: auditPassRate.value ? `${auditPassRate.value}%` : '--', icon: CheckCircleOutlined, colorIndex: 4 },
])

const usage = reactive({
  totalTokens: 0,
  totalCost: 0,
  calls: 0,
})

// 字数趋势数据（按章节）
const wordTrendData = reactive<{ chapters: number[]; words: number[] }>({
  chapters: [],
  words: [],
})

// 质量雷达图数据
const radarData = reactive<{ dimensions: string[]; scores: number[] }>({
  dimensions: [],
  scores: [],
})

const wordTrendOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis' as const,
    backgroundColor: palette.value.tooltipBg,
    borderColor: palette.value.tooltipBorder,
    textStyle: { color: palette.value.tooltipText, fontSize: 12 },
    formatter: (params: any) => {
      const p = Array.isArray(params) ? params[0] : params
      return `第${p.axisValue}章<br/>字数: <b>${p.value.toLocaleString()}</b>`
    },
  },
  grid: { top: 20, right: 24, bottom: 30, left: 60 },
  xAxis: {
    type: 'category' as const,
    data: wordTrendData.chapters.map(c => `Ch.${c}`),
    axisLine: { lineStyle: { color: palette.value.axis } },
    axisTick: { show: false },
    axisLabel: { color: palette.value.text, fontSize: 11 },
  },
  yAxis: {
    type: 'value' as const,
    name: '字数',
    nameTextStyle: { color: palette.value.text, fontSize: 11 },
    axisLabel: {
      color: palette.value.text,
      fontSize: 11,
      formatter: (v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v,
    },
    splitLine: { lineStyle: { color: palette.value.split, type: 'dashed' as const } },
  },
  series: [{
    type: 'line' as const,
    data: wordTrendData.words,
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: { color: palette.value.series, width: 2 },
    itemStyle: { color: palette.value.series },
    areaStyle: {
      color: {
        type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: palette.value.seriesArea[0] },
          { offset: 1, color: palette.value.seriesArea[1] },
        ],
      },
    },
  }],
}))

const radarOption = computed(() => {
  const indicator = radarData.dimensions.map(d => ({ name: d, max: 100 }))
  return {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: palette.value.tooltipBg,
      borderColor: palette.value.tooltipBorder,
      textStyle: { color: palette.value.tooltipText, fontSize: 12 },
    },
    legend: {
      bottom: 0,
      textStyle: { color: palette.value.text, fontSize: 12 },
      data: ['当前值'],
    },
    radar: {
      center: ['50%', '48%'],
      radius: '65%',
      indicator,
      axisName: { color: palette.value.text, fontSize: 11 },
      splitArea: {
        areaStyle: { color: [palette.value.seriesArea[1], palette.value.seriesArea[1]] },
      },
      splitLine: { lineStyle: { color: palette.value.split } },
      axisLine: { lineStyle: { color: palette.value.axis } },
    },
    series: [{
      type: 'radar' as const,
      name: '当前值',
      data: [{ value: radarData.scores, name: '当前值' }],
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: palette.value.series, width: 2 },
      itemStyle: { color: palette.value.series },
      areaStyle: { color: palette.value.seriesArea2 },
    }],
  }
})

function generateDemoWordTrend() {
  // 生成 12 章的演示字数数据
  const words: number[] = []
  let base = 2500
  for (let i = 1; i <= 12; i++) {
    base += Math.floor(Math.random() * 800) - 200
    words.push(Math.max(1500, Math.min(5000, base)))
  }
  wordTrendData.chapters = Array.from({ length: 12 }, (_, i) => i + 1)
  wordTrendData.words = words
}

function generateDemoRadar() {
  radarData.dimensions = ['字数合规', '对话密度', '动作密度', '描写丰富度', '句式多样性', '节奏控制', '信息密度', '完整性']
  radarData.scores = [78, 65, 72, 58, 81, 69, 74, 85]
}

async function refreshData() {
  loading.value = true
  demoMode.value = false
  try {
    await bookStore.loadBooks()
    const books = bookStore.books
    let chSum = 0
    let wordSum = 0
    books.forEach(b => {
      chSum += b.chapters || 0
      wordSum += b.total_words || 0
    })
    totalBooks.value = books.length
    totalChapters.value = chSum
    totalWords.value = wordSum

    // 尝试加载真实仪表盘数据
    try {
      const u = await api.getUsage()
      usage.totalTokens = u.total_tokens || 0
      usage.totalCost = u.total_cost_usd || 0
      usage.calls = u.calls || 0
    } catch { demoMode.value = true }

    // 尝试从后端加载字数趋势和雷达数据
    if (books.length > 0) {
      try {
        const statsRes = await api.getBookStats(books[0].uid)
        if (statsRes?.data?.word_trend) {
          wordTrendData.chapters = statsRes.data.word_trend.map((w: any) => w.chapter)
          wordTrendData.words = statsRes.data.word_trend.map((w: any) => w.words)
        } else {
          generateDemoWordTrend()
          demoMode.value = true
        }
        if (statsRes?.data?.audit_pass_rate) {
          auditPassRate.value = Math.round(statsRes.data.audit_pass_rate)
        }
      } catch {
        generateDemoWordTrend()
        demoMode.value = true
      }
    } else {
      generateDemoWordTrend()
      demoMode.value = true
    }
    generateDemoRadar() // 雷达图暂用演示数据（后端 radar 端点需要 book_id）
  } catch {
    demoMode.value = true
    totalBooks.value = 2
    totalChapters.value = 15
    totalWords.value = 45280
    generateDemoWordTrend()
    generateDemoRadar()
  } finally {
    loading.value = false
  }
}

onMounted(() => { refreshData() })
</script>

<style scoped>
.dashboard-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.dashboard-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.dashboard-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.dashboard-view__stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

/* stat-card 横向排版由模板中的 content-style 控制，避免 :deep() + !important 对抗框架 */

.stat-card__icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  background: var(--color-bg-overlay);
}

.stat-card__body {
  display: flex;
  flex-direction: column;
}

.stat-card__value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.stat-card__label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.dashboard-view__charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.chart-card {
  min-height: 360px;
}

.chart-instance {
  width: 100%;
  height: 300px;
}

.usage-card {
  max-width: 600px;
}

.usage-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.usage-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
}
.usage-item__label {
  color: var(--color-text-tertiary);
}
.usage-item__value {
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
}

.demo-badge {
  position: fixed;
  bottom: 36px;
  right: var(--space-4);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-warning-suppl);
  color: var(--color-warning);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  letter-spacing: 1px;
}
</style>

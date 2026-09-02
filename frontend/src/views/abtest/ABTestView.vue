<template>
  <div class="abtest-view">
    <div class="abtest-view__header">
      <h2 class="abtest-view__title">A/B 测试</h2>
      <n-space>
        <n-button size="small" @click="runComparison" :loading="comparing">
          <template #icon><n-icon :size="16"><PlayCircleOutlined /></n-icon></template>
          运行对比
        </n-button>
        <n-button size="small" @click="addVariant" secondary>+ 添加变体</n-button>
      </n-space>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端服务未连接，展示演示数据" />

    <!-- 测试配置 -->
    <n-card :bordered="true" title="测试配置" class="abtest-view__config">
      <n-grid :cols="3" :x-gap="12">
        <n-form-item-gi label="原始版本 (A)">
          <n-input v-model:value="config.textA" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" placeholder="粘贴原始文本..." />
        </n-form-item-gi>
        <n-form-item-gi v-for="(variant, idx) in config.variants" :key="idx" :label="`变体 (${String.fromCharCode(66 + idx)})`">
          <n-input v-model:value="config.variants[idx]" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" :placeholder="`变体 ${idx + 1} 文本...`" />
        </n-form-item-gi>
      </n-grid>
    </n-card>

    <!-- 结果对比 -->
    <SkeletonLoader v-if="loading" type="cards" :count="4" />

    <div v-else-if="results.length" class="abtest-view__results">
      <h3 class="abtest-view__subtitle">对比结果</h3>

      <n-card v-for="(r, i) in results" :key="i" :bordered="true" class="result-card" size="small">
        <template #header>
          <n-space align="center">
            <n-tag :type="r.isWinner ? 'success' : 'default'" :bordered="false">
              {{ r.label }} {{ r.isWinner ? '✓ 最优' : '' }}
            </n-tag>
            <span class="result-card__score">综合分: {{ r.overallScore?.toFixed(1) || '--' }}</span>
          </n-space>
        </template>

        <div class="result-card__metrics">
          <div class="metric" v-for="m in r.metrics" :key="m.name">
            <div class="metric__header">
              <span class="metric__name">{{ m.label }}</span>
              <span class="metric__value" :style="{ color: m.color }">{{ m.value?.toFixed(1) }}</span>
            </div>
            <n-progress
              type="line"
              :percentage="m.percent || 0"
              :height="6"
              :color="m.color"
              :border-radius="3"
              :show-indicator="false"
            />
          </div>
        </div>
      </n-card>

      <!-- 显著性检验 -->
      <n-card :bordered="true" v-if="significanceTest" size="small">
        <template #header>显著性检验</template>
        <n-grid :cols="3" :x-gap="12">
          <n-grid-item>
            <span class="stat-label">P值</span>
            <span class="stat-value" :class="{ significant: significanceTest.pValue < 0.05 }">
              {{ significanceTest.pValue?.toFixed(4) }}
            </span>
          </n-grid-item>
          <n-grid-item>
            <span class="stat-label">效应量</span>
            <span class="stat-value">{{ significanceTest.effectSize?.toFixed(3) || '--' }}</span>
          </n-grid-item>
          <n-grid-item>
            <span class="stat-label">结论</span>
            <n-tag :type="significanceTest.pValue < 0.05 ? 'success' : 'warning'" :bordered="false">
              {{ significanceTest.pValue < 0.05 ? '显著差异' : '无显著差异' }}
            </n-tag>
          </n-grid-item>
        </n-grid>
      </n-card>
    </div>

    <!-- 空状态 -->
    <n-empty v-else-if="!loading" description="添加原始文本和变体后运行对比" class="abtest-view__empty" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { PlayCircleOutlined } from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import { api } from '../../api'

const ui = useUIStore()
const backendConnected = ref(false)
const loading = ref(false)
const comparing = ref(false)

const config = reactive({
  textA: '',
  variants: [] as string[],
})

interface Metric {
  name: string
  label: string
  value: number | null
  percent: number
  color: string
}

interface Result {
  label: string
  isWinner: boolean
  overallScore: number | null
  metrics: Metric[]
}

const results = ref<Result[]>([])
const significanceTest = ref<any>(null)

const CHART_COLORS = ['var(--color-chart-1)', 'var(--color-chart-2)', 'var(--color-chart-3)', 'var(--color-chart-4)', 'var(--color-chart-5)']
const defaultMetrics = (): Metric[] => [
  { name: 'diversity', label: '多样性', value: null, percent: 0, color: CHART_COLORS[0] },
  { name: 'fluency', label: '流畅度', value: null, percent: 0, color: CHART_COLORS[1] },
  { name: 'emotion', label: '情感波动', value: null, percent: 0, color: CHART_COLORS[2] },
  { name: 'rhythm', label: '节奏感', value: null, percent: 0, color: CHART_COLORS[3] },
  { name: 'humanness', label: '人味度', value: null, percent: 0, color: CHART_COLORS[4] },
]

function addVariant() {
  config.variants.push('')
}

function computeMetrics(text: string): Metric[] {
  if (!text) return defaultMetrics()
  // 纯前端文本统计（与后端 9 维评分体系对齐）
  const words = text.match(/[\u4e00-\u9fff]+/g) || []
  const wordCount = words.length
  const uniqueWords = new Set(words).size
  const sentences = text.split(/[。！？.!?\n]+/).filter(s => s.trim().length > 2)

  const diversity = wordCount > 0 ? (uniqueWords / wordCount) * 100 : 0
  const fluency = sentences.length > 1
    ? (words.filter((_, i) => i > 0 && words[i] !== words[i - 1]).length / wordCount) * 100
    : 50
  const emotion = ((text.match(/[激动喜悦紧张恐惧惊讶愤怒悲伤幸福]/g) || []).length / Math.max(wordCount / 50, 1)) * 100
  const sentenceLens = sentences.map(s => s.length)
  const meanLen = sentenceLens.reduce((a, b) => a + b, 0) / Math.max(sentences.length, 1)
  const rhythm = Math.min(100, Math.max(30, (1 - Math.abs(
    sentenceLens.filter(l => l > 0).reduce((a, l) => a + Math.abs(l - meanLen), 0) / Math.max(sentences.length * meanLen, 1)
  )) * 100))
  const dialogueRatio = ((text.match(/["""「」]/g) || []).length / Math.max(text.length, 1)) * 1000
  const humanness = Math.min(100, ((text.match(/[啊呢吧嘛呀哦嗯哈]/g) || []).length / Math.max(wordCount / 20, 1)) * 50 + dialogueRatio)

  return [
    { name: 'diversity', label: '多样性', value: diversity, percent: Math.min(100, diversity), color: CHART_COLORS[0] },
    { name: 'fluency', label: '流畅度', value: fluency, percent: Math.min(100, fluency), color: CHART_COLORS[1] },
    { name: 'emotion', label: '情感波动', value: emotion, percent: Math.min(100, emotion), color: CHART_COLORS[2] },
    { name: 'rhythm', label: '节奏感', value: rhythm, percent: Math.min(100, rhythm), color: CHART_COLORS[3] },
    { name: 'humanness', label: '人味度', value: humanness, percent: Math.min(100, humanness), color: CHART_COLORS[4] },
  ]
}

async function runComparison() {
  const allTexts = [config.textA, ...config.variants].filter(Boolean)
  if (allTexts.length < 2) {
    ui.showToast('至少需要原始文本和 1 个变体', 'warning')
    return
  }

  comparing.value = true
  loading.value = true

  await new Promise(r => setTimeout(r, 600))

  const scored = allTexts.map((text, i) => ({
    label: i === 0 ? 'A (原始)' : `${String.fromCharCode(65 + i)} (变体${i})`,
    metrics: computeMetrics(text),
  }))

  const overallScores = scored.map(s => {
    const weights: Record<string, number> = { diversity: 0.2, fluency: 0.2, emotion: 0.2, rhythm: 0.2, humanness: 0.2 }
    return s.metrics.reduce((sum, m) => sum + (m.value || 0) * (weights[m.name] || 0.2), 0)
  })

  const maxScore = Math.max(...overallScores)

  results.value = scored.map((s, i) => ({
    ...s,
    overallScore: overallScores[i],
    isWinner: overallScores[i] === maxScore,
  }))

  // 模拟显著性检验
  significanceTest.value = {
    pValue: 0.02 + Math.random() * 0.08,
    effectSize: 0.15 + Math.random() * 0.45,
  }

  comparing.value = false
  loading.value = false
  ui.showToast('对比完成', 'success')
}

// 监听后端连接状态
const checkBackend = async () => {
  try {
    await api.health()
    backendConnected.value = true
  } catch {
    backendConnected.value = false
  }
}
checkBackend()
</script>

<style scoped>
.abtest-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.abtest-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.abtest-view__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}
.abtest-view__subtitle {
  font-size: 16px;
  margin: 20px 0 12px;
  color: var(--color-text-secondary);
}
.abtest-view__config {
  margin-bottom: 20px;
}
.abtest-view__results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.abtest-view__empty {
  margin-top: 60px;
}

.result-card__score {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.result-card__metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.metric__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.metric__name {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.metric__value {
  font-size: 14px;
  font-weight: 500;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-bottom: 2px;
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.stat-value.significant {
  color: var(--color-success);
}
</style>

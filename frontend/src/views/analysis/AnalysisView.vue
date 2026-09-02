<template>
  <div class="analysis-view">
    <div class="analysis-view__header">
      <h2 class="analysis-view__title">分析中心</h2>
      <n-space>
        <n-button size="small" @click="runAnalysis" :loading="analyzing">
          <template #icon><n-icon :size="16"><PlayCircleOutlined /></n-icon></template>
          运行分析
        </n-button>
      </n-space>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端服务未连接，展示演示数据" />

    <!-- 选项卡：弧光 / 冲突 / 爽点 -->
    <n-tabs v-model:value="activeTab" type="segment" class="analysis-view__tabs">
      <n-tab-pane name="arc" tab="角色弧光">
        <!-- 弧光总览 -->
        <n-grid v-if="data.arc.characters.length" :cols="2" :x-gap="12" :y-gap="12">
          <n-grid-item v-for="char in data.arc.characters" :key="char.id">
            <n-card size="small" :bordered="true" :title="char.name" class="arc-card">
              <template #header-extra>
                <n-tag :type="arcStatusTag(char.status)" :bordered="false" size="small">
                  {{ arcStatusLabel(char.status) }}
                </n-tag>
              </template>

              <!-- 弧光进度 -->
              <div class="arc-card__progress">
                <span class="label">弧光进度</span>
                <n-progress :percentage="char.progress" :height="6" :color="char.progress < 30 ? CC.red : char.progress < 70 ? CC.yellow : CC.green" :border-radius="3" :show-indicator="false" />
              </div>

              <!-- 情感曲线 -->
              <div class="arc-card__emotions">
                <span class="label">情感曲线</span>
                <div class="emotion-bars">
                  <div v-for="e in char.emotions" :key="e.label" class="emotion-bar" :title="`${e.label}: ${e.value}%`">
                    <span class="emotion-bar__label">{{ e.label }}</span>
                    <div class="emotion-bar__track">
                      <div class="emotion-bar__fill" :style="{ width: e.value + '%', background: e.color }" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 转折点 -->
              <div class="arc-card__milestones">
                <span class="label">转折点</span>
                <div class="milestone-list">
                  <div v-for="m in char.milestones" :key="m.chapter" class="milestone">
                    <span class="milestone__ch">第{{ m.chapter }}章</span>
                    <span class="milestone__desc">{{ m.description }}</span>
                  </div>
                </div>
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>
        <n-empty v-else description="运行分析后查看角色弧光" class="analysis-view__empty" />
      </n-tab-pane>

      <n-tab-pane name="conflict" tab="冲突管理">
        <n-grid :cols="2" :x-gap="12" :y-gap="12">
          <!-- 冲突热度 -->
          <n-grid-item>
            <n-card size="small" :bordered="true" title="章节冲突热度">
              <div class="conflict-heatmap">
                <div v-for="ch in data.conflict.heatmap" :key="ch.chapter" class="heatmap-row">
                  <span class="heatmap-row__label">Ch.{{ ch.chapter }}</span>
                  <div class="heatmap-row__bar">
                    <div class="heatmap-row__fill"
                         :style="{ width: ch.intensity + '%', background: intensityColor(ch.intensity) }"
                    />
                  </div>
                  <span class="heatmap-row__value">{{ ch.intensity }}%</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>

          <!-- 冲突类型分布 -->
          <n-grid-item>
            <n-card size="small" :bordered="true" title="冲突类型分布">
              <div v-for="ct in data.conflict.types" :key="ct.name" class="conflict-type">
                <div class="conflict-type__header">
                  <span>{{ ct.label }}</span>
                  <span>{{ ct.count }}次</span>
                </div>
                <n-progress :percentage="ct.percent" :height="6" :color="ct.color" :border-radius="3" :show-indicator="false" />
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>

        <n-card size="small" :bordered="true" title="冲突状态追踪" class="analysis-view__section">
          <n-data-table
            :columns="conflictColumns"
            :data="data.conflict.states"
            :bordered="false"
            size="small"
          />
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="pleasure" tab="爽点分析">
        <n-grid :cols="3" :x-gap="12" :y-gap="12">
          <n-grid-item v-for="pp in data.pleasure.points" :key="pp.name" class="pleasure-card-wrapper">
            <n-card size="small" :bordered="true" class="pleasure-card">
              <div class="pleasure-card__icon" :style="{ background: pp.color }">{{ pp.icon }}</div>
              <div class="pleasure-card__name">{{ pp.label }}</div>
              <div class="pleasure-card__count">{{ pp.count }}次</div>
              <n-progress :percentage="pp.satisfaction" :height="4" :color="pp.color" :border-radius="2" :show-indicator="false" />
              <div class="pleasure-card__satisfaction">满意度 {{ pp.satisfaction }}%</div>
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- 疲劳度曲线 -->
        <n-card size="small" :bordered="true" title="爽点疲劳度" class="analysis-view__section">
          <div class="fatigue-timeline">
            <div v-for="f in data.pleasure.fatigue" :key="f.chapter" class="fatigue-point">
              <div class="fatigue-point__label">Ch.{{ f.chapter }}</div>
              <div class="fatigue-point__bar">
                <div class="fatigue-point__fill"
                     :style="{ width: f.fatigue + '%', background: f.fatigue > 70 ? CC.red : f.fatigue > 40 ? CC.yellow : CC.blue }"
                />
              </div>
              <div class="fatigue-point__value" :class="{ warning: f.fatigue > 70 }">{{ f.fatigue }}%</div>
            </div>
          </div>
        </n-card>

        <!-- 黄金三章检查 -->
        <n-card size="small" :bordered="true" title="黄金三章检查" class="analysis-view__section">
          <n-grid :cols="3" :x-gap="12">
            <n-grid-item v-for="check in data.pleasure.goldenChecks" :key="check.name">
              <div class="golden-check" :class="{ passed: check.passed, failed: !check.passed }">
                <n-icon :size="20" :color="check.passed ? '#52c41a' : '#ff4d4f'">
                  <CheckCircleOutlined v-if="check.passed" />
                  <CloseCircleOutlined v-else />
                </n-icon>
                <span class="golden-check__name">{{ check.label }}</span>
                <span class="golden-check__detail">{{ check.detail }}</span>
              </div>
            </n-grid-item>
          </n-grid>
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { PlayCircleOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import { api } from '../../api'
import type { DataTableColumn } from 'naive-ui'

const ui = useUIStore()
const backendConnected = ref(false)
const analyzing = ref(false)
const activeTab = ref('arc')

// 图表色板常量（与 tokens.css 中 --color-chart-* 保持一致）
const CC = {
  blue: '#5B8FF9',    // --color-chart-1
  green: '#5AD8A6',   // --color-chart-2
  yellow: '#F6BD16',  // --color-chart-3
  red: '#E86452',     // --color-chart-4
  purple: '#9270CA',  // --color-chart-5
  orange: '#FF9845',  // --color-chart-6
} as const

interface EmotionItem { label: string; value: number; color: string }
interface Milestone { chapter: number; description: string }
interface ArcCharacter {
  id: string; name: string; status: 'rising' | 'falling' | 'flat'
  progress: number; arcType: string
  emotions: EmotionItem[]
  milestones: Milestone[]
}

interface ConflictState { chapter: number; type: string; intensity: number; status: string; parties: string }

interface PleasurePoint { name: string; label: string; icon: string; color: string; count: number; satisfaction: number }
interface FatiguePointData { chapter: number; fatigue: number }
interface GoldenCheck { name: string; label: string; passed: boolean; detail: string }

const data = reactive({
  arc: {
    characters: [] as ArcCharacter[],
  },
  conflict: {
    heatmap: [] as { chapter: number; intensity: number }[],
    types: [] as { name: string; label: string; count: number; percent: number; color: string }[],
    states: [] as ConflictState[],
  },
  pleasure: {
    points: [] as PleasurePoint[],
    fatigue: [] as FatiguePointData[],
    goldenChecks: [] as GoldenCheck[],
  },
})

const conflictColumns: DataTableColumn<ConflictState>[] = [
  { title: '章节', key: 'chapter', width: 60 },
  { title: '冲突类型', key: 'type', width: 100 },
  { title: '强度', key: 'intensity', width: 70, render: (r: ConflictState) => `${r.intensity}%` },
  { title: '状态', key: 'status', width: 80 },
  { title: '涉及角色', key: 'parties', ellipsis: { tooltip: true } },
]

function arcStatusTag(s: string) {
  return s === 'rising' ? 'success' : s === 'falling' ? 'error' : 'default'
}
function arcStatusLabel(s: string) {
  return s === 'rising' ? '上升' : s === 'falling' ? '下降' : '平稳'
}
function intensityColor(v: number) {
  return v >= 80 ? CC.red : v >= 50 ? CC.yellow : CC.blue
}

async function runAnalysis() {
  analyzing.value = true

  await new Promise(r => setTimeout(r, 800))

  // 弧光数据
  data.arc.characters = [
    {
      id: '1', name: '林玄', status: 'rising', progress: 65, arcType: '英雄成长',
      emotions: [
        { label: '决心', value: 78, color: '#5B8FF9' },
        { label: '愤怒', value: 45, color: '#E86452' },
        { label: '喜悦', value: 32, color: '#F6BD16' },
        { label: '恐惧', value: 20, color: '#9270CA' },
        { label: '悲伤', value: 15, color: '#5AD8A6' },
      ],
      milestones: [
        { chapter: 3, description: '丹田突破，晋升练气期' },
        { chapter: 7, description: '宗门大比，初露锋芒' },
        { chapter: 12, description: '得知身世之谜，心态转变' },
      ],
    },
    {
      id: '2', name: '苏婉儿', status: 'falling', progress: 38, arcType: '悲剧弧光',
      emotions: [
        { label: '爱意', value: 55, color: '#F6BD16' },
        { label: '担忧', value: 60, color: '#9270CA' },
        { label: '坚强', value: 42, color: '#5B8FF9' },
        { label: '悲伤', value: 35, color: '#5AD8A6' },
        { label: '愤怒', value: 25, color: '#E86452' },
      ],
      milestones: [
        { chapter: 5, description: '被迫离开宗门' },
        { chapter: 9, description: '投入敌对势力' },
      ],
    },
  ]

  // 冲突数据
  data.conflict.heatmap = [
    { chapter: 1, intensity: 25 }, { chapter: 2, intensity: 40 }, { chapter: 3, intensity: 85 },
    { chapter: 4, intensity: 35 }, { chapter: 5, intensity: 60 }, { chapter: 6, intensity: 45 },
    { chapter: 7, intensity: 90 }, { chapter: 8, intensity: 30 }, { chapter: 9, intensity: 75 },
    { chapter: 10, intensity: 50 }, { chapter: 11, intensity: 55 }, { chapter: 12, intensity: 88 },
  ]
  data.conflict.types = [
    { name: 'person_vs_person', label: '人与人的冲突', count: 15, percent: 45, color: '#E86452' },
    { name: 'person_vs_self', label: '内心冲突', count: 8, percent: 24, color: '#9270CA' },
    { name: 'person_vs_society', label: '人与社会', count: 6, percent: 18, color: '#5B8FF9' },
    { name: 'person_vs_fate', label: '人与命运', count: 4, percent: 12, color: '#5AD8A6' },
  ]
  data.conflict.states = [
    { chapter: 3, type: '宗门冲突', intensity: 85, status: '已解决', parties: '林玄 vs 外门弟子' },
    { chapter: 7, type: '生死战', intensity: 90, status: '进行中', parties: '林玄 vs 反派长老' },
    { chapter: 12, type: '身份危机', intensity: 75, status: '发展中', parties: '林玄 vs 自身' },
  ]

  // 爽点数据
  data.pleasure.points = [
    { name: 'level_up', label: '升级突破', icon: '⚡', color: '#5B8FF9', count: 3, satisfaction: 85 },
    { name: 'face_slap', label: '打脸爽点', icon: '👊', color: '#E86452', count: 5, satisfaction: 92 },
    { name: 'gain_treasure', label: '获得宝物', icon: '💎', color: '#F6BD16', count: 2, satisfaction: 78 },
    { name: 'recognition', label: '被认可', icon: '🏆', color: '#5AD8A6', count: 4, satisfaction: 70 },
    { name: 'revenge', label: '复仇爽点', icon: '⚔️', color: '#9270CA', count: 1, satisfaction: 65 },
    { name: 'save_others', label: '救场爽点', icon: '🛡️', count: 3, satisfaction: 80, color: '#FF9845' },
  ]
  data.pleasure.fatigue = [
    { chapter: 1, fatigue: 10 }, { chapter: 2, fatigue: 15 }, { chapter: 3, fatigue: 55 },
    { chapter: 4, fatigue: 25 }, { chapter: 5, fatigue: 40 }, { chapter: 6, fatigue: 35 },
    { chapter: 7, fatigue: 80 }, { chapter: 8, fatigue: 30 }, { chapter: 9, fatigue: 60 },
    { chapter: 10, fatigue: 45 }, { chapter: 11, fatigue: 50 }, { chapter: 12, fatigue: 75 },
  ]
  data.pleasure.goldenChecks = [
    { name: 'hook', label: '开场钩子', passed: true, detail: '第1章300字内出现冲突' },
    { name: 'promise', label: '期待感建立', passed: true, detail: '明确力量体系和升级路径' },
    { name: 'first_pleasure', label: '首爽点', passed: false, detail: '第3章才出现首个爽点，建议提前至第1-2章' },
  ]

  analyzing.value = false
  ui.showToast('分析完成', 'success')
}

// 初始化时自动加载演示数据
runAnalysis()
api.health().then(() => { backendConnected.value = true }).catch((e: unknown) => { console.debug('health check failed', e) })
</script>

<style scoped>
.analysis-view {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}
.analysis-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.analysis-view__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}
.analysis-view__tabs {
  margin-top: 4px;
}
.analysis-view__empty {
  margin-top: 40px;
}
.analysis-view__section {
  margin-top: 16px;
}

/* 弧光卡片 */
.arc-card__progress {
  margin-bottom: 12px;
}
.arc-card__emotions {
  margin-bottom: 12px;
}
.arc-card__milestones {
  margin-bottom: 4px;
}
.label {
  display: block;
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.emotion-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.emotion-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.emotion-bar__label {
  width: 36px;
  font-size: 12px;
  color: var(--color-text-secondary);
  text-align: right;
}
.emotion-bar__track {
  flex: 1;
  height: 6px;
  background: var(--color-bg-secondary);
  border-radius: 3px;
  overflow: hidden;
}
.emotion-bar__fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.milestone-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.milestone {
  font-size: 12px;
}
.milestone__ch {
  color: var(--color-primary, #5B8FF9);
  font-weight: 500;
  margin-right: 6px;
}
.milestone__desc {
  color: var(--color-text-secondary);
}

/* 冲突热度 */
.conflict-heatmap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.heatmap-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.heatmap-row__label {
  width: 40px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.heatmap-row__bar {
  flex: 1;
  height: 10px;
  background: var(--color-bg-secondary);
  border-radius: 5px;
  overflow: hidden;
}
.heatmap-row__fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.4s ease;
}
.heatmap-row__value {
  width: 36px;
  font-size: 12px;
  color: var(--color-text-secondary);
  text-align: right;
}

.conflict-type {
  margin-bottom: 10px;
}
.conflict-type__header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 3px;
}

/* 爽点卡片 */
.pleasure-card-wrapper {
  min-width: 0;
}
.pleasure-card {
  text-align: center;
}
.pleasure-card__icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 8px;
  font-size: 18px;
}
.pleasure-card__name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}
.pleasure-card__count {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}
.pleasure-card__satisfaction {
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

/* 疲劳度 */
.fatigue-timeline {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.fatigue-point {
  flex: 1;
  min-width: 60px;
  text-align: center;
}
.fatigue-point__label {
  font-size: 11px;
  color: var(--color-text-tertiary);
}
.fatigue-point__bar {
  height: 4px;
  background: var(--color-bg-secondary);
  border-radius: 2px;
  margin: 4px 0;
  overflow: hidden;
}
.fatigue-point__fill {
  height: 100%;
  border-radius: 2px;
}
.fatigue-point__value {
  font-size: 12px;
  font-weight: 500;
}
.fatigue-point__value.warning {
  color: #E86452;
}

/* 黄金三章 */
.golden-check {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 4px;
  padding: 12px;
  border-radius: 8px;
  background: var(--color-bg-secondary);
}
.golden-check.passed {
  border: 1px solid rgba(82, 196, 26, 0.3);
}
.golden-check.failed {
  border: 1px solid rgba(255, 77, 79, 0.3);
}
.golden-check__name {
  font-weight: 500;
  font-size: 13px;
}
.golden-check__detail {
  font-size: 11px;
  color: var(--color-text-tertiary);
}
</style>

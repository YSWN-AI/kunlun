<template>
  <div class="settings-view">
    <div class="settings-view__header">
      <h2 class="settings-view__title">设置</h2>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端服务未连接，部分数据不可用" />

    <n-tabs v-model:value="activeTab" type="line" animated>
      <n-tab-pane name="general" tab="通用">
        <n-card :bordered="true" title="基本设置" size="small" class="settings-card">
          <div class="settings-group">
            <div class="settings-row">
              <span class="settings-row__label">后端地址</span>
              <span class="settings-row__value">http://127.0.0.1:8000</span>
            </div>
            <div class="settings-row">
              <span class="settings-row__label">连接状态</span>
              <n-tag :type="backendConnected ? 'success' : 'error'" size="small" :bordered="false">
                {{ backendConnected ? '已连接' : '未连接' }}
              </n-tag>
            </div>
            <div class="settings-row">
              <span class="settings-row__label">版本</span>
              <span class="settings-row__value">v0.2.0</span>
            </div>
          </div>
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="params" tab="模型参数">
        <div v-if="paramsLoading" class="settings-loading">加载中...</div>
        <n-card v-else :bordered="true" title="AI 模型参数" size="small" class="settings-card">
          <div v-if="paramDefs.length === 0" class="settings-empty">
            暂无参数定义
          </div>
          <div v-for="p in paramDefs" :key="p.key" class="settings-row">
            <div class="settings-row__header">
              <span class="settings-row__label">{{ p.label }}</span>
              <span class="settings-row__desc">{{ p.description }}</span>
            </div>
            <div class="settings-row__control">
              <n-slider
                :value="paramValues[p.key] ?? p.default"
                :min="p.min"
                :max="p.max"
                :step="p.step"
                :format-tooltip="(v: number) => v.toFixed(2)"
                @update:value="(v: number) => updateParam(p.key, v)"
              />
              <span class="settings-row__number">{{ (paramValues[p.key] ?? p.default).toFixed(2) }}</span>
            </div>
          </div>
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="prompts" tab="Prompt">
        <div v-if="promptsLoading" class="settings-loading">加载中...</div>
        <n-card v-else :bordered="true" title="Prompt 管理" size="small" class="settings-card">
          <div v-if="prompts.length === 0" class="settings-empty">
            暂无 Prompt 配置
          </div>
          <div v-for="pro in prompts" :key="pro.agent" class="settings-row">
            <span class="settings-row__label">{{ pro.agent }}</span>
            <n-tag :type="pro.has_override ? 'warning' : 'default'" size="small" :bordered="false">
              {{ pro.has_override ? '已自定义' : '默认' }}
            </n-tag>
            <span class="settings-row__value">{{ pro.length }} 字符</span>
          </div>
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="export" tab="导出">
        <n-card :bordered="true" title="导出选项" size="small" class="settings-card">
          <div class="settings-group">
            <div class="settings-row">
              <span class="settings-row__label">默认格式</span>
              <n-select v-model:value="exportFormat" :options="formatOptions" size="small" style="width: 140px" />
            </div>
            <div class="settings-row">
              <span class="settings-row__label">默认范围</span>
              <n-select v-model:value="exportScope" :options="scopeOptions" size="small" style="width: 140px" />
            </div>
          </div>
        </n-card>
      </n-tab-pane>

      <n-tab-pane name="usage" tab="用量统计">
        <div v-if="usageLoading" class="settings-loading">加载中...</div>
        <n-card v-else :bordered="true" title="API 用量" size="small" class="settings-card">
          <div class="usage-stats">
            <div class="usage-stat">
              <span class="usage-stat__value">{{ (usageData.totalTokens || 0).toLocaleString() }}</span>
              <span class="usage-stat__label">总 Token</span>
            </div>
            <div class="usage-stat">
              <span class="usage-stat__value">${{ (usageData.totalCost || 0).toFixed(4) }}</span>
              <span class="usage-stat__label">总成本</span>
            </div>
            <div class="usage-stat">
              <span class="usage-stat__value">{{ (usageData.calls || 0).toLocaleString() }}</span>
              <span class="usage-stat__label">调用次数</span>
            </div>
          </div>

          <!-- 按 Agent 细分 -->
          <div v-if="usageData.byAgent && Object.keys(usageData.byAgent).length" class="usage-by-agent">
            <h4 class="usage-by-agent__title">按 Agent 细分</h4>
            <div v-for="(agent, name) in usageData.byAgent" :key="name" class="settings-row">
              <span class="settings-row__label">{{ name }}</span>
              <span class="settings-row__value">
                {{ (agent.total_tokens || 0).toLocaleString() }} Token / ${{ (agent.total_cost || 0).toFixed(4) }} / {{ (agent.calls || 0).toLocaleString() }} 调用
              </span>
            </div>
          </div>
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { NTabs, NTabPane, NCard, NTag, NSlider, NSelect } from 'naive-ui'
import { useUIStore } from '../../stores/ui'
import { useConfigStore } from '../../stores/config'
import { api } from '../../api'
import type { ModelParamDef, PromptStatus, UsageSummary } from '../../types/api'
import InlineNotice from '../../components/shared/InlineNotice.vue'

const uiStore = useUIStore()
const configStore = useConfigStore()
const backendConnected = uiStore.backendConnected
const activeTab = ref('general')

// ─── 模型参数 ────────────────────
const paramDefs = ref<ModelParamDef[]>([])
const paramValues = reactive<Record<string, number>>({})
const paramsLoading = ref(false)

// ─── Prompt ──────────────────────
const prompts = ref<PromptStatus[]>([])
const promptsLoading = ref(false)

// ─── 导出 ────────────────────────
const exportFormat = ref('txt')
const exportScope = ref('all')

const formatOptions = [
  { label: '纯文本 (.txt)', value: 'txt' },
  { label: 'EPUB', value: 'epub' },
  { label: 'Markdown', value: 'md' },
]
const scopeOptions = [
  { label: '全书', value: 'all' },
  { label: '指定章节', value: 'chapters' },
]

// ─── 用量 ────────────────────────
const usageLoading = ref(false)
const usageData = reactive<{
  totalTokens: number
  totalCost: number
  calls: number
  byAgent: Record<string, { total_tokens: number; total_cost: number; calls: number }> | null
}>({
  totalTokens: 0,
  totalCost: 0,
  calls: 0,
  byAgent: null,
})

// ─── 方法 ────────────────────────
async function loadParams() {
  paramsLoading.value = true
  try {
    await configStore.loadParamDefs()
    paramDefs.value = configStore.paramDefs || []
    // 初始化当前值
    for (const p of paramDefs.value) {
      if (!(p.key in paramValues)) {
        paramValues[p.key] = p.default
      }
    }
  } catch {
    // demo 模式静默
  } finally {
    paramsLoading.value = false
  }
}

async function loadPrompts() {
  promptsLoading.value = true
  try {
    const res = await api.listPrompts('default')
    prompts.value = res.prompts || []
  } catch {
    // demo 模式静默
  } finally {
    promptsLoading.value = false
  }
}

async function loadUsage() {
  usageLoading.value = true
  try {
    const u = await api.getUsage()
    usageData.totalTokens = u.total_tokens || 0
    usageData.totalCost = u.total_cost_usd || 0
    usageData.calls = u.calls || 0
    usageData.byAgent = u.by_agent || null
  } catch {
    // demo 模式静默
  } finally {
    usageLoading.value = false
  }
}

async function updateParam(key: string, value: number) {
  paramValues[key] = value
  try {
    await api.setParam('default', key, value, 'default')
    uiStore.showToast('参数已更新', 'success')
  } catch (e: any) {
    uiStore.showToast(`参数更新失败: ${e.message}`, 'error')
  }
}

// ─── 初始化 ──────────────────────
onMounted(() => {
  loadParams()
  loadPrompts()
  loadUsage()
})
</script>

<style scoped>
.settings-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.settings-view__header {
  margin-bottom: var(--space-4);
}

.settings-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.settings-card {
  max-width: 680px;
}

.settings-group {
  display: flex;
  flex-direction: column;
}

.settings-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
}
.settings-row:last-child {
  border-bottom: none;
}

.settings-row__header {
  width: 180px;
  flex-shrink: 0;
}
.settings-row__label {
  display: block;
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}
.settings-row__desc {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}
.settings-row__control {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.settings-row__number {
  width: 48px;
  text-align: right;
  font-family: var(--font-family-mono);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
.settings-row__value {
  color: var(--color-text-primary);
}

.settings-empty,
.settings-loading {
  padding: var(--space-8);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 用量统计卡片 */
.usage-stats {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-bg-overlay);
  margin-bottom: var(--space-4);
}
.usage-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.usage-stat__value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}
.usage-stat__label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.usage-by-agent {
  padding-top: var(--space-2);
}
.usage-by-agent__title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2) 0;
}
</style>

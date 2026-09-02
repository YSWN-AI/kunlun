<template>
  <div class="audit-view">
    <div class="audit-view__header">
      <h2 class="audit-view__title">审计中心</h2>
      <n-button size="small" @click="runAudit" :loading="auditing">
        <template #icon><n-icon :size="16"><PlayCircleOutlined /></n-icon></template>
        运行审计
      </n-button>
    </div>

    <InlineNotice v-if="!backendConnected" type="warning" message="后端服务未连接" />

    <!-- 输入区 -->
    <n-card :bordered="true" class="audit-view__input" title="待审计文本">
      <n-input
        v-model:value="draftText"
        type="textarea"
        :autosize="{ minRows: 4, maxRows: 10 }"
        placeholder="粘贴或输入待审计的文本内容..."
      />
    </n-card>

    <!-- 审计结果 -->
    <n-card v-if="auditResult" :bordered="true" class="audit-view__result" title="审计结果">
      <template #header-extra>
        <n-tag :type="auditResult.passed ? 'success' : 'error'" :bordered="false">
          {{ auditResult.passed ? '通过' : '未通过' }}
        </n-tag>
      </template>

      <div class="audit-result__summary">
        <div class="audit-result__stat" v-if="auditResult.score !== undefined">
          <span class="audit-result__stat-value">{{ auditResult.score }}</span>
          <span class="audit-result__stat-label">综合评分</span>
        </div>
        <div class="audit-result__stat">
          <span class="audit-result__stat-value error">{{ auditResult.fatal_count }}</span>
          <span class="audit-result__stat-label">致命问题</span>
        </div>
        <div class="audit-result__stat">
          <span class="audit-result__stat-value warning">{{ auditResult.warn_count }}</span>
          <span class="audit-result__stat-label">警告</span>
        </div>
      </div>

      <!-- 各门结果 -->
      <div class="audit-result__gates" v-if="auditResult.gates">
        <div
          v-for="(gate, key) in auditResult.gates"
          :key="key"
          class="audit-result__gate"
          :class="`gate-${gate.level}`"
        >
          <div class="gate-header">
            <span class="gate-name">{{ key }}</span>
            <n-tag :type="gateLevelType(gate.level)" size="tiny" :bordered="false">
              {{ gate.level }}
            </n-tag>
          </div>
          <div class="gate-detail">{{ gate.detail }}</div>
          <n-progress
            type="line"
            :percentage="gate.score * 10"
            :height="3"
            :show-indicator="false"
            :color="gateProgressColor(gate.level)"
          />
        </div>
      </div>
    </n-card>

    <!-- 空状态 -->
    <div v-if="!auditResult && !auditing" class="audit-view__empty">
      <h3>审计等待中</h3>
      <p>输入文本并点击"运行审计"来检查内容质量。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NIcon, NCard, NInput, NTag, NProgress } from 'naive-ui'
import { PlayCircleOutlined } from '@vicons/antd'
import { api } from '../../api'
import { useUIStore } from '../../stores/ui'
import InlineNotice from '../../components/shared/InlineNotice.vue'

const uiStore = useUIStore()
const backendConnected = uiStore.backendConnected

const draftText = ref('')
const auditing = ref(false)
const auditResult = ref<any>(null)

function gateLevelType(level: string): 'success' | 'warning' | 'error' | 'info' {
  return level === 'PASS' ? 'success' : level === 'WARN' ? 'warning' : 'error'
}

function gateProgressColor(level: string): string {
  return level === 'PASS' ? 'var(--color-success)' : level === 'WARN' ? 'var(--color-warning)' : 'var(--color-error)'
}

async function runAudit() {
  if (!draftText.value.trim()) {
    uiStore.showToast('请输入待审计文本', 'warning')
    return
  }
  auditing.value = true
  try {
    const res = await api.runAudit(draftText.value)
    auditResult.value = res.data || res
    uiStore.showToast('审计完成', 'success')
  } catch (e: any) {
    uiStore.showToast(`审计失败: ${e.message}`, 'error')
  } finally {
    auditing.value = false
  }
}
</script>

<style scoped>
.audit-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.audit-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.audit-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.audit-view__input {
  margin-bottom: var(--space-4);
  max-width: 800px;
}

.audit-view__result {
  max-width: 800px;
}

.audit-result__summary {
  display: flex;
  gap: var(--space-6);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-bg-overlay);
}

.audit-result__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.audit-result__stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}
.audit-result__stat-value.error { color: var(--color-error); }
.audit-result__stat-value.warning { color: var(--color-warning); }

.audit-result__stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.audit-result__gates {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.audit-result__gate {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg-overlay);
}

.gate-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-1);
}

.gate-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.gate-detail {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
}

.audit-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  text-align: center;
}
.audit-view__empty h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}
.audit-view__empty p {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-top: var(--space-1);
}
</style>

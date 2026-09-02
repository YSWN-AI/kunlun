<script setup lang="ts">
/**
 * 管线监控侧边面板 — 步骤状态与干预工具
 */
import { ref } from 'vue'
import { NButton, NDivider, NTag, NSpace, NProgress } from 'naive-ui'
import { PauseCircleOutlined, PlayCircleOutlined, StepForwardOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string }>()
const emit = defineEmits<{ 'ai-action': [action: string] }>()

const pipelineSteps = ref([
  { step: 'SNAPSHOT', label: '快照', status: 'done' },
  { step: 'ARCHITECT', label: '蓝图', status: 'done' },
  { step: 'WRITER', label: '写作', status: 'running' },
  { step: 'CONFLICT', label: '冲突', status: 'pending' },
  { step: 'AUDIT', label: '审计', status: 'pending' },
  { step: 'POLISH', label: '润色', status: 'pending' },
])
const progress = ref(45)

const statusMap: Record<string, string> = { done: 'success', running: 'info', pending: 'default', failed: 'error' }
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">管线进度</span>
    </div>
    <div class="panel-section__body">
      <n-progress :percentage="progress" :height="4" :border-radius="2" style="margin-bottom:12px" />
      <div style="display:flex;flex-direction:column;gap:4px">
        <div
          v-for="s in pipelineSteps" :key="s.step"
          class="panel-item"
        >
          <span class="panel-item__icon">
            {{ s.status === 'done' ? '✅' : s.status === 'running' ? '🔄' : s.status === 'failed' ? '❌' : '⏳' }}
          </span>
          <span class="panel-item__label">{{ s.label }}</span>
          <ntag size="tiny" :type="statusMap[s.status] as any">{{ s.step }}</ntag>
        </div>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">管线控制</span>
    </div>
    <div class="panel-section__body">
      <n-button size="small" quaternary block @click="emit('ai-action', 'pause-pipeline')">
        <template #icon><n-icon size="14"><PauseCircleOutlined /></n-icon></template>
        暂停管线
      </n-button>
      <n-button size="small" quaternary block @click="emit('ai-action', 'resume-pipeline')" style="margin-top:4px">
        <template #icon><n-icon size="14"><PlayCircleOutlined /></n-icon></template>
        恢复管线
      </n-button>
      <n-button size="small" quaternary block @click="emit('ai-action', 'skip-step')" style="margin-top:4px">
        <template #icon><n-icon size="14"><StepForwardOutlined /></n-icon></template>
        跳过当前步骤
      </n-button>
    </div>
  </div>
</template>

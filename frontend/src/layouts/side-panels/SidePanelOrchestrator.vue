<script setup lang="ts">
/**
 * Vibe总调度侧边面板 — 快捷指令与意图历史
 */
import { ref } from 'vue'
import { NButton, NDivider, NTag } from 'naive-ui'
import { ThunderboltOutlined, MessageOutlined, ClearOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string }>()
const emit = defineEmits<{ 'ai-action': [action: string] }>()

const quickCommands = [
  { id: 'write', label: '写下一章', icon: '✍️' },
  { id: 'revise', label: '修改当前章', icon: '🔧' },
  { id: 'outline', label: '调整大纲', icon: '📋' },
  { id: 'character', label: '添加角色', icon: '👤' },
  { id: 'export', label: '导出全书', icon: '📦' },
]

const intentHistory = ref([
  { intent: '写作', detail: '继续写第42章', time: '20:15' },
  { intent: '修改', detail: '增强冲突感', time: '19:48' },
  { intent: '大纲', detail: '调整第三卷结构', time: '18:30' },
])

const intentColor: Record<string, string> = { '写作': 'info', '修改': 'warning', '大纲': 'default' }
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><ThunderboltOutlined /></n-icon> 快捷指令
      </span>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:4px">
        <div
          v-for="c in quickCommands" :key="c.id"
          class="panel-item"
          @click="emit('ai-action', `orchestrator:${c.id}`)"
        >
          <span class="panel-item__icon">{{ c.icon }}</span>
          <span class="panel-item__label">{{ c.label }}</span>
        </div>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><MessageOutlined /></n-icon> 意图历史
      </span>
      <n-button text size="tiny" @click="emit('ai-action', 'clear-orchestrator-history')">
        <template #icon><n-icon size="14"><ClearOutlined /></n-icon></template>
      </n-button>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:4px">
        <div v-for="(h, i) in intentHistory" :key="i" class="panel-item">
          <div class="panel-item__content">
            <span class="panel-item__label">{{ h.detail }}</span>
            <span class="panel-item__desc">{{ h.time }}</span>
          </div>
          <ntag size="tiny" :type="intentColor[h.intent] as any">{{ h.intent }}</ntag>
        </div>
      </div>
    </div>
  </div>
</template>

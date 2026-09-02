<script setup lang="ts">
import { NButton, NIcon, NSpin } from 'naive-ui'
import { CheckOutlined, RestOutlined, CloseOutlined, SplitCellsOutlined } from '@vicons/antd'

const props = defineProps<{
  isGenerating: boolean
  generationStatus: string
  generatedWordCount: number
  selectedModel: string
}>()

const emit = defineEmits<{
  'apply': []
  'retry': []
  'discard': []
  'split': []
}>()
</script>

<template>
  <div v-if="props.isGenerating" class="ai-generation-toolbar">
    <div class="ai-generation-toolbar__status">
      <n-spin :show="props.isGenerating" size="small" />
      <span>{{ props.generationStatus }}</span>
    </div>
    <div class="ai-generation-toolbar__actions">
      <n-button size="small" @click="emit('apply')">
        <template #icon><n-icon :size="14"><CheckOutlined /></n-icon></template>
        应用
      </n-button>
      <n-button size="small" @click="emit('retry')">
        <template #icon><n-icon :size="14"><RestOutlined /></n-icon></template>
        重试
      </n-button>
      <n-button size="small" @click="emit('discard')">
        <template #icon><n-icon :size="14"><CloseOutlined /></n-icon></template>
        丢弃
      </n-button>
      <n-button size="small" @click="emit('split')">
        <template #icon><n-icon :size="14"><SplitCellsOutlined /></n-icon></template>
        分段
      </n-button>
    </div>
    <div class="ai-generation-toolbar__info">
      <span>{{ props.generatedWordCount }} 字</span>
      <span class="divider">|</span>
      <span>{{ props.selectedModel }}</span>
    </div>
  </div>
</template>

<style scoped>
.ai-generation-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-top: var(--space-3);
}

.ai-generation-toolbar__status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
}

.ai-generation-toolbar__actions {
  display: flex;
  gap: var(--space-1);
}

.ai-generation-toolbar__info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.ai-generation-toolbar__info .divider {
  color: var(--color-border);
}
</style>

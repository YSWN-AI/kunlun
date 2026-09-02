<script setup lang="ts">
import { NButton, NSelect, NIcon, NDivider } from 'naive-ui'
import { MessageOutlined, BranchesOutlined } from '@vicons/antd'
import type { AiTool } from '@/types/write'

const props = defineProps<{
  aiTools: AiTool[]
  activeTool: string
  selectedModel: string
  modelOptions: any[]
}>()

const emit = defineEmits<{
  'select-tool': [tool: AiTool]
  'update:selectedModel': [value: string]
  'open-ai-chat': []
  'open-next-outline': []
}>()
</script>

<template>
  <div class="ai-toolbar">
    <div class="ai-toolbar__group">
      <n-button
        v-for="tool in props.aiTools"
        :key="tool.id"
        :type="props.activeTool === tool.id ? 'primary' : 'default'"
        size="small"
        @click="emit('select-tool', tool)"
      >
        <template #icon><n-icon :size="16"><component :is="tool.icon" /></n-icon></template>
        {{ tool.name }}
      </n-button>
    </div>
    <n-divider vertical />
    <div class="ai-toolbar__model-select">
      <n-select
        :value="props.selectedModel"
        :options="props.modelOptions"
        size="small"
        placeholder="选择模型"
        @update:value="emit('update:selectedModel', $event)"
      />
    </div>
    <n-divider vertical />
    <div class="ai-toolbar__actions">
      <n-button text size="small" @click="emit('open-ai-chat')">
        <template #icon><n-icon :size="16"><MessageOutlined /></n-icon></template>
        AI聊天
      </n-button>
      <n-button text size="small" @click="emit('open-next-outline')">
        <template #icon><n-icon :size="16"><BranchesOutlined /></n-icon></template>
        剧情推演
      </n-button>
    </div>
  </div>
</template>

<style scoped>
.ai-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
}

.ai-toolbar__group {
  display: flex;
  gap: 4px;
}

.ai-toolbar__model-select {
  width: 150px;
}

.ai-toolbar__actions {
  display: flex;
  gap: var(--space-1);
  margin-left: auto;
}
</style>

<script setup lang="ts">
import { NButton, NIcon, NTag } from 'naive-ui'
import { EditOutlined } from '@vicons/antd'
import type { Scene } from '@/types/write'

defineProps<{
  currentScene: Scene | null
}>()

const emit = defineEmits<{
  'edit-scene-summary': []
}>()
</script>

<template>
  <div v-if="currentScene" class="scene-card">
    <div class="scene-card__header">
      <span class="scene-card__title">场景摘要</span>
      <n-button text size="tiny" @click="emit('edit-scene-summary')">
        <template #icon><n-icon :size="12"><EditOutlined /></n-icon></template>
      </n-button>
    </div>
    <div class="scene-card__content">{{ currentScene.summary }}</div>
    <div class="scene-card__tags">
      <n-tag v-for="tag in currentScene.tags" :key="tag" size="small">{{ tag }}</n-tag>
    </div>
  </div>
</template>

<style scoped>
.scene-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin-bottom: var(--space-4);
}

.scene-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.scene-card__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

.scene-card__content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.scene-card__tags {
  display: flex;
  gap: var(--space-1);
}
</style>

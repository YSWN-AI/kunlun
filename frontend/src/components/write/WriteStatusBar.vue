<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { SkinOutlined } from '@vicons/antd'

defineProps<{
  totalWordCount: number
  currentChapterInfo: string
  saveStatus: string
  lastSaveTime: string
  connectionStatus: string
}>()
</script>

<template>
  <div class="write-status-bar">
    <div class="status-bar-left">
      <span class="status-item">字数: {{ totalWordCount }}</span>
      <span class="status-item">章节: {{ currentChapterInfo }}</span>
      <span class="status-item">状态: {{ saveStatus }}</span>
    </div>
    <div class="status-bar-right">
      <span class="status-item">{{ lastSaveTime }}</span>
      <span class="status-item">
        <n-icon :size="14"><SkinOutlined /></n-icon>
        {{ connectionStatus }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.write-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-1) var(--space-4);
  background: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.status-bar-left,
.status-bar-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>

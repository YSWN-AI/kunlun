<template>
  <Transition name="slide-right">
    <footer
      v-if="statusBarVisible"
      class="status-bar no-select"
    >
      <div class="status-bar__left">
        <span class="status-bar__item" :class="{ 'status-connected': backendConnected }">
          <span class="status-bar__dot" />
          {{ backendConnected ? '已连接' : '未连接' }}
        </span>
        <span class="status-bar__separator" />
        <span class="status-bar__item">{{ currentBookTitle || '未选择作品' }}</span>
        <template v-if="chapterInfo">
          <span class="status-bar__separator" />
          <span class="status-bar__item">第{{ chapterInfo.num }}章</span>
          <span class="status-bar__separator" />
          <span class="status-bar__item">{{ chapterInfo.wordCount || 0 }}字</span>
        </template>
      </div>
      <div class="status-bar__right">
        <span class="status-bar__item" v-if="lastSaved">
          <n-time :time="lastSaved" type="relative" />
        </span>
        <span class="status-bar__separator" />
        <button class="theme-toggle" @click="$emit('toggleTheme')" :title="isDark ? '切换到亮色主题' : '切换到暗色主题'">
          {{ isDark ? '☀️' : '🌙' }}
        </button>
        <span class="status-bar__separator" />
        <span class="status-bar__item">Ctrl+Shift+P 命令面板</span>
      </div>
    </footer>
  </Transition>
</template>

<script setup lang="ts">
import { NTime } from 'naive-ui'

defineProps<{
  statusBarVisible: boolean
  backendConnected: boolean
  currentBookTitle?: string
  chapterInfo?: { num: number; wordCount: number } | null
  lastSaved?: number | null
  isDark?: boolean
}>()

defineEmits<{
  toggleTheme: []
}>()
</script>

<style scoped>
.status-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--status-bar-height);
  background: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  z-index: var(--z-sidebar);
}

.status-bar__left,
.status-bar__right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-bar__item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-bar__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-disabled);
}
.status-bar__dot.status-connected,
.status-connected .status-bar__dot {
  background: var(--color-success);
}

.status-bar__separator {
  width: 1px;
  height: 12px;
  background: var(--color-border);
}

.theme-toggle {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  line-height: 1;
  transition: background 0.15s;
}
.theme-toggle:hover {
  background: var(--color-bg-overlay);
}

/* 移动端：缩小状态栏并隐藏命令面板快捷键提示 */
@media (max-width: 768px) {
  .status-bar {
    font-size: var(--text-xs);
    padding: 0 var(--space-2);
    gap: 4px;
  }
  .status-bar__right .status-bar__item:last-child {
    display: none;
  }
}
</style>

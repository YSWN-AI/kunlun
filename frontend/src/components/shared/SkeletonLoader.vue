<template>
  <div class="skeleton-container" :style="{ padding: padding[type] }">
    <!-- 列表骨架 -->
    <template v-if="type === 'list'">
      <div v-for="i in count" :key="i" class="skeleton-row">
        <div class="skeleton-avatar skeleton-pulse" />
        <div class="skeleton-lines">
          <div class="skeleton-line skeleton-pulse" style="width: 60%" />
          <div class="skeleton-line skeleton-pulse" style="width: 40%" />
        </div>
      </div>
    </template>

    <!-- 卡片骨架 -->
    <template v-if="type === 'cards'">
      <div class="skeleton-cards">
        <div v-for="i in count" :key="i" class="skeleton-card skeleton-pulse" />
      </div>
    </template>

    <!-- 编辑器骨架 -->
    <template v-if="type === 'editor'">
      <div class="skeleton-editor">
        <div class="skeleton-line skeleton-pulse" style="width: 30%; height: 24px; margin-bottom: 8px" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%" />
        <div class="skeleton-line skeleton-pulse" style="width: 92%" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%" />
        <div class="skeleton-line skeleton-pulse" style="width: 48%" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%; margin-top: 16px" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%" />
        <div class="skeleton-line skeleton-pulse" style="width: 76%" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%" />
        <div class="skeleton-line skeleton-pulse" style="width: 88%" />
      </div>
    </template>

    <!-- 图表骨架 -->
    <template v-if="type === 'chart'">
      <div class="skeleton-chart skeleton-pulse" />
    </template>

    <!-- 表单骨架 -->
    <template v-if="type === 'form'">
      <div v-for="i in count" :key="i" class="skeleton-form-row">
        <div class="skeleton-line skeleton-pulse" style="width: 20%; height: 14px" />
        <div class="skeleton-line skeleton-pulse" style="width: 100%; height: 32px" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
export type SkeletonType = 'list' | 'cards' | 'editor' | 'chart' | 'form'

withDefaults(defineProps<{
  type?: SkeletonType
  count?: number
}>(), {
  type: 'list',
  count: 4,
})

const padding: Record<SkeletonType, string> = {
  list: 'var(--space-4)',
  cards: 'var(--space-4)',
  editor: 'var(--space-6)',
  chart: 'var(--space-4)',
  form: 'var(--space-4)',
}
</script>

<style scoped>
.skeleton-container { width: 100%; }

.skeleton-pulse {
  background: linear-gradient(90deg, var(--color-bg-overlay) 25%, var(--color-border) 50%, var(--color-bg-overlay) 75%);
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}
.skeleton-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}
.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.skeleton-line {
  height: 14px;
  border-radius: var(--radius-sm);
}

.skeleton-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}
.skeleton-card {
  height: 120px;
  border-radius: var(--radius-lg);
}

.skeleton-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 800px;
}

.skeleton-chart {
  width: 100%;
  height: 280px;
  border-radius: var(--radius-lg);
}

.skeleton-form-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
</style>

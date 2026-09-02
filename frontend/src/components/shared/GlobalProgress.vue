<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="active" class="global-progress__bar">
        <div class="global-progress__track" :style="{ width: `${percent}%`, background: color }" />
        <span class="global-progress__label">{{ label }}</span>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  active?: boolean
  percent?: number
  label?: string
  color?: string
}>()
</script>

<style scoped>
.global-progress__bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: transparent;
  z-index: var(--z-toast);
}

.global-progress__track {
  height: 100%;
  transition: width var(--transition-normal);
}

.global-progress__label {
  position: absolute;
  right: var(--space-4);
  top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-elevated);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}
</style>

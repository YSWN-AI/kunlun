<template>
  <Transition name="fade-slide">
    <div v-if="visible" class="inline-notice" :class="`inline-notice--${type}`">
      <span class="inline-notice__icon">{{ icons[type] }}</span>
      <span class="inline-notice__text">{{ message }}</span>
      <n-button
        v-if="action"
        text
        size="tiny"
        type="primary"
        @click="$emit('action')"
      >
        {{ action.label }}
      </n-button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'

export interface InlineNoticeProps {
  visible?: boolean
  type?: 'loading' | 'error' | 'empty' | 'success' | 'info' | 'warning'
  message?: string
  action?: { label: string }
}

withDefaults(defineProps<InlineNoticeProps>(), {
  type: 'info',
})

defineEmits<{ action: [] }>()

const icons: Record<string, string> = {
  loading: '⟳',
  error: '✗',
  empty: '○',
  success: '✓',
  info: 'i',
}
</script>

<style scoped>
.inline-notice {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}

.inline-notice--info {
  background: var(--color-primary-suppl);
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.inline-notice--success {
  background: var(--color-success-suppl);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.inline-notice--warning,
.inline-notice--loading {
  background: var(--color-warning-suppl);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.inline-notice--error {
  background: var(--color-error-suppl);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.inline-notice--empty {
  background: var(--color-bg-overlay);
  color: var(--color-text-tertiary);
  border: 1px dashed var(--color-border);
}

.inline-notice__icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
}
.inline-notice--loading .inline-notice__icon {
  animation: spin 1s linear infinite;
}
.inline-notice__text {
  flex: 1;
}
</style>

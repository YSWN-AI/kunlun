<script setup lang="ts">
/**
 * 提示词库侧边面板 — Prompt 分类与快捷操作
 */
import { ref } from 'vue'
import { NButton, NDivider, NInput } from 'naive-ui'
import { SearchOutlined, PlusOutlined, StarOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string }>()
const emit = defineEmits<{ 'ai-action': [action: string] }>()

const searchQuery = ref('')
const promptCategories = [
  { id: 'writing', label: '写作提示', count: 8 },
  { id: 'character', label: '角色设定', count: 5 },
  { id: 'world', label: '世界观', count: 4 },
  { id: 'audit', label: '审计规则', count: 3 },
  { id: 'style', label: '风格控制', count: 6 },
]
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><StarOutlined /></n-icon> 提示词库
      </span>
      <n-button text size="tiny" @click="emit('ai-action', 'new-prompt')">
        <template #icon><n-icon size="14"><PlusOutlined /></n-icon></template>
      </n-button>
    </div>
    <div class="panel-section__body">
      <n-input
        v-model:value="searchQuery" size="small" placeholder="搜索提示词..."
        clearable style="margin-bottom:8px"
      >
        <template #prefix><n-icon size="14"><SearchOutlined /></n-icon></template>
      </n-input>
      <div style="display:flex;flex-direction:column;gap:4px">
        <div
          v-for="c in promptCategories" :key="c.id"
          class="panel-item"
          @click="emit('ai-action', `prompt-category:${c.id}`)"
        >
          <span class="panel-item__label">{{ c.label }}</span>
          <span class="panel-item__extra">{{ c.count }}</span>
        </div>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__body">
      <n-button size="small" quaternary block @click="emit('ai-action', 'manage-prompts')">
        管理提示词
      </n-button>
    </div>
  </div>
</template>

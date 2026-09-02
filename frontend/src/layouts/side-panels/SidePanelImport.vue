<script setup lang="ts">
/**
 * 导入中心侧边面板 — 导入源与最近导入
 */
import { ref } from 'vue'
import { NButton, NDivider, NTag } from 'naive-ui'
import { ImportOutlined, FileAddOutlined, CloudUploadOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string }>()
const emit = defineEmits<{ 'ai-action': [action: string] }>()

const importSources = [
  { id: 'txt', label: '文本文件', formats: '.txt / .md', icon: '📄' },
  { id: 'web', label: '网页导入', formats: 'URL 抓取', icon: '🌐' },
  { id: 'fanfic', label: '同人正典', formats: '正典导入', icon: '📚' },
]
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><ImportOutlined /></n-icon> 导入来源
      </span>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:6px">
        <div
          v-for="s in importSources" :key="s.id"
          class="panel-item"
          @click="emit('ai-action', `import:${s.id}`)"
        >
          <span class="panel-item__icon">{{ s.icon }}</span>
          <div class="panel-item__content">
            <span class="panel-item__label">{{ s.label }}</span>
            <span class="panel-item__desc">{{ s.formats }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__body">
      <n-button size="small" quaternary block @click="emit('ai-action', 'import-file')">
        <template #icon><n-icon size="14"><FileAddOutlined /></n-icon></template>
        选择文件导入
      </n-button>
      <n-button size="small" quaternary block @click="emit('ai-action', 'import-url')" style="margin-top:4px">
        <template #icon><n-icon size="14"><CloudUploadOutlined /></n-icon></template>
        从URL导入
      </n-button>
    </div>
  </div>
</template>

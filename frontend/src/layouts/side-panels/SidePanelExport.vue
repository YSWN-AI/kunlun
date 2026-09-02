<script setup lang="ts">
/**
 * 导出中心侧边面板 — 快速导出操作
 */
import { ref } from 'vue'
import { NButton, NDivider, NSelect } from 'naive-ui'
import { DownloadOutlined, FileTextOutlined, BookOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string }>()
const emit = defineEmits<{ 'ai-action': [action: string] }>()

const quickFormat = ref('txt')
const formatOptions = [
  { label: '纯文本 (.txt)', value: 'txt' },
  { label: 'EPUB (.epub)', value: 'epub' },
  { label: 'Markdown (.md)', value: 'md' },
  { label: 'PDF (.pdf)', value: 'pdf' },
  { label: 'HTML (.html)', value: 'html' },
  { label: 'Word (.docx)', value: 'docx' },
  { label: '投稿包 (.zip)', value: 'submission' },
]
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><FileTextOutlined /></n-icon> 快速导出
      </span>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:8px">
        <n-select v-model:value="quickFormat" :options="formatOptions" size="small" placeholder="选择格式" />
        <n-button size="small" quaternary block @click="emit('ai-action', 'quick-export-chapter')">
          <template #icon><n-icon size="14"><DownloadOutlined /></n-icon></template>
          导出当前章
        </n-button>
        <n-button size="small" quaternary block @click="emit('ai-action', 'quick-export-book')">
          <template #icon><n-icon size="14"><BookOutlined /></n-icon></template>
          导出全书
        </n-button>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">依赖状态</span>
    </div>
    <div class="panel-section__body">
      <div style="font-size:12px;color:var(--color-text-tertiary)">
        <div>EPUB: <span style="color:var(--color-success)">可用</span></div>
        <div>PDF: <span style="color:var(--color-warning)">需GTK</span></div>
        <div>DOCX: <span style="color:var(--color-success)">可用</span></div>
        <div>MOBI: <span style="color:var(--color-text-tertiary)">需Calibre</span></div>
      </div>
    </div>
  </div>
</template>

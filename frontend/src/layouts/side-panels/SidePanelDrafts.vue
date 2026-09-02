<script setup lang="ts">
/**
 * 草稿管理侧边面板 — 版本历史与草稿操作
 */
import { ref } from 'vue'
import { NButton, NDivider, NTag } from 'naive-ui'
import { SaveOutlined, HistoryOutlined, DeleteOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string; chapters?: { num: number; status: string; word_count: number }[] }>()
const emit = defineEmits<{ 'select-chapter': [num: number]; 'ai-action': [action: string] }>()

const draftList = ref([
  { num: 42, version: 3, words: 2850, time: '20:15', status: '草稿' },
  { num: 42, version: 2, words: 2720, time: '19:48', status: '修订' },
  { num: 41, version: 1, words: 3010, time: '18:30', status: '已发布' },
])

const statusColor: Record<string, string> = { '已发布': 'success', '草稿': 'warning', '修订': 'info' }
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><HistoryOutlined /></n-icon> 最近草稿
      </span>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:6px">
        <div
          v-for="d in draftList" :key="`${d.num}-v${d.version}`"
          class="panel-item"
          @click="emit('select-chapter', d.num)"
        >
          <span class="panel-item__icon">📄</span>
          <div class="panel-item__content">
            <span class="panel-item__label">第{{ d.num }}章 v{{ d.version }}</span>
            <span class="panel-item__desc">{{ d.words }}字 · {{ d.time }}</span>
          </div>
          <ntag size="tiny" :type="statusColor[d.status] as any">{{ d.status }}</ntag>
        </div>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__body">
      <n-button size="small" quaternary block @click="emit('ai-action', 'save-draft')">
        <template #icon><n-icon size="14"><SaveOutlined /></n-icon></template>
        保存当前草稿
      </n-button>
      <n-button size="small" quaternary block @click="emit('ai-action', 'clean-drafts')" style="margin-top:4px">
        <template #icon><n-icon size="14"><DeleteOutlined /></n-icon></template>
        清理旧草稿
      </n-button>
    </div>
  </div>
</template>

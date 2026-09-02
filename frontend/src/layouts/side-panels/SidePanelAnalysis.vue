<script setup lang="ts">
/**
 * 分析中心侧边面板 — 数据筛选与分析维度
 */
import { ref } from 'vue'
import { NSelect, NButton, NDivider } from 'naive-ui'
import { FilterOutlined, ReloadOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string; books?: { uid: string; title: string }[] }>()
const emit = defineEmits<{ 'select-book': [id: string]; 'ai-action': [action: string] }>()

const analysisType = ref('quality')
const dimension = ref('all')

const typeOptions = [
  { label: '质量趋势', value: 'quality' },
  { label: '字数统计', value: 'wordcount' },
  { label: '爽点分布', value: 'pleasure' },
  { label: 'AIGC趋势', value: 'aigc' },
  { label: '留存预测', value: 'retention' },
]
const dimOptions = [
  { label: '全部维度', value: 'all' },
  { label: '最近10章', value: 'recent10' },
  { label: '最近20章', value: 'recent20' },
]
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><FilterOutlined /></n-icon> 分析筛选
      </span>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:8px">
        <n-select v-model:value="analysisType" :options="typeOptions" size="small" placeholder="分析类型" />
        <n-select v-model:value="dimension" :options="dimOptions" size="small" placeholder="范围" />
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><ReloadOutlined /></n-icon> 操作
      </span>
    </div>
    <div class="panel-section__body">
      <n-button size="small" quaternary block @click="emit('ai-action', 'refresh-analysis')">
        刷新分析数据
      </n-button>
    </div>
  </div>
</template>

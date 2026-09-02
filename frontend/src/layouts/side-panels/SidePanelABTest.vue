<script setup lang="ts">
/**
 * A/B 测试侧边面板 — 变体管理与对比
 */
import { ref } from 'vue'
import { NButton, NDivider, NTag, NSpace } from 'naive-ui'
import { PlusOutlined, SwapOutlined, ExperimentOutlined } from '@vicons/antd'

defineProps<{ currentBookId?: string }>()
const emit = defineEmits<{ 'ai-action': [action: string] }>()

const variants = ref([
  { id: 'A', label: '正文A', tone: '热血升级', model: 'deepseek-chat' },
  { id: 'B', label: '正文B', tone: '稳扎稳打', model: 'deepseek-reasoner' },
])
</script>

<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><ExperimentOutlined /></n-icon> 测试变体
      </span>
      <n-button text size="tiny" @click="emit('ai-action', 'add-variant')">
        <template #icon><n-icon size="14"><PlusOutlined /></n-icon></template>
      </n-button>
    </div>
    <div class="panel-section__body">
      <div style="display:flex;flex-direction:column;gap:8px">
        <div
          v-for="v in variants" :key="v.id"
          class="panel-item"
          @click="emit('ai-action', `select-variant:${v.id}`)"
        >
          <span class="panel-item__icon">{{ v.id }}</span>
          <div class="panel-item__content">
            <span class="panel-item__label">{{ v.label }}</span>
            <span class="panel-item__desc">{{ v.tone }} · {{ v.model }}</span>
          </div>
          <ntag size="tiny" type="info">{{ v.id }}</ntag>
        </div>
      </div>
    </div>
  </div>
  <n-divider style="margin:8px 0" />
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">
        <n-icon size="14"><SwapOutlined /></n-icon> 对比操作
      </span>
    </div>
    <div class="panel-section__body">
      <n-button size="small" quaternary block @click="emit('ai-action', 'run-ab-test')">
        运行对比测试
      </n-button>
      <n-button size="small" quaternary block @click="emit('ai-action', 'view-results')" style="margin-top:4px">
        查看测试结果
      </n-button>
    </div>
  </div>
</template>

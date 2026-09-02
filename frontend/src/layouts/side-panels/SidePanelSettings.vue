<template>
  <n-menu :value="menuValue" :options="menuOptions" :indent="16" @update:value="v => menuValue = v" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NMenu } from 'naive-ui'

const menuValue = ref('general')
const menuOptions = [
  { label: '通用', key: 'general' },
  { label: '模型参数', key: 'params' },
  { label: 'Prompt', key: 'prompts' },
  { label: '导出', key: 'export' },
  { label: '使用统计', key: 'usage' },
]
</script>

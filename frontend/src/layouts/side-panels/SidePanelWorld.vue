<template>
  <div class="panel-section">
    <n-menu :value="menuValue" :options="menuOptions" :indent="16" @update:value="v => menuValue = v" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NMenu } from 'naive-ui'

const menuValue = ref('characters')
const menuOptions = [
  { label: '角色', key: 'characters' },
  { label: '地点', key: 'locations' },
  { label: '势力', key: 'factions' },
  { label: '规则', key: 'rules' },
]
</script>

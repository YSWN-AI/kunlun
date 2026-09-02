<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">审计历史</span>
    </div>
    <n-scrollbar style="max-height: 400px">
      <div class="panel-empty">暂无审计记录</div>
    </n-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { NScrollbar } from 'naive-ui'
</script>

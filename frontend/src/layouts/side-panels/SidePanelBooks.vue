<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">作品列表</span>
      <n-tag type="info" size="small" :bordered="false">{{ (books || []).length }}</n-tag>
    </div>
    <n-scrollbar style="max-height: 400px">
      <div
        v-for="book in (books || [])"
        :key="book.uid"
        class="panel-item"
        :class="{ active: currentBookId === book.uid }"
        @click="$emit('select-book', book.uid)"
      >
        <n-icon :size="16" color="var(--color-primary)"><FileTextOutlined /></n-icon>
        <div class="panel-item__content">
          <span class="panel-item__label text-ellipsis">{{ book.title }}</span>
          <span class="panel-item__desc">{{ book.chapters || 0 }}章 · {{ (book.total_words || 0).toLocaleString() }}字</span>
        </div>
      </div>
      <div v-if="(books || []).length === 0" class="panel-empty">暂无作品，点击创建</div>
    </n-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { NTag, NScrollbar, NIcon } from 'naive-ui'
import { FileTextOutlined } from '@vicons/antd'

defineProps<{
  books?: { uid: string; title: string; chapters?: number; total_words?: number }[]
  currentBookId?: string
}>()

defineEmits<{ 'select-book': [id: string] }>()
</script>

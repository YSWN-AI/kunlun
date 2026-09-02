<script setup lang="ts">
import { NButton, NButtonGroup, NInput, NSelect, NIcon, NDivider } from 'naive-ui'
import { MenuOutlined, SaveOutlined, ExportOutlined, SettingOutlined } from '@vicons/antd'
const props = defineProps<{
  currentBook: string
  books: any[]
  currentChapter: string
  chapters: any[]
  chapterTitle: string
}>()

const emit = defineEmits<{
  'update:currentBook': [value: string]
  'update:currentChapter': [value: string]
  'update:chapterTitle': [value: string]
  'toggle-sidebar': []
  'save-draft': []
  'export-chapter': []
  'open-settings': []
}>()
</script>

<template>
  <div class="write-toolbar">
    <div class="write-toolbar__left">
      <n-button-group>
        <n-button text size="small" @click="emit('toggle-sidebar')">
          <template #icon><n-icon :size="18"><MenuOutlined /></n-icon></template>
        </n-button>
        <n-divider vertical />
        <n-select
          :value="props.currentBook"
          :options="props.books"
          size="small"
          placeholder="选择作品"
          class="write-toolbar__book-select"
          @update:value="emit('update:currentBook', $event)"
        />
        <n-select
          :value="props.currentChapter"
          :options="props.chapters"
          size="small"
          placeholder="选择章节"
          class="write-toolbar__chapter-select"
          @update:value="emit('update:currentChapter', $event)"
        />
      </n-button-group>
    </div>

    <div class="write-toolbar__center">
      <n-input
        :value="props.chapterTitle"
        placeholder="章节标题"
        size="small"
        class="write-toolbar__title-input"
        @update:value="emit('update:chapterTitle', $event)"
      />
    </div>

    <div class="write-toolbar__right">
      <n-button-group>
        <n-button text size="small" @click="emit('save-draft')">
          <template #icon><n-icon :size="18"><SaveOutlined /></n-icon></template>
          保存
        </n-button>
        <n-button text size="small" @click="emit('export-chapter')">
          <template #icon><n-icon :size="18"><ExportOutlined /></n-icon></template>
          导出
        </n-button>
        <n-button type="primary" size="small" @click="emit('open-settings')">
          <template #icon><n-icon :size="18"><SettingOutlined /></n-icon></template>
        </n-button>
      </n-button-group>
    </div>
  </div>
</template>

<style scoped>
.write-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
}

.write-toolbar__left,
.write-toolbar__right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.write-toolbar__center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 var(--space-4);
}

.write-toolbar__title-input {
  width: 300px;
}

.write-toolbar__book-select,
.write-toolbar__chapter-select {
  width: 180px;
}
</style>

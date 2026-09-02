<template>
  <ChapterTree
    :chapters="(chapters || [])"
    :current-chapter="currentChapter"
    @select-chapter="n => $emit('select-chapter', n)"
    @reorder="onReorder"
    @add-chapter="$emit('ai-action', 'new-chapter')"
    @chapter-action="onChapterAction"
  />

  <div class="panel-section" style="margin-top: var(--space-2)">
    <div class="panel-section__header">
      <span class="panel-section__title">AI 工具</span>
    </div>
    <div class="panel-section__body">
      <n-button block secondary size="small" @click="$emit('ai-action', 'continue')">续写当前章</n-button>
      <n-button block secondary size="small" @click="$emit('ai-action', 'polish')" style="margin-top: 8px">润色改写</n-button>
      <n-button block secondary size="small" @click="$emit('ai-action', 'outline')" style="margin-top: 8px">生成大纲</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'
import ChapterTree from '../../components/shared/ChapterTree.vue'
import type { ChapterItem } from '../../components/shared/ChapterTree.vue'

defineProps<{
  chapters?: ChapterItem[]
  currentChapter?: number
}>()

const emit = defineEmits<{
  'select-chapter': [num: number]
  'ai-action': [action: string]
  'reorder-chapters': [fromIndex: number, toIndex: number]
}>()

function onReorder(from: number, to: number) {
  emit('reorder-chapters', from, to)
}

function onChapterAction(action: string, ch: ChapterItem) {
  if (action === 'delete') {
    emit('ai-action', `delete-chapter:${ch.num}`)
  } else if (action === 'duplicate') {
    emit('ai-action', `duplicate-chapter:${ch.num}`)
  } else if (action === 'rename') {
    emit('ai-action', `rename-chapter:${ch.num}`)
  } else if (action === 'move-up' || action === 'move-down') {
    emit('ai-action', `${action}:${ch.num}`)
  }
}
</script>

<template>
  <div class="chapter-tree">
    <div class="chapter-tree__header">
      <span class="chapter-tree__title">章节</span>
      <div class="chapter-tree__actions">
        <n-tag type="info" size="small" :bordered="false">{{ chapters.length }}</n-tag>
        <n-button text size="tiny" @click="$emit('add-chapter')" title="新增章节">
          <template #icon><n-icon :size="14"><PlusOutlined /></n-icon></template>
        </n-button>
      </div>
    </div>

    <n-scrollbar style="max-height: var(--panel-content-max-height, 320px)">
      <TransitionGroup name="chapter-list" tag="div" class="chapter-tree__list">
        <div
          v-for="(ch, index) in chapters"
          :key="ch.num"
          class="chapter-item"
          :class="{
            active: currentChapter === ch.num,
            dragging: dragIndex === index,
            'drag-over': dragOverIndex === index && dragIndex !== index,
          }"
          draggable="true"
          @click="$emit('select-chapter', ch.num)"
          @dragstart="onDragStart($event, index)"
          @dragend="onDragEnd"
          @dragover.prevent="onDragOver($event, index)"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop(index)"
        >
          <!-- 拖拽手柄 -->
          <span class="chapter-item__grip" title="拖拽排序">
            <n-icon :size="12"><MenuOutlined /></n-icon>
          </span>

          <!-- 状态指示 -->
          <span class="chapter-item__status" :class="`status-${ch.status || 'draft'}`">
            <n-icon v-if="ch.status === 'completed'" :size="12"><CheckCircleFilled /></n-icon>
            <n-icon v-else-if="ch.status === 'writing'" :size="12"><LoadingOutlined /></n-icon>
            <span v-else class="status-dot" />
          </span>

          <!-- 章节信息 -->
          <div class="chapter-item__content">
            <span class="chapter-item__label">第{{ ch.num }}章</span>
            <span v-if="ch.title" class="chapter-item__title-text">{{ ch.title }}</span>
          </div>

          <!-- 字数 -->
          <span class="chapter-item__words">{{ formatWords(ch.word_count) }}</span>

          <!-- 右键菜单触发器 -->
          <span class="chapter-item__more" @click.stop="showContextMenu($event, ch)">
            <n-icon :size="12"><MoreOutlined /></n-icon>
          </span>
        </div>
      </TransitionGroup>

      <div v-if="chapters.length === 0" class="chapter-tree__empty">
        暂无章节，点击 + 创建
      </div>
    </n-scrollbar>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
    >
      <div class="context-menu__item" @click="onContextAction('rename')">重命名</div>
      <div class="context-menu__item" @click="onContextAction('delete')">删除</div>
      <div class="context-menu__item" @click="onContextAction('duplicate')">复制章节</div>
      <div class="context-menu__separator" />
      <div class="context-menu__item" @click="onContextAction('move-up')">上移</div>
      <div class="context-menu__item" @click="onContextAction('move-down')">下移</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NTag, NScrollbar, NButton, NIcon } from 'naive-ui'
import {
  PlusOutlined, MenuOutlined, CheckCircleFilled,
  LoadingOutlined, MoreOutlined,
} from '@vicons/antd'

export interface ChapterItem {
  num: number
  status?: string
  word_count?: number
  title?: string
}

const props = defineProps<{
  chapters: ChapterItem[]
  currentChapter?: number
}>()

const emit = defineEmits<{
  'select-chapter': [num: number]
  'reorder': [fromIndex: number, toIndex: number]
  'add-chapter': []
  'chapter-action': [action: string, chapter: ChapterItem]
}>()

const dragIndex = ref(-1)
const dragOverIndex = ref(-1)

function onDragStart(e: DragEvent, index: number) {
  dragIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragEnd() {
  dragIndex.value = -1
  dragOverIndex.value = -1
}

function onDragOver(e: DragEvent, index: number) {
  if (dragIndex.value === -1) return
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  dragOverIndex.value = index
}

function onDragLeave() {
  dragOverIndex.value = -1
}

function onDrop(index: number) {
  if (dragIndex.value === -1 || dragIndex.value === index) return
  emit('reorder', dragIndex.value, index)
  dragIndex.value = -1
  dragOverIndex.value = -1
}

function formatWords(n?: number): string {
  if (!n) return '0字'
  return n >= 10000 ? `${(n / 10000).toFixed(1)}万字` : `${n.toLocaleString()}字`
}

// 右键菜单
const contextMenu = ref({ visible: false, x: 0, y: 0, chapter: null as ChapterItem | null })

function showContextMenu(e: MouseEvent, ch: ChapterItem) {
  e.preventDefault()
  contextMenu.value = {
    visible: true, x: e.clientX, y: e.clientY, chapter: ch,
  }
}

function hideContextMenu() {
  contextMenu.value.visible = false
}

function onContextAction(action: string) {
  if (contextMenu.value.chapter) {
    emit('chapter-action', action, contextMenu.value.chapter)
  }
  hideContextMenu()
}

onMounted(() => document.addEventListener('click', hideContextMenu))
onUnmounted(() => document.removeEventListener('click', hideContextMenu))
</script>

<style scoped>
.chapter-tree {
  display: flex;
  flex-direction: column;
}

.chapter-tree__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-2);
}

.chapter-tree__title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.chapter-tree__actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.chapter-tree__list {
  padding: 0 var(--space-1);
}

.chapter-tree__empty {
  padding: var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 章节项 */
.chapter-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  user-select: none;
}

.chapter-item:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.chapter-item.active {
  background: var(--color-primary-suppl);
  color: var(--color-primary);
}

.chapter-item.dragging {
  opacity: 0.4;
}

.chapter-item.drag-over {
  border-top: 2px solid var(--color-primary);
  border-radius: 0;
}

/* 拖拽手柄 */
.chapter-item__grip {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  cursor: grab;
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.chapter-item:hover .chapter-item__grip {
  opacity: 0.6;
}

.chapter-item__grip:active {
  cursor: grabbing;
}

/* 状态指示 */
.chapter-item__status {
  flex-shrink: 0;
  width: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
}

.status-completed { color: var(--color-success); }
.status-writing { color: var(--color-primary); }
.status-draft { color: var(--color-text-tertiary); }

/* 章节内容 */
.chapter-item__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
  min-width: 0;
}

.chapter-item__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chapter-item__title-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 字数 */
.chapter-item__words {
  flex-shrink: 0;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 更多按钮 */
.chapter-item__more {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  opacity: 0;
  transition: opacity var(--transition-fast);
  padding: 2px;
  border-radius: var(--radius-sm);
}

.chapter-item:hover .chapter-item__more {
  opacity: 0.6;
}

.chapter-item__more:hover {
  opacity: 1 !important;
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

/* 列表过渡动画 */
.chapter-list-enter-active,
.chapter-list-leave-active {
  transition: all var(--transition-normal);
}

.chapter-list-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.chapter-list-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.chapter-list-move {
  transition: transform var(--transition-normal);
}

/* 右键菜单 */
.context-menu {
  position: fixed;
  z-index: var(--z-dropdown);
  min-width: 140px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--space-1) 0;
  backdrop-filter: blur(12px);
}

.context-menu__item {
  padding: 6px var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.context-menu__item:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.context-menu__separator {
  height: 1px;
  background: var(--color-border-light);
  margin: var(--space-1) 0;
}
</style>

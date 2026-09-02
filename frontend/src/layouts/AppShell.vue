<template>
  <div class="app-shell">
    <!-- 活动栏 -->
    <ActivityBar v-model:showCommandPalette="showCommandPalette" />

    <!-- 移动端侧栏遮罩 -->
    <div
      v-if="uiStore.isMobile && uiStore.sidebarVisible"
      class="app-shell__scrim"
      @click="uiStore.toggleSidebar()"
    />

    <!-- 主侧边栏 -->
    <SidePanel
      :sidebar-visible="uiStore.sidebarVisible"
      :sidebar-width="uiStore.sidebarWidth"
      :active-activity="uiStore.activeActivity"
      :chapters="bookStore.chapters"
      :current-chapter="currentChapter"
      :books="bookStore.books"
      :current-book-id="bookStore.currentBookId"
      @toggle="uiStore.toggleSidebar()"
      @update:sidebar-width="uiStore.setSidebarWidth"
      @select-chapter="onSelectChapter"
      @select-book="onSelectBook"
      @ai-action="onAiAction"
      @reorder-chapters="onReorderChapters"
    />

    <!-- 主内容区 -->
    <main class="app-shell__main" :style="uiStore.mainContentStyle">
      <!-- Toast 通知 -->
      <div class="app-shell__toasts" role="status" aria-live="polite">
        <TransitionGroup name="fade-slide">
          <div
            v-for="toast in uiStore.toasts"
            :key="toast.id"
            class="toast-item"
            :class="`toast-${toast.type}`"
            @click="uiStore.dismissToast(toast.id)"
          >
            <span class="toast-icon">{{ toastIcon(toast.type) }}</span>
            <span class="toast-text">{{ toast.message }}</span>
          </div>
        </TransitionGroup>
      </div>

      <!-- 路由视图 -->
      <div class="app-shell__content">
        <router-view v-slot="{ Component, route }">
          <Transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </router-view>
      </div>
    </main>

    <!-- 状态栏 -->
    <StatusBar
      :status-bar-visible="uiStore.statusBarVisible"
      :backend-connected="uiStore.backendConnected"
      :current-book-title="bookStore.currentBook?.title"
      :chapter-info="chapterInfo"
      :last-saved="lastSaved"
      :is-dark="isDark"
      @toggle-theme="toggleTheme"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBookStore } from '../stores/book'
import { useUIStore } from '../stores/ui'
import { useTheme } from '../composables/useTheme'
import { useKeyboard } from '../composables/useKeyboard'
import { api } from '../api'
import ActivityBar from './ActivityBar.vue'
import SidePanel from './SidePanel.vue'
import StatusBar from './StatusBar.vue'

const router = useRouter()
const uiStore = useUIStore()
const bookStore = useBookStore()
const { isDark, toggleTheme } = useTheme()

const showCommandPalette = inject<Ref<boolean>>('showCommandPalette', ref(false))

// 键盘快捷键
useKeyboard()

// 当前章节
const currentChapter = ref(1)
const chapterInfo = computed(() => {
  const ch = bookStore.chapters.find(c => c.num === currentChapter.value)
  return ch ? { num: ch.num, wordCount: ch.word_count } : null
})
const lastSaved = ref<number | null>(null)

function onSelectChapter(num: number) {
  currentChapter.value = num
}

function onSelectBook(bookId: string) {
  bookStore.selectBook(bookId)
  router.push(`/books/${bookId}`)
}

function onAiAction(action: string) {
  if (action.startsWith('new-chapter')) {
    bookStore.addChapter()
    uiStore.showToast('已新增章节', 'success')
  } else if (action.startsWith('delete-chapter:')) {
    const num = parseInt(action.split(':')[1])
    bookStore.removeChapter(num)
    uiStore.showToast(`已删除第${num}章`, 'success')
  } else if (action.startsWith('duplicate-chapter:')) {
    const num = parseInt(action.split(':')[1])
    bookStore.duplicateChapter(num)
    uiStore.showToast(`已复制第${num}章`, 'success')
  } else if (action.startsWith('move-up:') || action.startsWith('move-down:')) {
    const [act, numStr] = action.split(':')
    const num = parseInt(numStr)
    bookStore.moveChapter(num, act === 'move-up' ? -1 : 1)
  } else {
    uiStore.showToast(`AI 操作: ${action}`, 'info')
  }
}

function onReorderChapters(fromIndex: number, toIndex: number) {
  bookStore.reorderChapters(fromIndex, toIndex)
}

function toastIcon(type: string): string {
  return { success: '✓', error: '✗', warning: '!', info: 'i' }[type] || 'i'
}

// 初始化：检查后端连接、加载作品
onMounted(async () => {
  try {
    await api.health()
    uiStore.setBackendStatus(true)
  } catch {
    uiStore.setBackendStatus(false)
    uiStore.showToast('后端服务未连接，部分功能不可用', 'warning')
  }

  try {
    await bookStore.loadBooks()
  } catch {
    // 静默处理
  }
})
</script>

<style scoped>
.app-shell {
  width: 100%;
  height: 100%;
  display: flex;
  background: var(--color-bg-base);
}

.app-shell__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  transition: margin var(--transition-normal);
}

.app-shell__content {
  flex: 1;
  overflow: auto;
  position: relative;
}

/* 移动端侧栏遮罩 */
.app-shell__scrim {
  position: fixed;
  top: 0;
  left: var(--activity-bar-width);
  right: 0;
  bottom: 0;
  background: var(--color-bg-mask);
  z-index: 99;
}

/* Toast 通知 */
.app-shell__toasts {
  position: fixed;
  top: var(--space-4);
  right: var(--space-4);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: none;
}
.app-shell__toasts > * {
  pointer-events: auto;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  font-size: var(--text-sm);
  cursor: pointer;
  backdrop-filter: blur(12px);
  max-width: 360px;
  box-shadow: var(--shadow-md);
}
.toast-success { border-left: 3px solid var(--color-success); }
.toast-error { border-left: 3px solid var(--color-error); }
.toast-warning { border-left: 3px solid var(--color-warning); }
.toast-info { border-left: 3px solid var(--color-info); }

.toast-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
}
.toast-success .toast-icon { background: var(--color-success-suppl); color: var(--color-success); }
.toast-error .toast-icon { background: var(--color-error-suppl); color: var(--color-error); }
.toast-warning .toast-icon { background: var(--color-warning-suppl); color: var(--color-warning); }
.toast-info .toast-icon { background: var(--color-primary-suppl); color: var(--color-primary); }

.toast-text {
  color: var(--color-text-primary);
  word-break: break-word;
}
</style>

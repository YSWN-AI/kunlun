<template>
  <div class="book-detail">
    <!-- 返回 + 标题 -->
    <div class="book-detail__header">
      <n-button text @click="$router.back()">
        <template #icon><n-icon :size="18"><ArrowLeftOutlined /></n-icon></template>
      </n-button>
      <div>
        <h2 class="book-detail__title">{{ book?.title || '加载中...' }}</h2>
        <p class="book-detail__meta">{{ book?.genre }} · {{ book?.chapters || 0 }}章 · {{ (book?.total_words || 0).toLocaleString() }}字</p>
      </div>
      <div class="book-detail__actions">
        <n-button size="small" @click="$router.push(`/write?book=${bookId}&chapter=1`)">
          开始创作
        </n-button>
      </div>
    </div>

    <InlineNotice v-if="!book" type="loading" message="加载作品信息..." />
    <SkeletonLoader v-if="!book" type="list" :count="6" />

    <!-- 章节列表 -->
    <div v-if="book" class="book-detail__section">
      <h3 class="section-title">章节列表</h3>
      <div v-if="chapters.length === 0" class="book-detail__empty">
        暂无章节
      </div>
      <div v-else class="chapter-list">
        <div
          v-for="ch in chapters"
          :key="ch.num"
          class="chapter-item"
          @click="$router.push(`/write?book=${bookId}&chapter=${ch.num}`)"
        >
          <span class="chapter-item__num">第{{ ch.num }}章</span>
          <span class="chapter-item__status" :class="`status-${ch.status}`">
            {{ ch.status === 'completed' ? '已完成' : ch.status }}
          </span>
          <span class="chapter-item__words">{{ (ch.word_count || 0).toLocaleString() }}字</span>
        </div>
      </div>
    </div>

    <!-- 基本信息 -->
    <div v-if="book" class="book-detail__section">
      <h3 class="section-title">基本信息</h3>
      <div class="book-detail__info">
        <div class="info-row">
          <span class="info-row__label">ID</span>
          <span class="info-row__value">{{ book.uid }}</span>
        </div>
        <div class="info-row">
          <span class="info-row__label">状态</span>
          <span class="info-row__value">{{ book.status }}</span>
        </div>
        <div class="info-row">
          <span class="info-row__label">创建时间</span>
          <span class="info-row__value">{{ book.created_at }}</span>
        </div>
        <div class="info-row">
          <span class="info-row__label">简介</span>
          <span class="info-row__value">{{ book.description || '暂无' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NIcon } from 'naive-ui'
import { ArrowLeftOutlined } from '@vicons/antd'
import { useBookStore } from '../../stores/book'
import SkeletonLoader from '../../components/shared/SkeletonLoader.vue'
import InlineNotice from '../../components/shared/InlineNotice.vue'

const route = useRoute()
const bookStore = useBookStore()
const bookId = computed(() => route.params.id as string)
const book = computed(() => bookStore.currentBook)
const chapters = computed(() => bookStore.chapters)

onMounted(async () => {
  await bookStore.selectBook(bookId.value)
})
</script>

<style scoped>
.book-detail {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.book-detail__header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.book-detail__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.book-detail__meta {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.book-detail__actions {
  margin-left: auto;
}

.book-detail__section {
  margin-bottom: var(--space-6);
}

.section-title {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3);
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 600px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
  font-size: var(--text-sm);
}
.chapter-item:hover {
  background: var(--color-bg-overlay);
}

.chapter-item__num {
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.chapter-item__status {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-overlay);
  color: var(--color-text-tertiary);
}
.chapter-item__status.status-completed {
  color: var(--color-success);
}

.chapter-item__words {
  margin-left: auto;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.book-detail__info {
  max-width: 500px;
}

.info-row {
  display: flex;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
}
.info-row__label {
  width: 80px;
  flex-shrink: 0;
  color: var(--color-text-tertiary);
}
.info-row__value {
  color: var(--color-text-primary);
}

.book-detail__empty {
  padding: var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}
</style>

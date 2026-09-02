<template>
  <div class="books-view">
    <div class="books-view__header">
      <h2 class="books-view__title">作品管理</h2>
      <n-button type="primary" size="small" @click="showCreate = true">
        <template #icon><n-icon :size="16"><PlusOutlined /></n-icon></template>
        创建作品
      </n-button>
    </div>

    <!-- 加载中 -->
    <SkeletonLoader v-if="bookStore.loading && books.length === 0" type="cards" />

    <!-- 空状态 -->
    <div v-else-if="books.length === 0" class="books-view__empty">
      <h3>还没有作品</h3>
      <p>创建你的第一部作品，开始 AI 辅助创作之旅。</p>
      <n-button type="primary" @click="showCreate = true">
        <template #icon><n-icon :size="18"><PlusOutlined /></n-icon></template>
        创建第一部作品
      </n-button>
    </div>

    <!-- 作品网格 -->
    <div v-else class="books-view__grid">
      <n-card
        v-for="book in books"
        :key="book.uid"
        class="book-card"
        :bordered="true"
        hoverable
        @click="openBook(book.uid)"
      >
        <template #cover>
          <div class="book-card__cover">
            <n-icon :size="32" color="var(--color-primary)">
              <BookOutlined />
            </n-icon>
          </div>
        </template>
        <div class="book-card__body">
          <h3 class="book-card__title text-ellipsis">{{ book.title }}</h3>
          <p class="book-card__genre">{{ book.genre || '未分类' }}</p>
          <div class="book-card__stats">
            <span>{{ book.chapters || 0 }} 章</span>
            <span class="book-card__dot">·</span>
            <span>{{ (book.total_words || 0).toLocaleString() }} 字</span>
            <span class="book-card__dot">·</span>
            <span class="book-card__status">{{ statusLabel(book.status) }}</span>
          </div>
        </div>
        <template #action>
          <n-button text size="tiny" type="error" @click.stop="onDelete(book.uid)">
            删除
          </n-button>
        </template>
      </n-card>
    </div>

    <!-- 创建弹窗 -->
    <n-modal v-model:show="showCreate" preset="card" title="创建新作品" style="width: 480px" :bordered="false">
      <n-form ref="formRef" :model="newBook" :rules="bookRules" label-placement="top">
        <n-form-item label="作品 ID" path="uid">
          <n-input v-model:value="newBook.uid" placeholder="英文、数字、下划线" />
        </n-form-item>
        <n-form-item label="书名" path="title">
          <n-input v-model:value="newBook.title" placeholder="给你的作品起个名字" />
        </n-form-item>
        <n-form-item label="体裁">
          <n-select v-model:value="newBook.genre" :options="genreOptions" placeholder="选择体裁" />
        </n-form-item>
        <n-form-item label="简介">
          <n-input v-model:value="newBook.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="简短描述..." />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showCreate = false">取消</n-button>
        <n-button type="primary" :loading="bookStore.loading" @click="onCreate">创建</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NCard, NModal, NForm, NFormItem, NInput, NSelect } from 'naive-ui'
import { PlusOutlined, BookOutlined } from '@vicons/antd'
import { useBookStore } from '../../stores/book'
import { useUIStore } from '../../stores/ui'
import SkeletonLoader from '../../components/shared/SkeletonLoader.vue'

const router = useRouter()
const bookStore = useBookStore()
const uiStore = useUIStore()
const books = computed(() => bookStore.books)

const showCreate = ref(false)
const newBook = ref({ uid: '', title: '', genre: '玄幻', description: '' })
const bookRules = {
  uid: [{ required: true, message: '请输入作品 ID' }],
  title: [{ required: true, message: '请输入书名' }],
}

const genreOptions = [
  { label: '玄幻', value: '玄幻' },
  { label: '仙侠', value: '仙侠' },
  { label: '都市', value: '都市' },
  { label: '科幻', value: '科幻' },
  { label: '历史', value: '历史' },
  { label: '悬疑', value: '悬疑' },
  { label: '轻小说', value: '轻小说' },
]

function statusLabel(s: string): string {
  const m: Record<string, string> = { draft: '草稿', active: '创作中', completed: '已完成', paused: '已暂停' }
  return m[s] || s
}

function openBook(id: string) {
  bookStore.selectBook(id)
  router.push(`/books/${id}`)
}

async function onCreate() {
  const { uid, title, genre, description } = newBook.value
  const ok = await bookStore.createBook(uid, title, genre, description)
  if (ok) {
    uiStore.showToast('作品创建成功', 'success')
    showCreate.value = false
    newBook.value = { uid: '', title: '', genre: '玄幻', description: '' }
  }
}

async function onDelete(id: string) {
  await bookStore.deleteBook(id)
  uiStore.showToast('作品已删除', 'info')
}
</script>

<style scoped>
.books-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.books-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.books-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.books-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-16) var(--space-8);
  text-align: center;
}
.books-view__empty h3 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}
.books-view__empty p {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  max-width: 320px;
}

.books-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}

.book-card {
  cursor: pointer;
  transition: transform var(--transition-fast);
}
.book-card:hover {
  transform: translateY(-2px);
}

.book-card__cover {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-bg-overlay), var(--color-bg-elevated));
}

.book-card__body {
  padding: var(--space-2) 0 0;
}

.book-card__title {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.book-card__genre {
  font-size: var(--text-xs);
  color: var(--color-primary);
  margin-bottom: var(--space-1);
}

.book-card__stats {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.book-card__dot {
  margin: 0 4px;
}

.book-card__status {
  color: var(--color-success);
}
</style>

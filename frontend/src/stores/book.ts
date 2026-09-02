/**
 * 昆仑创作引擎 — 作品状态管理
 * 类型安全 + 关键操作错误反馈
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'
import type { Book, Chapter, GenerateChapterResponse } from '../types/api'

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

export const useBookStore = defineStore('book', () => {
  const currentBookId = ref('')
  const books = ref<Book[]>([])
  const chapters = ref<Chapter[]>([])
  const loading = ref(false)
  const error = ref('')

  const currentBook = computed(() => books.value.find(b => b.uid === currentBookId.value))

  async function loadBooks() {
    loading.value = true
    error.value = ''
    try {
      const res = await api.listBooks()
      books.value = res.books || []
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function selectBook(bookId: string) {
    currentBookId.value = bookId
    await loadBookStats(bookId)
  }

  async function loadBookStats(bookId: string) {
    try {
      const res = await api.getBookStats(bookId)
      const data = res.data
      if (data?.chapters?.list) {
        chapters.value = data.chapters.list
      }
    } catch (e: unknown) {
      console.debug('加载书籍统计失败:', getErrorMessage(e))
    }
  }

  async function createBook(bookId: string, title: string, genre = '玄幻', description = '') {
    loading.value = true
    error.value = ''
    try {
      await api.createBook({ book_id: bookId, title, genre, description })
      await loadBooks()

      // 延迟通知（依赖动态导入避免循环依赖）
      const { useUIStore } = await import('../stores/ui')
      useUIStore().showToast('作品创建成功', 'success')
      return true
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
      const { useUIStore } = await import('../stores/ui')
      useUIStore().showToast(`创建失败: ${getErrorMessage(e)}`, 'error')
      return false
    } finally {
      loading.value = false
    }
  }

  async function deleteBook(bookId: string) {
    try {
      await api.deleteBook(bookId)
      if (currentBookId.value === bookId) currentBookId.value = ''
      await loadBooks()
      const { useUIStore } = await import('../stores/ui')
      useUIStore().showToast('作品已删除', 'success')
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
      const { useUIStore } = await import('../stores/ui')
      useUIStore().showToast(`删除失败: ${getErrorMessage(e)}`, 'error')
    }
  }

  async function generateChapter(bookId: string, chapter: number, mode = 'gacha_parallel_3', chapterType = 'normal') {
    error.value = ''
    try {
      const result = await api.generateChapter(bookId, chapter, mode, chapterType)
      return result
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
      const { useUIStore } = await import('../stores/ui')
      useUIStore().showToast(`生成失败: ${getErrorMessage(e)}`, 'error')
      return null
    }
  }

  async function initializeBook(bookId: string) {
    try {
      const res = await api.initializeBook(bookId)
      return res
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
      const { useUIStore } = await import('../stores/ui')
      useUIStore().showToast(`初始化失败: ${getErrorMessage(e)}`, 'error')
      return null
    }
  }

  // ─── 章节本地操作 ──────────────────────
  function addChapter() {
    const maxNum = chapters.value.reduce((m, c) => Math.max(m, c.num), 0)
    chapters.value.push({
      num: maxNum + 1,
      status: 'draft',
      word_count: 0,
      title: '',
    } as Chapter)
  }

  function removeChapter(num: number) {
    chapters.value = chapters.value.filter(c => c.num !== num)
  }

  function duplicateChapter(num: number) {
    const src = chapters.value.find(c => c.num === num)
    if (!src) return
    const maxNum = chapters.value.reduce((m, c) => Math.max(m, c.num), 0)
    chapters.value.push({
      ...src,
      num: maxNum + 1,
      title: src.title ? `${src.title}(副本)` : '',
      word_count: 0,
      status: 'draft',
    } as Chapter)
  }

  function moveChapter(num: number, delta: number) {
    const sorted = [...chapters.value].sort((a, b) => a.num - b.num)
    const idx = sorted.findIndex(c => c.num === num)
    if (idx === -1) return
    const newIdx = idx + delta
    if (newIdx < 0 || newIdx >= sorted.length) return
    // 交换 num
    const temp = sorted[idx].num
    sorted[idx].num = sorted[newIdx].num
    sorted[newIdx].num = temp
    chapters.value = sorted
  }

  function reorderChapters(fromIndex: number, toIndex: number) {
    const sorted = [...chapters.value].sort((a, b) => a.num - b.num)
    const [moved] = sorted.splice(fromIndex, 1)
    sorted.splice(toIndex, 0, moved)
    // 重新分配章节号
    sorted.forEach((c, i) => { c.num = i + 1 })
    chapters.value = sorted
  }

  return {
    currentBookId, books, chapters, loading, error, currentBook,
    loadBooks, selectBook, loadBookStats, createBook, deleteBook, generateChapter, initializeBook,
    addChapter, removeChapter, duplicateChapter, moveChapter, reorderChapters,
  }
}, {
  persist: {
    paths: ['currentBookId'],
  },
})

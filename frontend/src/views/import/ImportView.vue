<template>
  <div class="import-view">
    <!-- 顶部标题栏 -->
    <div class="import-view__header">
      <h2 class="import-view__title">
        <n-icon size="22" :component="UploadOutlined" />
        导入中心
      </h2>
      <p class="import-view__subtitle">从本地文件导入小说内容，支持多种格式</p>
    </div>

    <div class="import-layout">
      <!-- 左侧：文件选择区 -->
      <div class="import-config">
        <!-- 文件上传 -->
        <n-card :bordered="true" title="选择文件" size="small" class="import-card">
          <div
            class="file-drop-zone"
            :class="{ 'file-drop-zone--active': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input
              type="file"
              accept=".txt,.md,.epub"
              class="file-input"
              @change="handleFileSelect"
              multiple
            />
            <div class="file-drop-zone__content">
              <n-icon :size="48" :component="CloudUploadOutlined" class="file-drop-zone__icon" />
              <p class="file-drop-zone__text">拖拽文件到此处</p>
              <p class="file-drop-zone__hint">或点击选择文件</p>
              <p class="file-drop-zone__formats">支持格式：TXT、MD、EPUB</p>
            </div>
          </div>

          <!-- 已选择文件列表 -->
          <div v-if="selectedFiles.length > 0" class="selected-files">
            <n-divider />
            <div class="selected-files__header">
              <span>已选择文件</span>
              <n-button text size="small" @click="clearFiles">
                <template #icon><n-icon :size="12"><CloseOutlined /></n-icon></template>
                清空
              </n-button>
            </div>
            <div
              v-for="(file, index) in selectedFiles"
              :key="index"
              class="selected-file-item"
            >
              <n-icon :size="16" :component="getFileIcon(file.name)" />
              <span class="selected-file-item__name">{{ file.name }}</span>
              <span class="selected-file-item__size">{{ formatFileSize(file.size) }}</span>
              <n-button text size="tiny" @click="removeFile(index)">
                <n-icon :size="12"><CloseOutlined /></n-icon>
              </n-button>
            </div>
          </div>
        </n-card>

        <!-- 导入选项 -->
        <n-card :bordered="true" title="导入选项" size="small" class="import-card">
          <!-- 编码选择 -->
          <div class="config-row">
            <span class="config-label">文件编码</span>
            <n-select
              v-model:value="encoding"
              :options="encodingOptions"
              size="small"
              class="config-select"
            />
          </div>

          <!-- 章节分隔符 -->
          <div class="config-row">
            <span class="config-label">章节分隔</span>
            <n-select
              v-model:value="chapterDelimiter"
              :options="delimiterOptions"
              size="small"
              class="config-select"
            />
          </div>

          <!-- 自动检测标题 -->
          <div class="config-row">
            <span class="config-label">自动检测标题</span>
            <n-switch v-model:value="autoDetectTitles" size="small" />
          </div>

          <!-- 创建新作品 -->
          <div class="config-row">
            <span class="config-label">创建新作品</span>
            <n-switch v-model:value="createNewBook" size="small" />
          </div>

          <!-- 作品名称输入 -->
          <div v-if="createNewBook" class="config-row">
            <span class="config-label">作品名称</span>
            <n-input
              v-model:value="newBookName"
              placeholder="输入作品名称"
              size="small"
              class="config-input"
            />
          </div>

          <!-- 添加到现有作品 -->
          <div v-else class="config-row">
            <span class="config-label">添加到</span>
            <n-select
              v-model:value="targetBookId"
              :options="books.map(b => ({ label: b.title, value: b.id }))"
              placeholder="选择作品"
              size="small"
              class="config-select"
            />
          </div>
        </n-card>
      </div>

      <!-- 右侧：预览与操作 -->
      <div class="import-action">
        <!-- 预览卡片 -->
        <n-card :bordered="true" title="内容预览" size="small" class="import-card">
          <div v-if="!previewContent" class="preview-empty">
            <n-icon :size="32" :component="FileTextOutlined" class="preview-empty__icon" />
            <p>选择文件后预览内容</p>
          </div>
          <div v-else class="preview-content">
            <div class="preview-header">
              <span class="preview-filename">{{ currentPreviewFile }}</span>
              <n-button text size="tiny" @click="refreshPreview">
                <template #icon><n-icon :size="12"><RestOutlined /></n-icon></template>
                刷新预览
              </n-button>
            </div>
            <div class="preview-body">
              <pre class="preview-text">{{ previewContent }}</pre>
            </div>
          </div>
        </n-card>

        <!-- 章节检测结果 -->
        <n-card :bordered="true" title="章节检测" size="small" class="import-card">
          <div v-if="detectedChapters.length === 0" class="chapters-empty">
            <p>未检测到章节，或未选择文件</p>
          </div>
          <div v-else class="chapters-list">
            <div class="chapters-summary">
              <n-tag type="success" size="small">检测到 {{ detectedChapters.length }} 个章节</n-tag>
            </div>
            <div class="chapters-scroll">
              <div
                v-for="(chapter, index) in detectedChapters.slice(0, 10)"
                :key="index"
                class="chapter-item"
              >
                <span class="chapter-item__num">{{ index + 1 }}</span>
                <span class="chapter-item__title">{{ chapter.title }}</span>
              </div>
              <div v-if="detectedChapters.length > 10" class="chapters-more">
                还有 {{ detectedChapters.length - 10 }} 个章节...
              </div>
            </div>
          </div>
        </n-card>

        <!-- 操作按钮 -->
        <n-card :bordered="true" title="开始导入" size="small" class="import-card">
          <div v-if="importing" class="import-progress">
            <n-progress
              :percentage="importProgress"
              :status="importStatus === 'error' ? 'error' : importStatus === 'success' ? 'success' : 'default'"
              :indicator-placement="'inside'"
            />
            <p v-if="importStatus === 'success'" class="progress-hint success">
              导入完成！已创建 {{ importedChapters }} 个章节
            </p>
            <p v-else-if="importStatus === 'error'" class="progress-hint error">
              导入失败：{{ importError }}
            </p>
            <p v-else class="progress-hint">{{ importMessage }}</p>
          </div>

          <n-button
            type="primary"
            size="large"
            block
            :loading="importing"
            :disabled="!canImport"
            @click="startImport"
          >
            <template #icon>
              <n-icon :component="UploadOutlined" />
            </template>
            {{ importing ? '导入中...' : '开始导入' }}
          </n-button>

          <p v-if="!backendConnected" class="disconnected-hint">
            后端未连接，无法执行导入
          </p>
        </n-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NButton, NCard, NSelect, NSwitch, NIcon, NDivider, NProgress, NTag,
} from 'naive-ui'
import {
  UploadOutlined, CloudUploadOutlined, FileTextOutlined, FileOutlined,
  CloseOutlined, RestOutlined, BookOutlined, CodeOutlined,
} from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import { api } from '../../api'

const uiStore = useUIStore()
const backendConnected = uiStore.backendConnected

// 文件相关
const selectedFiles = ref<File[]>([])
const isDragging = ref(false)
const previewContent = ref('')
const currentPreviewFile = ref('')

// 配置选项
const encoding = ref('utf-8')
const chapterDelimiter = ref('auto')
const autoDetectTitles = ref(true)
const createNewBook = ref(true)
const newBookName = ref('')
const targetBookId = ref('')

// 书籍列表
const books = ref<{ id: string; title: string }[]>([])

// 章节检测
const detectedChapters = ref<{ title: string; start: number; end: number }[]>([])

// 导入状态
const importing = ref(false)
const importProgress = ref(0)
const importStatus = ref<'success' | 'error' | ''>('')
const importMessage = ref('')
const importError = ref('')
const importedChapters = ref(0)

// 选项配置
const encodingOptions = [
  { label: 'UTF-8', value: 'utf-8' },
  { label: 'GBK', value: 'gbk' },
  { label: 'GB2312', value: 'gb2312' },
  { label: 'GB18030', value: 'gb18030' },
  { label: 'UTF-16', value: 'utf-16' },
]

const delimiterOptions = [
  { label: '自动检测', value: 'auto' },
  { label: '第X章', value: 'chapter' },
  { label: '卷X', value: 'volume' },
  { label: '自定义', value: 'custom' },
]

// 计算属性
const canImport = computed(() => {
  if (selectedFiles.value.length === 0) return false
  if (createNewBook.value && !newBookName.value.trim()) return false
  if (!createNewBook.value && !targetBookId.value) return false
  return true
})

// 方法
function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'txt') return FileTextOutlined
  if (ext === 'md') return CodeOutlined
  if (ext === 'epub') return BookOutlined
  return FileOutlined
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) {
    selectedFiles.value = Array.from(target.files)
    updatePreview()
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false
  if (event.dataTransfer?.files) {
    selectedFiles.value = Array.from(event.dataTransfer.files).filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase()
      return ['txt', 'md', 'epub'].includes(ext || '')
    })
    updatePreview()
  }
}

function clearFiles() {
  selectedFiles.value = []
  previewContent.value = ''
  currentPreviewFile.value = ''
  detectedChapters.value = []
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
  if (selectedFiles.value.length === 0) {
    previewContent.value = ''
    currentPreviewFile.value = ''
    detectedChapters.value = []
  } else if (currentPreviewFile.value === selectedFiles.value[index]?.name) {
    updatePreview()
  }
}

async function updatePreview() {
  if (selectedFiles.value.length === 0) return

  const file = selectedFiles.value[0]
  currentPreviewFile.value = file.name

  try {
    const text = await readFileAsText(file)
    previewContent.value = text.substring(0, 2000) + (text.length > 2000 ? '...' : '')
    detectChapters(text)
  } catch (e) {
    previewContent.value = '无法读取文件内容'
  }
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsText(file, encoding.value)
  })
}

function detectChapters(text: string) {
  const chapters: { title: string; start: number; end: number }[] = []
  
  // 匹配章节标题的正则表达式
  const chapterPatterns = [
    /第[\u4e00-\u9fa5\d]+章[\s\S]*?(?=第[\u4e00-\u9fa5\d]+章|$)/g,
    /卷[\u4e00-\u9fa5\d]+[\s\S]*?(?=卷[\u4e00-\u9fa5\d]+|$)/g,
    /Chapter\s*\d+[\s\S]*?(?=Chapter\s*\d+|$)/gi,
    /第[\u4e00-\u9fa5\d]+节[\s\S]*?(?=第[\u4e00-\u9fa5\d]+节|$)/g,
  ]

  for (const pattern of chapterPatterns) {
    let match
    while ((match = pattern.exec(text)) !== null) {
      const title = match[0].split('\n')[0].trim()
      if (title && !chapters.some(c => c.title === title)) {
        chapters.push({
          title,
          start: match.index,
          end: match.index + match[0].length,
        })
      }
    }
  }

  // 如果没有检测到章节，尝试按空行分割
  if (chapters.length === 0) {
    const lines = text.split('\n')
    let currentChapter = ''
    let lineCount = 0
    lines.forEach((line, index) => {
      if (line.trim() === '' && currentChapter.trim()) {
        chapters.push({
          title: `第${chapters.length + 1}章`,
          start: 0,
          end: 0,
        })
        currentChapter = ''
        lineCount = 0
      } else {
        currentChapter += line + '\n'
        lineCount++
      }
    })
    if (currentChapter.trim()) {
      chapters.push({
        title: `第${chapters.length + 1}章`,
        start: 0,
        end: 0,
      })
    }
  }

  detectedChapters.value = chapters.slice(0, 50)
}

function refreshPreview() {
  updatePreview()
}

async function loadBooks() {
  try {
    const res = await api.listBooks()
    books.value = (res as any).books || []
    if (books.value.length > 0) {
      targetBookId.value = books.value[0].id
    }
  } catch {
    books.value = []
  }
}

async function startImport() {
  if (!canImport.value) return

  importing.value = true
  importProgress.value = 0
  importStatus.value = ''
  importMessage.value = '正在处理文件...'
  importedChapters.value = 0

  try {
    const file = selectedFiles.value[0]
    const text = await readFileAsText(file)
    
    // 检测章节
    detectChapters(text)
    
    importProgress.value = 30
    importMessage.value = '正在创建作品...'

    // 创建作品
    let bookId = targetBookId.value
    if (createNewBook.value) {
      const bookName = newBookName.value.trim() || file.name.replace(/\.[^.]+$/, '')
      // 生成唯一的 book_id
      const newBookId = 'book-' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9)
      const createRes = await api.createBook({ book_id: newBookId, title: bookName })
      bookId = (createRes as any).book_id || (createRes as any).id || newBookId
    }

    importProgress.value = 50
    importMessage.value = '正在导入内容...'

    // 逐个导入章节（使用 rawRequest 调用后端端点）
    const chaptersToImport = detectedChapters.value.length || 1
    
    for (let i = 0; i < chaptersToImport; i++) {
      importMessage.value = `正在导入第 ${i + 1} / ${chaptersToImport} 章...`
      
      let chapterContent = ''
      let chapterTitle = ''
      
      if (detectedChapters.value[i]) {
        const chapter = detectedChapters.value[i]
        chapterTitle = chapter.title
        const nextChapter = detectedChapters.value[i + 1]
        if (nextChapter) {
          chapterContent = text.substring(chapter.start, nextChapter.start).trim()
        } else {
          chapterContent = text.substring(chapter.start).trim()
        }
      } else {
        chapterTitle = `第${i + 1}章`
        chapterContent = text
      }

      // 使用 rawRequest 创建章节
      await api.rawRequest(`/books/${bookId}/chapters/${i + 1}`, {
        method: 'POST',
        body: JSON.stringify({
          title: chapterTitle,
          content: chapterContent,
          number: i + 1,
        }),
      })

      importedChapters.value = i + 1
      importProgress.value = 50 + Math.round((i + 1) / chaptersToImport * 45)
    }

    importProgress.value = 100
    importStatus.value = 'success'
    uiStore.showToast(`成功导入 ${importedChapters.value} 个章节！`, 'success')
  } catch (e: any) {
    importStatus.value = 'error'
    importError.value = e.message || '未知错误'
    uiStore.showToast(`导入失败: ${importError.value}`, 'error')
  } finally {
    importing.value = false
  }
}

// 初始化
onMounted(() => {
  loadBooks()
})
</script>

<style scoped>
.import-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.import-view__header {
  margin-bottom: var(--space-6);
}

.import-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-1) 0;
}

.import-view__subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.import-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  align-items: start;
}

@media (max-width: 900px) {
  .import-layout {
    grid-template-columns: 1fr;
  }
}

.import-config,
.import-action {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.import-card {
  /* inherits */
}

/* 文件上传区域 */
.file-drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--color-bg-secondary);
}

.file-drop-zone:hover,
.file-drop-zone--active {
  border-color: var(--color-primary);
  background: var(--color-primary-suppl);
}

.file-input {
  display: none;
}

.file-drop-zone__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.file-drop-zone__icon {
  color: var(--color-text-tertiary);
}

.file-drop-zone__text {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  margin: 0;
}

.file-drop-zone__hint {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.file-drop-zone__formats {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin: 0;
}

/* 已选择文件列表 */
.selected-files {
  margin-top: var(--space-4);
}

.selected-files__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.selected-file-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-1);
}

.selected-file-item__name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-file-item__size {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 配置选项 */
.config-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.config-row:last-child {
  margin-bottom: 0;
}

.config-label {
  width: 80px;
  flex-shrink: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.config-select {
  flex: 1;
}

.config-input {
  flex: 1;
}

/* 预览区域 */
.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  color: var(--color-text-tertiary);
}

.preview-empty__icon {
  margin-bottom: var(--space-2);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.preview-filename {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.preview-body {
  max-height: 300px;
  overflow: auto;
}

.preview-text {
  font-family: var(--font-family-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  line-height: 1.6;
}

/* 章节检测 */
.chapters-empty {
  padding: var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.chapters-summary {
  margin-bottom: var(--space-2);
}

.chapters-scroll {
  max-height: 200px;
  overflow: auto;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--color-border-light);
}

.chapter-item:last-child {
  border-bottom: none;
}

.chapter-item__num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-suppl);
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.chapter-item__title {
  flex: 1;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapters-more {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  padding: var(--space-2);
}

/* 导入进度 */
.import-progress {
  margin-bottom: var(--space-3);
}

.progress-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin: var(--space-2) 0 0 0;
}

.progress-hint.success {
  color: var(--color-success);
}

.progress-hint.error {
  color: var(--color-error);
}

.disconnected-hint {
  font-size: var(--text-xs);
  color: var(--color-warning);
  text-align: center;
  margin: var(--space-2) 0 0 0;
}
</style>
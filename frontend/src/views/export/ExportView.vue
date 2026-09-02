<script setup lang="ts">
/**
 * 昆仑创作引擎 — 导出视图
 * 支持 7 种格式导出：txt, epub, md, pdf, html, docx, submission
 * 单章/全书/投稿三种模式，带进度反馈和下载
 */
import { ref, computed, onMounted } from 'vue'
import {
  NButton, NCard, NSelect, NRadio, NRadioGroup, NTag,
  NProgress, NSpace, NDivider, NInputNumber, NCheckbox, NSpin,
} from 'naive-ui'
import { DownloadOutlined, ExportOutlined } from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import { api } from '../../api'

const uiStore = useUIStore()
const backendConnected = uiStore.backendConnected

// ─── 书籍列表 ──────────────────────
const books = ref<{ id: string; title: string }[]>([])
const booksLoading = ref(false)

// ─── 导出模式 ──────────────────────
type ExportMode = 'chapter' | 'book' | 'submission'
const exportMode = ref<ExportMode>('book')

const modeOptions = [
  { label: '全书导出', value: 'book' },
  { label: '单章导出', value: 'chapter' },
  { label: '投稿包', value: 'submission' },
]

// ─── 格式选项（7种） ────────────────
const exportFormat = ref('txt')

const formatOptions = [
  { label: '纯文本 (.txt)', value: 'txt' },
  { label: 'EPUB 电子书 (.epub)', value: 'epub' },
  { label: 'Markdown (.md)', value: 'md' },
  { label: 'PDF (.pdf)', value: 'pdf' },
  { label: 'HTML (.html)', value: 'html' },
  { label: 'Word (.docx)', value: 'docx' },
  { label: '投稿包 (.zip)', value: 'submission', disabled: true },
]

// ─── 全书导出选项 ──────────────────
const bookScope = ref('all')
const bookLayout = ref('standard')

const scopeOptions = [
  { label: '全书', value: 'all' },
  { label: '指定章节范围', value: 'chapters' },
]

const layoutOptions = [
  { label: '标准布局', value: 'standard' },
  { label: '紧凑布局', value: 'compact' },
  { label: '精美排版', value: 'beautiful' },
]

// 章节范围
const chapterStart = ref(1)
const chapterEnd = ref(10)

// ─── 选择书籍 ──────────────────────
const selectedBookId = ref('')

const selectedBook = computed(() =>
  books.value.find(b => b.id === selectedBookId.value)
)

// ─── 单章导出 ──────────────────────
const chapterNumber = ref(1)

// ─── 导出状态 ──────────────────────
const exporting = ref(false)
const exportProgress = ref(0)
const exportStatus = ref('')  // '' | 'success' | 'error'
const lastExportPath = ref('')

// ─── 方法 ──────────────────────────
async function loadBooks() {
  booksLoading.value = true
  try {
    const res = await api.listBooks()
    books.value = (res as any).books || []
    if (books.value.length > 0 && !selectedBookId.value) {
      selectedBookId.value = books.value[0].id
    }
  } catch {
    books.value = []
  } finally {
    booksLoading.value = false
  }
}

async function doExport() {
  if (!selectedBookId.value) {
    uiStore.showToast('请先选择要导出的作品', 'warning')
    return
  }

  exporting.value = true
  exportProgress.value = 0
  exportStatus.value = ''
  lastExportPath.value = ''

  // 模拟进度
  const progressTimer = setInterval(() => {
    if (exportProgress.value < 90) {
      exportProgress.value += Math.random() * 15
    }
  }, 400)

  try {
    let result: any

    if (exportMode.value === 'submission') {
      result = await api.exportSubmission(selectedBookId.value)
      lastExportPath.value = (result as any).file_path || (result as any).path || ''
    } else if (exportMode.value === 'chapter') {
      result = await api.exportChapter(selectedBookId.value, chapterNumber.value, exportFormat.value)
      lastExportPath.value = (result as any).path || ''
    } else {
      result = await api.exportBook(
        selectedBookId.value,
        exportFormat.value,
        bookScope.value,
        bookLayout.value,
      )
      lastExportPath.value = (result as any).path || ''
    }

    exportProgress.value = 100
    exportStatus.value = 'success'
    uiStore.showToast('导出成功！', 'success')
  } catch (e: any) {
    exportProgress.value = 0
    exportStatus.value = 'error'
    uiStore.showToast(`导出失败: ${e.message}`, 'error')
  } finally {
    clearInterval(progressTimer)
    exporting.value = false
  }
}

// ─── 初始化 ────────────────────────
onMounted(() => {
  loadBooks()
})
</script>

<template>
  <div class="export-view">
    <div class="export-view__header">
      <h2 class="export-view__title">
        <n-icon size="22" :component="ExportOutlined" />
        导出中心
      </h2>
      <p class="export-view__subtitle">将创作内容导出为多种格式，支持单章、全书和投稿包</p>
    </div>

    <div class="export-layout">
      <!-- 左侧：配置区 -->
      <div class="export-config">
        <!-- 选择作品 -->
        <n-card :bordered="true" title="选择作品" size="small" class="export-card">
          <n-spin :show="booksLoading">
            <n-select
              v-model:value="selectedBookId"
              :options="books.map(b => ({ label: b.title, value: b.id }))"
              placeholder="选择要导出的作品"
              :loading="booksLoading"
              filterable
            />
          </n-spin>
        </n-card>

        <!-- 导出模式 -->
        <n-card :bordered="true" title="导出模式" size="small" class="export-card">
          <n-radio-group v-model:value="exportMode" name="export-mode">
            <n-space vertical>
              <n-radio
                v-for="opt in modeOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </n-radio>
            </n-space>
          </n-radio-group>
        </n-card>

        <!-- 格式选择（投稿包不显示） -->
        <n-card
          v-if="exportMode !== 'submission'"
          :bordered="true"
          title="导出格式"
          size="small"
          class="export-card"
        >
          <n-select
            v-model:value="exportFormat"
            :options="formatOptions.filter(o => !o.disabled)"
            placeholder="选择格式"
          />
        </n-card>

        <!-- 全书选项 -->
        <n-card
          v-if="exportMode === 'book'"
          :bordered="true"
          title="全书选项"
          size="small"
          class="export-card"
        >
          <div class="config-group">
            <div class="config-row">
              <span class="config-label">范围</span>
              <n-radio-group v-model:value="bookScope" name="scope" size="small">
                <n-radio
                  v-for="opt in scopeOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </n-radio>
              </n-radio-group>
            </div>

            <div v-if="bookScope === 'chapters'" class="config-row">
              <span class="config-label">章节范围</span>
              <n-space align="center">
                <n-input-number
                  v-model:value="chapterStart"
                  size="small"
                  style="width: 80px"
                  :min="1"
                />
                <span>至</span>
                <n-input-number
                  v-model:value="chapterEnd"
                  size="small"
                  style="width: 80px"
                  :min="chapterStart"
                />
              </n-space>
            </div>

            <div class="config-row">
              <span class="config-label">排版</span>
              <n-radio-group v-model:value="bookLayout" name="layout" size="small">
                <n-radio
                  v-for="opt in layoutOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </n-radio>
              </n-radio-group>
            </div>
          </div>
        </n-card>

        <!-- 单章选项 -->
        <n-card
          v-if="exportMode === 'chapter'"
          :bordered="true"
          title="章节选择"
          size="small"
          class="export-card"
        >
          <div class="config-row">
            <span class="config-label">章节号</span>
            <n-input-number
              v-model:value="chapterNumber"
              size="small"
              style="width: 100px"
              :min="1"
            />
          </div>
        </n-card>

        <!-- 投稿包说明 -->
        <n-card
          v-if="exportMode === 'submission'"
          :bordered="true"
          title="投稿包说明"
          size="small"
          class="export-card"
        >
          <p class="hint-text">
            投稿包将生成包含以下内容的 ZIP 压缩包：<br/>
            • 正文（TXT 格式）<br/>
            • 大纲摘要<br/>
            • 人物设定表<br/>
            • 作品简介（适合投稿平台）
          </p>
        </n-card>
      </div>

      <!-- 右侧：预览与操作 -->
      <div class="export-action">
        <n-card :bordered="true" title="导出摘要" size="small" class="export-card">
          <div v-if="!selectedBook" class="export-empty">
            请在左侧选择作品
          </div>
          <div v-else class="export-summary">
            <div class="summary-row">
              <span class="summary-label">作品</span>
              <span class="summary-value">{{ selectedBook.title }}</span>
            </div>
            <div class="summary-row">
              <span class="summary-label">模式</span>
              <n-tag size="small" :bordered="false" type="info">
                {{ modeOptions.find(m => m.value === exportMode)?.label }}
              </n-tag>
            </div>
            <div v-if="exportMode !== 'submission'" class="summary-row">
              <span class="summary-label">格式</span>
              <n-tag size="small" :bordered="false">
                {{ formatOptions.find(f => f.value === exportFormat)?.label }}
              </n-tag>
            </div>
            <div v-if="exportMode === 'book' && bookScope === 'chapters'" class="summary-row">
              <span class="summary-label">章节</span>
              <span class="summary-value">第 {{ chapterStart }} - {{ chapterEnd }} 章</span>
            </div>
            <div v-if="exportMode === 'chapter'" class="summary-row">
              <span class="summary-label">章节</span>
              <span class="summary-value">第 {{ chapterNumber }} 章</span>
            </div>
          </div>

          <n-divider />

          <!-- 进度条 -->
          <div v-if="exporting || exportStatus" class="export-progress">
            <n-progress
              :percentage="exportProgress"
              :status="exportStatus === 'error' ? 'error' : exportStatus === 'success' ? 'success' : 'default'"
              :indicator-placement="'inside'"
            />
            <p v-if="exportStatus === 'success'" class="progress-hint success">
              导出完成！文件路径：{{ lastExportPath || '已生成' }}
            </p>
            <p v-else-if="exportStatus === 'error'" class="progress-hint error">
              导出失败，请检查后端服务是否正常
            </p>
            <p v-else class="progress-hint">
              正在导出，请稍候...
            </p>
          </div>

          <!-- 导出按钮 -->
          <n-button
            type="primary"
            size="large"
            block
            :loading="exporting"
            :disabled="!selectedBookId || !backendConnected"
            @click="doExport"
          >
            <template #icon>
              <n-icon :component="DownloadOutlined" />
            </template>
            {{ exporting ? '导出中...' : '开始导出' }}
          </n-button>

          <p v-if="!backendConnected" class="disconnected-hint">
            后端未连接，无法执行导出
          </p>
        </n-card>

        <!-- 格式说明 -->
        <n-card :bordered="true" title="格式说明" size="small" class="export-card">
          <div class="format-notes">
            <div v-for="f in formatOptions" :key="f.value" class="format-note">
              <span class="format-note__name">{{ f.label }}</span>
              <span class="format-note__desc">{{ formatDesc[f.value] }}</span>
            </div>
          </div>
        </n-card>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
const formatDesc: Record<string, string> = {
  txt: '通用纯文本，兼容所有设备',
  epub: '电子书标准格式，支持目录和排版',
  md: 'Markdown 格式，适合导入写作工具',
  pdf: '固定版式，适合打印和投稿',
  html: '网页格式，可在浏览器中阅读',
  docx: 'Word 文档，适合进一步编辑',
  submission: '投稿专用包，含正文+大纲+设定',
}
</script>

<style scoped>
.export-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.export-view__header {
  margin-bottom: var(--space-6);
}

.export-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-1) 0;
}

.export-view__subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.export-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  align-items: start;
}

@media (max-width: 900px) {
  .export-layout {
    grid-template-columns: 1fr;
  }
}

.export-config,
.export-action {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.export-card {
  /* inherits */
}

.config-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.config-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.config-label {
  width: 80px;
  flex-shrink: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.export-empty {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.export-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.summary-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.summary-label {
  width: 48px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.summary-value {
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
}

.export-progress {
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

.hint-text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.format-notes {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.format-note {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-xs);
  padding: var(--space-1) 0;
}

.format-note__name {
  width: 100px;
  flex-shrink: 0;
  color: var(--color-text-secondary);
  font-weight: var(--font-semibold);
}

.format-note__desc {
  color: var(--color-text-tertiary);
}
</style>

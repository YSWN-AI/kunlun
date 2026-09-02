<template>
  <div class="prompts-view">
    <!-- 顶部工具栏 -->
    <div class="prompts-view__toolbar">
      <div class="prompts-view__toolbar-left">
        <n-select
          v-model:value="currentBook"
          :options="books"
          size="small"
          placeholder="选择作品"
          class="prompts-view__book-select"
        />
        <n-divider vertical />
        <n-select
          v-model:value="selectedPromptType"
          :options="promptTypeOptions"
          size="small"
          placeholder="提示词类型"
          class="prompts-view__type-select"
        />
      </div>
      
      <div class="prompts-view__toolbar-right">
        <n-button-group>
          <n-button text size="small" @click="importPrompts">
            <template #icon><n-icon :size="16"><ImportOutlined /></n-icon></template>
            导入
          </n-button>
          <n-button text size="small" @click="exportPrompts">
            <template #icon><n-icon :size="16"><ExportOutlined /></n-icon></template>
            导出
          </n-button>
          <n-button type="primary" size="small" @click="createPromptTemplate">
            <template #icon><n-icon :size="16"><PlusOutlined /></n-icon></template>
            创建模板
          </n-button>
        </n-button-group>
      </div>
    </div>

    <div class="prompts-view__main">
      <!-- 左侧提示词列表 -->
      <div class="prompts-view__sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">提示词列表</span>
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索..."
            size="small"
            class="sidebar-search"
          >
            <template #prefix>
              <n-icon :size="14"><SearchOutlined /></n-icon>
            </template>
          </n-input>
        </div>
        
        <div class="prompt-list">
          <div
            v-for="prompt in filteredPrompts"
            :key="prompt.agent"
            class="prompt-item"
            :class="{ 'prompt-item--active': selectedPrompt?.agent === prompt.agent }"
            @click="selectPrompt(prompt)"
          >
            <div class="prompt-item__header">
              <n-icon :size="14"><component :is="getPromptIcon(prompt.source)" /></n-icon>
              <span class="prompt-item__name">{{ getPromptName(prompt.agent) }}</span>
              <n-tag v-if="prompt.has_override" size="small" type="success">已覆盖</n-tag>
            </div>
            <div class="prompt-item__meta">
              <span class="prompt-item__source">{{ getSourceLabel(prompt.source) }}</span>
              <span class="prompt-item__length">{{ prompt.length }}字</span>
            </div>
            <div class="prompt-item__preview">{{ prompt.preview }}</div>
          </div>
        </div>
      </div>

      <!-- 右侧编辑区 -->
      <div class="prompts-view__editor">
        <div v-if="selectedPrompt" class="editor-container">
          <!-- 提示词信息栏 -->
          <div class="editor-header">
            <div class="editor-header__left">
              <h2>{{ getPromptName(selectedPrompt.agent) }}</h2>
              <div class="editor-header__tags">
                <n-tag size="small" :type="selectedPrompt.has_override ? 'success' : 'default'">
                  {{ selectedPrompt.has_override ? '用户自定义' : '系统默认' }}
                </n-tag>
                <n-tag size="small">{{ selectedPrompt.length }} 字</n-tag>
              </div>
            </div>
            <div class="editor-header__right">
              <n-button-group>
                <n-button text size="small" @click="resetPrompt" v-if="selectedPrompt.has_override">
                  <template #icon><n-icon :size="14"><RestOutlined /></n-icon></template>
                  恢复默认
                </n-button>
                <n-button text size="small" @click="copyPrompt">
                  <template #icon><n-icon :size="14"><CopyOutlined /></n-icon></template>
                  复制
                </n-button>
                <n-button type="primary" size="small" @click="savePrompt" :disabled="!hasChanges">
                  <template #icon><n-icon :size="14"><SaveOutlined /></n-icon></template>
                  保存
                </n-button>
              </n-button-group>
            </div>
          </div>

          <!-- 提示词编辑器 -->
          <div class="editor-content">
            <n-input
              v-model:value="editorContent"
              type="textarea"
              :autosize="{ minRows: 20, maxRows: 30 }"
              :maxlength="10000"
              :placeholder="`输入${getPromptName(selectedPrompt.agent)}的提示词内容...`"
              class="prompt-editor"
              @input="onEditorChange"
            />
            <div class="editor-footer">
              <span class="editor-footer__length">{{ editorContent.length }} / 10000</span>
              <span class="editor-footer__hint">支持使用 {{ variable }} 等变量占位符</span>
            </div>
          </div>

          <!-- 变量参考面板 -->
          <div class="variable-panel">
            <div class="variable-panel__header">
              <n-icon :size="16"><CodeOutlined /></n-icon>
              <span>可用变量</span>
            </div>
            <div class="variable-list">
              <div
                v-for="variable in availableVariables"
                :key="variable.name"
                class="variable-item"
                @click="insertVariable(variable.name)"
              >
                <code>{{ variable.name }}</code>
                <span class="variable-description">{{ variable.description }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 未选择提示词时的占位 -->
        <div v-else class="empty-state">
          <n-icon :size="48" class="empty-state__icon"><FileTextOutlined /></n-icon>
          <h3>选择一个提示词进行编辑</h3>
          <p>从左侧列表中选择一个提示词，或创建新的提示词模板</p>
        </div>
      </div>
    </div>

    <!-- 模板管理弹窗 -->
    <n-modal
      v-if="showTemplateModal"
      :show="showTemplateModal"
      :title="templateModalTitle"
      :width="600"
      @update:show="showTemplateModal = false"
    >
      <div class="template-modal">
        <n-form :model="templateForm" label-width="80">
          <n-form-item label="模板名称">
            <n-input v-model:value="templateForm.name" placeholder="输入模板名称" />
          </n-form-item>
          <n-form-item label="模板分类">
            <n-select
              v-model:value="templateForm.category"
              :options="templateCategories"
              placeholder="选择分类"
            />
          </n-form-item>
          <n-form-item label="适用场景">
            <n-select
              v-model:value="templateForm.scenario"
              :options="templateScenarios"
              placeholder="选择场景"
            />
          </n-form-item>
          <n-form-item label="模板内容">
            <n-input
              v-model:value="templateForm.content"
              type="textarea"
              :autosize="{ minRows: 10, maxRows: 15 }"
              placeholder="输入模板内容"
            />
          </n-form-item>
        </n-form>
        <div class="template-modal__actions">
          <n-button @click="showTemplateModal = false">取消</n-button>
          <n-button type="primary" @click="saveTemplate">保存模板</n-button>
        </div>
      </div>
    </n-modal>

    <!-- 预设模板列表弹窗 -->
    <n-modal
      v-if="showPresetsModal"
      :show="showPresetsModal"
      title="预设模板库"
      :width="800"
      @update:show="showPresetsModal = false"
    >
      <div class="presets-modal">
        <div class="presets-modal__filter">
          <n-select
            v-model:value="presetFilter"
            :options="templateCategories"
            placeholder="筛选分类"
            size="small"
          />
        </div>
        <div class="presets-list">
          <div
            v-for="preset in filteredPresets"
            :key="preset.id"
            class="preset-item"
          >
            <div class="preset-item__header">
              <h4>{{ preset.name }}</h4>
              <n-tag size="small">{{ preset.category }}</n-tag>
            </div>
            <p class="preset-item__description">{{ preset.description }}</p>
            <div class="preset-item__actions">
              <n-button text size="small" @click="previewPreset(preset)">预览</n-button>
              <n-button text size="small" type="primary" @click="applyPreset(preset)">应用</n-button>
            </div>
          </div>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, type Component } from 'vue'
import {
  NButton, NButtonGroup, NInput, NSelect, NIcon, NDivider,
  NTag, NForm, NFormItem, NModal,
} from 'naive-ui'
import {
  ImportOutlined, ExportOutlined, PlusOutlined, SearchOutlined,
  RestOutlined, CopyOutlined, SaveOutlined, CodeOutlined,
  FileTextOutlined, FileOutlined, UserOutlined, LockOutlined,
} from '@vicons/antd'
import type { PromptStatus } from '@/types/api'

interface PromptPreset {
  id: string
  name: string
  category: string
  description: string
  content: string
}

// 状态
const currentBook = ref('default')
const selectedPromptType = ref('all')
const searchKeyword = ref('')
const selectedPrompt = ref<PromptStatus | null>(null)
const editorContent = ref('')
const originalContent = ref('')
const hasChanges = ref(false)

// 弹窗状态
const showTemplateModal = ref(false)
const showPresetsModal = ref(false)
const templateModalTitle = ref('创建模板')

// 模板表单
const templateForm = ref({
  name: '',
  category: '',
  scenario: '',
  content: '',
})

const presetFilter = ref('')

// 模拟数据
const books = ref([
  { label: '默认', value: 'default' },
  { label: '我的第一部小说', value: 'book-1' },
  { label: '玄幻世界', value: 'book-2' },
])

const promptTypeOptions = ref([
  { label: '全部', value: 'all' },
  { label: '创作类', value: 'writing' },
  { label: '分析类', value: 'analysis' },
  { label: '审计类', value: 'audit' },
])

const prompts = ref<PromptStatus[]>([
  { agent: 'architect', source: 'system', has_override: false, preview: '作为架构师，你的任务是分析小说大纲...', length: 1200 },
  { agent: 'writer', source: 'user', has_override: true, preview: '你是一位专业的小说作家，请根据以下情节继续创作...', length: 850 },
  { agent: 'auditor', source: 'system', has_override: false, preview: '作为审计员，你需要检查以下内容是否符合要求...', length: 600 },
  { agent: 'polisher', source: 'system', has_override: false, preview: '作为润色师，请优化以下文本的语言表达...', length: 450 },
  { agent: 'character', source: 'session', has_override: false, preview: '根据以下设定，生成角色描述...', length: 380 },
  { agent: 'plotter', source: 'system', has_override: false, preview: '分析当前剧情，提供后续发展建议...', length: 520 },
])

const availableVariables = ref([
  { name: '{{story_context}}', description: '故事上下文' },
  { name: '{{chapter_summary}}', description: '章节摘要' },
  { name: '{{characters}}', description: '角色列表' },
  { name: '{{location}}', description: '当前场景' },
  { name: '{{word_count}}', description: '目标字数' },
  { name: '{{style}}', description: '写作风格' },
  { name: '{{tone}}', description: '语气风格' },
  { name: '{{genre}}', description: '小说类型' },
])

const templateCategories = ref([
  { label: '全部', value: '' },
  { label: '玄幻', value: 'xuanhuan' },
  { label: '仙侠', value: 'xianxia' },
  { label: '都市', value: 'urban' },
  { label: '科幻', value: 'scifi' },
  { label: '悬疑', value: 'mystery' },
])

const templateScenarios = ref([
  { label: '开场', value: 'opening' },
  { label: '对话', value: 'dialogue' },
  { label: '战斗', value: 'battle' },
  { label: '情感', value: 'emotion' },
  { label: '描写', value: 'description' },
])

const presets = ref<PromptPreset[]>([
  { id: '1', name: '玄幻战斗场景', category: 'xuanhuan', description: '适用于描写激烈的玄幻战斗场面', content: '请描写一场激烈的战斗场景，注意动作描写和氛围营造...' },
  { id: '2', name: '仙侠修炼', category: 'xianxia', description: '适用于描写仙侠世界的修炼过程', content: '请详细描写主角的修炼过程，包括心法运转、灵气流动...' },
  { id: '3', name: '都市对话', category: 'urban', description: '适用于都市小说的日常对话', content: '请设计一段自然流畅的对话，展现人物性格...' },
  { id: '4', name: '科幻场景', category: 'scifi', description: '适用于科幻小说的场景描写', content: '请描写一个未来科技场景，注重细节和画面感...' },
])

// 计算属性
const filteredPrompts = computed(() => {
  let result = prompts.value
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(p =>
      p.agent.toLowerCase().includes(keyword) ||
      p.preview.toLowerCase().includes(keyword)
    )
  }
  return result
})

const filteredPresets = computed(() => {
  if (!presetFilter.value) return presets.value
  return presets.value.filter(p => p.category === presetFilter.value)
})

const variable = ref('{{variable}}')

// 方法
const getPromptName = (agent: string) => {
  const names: Record<string, string> = {
    architect: '架构师提示词',
    writer: '作家提示词',
    auditor: '审计员提示词',
    polisher: '润色师提示词',
    character: '角色生成提示词',
    plotter: '剧情推演提示词',
  }
  return names[agent] || agent
}

const getPromptIcon = (source: string) => {
  const icons: Record<string, Component> = {
    system: FileOutlined,
    user: UserOutlined,
    session: LockOutlined,
  }
  return icons[source] || FileTextOutlined
}

const getSourceLabel = (source: string) => {
  const labels: Record<string, string> = {
    system: '系统默认',
    user: '用户自定义',
    session: '会话临时',
  }
  return labels[source] || source
}

const selectPrompt = (prompt: PromptStatus) => {
  selectedPrompt.value = prompt
  // 模拟加载完整内容
  editorContent.value = `这是${getPromptName(prompt.agent)}的完整内容。\n\n${prompt.preview}\n\n继续补充更多内容...`
  originalContent.value = editorContent.value
  hasChanges.value = false
}

const onEditorChange = () => {
  hasChanges.value = editorContent.value !== originalContent.value
}

const savePrompt = () => {
  if (!selectedPrompt.value) return
  // 模拟保存
  hasChanges.value = false
  originalContent.value = editorContent.value
  selectedPrompt.value.has_override = true
  selectedPrompt.value.length = editorContent.value.length
  selectedPrompt.value.preview = editorContent.value.substring(0, 200) + (editorContent.value.length > 200 ? '...' : '')
}

const resetPrompt = () => {
  if (!selectedPrompt.value) return
  editorContent.value = `这是${getPromptName(selectedPrompt.value.agent)}的系统默认内容...`
  originalContent.value = editorContent.value
  hasChanges.value = false
  selectedPrompt.value.has_override = false
}

const copyPrompt = () => {
  navigator.clipboard.writeText(editorContent.value)
}

const insertVariable = (variable: string) => {
  editorContent.value += variable + ' '
}

const importPrompts = () => {
  // 模拟导入
}

const exportPrompts = () => {
  // 模拟导出
}

const createPromptTemplate = () => {
  templateModalTitle.value = '创建模板'
  templateForm.value = { name: '', category: '', scenario: '', content: '' }
  showTemplateModal.value = true
}

const saveTemplate = () => {
  // 模拟保存模板
  showTemplateModal.value = false
}

const previewPreset = (preset: PromptPreset) => {
  selectedPrompt.value = {
    agent: 'custom',
    source: 'preset',
    has_override: false,
    preview: preset.content.substring(0, 200) + (preset.content.length > 200 ? '...' : ''),
    length: preset.content.length,
  }
  editorContent.value = preset.content
  originalContent.value = preset.content
  hasChanges.value = false
  showPresetsModal.value = false
}

const applyPreset = (preset: PromptPreset) => {
  if (!selectedPrompt.value) {
    selectedPrompt.value = {
      agent: 'custom',
      source: 'preset',
      has_override: true,
      preview: preset.content.substring(0, 200) + (preset.content.length > 200 ? '...' : ''),
      length: preset.content.length,
    }
  } else {
    selectedPrompt.value.has_override = true
    selectedPrompt.value.length = preset.content.length
    selectedPrompt.value.preview = preset.content.substring(0, 200) + (preset.content.length > 200 ? '...' : '')
  }
  editorContent.value = preset.content
  originalContent.value = preset.content
  hasChanges.value = false
  showPresetsModal.value = false
}
</script>

<style scoped>
.prompts-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg);
}

/* 顶部工具栏 */
.prompts-view__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
}

.prompts-view__toolbar-left,
.prompts-view__toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.prompts-view__book-select,
.prompts-view__type-select {
  width: 180px;
}

/* 主区域 */
.prompts-view__main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧边栏 */
.prompts-view__sidebar {
  width: 320px;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.sidebar-title {
  font-weight: 600;
  font-size: 14px;
  display: block;
  margin-bottom: var(--space-2);
}

.sidebar-search {
  width: 100%;
}

.prompt-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.prompt-item {
  padding: var(--space-3);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-2);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.prompt-item:hover {
  border-color: var(--color-primary);
}

.prompt-item--active {
  border-color: var(--color-primary);
  background: var(--color-primary-suppl);
}

.prompt-item__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.prompt-item__name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.prompt-item__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-1);
}

.prompt-item__preview {
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 右侧编辑区 */
.prompts-view__editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  overflow-y: auto;
}

.editor-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.editor-header__left h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 var(--space-1);
}

.editor-header__tags {
  display: flex;
  gap: var(--space-1);
}

.editor-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.prompt-editor {
  font-family: var(--font-family-mono);
  font-size: 13px;
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.editor-footer__hint {
  color: var(--color-primary);
}

/* 变量参考面板 */
.variable-panel {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.variable-panel__header {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: var(--space-2);
}

.variable-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.variable-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  min-width: 180px;
  transition: all var(--transition-fast);
}

.variable-item:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-suppl);
}

.variable-item code {
  font-size: 12px;
  color: var(--color-primary);
  font-family: var(--font-family-mono);
}

.variable-description {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
}

.empty-state__icon {
  color: var(--color-text-tertiary);
}

.empty-state h3 {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-state p {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 0;
}

/* 模板弹窗 */
.template-modal {
  padding: var(--space-2);
}

.template-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

/* 预设模板弹窗 */
.presets-modal {
  height: 400px;
  display: flex;
  flex-direction: column;
}

.presets-modal__filter {
  margin-bottom: var(--space-3);
}

.presets-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.preset-item {
  padding: var(--space-3);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.preset-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-1);
}

.preset-item__header h4 {
  font-size: 14px;
  font-weight: 500;
  margin: 0;
}

.preset-item__description {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2);
}

.preset-item__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1);
}
</style>
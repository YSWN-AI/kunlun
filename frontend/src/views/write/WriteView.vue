<script setup lang="ts">
defineOptions({ name: 'WriteView' })

import { ref, computed, onMounted } from 'vue'
import TiptapEditor from '@/components/shared/TiptapEditor.vue'
import WriteToolbar from '@/components/write/WriteToolbar.vue'
import ChapterSidebar from '@/components/write/ChapterSidebar.vue'
import AiToolbar from '@/components/write/AiToolbar.vue'
import SceneCard from '@/components/write/SceneCard.vue'
import AiGenerationToolbar from '@/components/write/AiGenerationToolbar.vue'
import WriteRightPanel from '@/components/write/WriteRightPanel.vue'
import WriteStatusBar from '@/components/write/WriteStatusBar.vue'
import {
  mockBooks, mockChapters, mockVolumeTree,
  mockSettingGroups, mockSnippets, mockScene,
  mockAiTools, mockModelOptions,
} from '@/data/mockWriteData'
import type { AiMessage, OutlineOption, SettingDetail } from '@/types/write'

const sidebarCollapsed = ref(false)
const rightPanelCollapsed = ref(false)
const sidebarTab = ref('chapters')
const rightPanel = ref('ai')

const currentBook = ref('')
const currentChapter = ref('')
const currentChapterId = ref('')
const chapterTitle = ref('')

const editorContent = ref('')
const placeholder = ref('开始创作...')
const editorRef = ref()

const activeTool = ref('continue')
const selectedModel = ref('gpt-4o')
const isGenerating = ref(false)
const generationStatus = ref('')
const generatedWordCount = ref(0)

const aiMessages = ref<AiMessage[]>([])
const aiInput = ref('')

const nextOutlines = ref<OutlineOption[]>([])
const selectedOutlineIndex = ref(-1)

const selectedSetting = ref<SettingDetail | null>(null)

const saveStatus = ref('已保存')
const lastSaveTime = ref('刚刚')
const connectionStatus = ref('已连接')

const books = ref([...mockBooks])
const chapters = ref([...mockChapters])
const volumeTree = ref([...mockVolumeTree])
const settingGroups = ref([...mockSettingGroups])
const snippets = ref([...mockSnippets])
const currentScene = ref({ ...mockScene })
const aiTools = ref([...mockAiTools])
const modelOptions = ref([...mockModelOptions])

const rightPanelTitle = computed(() => {
  const titles: Record<string, string> = {
    ai: 'AI助手',
    outline: '剧情推演',
    setting: '设定详情',
  }
  return titles[rightPanel.value] || '面板'
})

const totalWordCount = computed(() => {
  const text = editorContent.value.replace(/<[^>]*>/g, '')
  const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length
  const englishWords = text.replace(/[\u4e00-\u9fff]/g, ' ').split(/\s+/).filter(Boolean).length
  return chineseChars + englishWords
})

const currentChapterInfo = computed(() => {
  return `${currentChapter.value || '未选择'}`
})

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleRightPanel() {
  rightPanelCollapsed.value = !rightPanelCollapsed.value
}

function toggleVolume(volumeId: string) {
  const volume = volumeTree.value.find(v => v.id === volumeId)
  if (volume) {
    volume.expanded = !volume.expanded
  }
}

function toggleSettingGroup(groupId: string) {
  const group = settingGroups.value.find(g => g.id === groupId)
  if (group) {
    group.expanded = !group.expanded
  }
}

function selectChapter(chapter: { id: string; title: string }) {
  currentChapterId.value = chapter.id
  currentChapter.value = chapter.title
  chapterTitle.value = chapter.title
}

function showSettingDetail(item: { id: string; name: string; type: string }) {
  selectedSetting.value = {
    id: item.id,
    name: item.name,
    type: item.type,
    description: `这是关于${item.name}的详细设定描述...`,
    attributes: item.type === 'character' ? {
      '修为': '筑基期',
      '年龄': '18岁',
      '性格': '沉稳',
    } : {},
    relationships: [
      { id: 'rel-1', type: '师徒', target: '青云子' },
      { id: 'rel-2', type: '同门', target: '苏婉' },
    ],
  }
  rightPanel.value = 'setting'
}

function selectTool(tool: { id: string }) {
  activeTool.value = tool.id
}

function saveDraft() {
  saveStatus.value = '保存中...'
  setTimeout(() => {
    saveStatus.value = '已保存'
    lastSaveTime.value = '刚刚'
  }, 500)
}

function exportChapter() {
}

function openSettings() {
}

function addSnippet() {
}

function insertSnippet(_snippet: unknown) {
}

function editSceneSummary() {
}

function onEditorFocus() {
}

function onEditorBlur() {
}

function openAIChat() {
  rightPanel.value = 'ai'
}

function openNextOutline() {
  rightPanel.value = 'outline'
  if (nextOutlines.value.length === 0) {
    generateOutlines()
  }
}

function sendAIMessage() {
  if (!aiInput.value.trim()) return

  aiMessages.value.push({
    id: Date.now().toString(),
    content: aiInput.value,
    isAI: false,
  })

  aiInput.value = ''

  setTimeout(() => {
    aiMessages.value.push({
      id: (Date.now() + 1).toString(),
      content: '好的，我来帮您分析这段剧情...',
      isAI: true,
    })
  }, 1000)
}

function generateOutlines() {
  nextOutlines.value = [
    {
      title: '选项一：秘境探险',
      description: '林飞在修炼中感受到神秘召唤，前往迷雾森林深处探索，发现上古传承。',
      score: 8.5,
    },
    {
      title: '选项二：宗门危机',
      description: '血魔突然袭击青云宗，林飞挺身而出，与师兄师姐共同御敌。',
      score: 7.8,
    },
    {
      title: '选项三：意外重逢',
      description: '林飞在下山历练时偶遇失散多年的亲人，揭开身世之谜。',
      score: 8.2,
    },
  ]
}

function selectOutline(index: number) {
  selectedOutlineIndex.value = index
}

function applyOutline() {
  if (selectedOutlineIndex.value >= 0) {
    const outline = nextOutlines.value[selectedOutlineIndex.value]
    editorContent.value += `\n\n## ${outline.title}\n\n${outline.description}`
    selectedOutlineIndex.value = -1
  }
}

function applyGeneration() {
  isGenerating.value = false
}

function retryGeneration() {
}

function discardGeneration() {
  isGenerating.value = false
  generatedWordCount.value = 0
}

function splitGeneration() {
}

onMounted(() => {
  generateOutlines()
})
</script>

<template>
  <div class="write-view">
    <WriteToolbar
      :current-book="currentBook"
      :books="books"
      :current-chapter="currentChapter"
      :chapters="chapters"
      :chapter-title="chapterTitle"
      @update:current-book="currentBook = $event"
      @update:current-chapter="currentChapter = $event"
      @update:chapter-title="chapterTitle = $event"
      @toggle-sidebar="toggleSidebar"
      @save-draft="saveDraft"
      @export-chapter="exportChapter"
      @open-settings="openSettings"
    />

    <div class="write-view__main">
      <ChapterSidebar
        :sidebar-collapsed="sidebarCollapsed"
        :volume-tree="volumeTree"
        :sidebar-tab="sidebarTab"
        :setting-groups="settingGroups"
        :snippets="snippets"
        :current-chapter-id="currentChapterId"
        @update:sidebar-tab="sidebarTab = $event"
        @toggle-sidebar="toggleSidebar"
        @toggle-volume="toggleVolume"
        @select-chapter="selectChapter"
        @toggle-setting-group="toggleSettingGroup"
        @show-setting-detail="showSettingDetail"
        @add-snippet="addSnippet"
        @insert-snippet="insertSnippet"
      />

      <div class="write-view__editor-area">
        <AiToolbar
          :ai-tools="aiTools"
          :active-tool="activeTool"
          :selected-model="selectedModel"
          :model-options="modelOptions"
          @select-tool="selectTool"
          @update:selected-model="selectedModel = $event"
          @open-ai-chat="openAIChat"
          @open-next-outline="openNextOutline"
        />

        <div class="editor-container">
          <SceneCard
            :current-scene="currentScene"
            @edit-scene-summary="editSceneSummary"
          />

          <div class="editor-wrapper">
            <tiptap-editor
              ref="editorRef"
              v-model="editorContent"
              :placeholder="placeholder"
              @focus="onEditorFocus"
              @blur="onEditorBlur"
            />
          </div>

          <AiGenerationToolbar
            :is-generating="isGenerating"
            :generation-status="generationStatus"
            :generated-word-count="generatedWordCount"
            :selected-model="selectedModel"
            @apply="applyGeneration"
            @retry="retryGeneration"
            @discard="discardGeneration"
            @split="splitGeneration"
          />
        </div>
      </div>

      <WriteRightPanel
        :right-panel-collapsed="rightPanelCollapsed"
        :right-panel="rightPanel"
        :right-panel-title="rightPanelTitle"
        :ai-messages="aiMessages"
        :ai-input="aiInput"
        :next-outlines="nextOutlines"
        :selected-outline-index="selectedOutlineIndex"
        :selected-setting="selectedSetting"
        @toggle-right-panel="toggleRightPanel"
        @update:ai-input="aiInput = $event"
        @send-ai-message="sendAIMessage"
        @generate-outlines="generateOutlines"
        @select-outline="selectOutline"
        @apply-outline="applyOutline"
      />
    </div>

    <WriteStatusBar
      :total-word-count="totalWordCount"
      :current-chapter-info="currentChapterInfo"
      :save-status="saveStatus"
      :last-save-time="lastSaveTime"
      :connection-status="connectionStatus"
    />
  </div>
</template>

<style scoped>
.write-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg);
}

.write-view__main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.write-view__editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  overflow-y: auto;
}

.editor-wrapper {
  flex: 1;
  min-height: 400px;
}
</style>

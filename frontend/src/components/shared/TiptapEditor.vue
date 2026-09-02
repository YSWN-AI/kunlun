<template>
  <div class="tiptap-editor" :class="{ 'tiptap-editor--focused': isFocused }">
    <!-- 工具栏 -->
    <div v-if="showToolbar" class="tiptap-editor__toolbar">
      <n-button-group>
        <n-button
          v-for="btn in toolbarButtons"
          :key="btn.action"
          text
          size="tiny"
          :type="btn.isActive?.() ? 'primary' : 'default'"
          :title="btn.title"
          @click="btn.run"
        >
          <template #icon><n-icon :size="16"><component :is="btn.icon" /></n-icon></template>
        </n-button>
      </n-button-group>
      <n-divider vertical />
      <n-button-group>
        <n-button text size="tiny" title="撤销" @click="editor?.chain().undo().run()">
          <template #icon><n-icon :size="16"><UndoOutlined /></n-icon></template>
        </n-button>
        <n-button text size="tiny" title="重做" @click="editor?.chain().redo().run()">
          <template #icon><n-icon :size="16"><RedoOutlined /></n-icon></template>
        </n-button>
      </n-button-group>
      <n-divider vertical />
      <n-button text size="tiny" title="清除格式" @click="editor?.chain().clearNodes().unsetAllMarks().run()">
        <template #icon><n-icon :size="16"><ClearOutlined /></n-icon></template>
      </n-button>
      <div class="tiptap-editor__toolbar-right">
        <span class="tiptap-editor__word-count">{{ wordCount }} 字</span>
      </div>
    </div>

    <!-- 编辑器内容区 -->
    <editor-content :editor="editor" class="tiptap-editor__content" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { NButton, NButtonGroup, NIcon, NDivider } from 'naive-ui'
import {
  BoldOutlined, ItalicOutlined, StrikethroughOutlined,
  OrderedListOutlined, UnorderedListOutlined, BlockOutlined,
  UndoOutlined, RedoOutlined, ClearOutlined,
} from '@vicons/antd'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

const props = withDefaults(defineProps<{
  modelValue?: string
  placeholder?: string
  showToolbar?: boolean
  editable?: boolean
}>(), {
  modelValue: '',
  placeholder: '开始创作...',
  showToolbar: true,
  editable: true,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'focus': []
  'blur': []
}>()

const isFocused = ref(false)

const editor = new Editor({
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
    }),
    Placeholder.configure({
      placeholder: props.placeholder,
    }),
  ],
  content: props.modelValue,
  editable: props.editable,
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
  onFocus: () => {
    isFocused.value = true
    emit('focus')
  },
  onBlur: () => {
    isFocused.value = false
    emit('blur')
  },
})

const wordCount = computed(() => {
  const text = editor?.getText() || ''
  // 中文字符 + 英文单词
  const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length
  const englishWords = text.replace(/[\u4e00-\u9fff]/g, ' ').split(/\s+/).filter(Boolean).length
  return chineseChars + englishWords
})

const toolbarButtons = computed(() => [
  {
    title: '加粗',
    icon: BoldOutlined,
    action: 'bold',
    isActive: () => editor?.isActive('bold'),
    run: () => editor?.chain().focus().toggleBold().run(),
  },
  {
    title: '斜体',
    icon: ItalicOutlined,
    action: 'italic',
    isActive: () => editor?.isActive('italic'),
    run: () => editor?.chain().focus().toggleItalic().run(),
  },
  {
    title: '删除线',
    icon: StrikethroughOutlined,
    action: 'strike',
    isActive: () => editor?.isActive('strike'),
    run: () => editor?.chain().focus().toggleStrike().run(),
  },
  {
    title: '有序列表',
    icon: OrderedListOutlined,
    action: 'orderedList',
    isActive: () => editor?.isActive('orderedList'),
    run: () => editor?.chain().focus().toggleOrderedList().run(),
  },
  {
    title: '无序列表',
    icon: UnorderedListOutlined,
    action: 'bulletList',
    isActive: () => editor?.isActive('bulletList'),
    run: () => editor?.chain().focus().toggleBulletList().run(),
  },
  {
    title: '引用块',
    icon: BlockOutlined,
    action: 'blockquote',
    isActive: () => editor?.isActive('blockquote'),
    run: () => editor?.chain().focus().toggleBlockquote().run(),
  },
])

// 监听外部 modelValue 变化
watch(() => props.modelValue, (val) => {
  if (editor && val !== editor.getHTML()) {
    editor.commands.setContent(val, { emitUpdate: false })
  }
})

watch(() => props.editable, (val) => {
  editor?.setEditable(val)
})

onBeforeUnmount(() => {
  editor?.destroy()
})

defineExpose({ editor })
</script>

<style scoped>
.tiptap-editor {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  transition: border-color var(--transition-fast);
}

.tiptap-editor--focused {
  border-color: var(--color-primary);
}

.tiptap-editor__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border-light);
  flex-wrap: wrap;
}

.tiptap-editor__toolbar-right {
  margin-left: auto;
}

.tiptap-editor__word-count {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.tiptap-editor__content {
  min-height: 320px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}

/* Tiptap 内容样式 */
.tiptap-editor__content :deep(.ProseMirror) {
  padding: var(--space-4) var(--space-6);
  outline: none;
  font-size: 15px;
  line-height: 1.8;
  color: var(--color-text-primary);
  min-height: 300px;
}

.tiptap-editor__content :deep(.ProseMirror p) {
  margin: 0 0 0.8em;
}

.tiptap-editor__content :deep(.ProseMirror p:last-child) {
  margin-bottom: 0;
}

.tiptap-editor__content :deep(.ProseMirror h1) {
  font-size: 24px;
  font-weight: 700;
  margin: 1.2em 0 0.6em;
  color: var(--color-text-primary);
}

.tiptap-editor__content :deep(.ProseMirror h2) {
  font-size: 20px;
  font-weight: 600;
  margin: 1em 0 0.5em;
  color: var(--color-text-primary);
}

.tiptap-editor__content :deep(.ProseMirror h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 0.8em 0 0.4em;
  color: var(--color-text-primary);
}

.tiptap-editor__content :deep(.ProseMirror ul),
.tiptap-editor__content :deep(.ProseMirror ol) {
  padding-left: 1.5em;
  margin: 0.4em 0;
}

.tiptap-editor__content :deep(.ProseMirror li) {
  margin: 0.2em 0;
}

.tiptap-editor__content :deep(.ProseMirror blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: var(--space-4);
  margin: 0.6em 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.tiptap-editor__content :deep(.ProseMirror code) {
  background: var(--color-bg-code);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: 13px;
}

.tiptap-editor__content :deep(.ProseMirror pre) {
  background: var(--color-bg-code);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  font-family: var(--font-family-mono);
  font-size: 13px;
  overflow-x: auto;
}

.tiptap-editor__content :deep(.ProseMirror pre code) {
  background: none;
  padding: 0;
}

/* Placeholder */
.tiptap-editor__content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--color-text-tertiary);
  pointer-events: none;
  height: 0;
}

.tiptap-editor__content :deep(.ProseMirror strong) {
  color: var(--color-text-primary);
}

.tiptap-editor__content :deep(.ProseMirror s) {
  color: var(--color-text-tertiary);
}

/* 选中文本 */
.tiptap-editor__content :deep(.ProseMirror ::selection) {
  background: var(--color-primary-suppl);
}

/* 水平线 */
.tiptap-editor__content :deep(.ProseMirror hr) {
  border: none;
  border-top: 1px solid var(--color-border-light);
  margin: 1em 0;
}
</style>

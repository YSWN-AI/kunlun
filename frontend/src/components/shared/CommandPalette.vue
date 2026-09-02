<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="command-palette__overlay" @click="close">
        <div class="command-palette" @click.stop @keydown="onKeydown">
          <!-- 搜索输入 -->
          <div class="command-palette__input">
            <n-icon :size="16" color="var(--color-text-tertiary)">
              <SearchOutlined />
            </n-icon>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              placeholder="输入命令..."
              class="command-palette__field"
              @input="onQueryChange"
            />
            <kbd class="command-palette__hint">Esc</kbd>
          </div>

          <!-- 结果列表 -->
          <div class="command-palette__results">
            <n-scrollbar style="max-height: 320px">
              <div
                v-for="(item, i) in filteredCmds"
                :key="item.keys"
                class="command-palette__item"
                :class="{ active: i === selectedIndex }"
                @click="execute(item)"
                @mouseenter="selectedIndex = i"
              >
                <span class="command-palette__label">{{ item.description }}</span>
                <span class="command-palette__category">{{ item.category }}</span>
                <div class="command-palette__shortcut">
                  <kbd v-for="k in formatKeys(item.keys)" :key="k">{{ k }}</kbd>
                </div>
              </div>
              <div v-if="filteredCmds.length === 0" class="command-palette__empty">
                未找到匹配的命令
              </div>
            </n-scrollbar>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NScrollbar } from 'naive-ui'
import { SearchOutlined } from '@vicons/antd'
import { useUIStore } from '../../stores/ui'
import { useKeyboard } from '../../composables/useKeyboard'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const router = useRouter()
const uiStore = useUIStore()
const { getAllShortcuts } = useKeyboard()

const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement>()

function close() {
  emit('update:modelValue', false)
  query.value = ''
  selectedIndex.value = 0
}

// 聚焦输入框
watch(
  () => props.modelValue,
  (v) => {
    if (v) nextTick(() => inputRef.value?.focus())
  }
)

// 命令列表：快捷键 + 快速导航
const allCommands = computed(() => {
  const cmds = getAllShortcuts().map(s => ({
    keys: s.keys,
    description: s.description,
    category: s.category,
    handler: s.handler,
    type: 'shortcut' as const,
  }))

  // 添加快速导航
  const navItems = [
    { keys: '', description: '创作中心', category: '导航', handler: () => router.push('/write'), type: 'nav' as const },
    { keys: '', description: '作品管理', category: '导航', handler: () => router.push('/books'), type: 'nav' as const },
    { keys: '', description: '仪表盘', category: '导航', handler: () => router.push('/dashboard'), type: 'nav' as const },
    { keys: '', description: '世界设定', category: '导航', handler: () => router.push('/world'), type: 'nav' as const },
    { keys: '', description: '审计中心', category: '导航', handler: () => router.push('/audit'), type: 'nav' as const },
    { keys: '', description: '设置', category: '导航', handler: () => router.push('/settings'), type: 'nav' as const },
  ]

  return [...navItems, ...cmds]
})

const filteredCmds = computed(() => {
  if (!query.value.trim()) return allCommands.value
  const q = query.value.toLowerCase()
  return allCommands.value.filter(
    c => c.description.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)
  )
})

function onQueryChange() {
  selectedIndex.value = 0
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    close()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, filteredCmds.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const cmd = filteredCmds.value[selectedIndex.value]
    if (cmd) execute(cmd)
  }
}

function execute(item: typeof filteredCmds.value[0]) {
  item.handler()
  close()
}

function formatKeys(keys: string): string[] {
  return keys.split('+').map(k => {
    if (k === 'Ctrl') return 'Ctrl'
    if (k === 'Shift') return 'Shift'
    if (k === 'Alt') return 'Alt'
    return k.toUpperCase()
  })
}
</script>

<style scoped>
.command-palette__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  padding-top: 120px;
  z-index: var(--z-command-palette);
}

.command-palette {
  width: 560px;
  max-height: 420px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.command-palette__input {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.command-palette__field {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-family: var(--font-family);
}
.command-palette__field::placeholder {
  color: var(--color-text-tertiary);
}

.command-palette__hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  font-family: var(--font-family-mono);
}

.command-palette__results {
  flex: 1;
  overflow: hidden;
}

.command-palette__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.command-palette__item:hover,
.command-palette__item.active {
  background: var(--color-primary-suppl);
}

.command-palette__label {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.command-palette__category {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-overlay);
}

.command-palette__shortcut {
  display: flex;
  gap: 2px;
}

.command-palette__shortcut kbd {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1px 4px;
  font-family: var(--font-family-mono);
}

.command-palette__empty {
  padding: var(--space-8);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}
</style>

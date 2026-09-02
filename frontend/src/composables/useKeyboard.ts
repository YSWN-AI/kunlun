/**
 * 昆仑创作引擎 — 全局键盘快捷键系统（单例模式）
 * 参考 VS Code 命令面板模式
 * 消除双重 keydown 监听问题
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

let _instance: ReturnType<typeof createKeyboard> | null = null

export interface ShortcutBinding {
  keys: string
  handler: () => void
  description: string
  category: string
}

function normalizeKey(k: string): string {
  const parts = k.toLowerCase().split('+')
  const mods: string[] = []
  let key = ''
  for (const p of parts) {
    if (p === 'ctrl') mods.push('ctrl')
    else if (p === 'shift') mods.push('shift')
    else if (p === 'alt') mods.push('alt')
    else key = p
  }
  mods.sort()
  return [...mods, key].join('+')
}

function createKeyboard() {
  const showCommandPalette = ref(false)
  const registeredShortcuts = ref<ShortcutBinding[]>([])
  const router = useRouter()

  const defaultShortcuts: ShortcutBinding[] = [
    { keys: 'Ctrl+Shift+P', handler: () => { showCommandPalette.value = true }, description: '打开命令面板', category: '全局' },
    { keys: 'Ctrl+B', handler: () => { document.dispatchEvent(new CustomEvent('kunlun:toggle-sidebar')) }, description: '切换侧边栏', category: '导航' },
    { keys: 'Ctrl+\\', handler: () => { document.dispatchEvent(new CustomEvent('kunlun:toggle-right-panel')) }, description: '切换右侧面板', category: '导航' },
    { keys: 'Ctrl+J', handler: () => { document.dispatchEvent(new CustomEvent('kunlun:toggle-statusbar')) }, description: '切换状态栏', category: '导航' },
    { keys: 'Ctrl+1', handler: () => { router.push('/write') }, description: '进入创作中心', category: '导航' },
    { keys: 'Ctrl+2', handler: () => { router.push('/books') }, description: '进入作品管理', category: '导航' },
    { keys: 'Ctrl+3', handler: () => { router.push('/dashboard') }, description: '进入仪表盘', category: '导航' },
    { keys: 'Ctrl+4', handler: () => { router.push('/world') }, description: '进入世界设定', category: '导航' },
    { keys: 'Ctrl+5', handler: () => { router.push('/audit') }, description: '进入审计', category: '导航' },
  ]

  let _mounted = false

  function handleKeydown(e: KeyboardEvent) {
    const target = e.target as HTMLElement
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable

    const mods: string[] = []
    if (e.ctrlKey || e.metaKey) mods.push('ctrl')
    if (e.shiftKey) mods.push('shift')
    if (e.altKey) mods.push('alt')

    const key = e.key === '\\' ? '\\' : e.key.toLowerCase()
    const pressed = [...mods.sort(), key].join('+')

    if (pressed === 'ctrl+shift+p') {
      e.preventDefault()
      showCommandPalette.value = true
      return
    }

    if (isInput) return

    const allShortcuts = [...defaultShortcuts, ...registeredShortcuts.value]
    for (const s of allShortcuts) {
      if (normalizeKey(s.keys) === pressed) {
        e.preventDefault()
        s.handler()
        return
      }
    }
  }

  function ensureMounted() {
    if (_mounted) return
    document.addEventListener('keydown', handleKeydown)
    _mounted = true
  }

  function register(shortcut: ShortcutBinding) {
    registeredShortcuts.value.push(shortcut)
  }

  function unregister(keys: string) {
    const normalized = normalizeKey(keys)
    registeredShortcuts.value = registeredShortcuts.value.filter(s => normalizeKey(s.keys) !== normalized)
  }

  function getAllShortcuts(): ShortcutBinding[] {
    return [...defaultShortcuts, ...registeredShortcuts.value]
  }

  // 首次挂载时注册事件（多次调用只注册一次）
  onMounted(ensureMounted)

  return { showCommandPalette, register, unregister, getAllShortcuts }
}

/** 全局唯一键盘快捷键实例 */
export function useKeyboard() {
  if (!_instance) _instance = createKeyboard()
  return _instance
}

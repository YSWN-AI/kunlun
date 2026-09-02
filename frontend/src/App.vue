<script setup lang="ts">
import { ref, provide, watch } from 'vue'
import { NConfigProvider, NMessageProvider, NDialogProvider } from 'naive-ui'
import { useTheme } from './composables/useTheme'
import AppShell from './layouts/AppShell.vue'
import CommandPalette from './components/shared/CommandPalette.vue'
import GlobalProgress from './components/shared/GlobalProgress.vue'

const { naiveTheme, themeOverrides, isDark } = useTheme()
const showCommandPalette = ref(false)
provide('showCommandPalette', showCommandPalette)

// 主题切换时同步 body class（用于 CSS 变量联动）
watch(isDark, (dark) => {
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.classList.toggle('light', !dark)
}, { immediate: true })
</script>

<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <CommandPalette v-model="showCommandPalette" />
        <GlobalProgress />
        <AppShell />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-family);
  font-size: var(--text-md);
  line-height: var(--leading-normal);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow: hidden;
  background: var(--color-bg-base);
  color: var(--color-text-primary);
}

html, body, #app {
  width: 100%;
  height: 100%;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
::-webkit-scrollbar-track {
  background: var(--color-scrollbar-track);
}
::-webkit-scrollbar-thumb {
  background: var(--color-scrollbar-thumb);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--color-scrollbar-thumb-hover);
}

/* 选区颜色 */
::selection {
  background: rgba(91, 143, 249, 0.25);
  color: var(--color-text-primary);
}

/* 禁止文本选择（非编辑器区域） */
.no-select {
  user-select: none;
}

/* 文本溢出省略 */
.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

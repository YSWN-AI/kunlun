<script setup lang="ts">
import { NButton, NIcon, NTabs, NTabPane } from 'naive-ui'
import {
  ArrowRightOutlined, ArrowDownOutlined, FileTextOutlined,
  ArrowLeftOutlined, PlusOutlined, UserOutlined,
} from '@vicons/antd'
import type { Component } from 'vue'
import type { Volume, SettingGroup, Snippet, ChapterItem, SettingItem } from '@/types/write'

const props = defineProps<{
  sidebarCollapsed: boolean
  volumeTree: Volume[]
  sidebarTab: string
  settingGroups: SettingGroup[]
  snippets: Snippet[]
  currentChapterId: string
}>()

const emit = defineEmits<{
  'update:sidebarTab': [value: string]
  'toggle-sidebar': []
  'toggle-volume': [volumeId: string]
  'select-chapter': [chapter: ChapterItem]
  'toggle-setting-group': [groupId: string]
  'show-setting-detail': [item: SettingItem]
  'add-snippet': []
  'insert-snippet': [snippet: Snippet]
}>()

function getSettingIcon(type: string) {
  const icons: Record<string, Component> = {
    character: UserOutlined,
    location: FileTextOutlined,
    item: PlusOutlined,
  }
  return icons[type] || FileTextOutlined
}
</script>

<template>
  <div class="chapter-sidebar" :class="{ 'chapter-sidebar--collapsed': props.sidebarCollapsed }">
    <div class="sidebar-header">
      <span class="sidebar-title">章节目录</span>
      <n-button text size="tiny" @click="emit('toggle-sidebar')">
        <template #icon><n-icon :size="16"><ArrowLeftOutlined /></n-icon></template>
      </n-button>
    </div>

    <div class="chapter-tree">
      <div
        v-for="volume in props.volumeTree"
        :key="volume.id"
        class="volume-item"
      >
        <div class="volume-header" @click="emit('toggle-volume', volume.id)">
          <n-icon :size="16" class="volume-icon">
            <component :is="volume.expanded ? ArrowDownOutlined : ArrowRightOutlined" />
          </n-icon>
          <span class="volume-name">{{ volume.name }}</span>
          <span class="volume-count">{{ volume.chapters.length }}</span>
        </div>
        <div v-if="volume.expanded" class="chapter-list">
          <div
            v-for="chapter in volume.chapters"
            :key="chapter.id"
            class="chapter-item"
            :class="{ 'chapter-item--active': chapter.id === props.currentChapterId }"
            @click="emit('select-chapter', chapter)"
          >
            <n-icon :size="14"><FileTextOutlined /></n-icon>
            <span class="chapter-title">{{ chapter.title }}</span>
            <span class="chapter-word-count">{{ chapter.wordCount }}字</span>
          </div>
        </div>
      </div>
    </div>

    <div class="sidebar-tabs">
      <n-tabs :value="props.sidebarTab" size="small" @update:value="emit('update:sidebarTab', $event)">
        <n-tab-pane name="chapters" tab="章节">
        </n-tab-pane>
        <n-tab-pane name="settings" tab="设定">
          <div class="setting-tree">
            <div
              v-for="group in props.settingGroups"
              :key="group.id"
              class="setting-group"
            >
              <div class="setting-group-header" @click="emit('toggle-setting-group', group.id)">
                <n-icon :size="14">
                  <component :is="group.expanded ? ArrowDownOutlined : ArrowRightOutlined" />
                </n-icon>
                <span>{{ group.name }}</span>
              </div>
              <div v-if="group.expanded" class="setting-items">
                <div
                  v-for="item in group.items"
                  :key="item.id"
                  class="setting-item"
                  @click="emit('show-setting-detail', item)"
                >
                  <n-icon :size="12"><component :is="getSettingIcon(item.type)" /></n-icon>
                  <span>{{ item.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </n-tab-pane>
        <n-tab-pane name="snippets" tab="片段">
          <div class="snippets-panel">
            <div class="snippets-header">
              <span>灵感片段</span>
              <n-button text size="tiny" @click="emit('add-snippet')">
                <template #icon><n-icon :size="12"><PlusOutlined /></n-icon></template>
              </n-button>
            </div>
            <div class="snippets-list">
              <div
                v-for="snippet in props.snippets"
                :key="snippet.id"
                class="snippet-item"
              >
                <div class="snippet-title">{{ snippet.title }}</div>
                <div class="snippet-content">{{ snippet.content }}</div>
                <div class="snippet-actions">
                  <n-button text size="tiny" @click="emit('insert-snippet', snippet)">
                    <template #icon><n-icon :size="10"><ArrowRightOutlined /></n-icon></template>
                  </n-button>
                </div>
              </div>
            </div>
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<style scoped>
.chapter-sidebar {
  width: 280px;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  overflow: hidden;
}

.chapter-sidebar--collapsed {
  width: 64px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.sidebar-title {
  font-weight: 600;
  font-size: 14px;
}

.chapter-tree {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.volume-item {
  margin-bottom: var(--space-1);
}

.volume-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.volume-header:hover {
  background: var(--color-bg-hover);
}

.volume-icon {
  color: var(--color-text-secondary);
}

.volume-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.volume-count {
  font-size: 12px;
  color: var(--color-text-tertiary);
  background: var(--color-bg-muted);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.chapter-list {
  padding-left: var(--space-4);
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
  margin-bottom: 2px;
}

.chapter-item:hover {
  background: var(--color-bg-hover);
}

.chapter-item--active {
  background: var(--color-primary-suppl);
}

.chapter-title {
  flex: 1;
  font-size: 13px;
}

.chapter-word-count {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.sidebar-tabs {
  border-top: 1px solid var(--color-border);
}

.setting-tree {
  padding: var(--space-2);
}

.setting-group {
  margin-bottom: var(--space-1);
}

.setting-group-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.setting-group-header:hover {
  background: var(--color-bg-hover);
}

.setting-items {
  padding-left: var(--space-4);
}

.setting-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.setting-item:hover {
  background: var(--color-bg-hover);
}

.snippets-panel {
  padding: var(--space-2);
}

.snippets-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  font-size: 13px;
  font-weight: 500;
}

.snippets-list {
  max-height: 200px;
  overflow-y: auto;
}

.snippet-item {
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
}

.snippet-title {
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
}

.snippet-content {
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.snippet-actions {
  margin-top: var(--space-1);
  text-align: right;
}
</style>

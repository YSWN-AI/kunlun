<script setup lang="ts">
import { NButton, NIcon, NInput, NTag } from 'naive-ui'
import {
  ArrowRightOutlined, RobotOutlined, UserOutlined, SendOutlined,
  RestOutlined, StarOutlined, CheckOutlined, LinkOutlined,
} from '@vicons/antd'
import type { AiMessage, OutlineOption, SettingDetail } from '@/types/write'

const props = defineProps<{
  rightPanelCollapsed: boolean
  rightPanel: string
  rightPanelTitle: string
  aiMessages: AiMessage[]
  aiInput: string
  nextOutlines: OutlineOption[]
  selectedOutlineIndex: number
  selectedSetting: SettingDetail | null
}>()

const emit = defineEmits<{
  'toggle-right-panel': []
  'update:aiInput': [value: string]
  'send-ai-message': []
  'generate-outlines': []
  'select-outline': [index: number]
  'apply-outline': []
}>()

function getSettingTypeName(type: string) {
  const names: Record<string, string> = {
    character: '角色',
    location: '地点',
    item: '物品',
  }
  return names[type] || type
}
</script>

<template>
  <div class="write-right-panel" :class="{ 'write-right-panel--collapsed': props.rightPanelCollapsed }">
    <div class="right-panel-header">
      <span class="right-panel-title">{{ props.rightPanelTitle }}</span>
      <n-button text size="tiny" @click="emit('toggle-right-panel')">
        <template #icon><n-icon :size="16"><ArrowRightOutlined /></n-icon></template>
      </n-button>
    </div>

    <div class="right-panel-content">
      <div v-if="props.rightPanel === 'ai'">
        <div class="ai-assistant-panel">
          <div class="ai-assistant-header">
            <span>AI助手</span>
          </div>
          <div class="ai-assistant-chat">
            <div
              v-for="msg in props.aiMessages"
              :key="msg.id"
              class="chat-message"
              :class="{ 'chat-message--ai': msg.isAI }"
            >
              <div class="chat-avatar">
                <n-icon :size="20"><component :is="msg.isAI ? RobotOutlined : UserOutlined" /></n-icon>
              </div>
              <div class="chat-content">{{ msg.content }}</div>
            </div>
          </div>
          <div class="ai-assistant-input">
            <n-input
              :value="props.aiInput"
              placeholder="输入您的问题..."
              @keyup.enter="emit('send-ai-message')"
              @update:value="emit('update:aiInput', $event)"
            />
            <n-button type="primary" @click="emit('send-ai-message')">
              <template #icon><n-icon :size="16"><SendOutlined /></n-icon></template>
            </n-button>
          </div>
        </div>
      </div>

      <div v-if="props.rightPanel === 'outline'">
        <div class="next-outline-panel">
          <div class="next-outline-header">
            <span>剧情推演</span>
            <n-button text size="tiny" @click="emit('generate-outlines')">
              <template #icon><n-icon :size="12"><RestOutlined /></n-icon></template>
              重新生成
            </n-button>
          </div>
          <div class="outline-options">
            <div
              v-for="(outline, index) in props.nextOutlines"
              :key="index"
              class="outline-option"
              :class="{ 'outline-option--selected': props.selectedOutlineIndex === index }"
              @click="emit('select-outline', index)"
            >
              <div class="outline-number">{{ index + 1 }}</div>
              <div class="outline-content">
                <div class="outline-title">{{ outline.title }}</div>
                <div class="outline-description">{{ outline.description }}</div>
              </div>
              <div class="outline-score">
                <n-icon :size="14"><StarOutlined /></n-icon>
                <span>{{ outline.score }}</span>
              </div>
              <n-button
                v-if="props.selectedOutlineIndex === index"
                text
                size="tiny"
                @click.stop="emit('apply-outline')"
              >
                <template #icon><n-icon :size="12"><CheckOutlined /></n-icon></template>
                应用
              </n-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="props.rightPanel === 'setting' && props.selectedSetting">
        <div class="setting-detail-panel">
          <div class="setting-detail-header">
            <span>{{ props.selectedSetting.name }}</span>
            <n-tag size="small">{{ getSettingTypeName(props.selectedSetting.type) }}</n-tag>
          </div>
          <div class="setting-detail-content">
            <div class="setting-detail-section">
              <h4>基本信息</h4>
              <p>{{ props.selectedSetting.description }}</p>
            </div>
            <div class="setting-detail-section" v-if="props.selectedSetting.attributes && Object.keys(props.selectedSetting.attributes).length">
              <h4>属性</h4>
              <div class="setting-attributes">
                <div
                  v-for="(value, key) in props.selectedSetting.attributes"
                  :key="key"
                  class="setting-attribute"
                >
                  <span class="attribute-key">{{ key }}</span>
                  <span class="attribute-value">{{ value }}</span>
                </div>
              </div>
            </div>
            <div class="setting-detail-section" v-if="props.selectedSetting.relationships?.length">
              <h4>关系</h4>
              <div class="setting-relationships">
                <div
                  v-for="rel in props.selectedSetting.relationships"
                  :key="rel.id"
                  class="setting-relationship"
                >
                  <n-icon :size="12"><LinkOutlined /></n-icon>
                  <span>{{ rel.type }}: {{ rel.target }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.write-right-panel {
  width: 320px;
  background: var(--color-bg-elevated);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.write-right-panel--collapsed {
  width: 0;
  padding: 0;
  overflow: hidden;
}

.right-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.right-panel-title {
  font-weight: 600;
  font-size: 14px;
}

.right-panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3);
}

.ai-assistant-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-assistant-header {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: var(--space-2);
}

.ai-assistant-chat {
  flex: 1;
  overflow-y: auto;
  margin-bottom: var(--space-2);
}

.chat-message {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.chat-message--ai .chat-avatar {
  background: var(--color-primary-suppl);
}

.chat-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.chat-content {
  flex: 1;
  font-size: 13px;
  line-height: 1.5;
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
}

.chat-message--ai .chat-content {
  background: var(--color-primary-suppl);
  border-radius: var(--radius-md) 0 var(--radius-md) var(--radius-md);
}

.ai-assistant-input {
  display: flex;
  gap: var(--space-1);
}

.ai-assistant-input :deep(.n-input) {
  flex: 1;
}

.next-outline-panel {
  height: 100%;
}

.next-outline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
  font-size: 13px;
  font-weight: 500;
}

.outline-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.outline-option {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.outline-option:hover {
  border-color: var(--color-primary);
}

.outline-option--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-suppl);
}

.outline-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.outline-content {
  flex: 1;
  min-width: 0;
}

.outline-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
}

.outline-description {
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.outline-score {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-warning);
  flex-shrink: 0;
}

.setting-detail-panel {
  height: 100%;
}

.setting-detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  font-size: 15px;
  font-weight: 600;
}

.setting-detail-content {
  font-size: 13px;
}

.setting-detail-section {
  margin-bottom: var(--space-3);
}

.setting-detail-section h4 {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-1);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.setting-detail-section p {
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.setting-attributes {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.setting-attribute {
  display: flex;
  justify-content: space-between;
  padding: var(--space-1);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.attribute-key {
  color: var(--color-text-secondary);
}

.attribute-value {
  font-weight: 500;
}

.setting-relationships {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.setting-relationship {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  font-size: 12px;
}
</style>

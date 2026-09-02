<template>
  <nav class="activity-bar no-select" aria-label="主导航">
    <div class="activity-bar__top">
      <n-tooltip
        v-for="item in topActivities"
        :key="item.id"
        placement="right"
      >
        <template #trigger>
          <button
            type="button"
            class="activity-bar__item"
            :class="{ active: activeActivity === item.id }"
            :aria-label="item.label"
            :aria-current="activeActivity === item.id ? 'page' : undefined"
            @click="setActivity(item.id)"
          >
            <n-icon :size="22">
              <component :is="activityIcons[item.id]" />
            </n-icon>
            <n-badge
              v-if="item.badge && item.badge > 0"
              :value="item.badge"
              :max="99"
              processing
              class="activity-bar__badge"
            />
            <div class="activity-bar__indicator" v-if="activeActivity === item.id" />
          </button>
        </template>
        {{ item.label }}
      </n-tooltip>
    </div>

    <div class="activity-bar__middle">
      <n-tooltip
        v-for="item in middleActivities"
        :key="item.id"
        placement="right"
      >
        <template #trigger>
          <button
            type="button"
            class="activity-bar__item"
            :class="{ active: activeActivity === item.id }"
            :aria-label="item.label"
            :aria-current="activeActivity === item.id ? 'page' : undefined"
            @click="setActivity(item.id)"
          >
            <n-icon :size="20">
              <component :is="activityIcons[item.id]" />
            </n-icon>
            <div class="activity-bar__indicator" v-if="activeActivity === item.id" />
          </button>
        </template>
        {{ item.label }}
      </n-tooltip>
    </div>

    <div class="activity-bar__bottom">
      <n-tooltip placement="right">
        <template #trigger>
          <button
            type="button"
            class="activity-bar__item"
            aria-label="切换侧边栏"
            @click="toggleSidebar"
          >
            <span class="activity-bar__hint">{{ sidebarVisible ? '◀' : '▶' }}</span>
          </button>
        </template>
        切换侧边栏 (Ctrl+B)
      </n-tooltip>
      <n-tooltip placement="right">
        <template #trigger>
          <button
            type="button"
            class="activity-bar__item"
            aria-label="打开命令面板"
            @click="showCommandPalette = true"
          >
            <n-icon :size="20">
              <SearchOutlined />
            </n-icon>
          </button>
        </template>
        命令面板 (Ctrl+Shift+P)
      </n-tooltip>
      <n-tooltip placement="right">
        <template #trigger>
          <button
            type="button"
            class="activity-bar__item"
            :class="{ active: activeActivity === 'settings' }"
            aria-label="设置"
            :aria-current="activeActivity === 'settings' ? 'page' : undefined"
            @click="setActivity('settings')"
          >
            <n-icon :size="20">
              <SettingOutlined />
            </n-icon>
          </button>
        </template>
        设置
      </n-tooltip>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { NIcon, NTooltip, NBadge } from 'naive-ui'
import {
  EditOutlined,
  BookOutlined,
  DashboardOutlined,
  GlobalOutlined,
  AuditOutlined,
  SettingOutlined,
  SearchOutlined,
  PieChartOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  ApartmentOutlined,
  ExportOutlined,
  MessageOutlined,
  UploadOutlined,
  RocketOutlined,
} from '@vicons/antd'
import { storeToRefs } from 'pinia'
import { computed, type Component } from 'vue'
import { useUIStore, type ActivityId } from '../stores/ui'
import { useRouter } from 'vue-router'

const uiStore = useUIStore()
const router = useRouter()
const { activeActivity, sidebarVisible, visibleActivities } = storeToRefs(uiStore)
const { setActivity: storeSetActivity, toggleSidebar } = uiStore

const activityIcons: Record<ActivityId, Component> = {
  write: EditOutlined,
  books: BookOutlined,
  dashboard: DashboardOutlined,
  world: GlobalOutlined,
  audit: AuditOutlined,
  settings: SettingOutlined,
  analysis: PieChartOutlined,
  abtest: ExperimentOutlined,
  drafts: HistoryOutlined,
  pipeline: ApartmentOutlined,
  export: ExportOutlined,
  prompts: MessageOutlined,
  import: UploadOutlined,
  orchestrator: RocketOutlined,
}

// 核心活动（前段，简洁/完整模式均显示）
const coreIds = ['write', 'books', 'dashboard', 'world', 'audit']
// 辅助活动（中段，仅完整模式显示）
const auxIds = ['analysis', 'abtest', 'drafts', 'pipeline', 'export', 'import', 'prompts', 'orchestrator']

// 直接消费 store 的 visibleActivities（简洁模式唯一真源），避免“看得见点不动”
const topActivities = computed(() =>
  visibleActivities.value.filter(a => coreIds.includes(a.id))
)
const middleActivities = computed(() =>
  visibleActivities.value.filter(a => auxIds.includes(a.id))
)

function setActivity(id: string) {
  const activity = visibleActivities.value.find(a => a.id === id)
  if (activity) {
    storeSetActivity(id as ActivityId)
    router.push(activity.route)
  }
}

const showCommandPalette = defineModel<boolean>('showCommandPalette', { default: false })
</script>

<style scoped>
.activity-bar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--activity-bar-width);
  height: 100%;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
  z-index: var(--z-activity-bar);
}

.activity-bar__top,
.activity-bar__middle,
.activity-bar__bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.activity-bar__middle {
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}

.activity-bar__item {
  position: relative;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  /* 重置原生 button 样式 */
  font: inherit;
  border: none;
  background: transparent;
  padding: 0;
  -webkit-appearance: none;
  appearance: none;
}

.activity-bar__item:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-overlay);
}

.activity-bar__item.active {
  color: var(--color-primary);
  background: var(--color-primary-suppl);
}

/* 键盘可达焦点环 (WCAG 2.4.7) */
.activity-bar__item:focus {
  outline: none;
}
.activity-bar__item:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.activity-bar__indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 20px;
  background: var(--color-primary);
  border-radius: 0 2px 2px 0;
}

.activity-bar__badge {
  position: absolute;
  top: 2px;
  right: 2px;
}

.activity-bar__hint {
  font-size: 10px;
  line-height: 1;
}
</style>

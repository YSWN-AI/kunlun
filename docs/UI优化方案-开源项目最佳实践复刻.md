# 昆仑创作引擎 — UI 优化方案：开源项目最佳实践复刻

> 基于对 Soybean Admin、Naive UI Admin、Obsidian、novelWriter、VS Code、Linear 等优秀开源项目的深度调研，针对当前 UI 的 4 大维度提出可落地的优化方案。

---

## 目录

1. [调研项目概览](#1-调研项目概览)
2. [维度一：组件布局与信息架构](#2-维度一组件布局与信息架构)
3. [维度二：交互动效与状态反馈](#3-维度二维动效与状态反馈)
4. [维度三：视觉风格统一](#4-维度三视觉风格统一)
5. [维度四：响应式设计与跨端适配](#5-维度四响应式设计与跨端适配)
6. [实施路线图](#6-实施路线图)

---

## 1. 调研项目概览

| 项目 | Stars | 技术栈 | 核心设计理念 | 对昆仑的参考价值 |
|------|-------|--------|-------------|-----------------|
| **Soybean Admin** | ~15k | Vue3 + NaiveUI + UnoCSS | 清新优雅、多组件库适配、CSS变量设计token体系 | ⭐⭐⭐⭐⭐ 同技术栈，直接可复刻 |
| **Naive UI Admin** | ~6k | Vue3 + NaiveUI + TypeScript | 二次封装组件、动态路由权限、暗色主题最佳实践 | ⭐⭐⭐⭐ 组件封装模式 |
| **Obsidian** | - | Electron + Plugin | 多窗格工作区、标签页系统、侧边栏停靠、命令面板 | ⭐⭐⭐⭐⭐ 创作工具信息架构 |
| **novelWriter** | ~2k | Python + Qt5 | 项目树+编辑器+大纲三面板、章节组织、纯文本哲学 | ⭐⭐⭐⭐ 写作工具专用布局 |
| **VS Code** | - | Electron + Monaco | 活动栏+侧边栏+编辑器+面板四区布局、命令面板、快捷键体系 | ⭐⭐⭐⭐ IDE级交互范式 |
| **Linear** | - | React | 极简暗色、微交互、快捷键驱动、状态可视化 | ⭐⭐⭐ 交互动效与精致感 |

---

## 2. 维度一：组件布局与信息架构

### 2.1 当前问题诊断

| 问题 | 严重程度 | 涉及文件 | 开源对照 |
|------|----------|---------|---------|
| 右侧面板数据全是硬编码假数据 | 🔴 严重 | `MainLayout.vue` L199-254 | Obsidian/novelWriter 面板数据全部来自 Store/API |
| ContentTree 组件未复用，多处手写章节树 | 🔴 严重 | `ContentTree.vue` vs `MainLayout.vue` L71-101 | Soybean Admin 高度组件复用 |
| 4个导航入口过少，无法承载功能增长 | 🟡 中等 | `MainLayout.vue` L180-185 | VS Code 活动栏 + 侧边栏双层导航 |
| RichEditor 与 CreateCenter 的 AI 工具栏功能重叠 | 🟡 中等 | `CreateCenter.vue` + `RichEditor.vue` | - |
| 多个视图为空壳 | 🟡 中等 | `SearchView.vue`, `SnapshotView.vue` 等 | - |

### 2.2 布局架构优化方案

#### 2.2.1 参考：VS Code / Obsidian 四区布局

```
┌───────────┬─────────────────────────┬──────────────────┐
│ ACTIVITY  │  PRIMARY SIDEBAR        │  MAIN CONTENT    │  SECONDARY
│ BAR       │  (可折叠, 200-300px)    │  (flex: 1)       │  SIDEBAR
│ 48-56px   │  ┌───────────────────┐  │                  │  320px
│           │  │ 项目树 / 大纲     │  │  ┌────────────┐  │
│  📖 作品  │  │ 角色列表          │  │  │ Top Bar    │  │
│  ✍️ 写作  │  │ 世界观            │  │  ├────────────┤  │
│  📊 分析  │  │                   │  │  │            │  │
│  🗂️ 设定  │  │                   │  │  │ <router    │  │
│           │  │                   │  │  │  -view/>   │  │
│  ⚙️ 设置  │  └───────────────────┘  │  │            │  │
│           │  ┌───────────────────┐  │  ├────────────┤  │
│           │  │ 状态栏            │  │  │ Status Bar │  │
│           │  └───────────────────┘  │  └────────────┘  │
└───────────┴─────────────────────────┴──────────────────┘
```

**关键改进：**

1. **活动栏 (Activity Bar)**: 48-56px 宽，仅图标，点击切换侧边栏内容
   - 参考 VS Code：每个活动切换不同的侧边栏视图
   - 当前 72px 宽导航 → 缩减至 48px，图标 + tooltip

2. **主侧边栏 (Primary Sidebar)**: 200-300px 可拖拽宽度
   - 默认显示项目树（章节结构 + 角色 + 设定 + 片段）
   - 根据活动栏选中项切换内容
   - **将当前右侧面板内容合并到此处**，消除右侧面板

3. **次级侧边栏 (Right Panel)**: 可选，用于辅助信息
   - 参考 Obsidian：放 AI 输出结果、审计报告、片段收藏
   - 默认关闭，通过快捷键 `Ctrl+B` 切换

#### 2.2.2 导航结构重构

**当前 (4 项) → 优化后 (5 项 + 活动切换)**

```
活动栏 (Activity Bar):
  📖 作品管理  → 侧边栏显示：项目列表 + 章节树
  ✍️ 创作中心  → 侧边栏显示：当前章节目录 + AI工具面板  
  📊 仪表盘    → 侧边栏显示：统计筛选器
  🗂️ 世界设定  → 侧边栏显示：角色/地点/势力/规则
  ⚙️ 更多      → 侧边栏显示：搜索/快照/导出/设置
```

**实现要点：**
- 使用 Pinia Store 管理侧边栏可见性和活动项状态
- 侧边栏宽度支持拖拽调整（参考 VS Code 的 `resize` 逻辑）
- 活动栏图标增加活动指示器（左侧 2px 色条 + 背景高亮）

#### 2.2.3 信息架构：消除"假数据层"

**核心原则参考 novelWriter/Obsidian：所有展示数据必须来自真实数据源**

| 当前位置 | 当前问题 | 对策 |
|---------|---------|------|
| `MainLayout.vue` `volumeData` | 硬编码2卷5章 | 从 `bookStore.chapters` 获取，接入真实 API → `GET /api/books/{id}/chapters` |
| `MainLayout.vue` `characters` | 硬编码4角色 | 从 `characterStore` 获取 → `GET /api/world/characters` |
| `MainLayout.vue` `locations`/`factions`/`worldRules` | 全部硬编码 | 接入 WorldStore |
| `DashboardView.vue` 图表数据 | API 失败后降级到 demo 数据 | 保持 demo 但加明确的 "Demo Mode" 标识 |
| `CreateCenter.vue` `nextOutlineOptions` | 硬编码3个选项 | 接入 AI outline 生成 API |

#### 2.2.4 内容区布局优化

**参考 Soybean Admin 的卡片式布局模式：**

```vue
<!-- CreateCenter.vue 优化后结构 -->
<div class="editor-workspace">
  <!-- 1. AI 工具栏区域 (固定顶部) -->
  <EditorToolbar 
    :loading="generating"
    :word-count="wordCount"
    @action="handleAi"
  />

  <!-- 2. Pipeline 进度 (仅生成时显示) -->
  <Transition name="slide-down">
    <GenerationPipeline 
      v-if="generating" 
      :steps="pipelineSteps"
      :current="pipelineStep" 
      :progress="pipelineProgress"
    />
  </Transition>

  <!-- 3. 编辑器主区域 (flex: 1) -->
  <div class="editor-main">
    <RichEditor ref="editorRef" v-model="draft" />
    
    <!-- 4. 右侧辅助面板 (可选) -->
    <Transition name="slide-left">
      <AIAssistPanel v-if="showAiPanel" @close="showAiPanel = false" />
    </Transition>
  </div>

  <!-- 5. 底部状态栏 -->
  <StatusBar 
    :chapter-info="chapterInfo"
    :last-saved="lastSaved"
    :ai-status="aiStatus"
  />
</div>
```

---

## 3. 维度二维动效与状态反馈

### 3.1 当前问题

| 问题 | 涉及文件 | 对照 |
|------|---------|------|
| **无路由过渡动画** | `MainLayout.vue` `<router-view />` | Soybean Admin: `<transition name="fade-slide">` 包裹 router-view |
| **无骨架屏 (Skeleton)** | 全部加载态 | Naive UI Admin: 使用 `n-skeleton` 组件 |
| **无乐观更新** | 所有操作必须等待 API 响应 | Linear: 操作立即反映到 UI，后台同步 |
| **无键盘快捷键** | 仅 web/index.html 有 Enter | VS Code: 完整快捷键体系 |
| **Loading 态仅按钮 spinner** | 各处 `:loading` | Linear: 进度条 + 骨架屏 + 乐观更新结合 |
| **错误处理统一粗糙** | `ui.showToast(error, 'error')` | Soybean Admin: 分级错误展示 |

### 3.2 交互优化方案

#### 3.2.1 路由过渡动画

```vue
<!-- MainLayout.vue -->
<router-view v-slot="{ Component, route }">
  <transition name="fade-slide" mode="out-in">
    <component :is="Component" :key="route.path" />
  </transition>
</router-view>
```

```css
/* 全局过渡动画 - 参考 Soybean Admin */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
```

#### 3.2.2 骨架屏系统

**建立统一的 Loading 状态组件：**

```vue
<!-- components/SkeletonLoader.vue -->
<template>
  <div class="skeleton-container">
    <!-- 列表骨架 -->
    <n-skeleton v-if="type === 'list'" text :repeat="3" />
    
    <!-- 卡片骨架 -->
    <div v-if="type === 'cards'" class="skeleton-cards">
      <n-skeleton v-for="i in 4" :key="i" height="120" />
    </div>
    
    <!-- 编辑器骨架 -->
    <div v-if="type === 'editor'" class="skeleton-editor">
      <n-skeleton height="32" width="60%" />
      <n-skeleton text :repeat="5" style="margin-top: 16px" />
    </div>
    
    <!-- 图表骨架 -->
    <n-skeleton v-if="type === 'chart'" height="280" />
  </div>
</template>
```

**使用场景映射：**

| 页面 | 骨架类型 | 触发时机 |
|------|---------|---------|
| DashboardView | `chart` + `cards` | 统计数据加载中 |
| BookManager | `list` | 作品列表加载中 |
| CreateCenter | `editor` | 章节内容加载中 |
| WorldView | `cards` | 世界观数据加载中 |
| AuditView | `list` | 审计结果加载中 |

#### 3.2.3 状态反馈机制增强

**参考 Linear 的三层反馈体系：**

```typescript
// stores/feedback.ts — 全局反馈 Store
export const useFeedbackStore = defineStore('feedback', () => {
  // Level 1: Toast (轻量操作结果)
  const showToast = (msg: string, type: 'success' | 'error' | 'warning' | 'info') => { ... }
  
  // Level 2: 内联通知 (区域级状态)
  const inlineNotice = ref<{
    show: boolean
    type: 'loading' | 'error' | 'empty' | 'success'
    message: string
    action?: { label: string; onClick: () => void }
  }>({ show: false, type: 'loading', message: '' })
  
  // Level 3: 全局进度 (长时间操作)
  const globalProgress = ref<{
    show: boolean
    percent: number
    label: string
  }>({ show: false, percent: 0, label: '' })
  
  return { showToast, inlineNotice, globalProgress }
})
```

#### 3.2.4 AI 生成状态可视化

**当前问题**: Pipeline 进度条只有 8 步固定动画，没有真实的步进反馈。

**优化方案 (参考 AI 聊天工具的 streaming 模式):**

```vue
<!-- GenerationPipeline.vue - 优化后 -->
<div class="pipeline-visual">
  <!-- 步骤列表 -->
  <div class="pipe-steps">
    <div v-for="(step, i) in steps" :key="i" 
      class="pipe-step"
      :class="{
        active: i === currentStep,
        done: i < currentStep,
        pending: i > currentStep
      }">
      <!-- 步骤图标旋转动画 (进行中) -->
      <span v-if="i === currentStep" class="step-spinner">⟳</span>
      <!-- 完成打勾 -->
      <span v-else-if="i < currentStep" class="step-check">✓</span>
      <!-- 待处理 -->
      <span v-else class="step-dot">○</span>
      <span class="step-label">{{ step }}</span>
    </div>
  </div>
  
  <!-- 实时状态文本 (Streaming 式反馈) -->
  <div class="pipe-status">
    <span class="status-icon">⌨️</span>
    <Transition name="fade" mode="out-in">
      <span :key="statusText" class="status-text">{{ statusText }}</span>
    </Transition>
    <!-- 打字光标动画 -->
    <span class="typing-cursor">|</span>
  </div>
  
  <!-- 生成字数实时计数 -->
  <div class="pipe-stats">
    <span>已生成 {{ generatedWords }} 字</span>
    <n-progress type="line" :percentage="progress" :height="2" 
      :show-indicator="false" color="#5B8FF9" rail-color="#1E2030" />
  </div>
</div>
```

#### 3.2.5 键盘快捷键体系

**参考 VS Code 的 `Ctrl+Shift+P` 命令面板模式：**

```typescript
// composables/useKeyboard.ts
export function useKeyboard() {
  const shortcuts = {
    // 创作
    'Ctrl+S': () => saveDraft(),
    'Ctrl+Enter': () => handleAi('continue'),
    'Ctrl+Shift+P': () => showCommandPalette.value = true,
    
    // 导航
    'Ctrl+1': () => setActiveView('write'),
    'Ctrl+2': () => setActiveView('books'),
    'Ctrl+3': () => setActiveView('dashboard'),
    'Ctrl+4': () => setActiveView('world'),
    
    // 面板
    'Ctrl+B': () => toggleLeftSidebar(),
    'Ctrl+J': () => toggleBottomPanel(),
    'Ctrl+\\': () => toggleRightPanel(),
    
    // 编辑
    'Ctrl+Z': () => undoManager.undo(),
    'Ctrl+Shift+Z': () => undoManager.redo(),
    'Ctrl+F': () => showSearch.value = true,
  }
  
  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
  })
}
```

---

## 4. 维度三：视觉风格统一

### 4.1 当前问题：两套配色系统并存

```
旧主题 (至少6个文件在用)          新主题 (MainLayout 在用)
─────────────────────────        ─────────────────────────
背景: #141414 / #0d0d0d          背景: #0F1117
主色: #c9a959 (金色)              主色: #5B8FF9 (蓝色)
卡片: #222                        卡片: #161822
边框: #333                        边框: #1E2030 / #252839
```

**受影响文件:**
- `RichEditor.vue` — 完整旧主题
- `DashboardView.vue` — 混合两套主题
- `ContentTree.vue` — 旧主题 (#0d0d0d + #c9a959)
- `BookManager.vue` — 旧主题
- `web/index.html` — 第三套配色 (#0f172a + #6366f1)
- `web/config.html` — 第四套配色 (#0a0e14 + #3b82f6)

### 4.2 统一配色方案

#### 4.2.1 设计 Token 体系 (参考 Soybean Admin)

```css
/* styles/tokens.css — 全局 CSS 变量 */
:root {
  /* ===== 主色调 ===== */
  --color-primary: #5B8FF9;
  --color-primary-hover: #6DA0FA;
  --color-primary-pressed: #4A7DE8;
  --color-primary-suppl: rgba(91, 143, 249, 0.1);
  
  /* ===== 语义色 ===== */
  --color-success: #52C41A;
  --color-warning: #FAAD14;
  --color-error: #FF4D4F;
  --color-info: #5B8FF9;
  
  /* ===== 表面色 (暗色主题) ===== */
  --color-bg-base: #0F1117;       /* 页面背景 */
  --color-bg-elevated: #161822;    /* 卡片/弹窗背景 */
  --color-bg-overlay: #1A1D2E;     /* 输入框/选中背景 */
  --color-bg-mask: rgba(0,0,0,0.5);/* 遮罩层 */
  
  /* ===== 边框色 ===== */
  --color-border-light: #1E2030;   /* 分割线/容器边框 */
  --color-border: #252839;         /* 输入框/卡片边框 */
  --color-border-hover: #3A3F55;   /* 悬停边框 */
  
  /* ===== 文本色 ===== */
  --color-text-primary: #E8EAED;   /* 主文本 */
  --color-text-secondary: #B0B3BD; /* 次级文本 */
  --color-text-tertiary: #6B6F7B;  /* 辅助文本 */
  --color-text-disabled: #4A4E5A;  /* 禁用文本 */
  
  /* ===== 排版 ===== */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  /* 字体大小层级 */
  --text-xs: 10px;
  --text-sm: 12px;
  --text-base: 13px;
  --text-md: 14px;
  --text-lg: 16px;
  --text-xl: 20px;
  --text-2xl: 24px;
  
  /* ===== 间距系统 (4px 基准) ===== */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  
  /* ===== 圆角 ===== */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 10px;
  --radius-xl: 14px;
  
  /* ===== 阴影 ===== */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.5);
  
  /* ===== 过渡 ===== */
  --transition-fast: 0.12s ease;
  --transition-normal: 0.2s ease;
  --transition-slow: 0.3s ease;
}
```

#### 4.2.2 Naive UI 主题统一

```typescript
// composables/useTheme.ts
import { darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

export const kunlunThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#5B8FF9',
    primaryColorHover: '#6DA0FA',
    primaryColorPressed: '#4A7DE8',
    primaryColorSuppl: 'rgba(91,143,249,0.1)',
    // ... 完整映射到 CSS 变量
  }
}

export const kunlunDarkTheme = darkTheme
```

#### 4.2.3 逐个文件配色迁移清单

| 文件 | 当前主色 | 目标主色 | 工作量 |
|------|---------|---------|--------|
| `RichEditor.vue` | `#c9a959` (金) | `var(--color-primary)` | 🔴 大 |
| `DashboardView.vue` | 混用 `#c9a959` + `#141414` | 统一 token | 🟡 中 |
| `ContentTree.vue` | `#0d0d0d` + `#c9a959` | 统一 token | 🟡 中 |
| `BookManager.vue` | 旧主题色 | 统一 token | 🟡 中 |
| `BookWizard.vue` | 需确认 | 统一 token | 🟢 小 |
| `web/index.html` | `#0f172a` + `#6366f1` | 同步到主主题或独立风格 | 🟡 中 |

**迁移策略：**
1. 先创建 `styles/tokens.css`，全局引入
2. 用 CSS 变量替换所有硬编码颜色
3. 逐文件替换，每个文件完成后验证

#### 4.2.4 图标系统升级：Emoji → SVG Icons

**当前问题**: 全部使用 Emoji 作为图标，不同平台的 Emoji 渲染差异大。

**优化方案**: 使用 Naive UI 内置的 `@vicons` 图标库

```typescript
// composables/useIcons.ts
import {
  EditOutlined, BookOutlined, DashboardOutlined, 
  SettingOutlined, FileTextOutlined, UserOutlined,
  EnvironmentOutlined, TeamOutlined, BulbOutlined,
  SearchOutlined, SaveOutlined, ExportOutlined,
  RobotOutlined, AuditOutlined, CheckCircleOutlined,
} from '@vicons/antd'

export const navIcons = {
  write: EditOutlined,
  books: BookOutlined,
  dashboard: DashboardOutlined,
  world: SettingOutlined,  // 或使用 GlobeOutline
  settings: SettingOutlined,
}
```

**迁移量**：约 40+ 处 Emoji 替换为 SVG 图标组件。

#### 4.2.5 排版规范

```
标题层级:
  H1: 24px / 700 weight / margin-bottom: 24px
  H2: 20px / 600 weight / margin-bottom: 16px  
  H3: 16px / 600 weight / margin-bottom: 12px
  H4: 14px / 600 weight / margin-bottom: 8px

正文: 13px / 400 weight / line-height: 1.6
小字: 12px / 400 weight / line-height: 1.5
辅助文字: 10-11px / 400 weight

编辑器内文字: 15px / 400 weight / line-height: 1.8  (阅读舒适度)
```

---

## 5. 维度四：响应式设计与跨端适配

### 5.1 当前状态

- 仅 2 个文件有 `@media` 查询：`DashboardView.vue` (900px)、`web/index.html` (768px)
- 这是桌面优先应用，但 Tauri 桌面窗口可调整大小
- `web/` 和 `frontend/` 是两套完全独立的 UI

### 5.2 响应式断点策略

**参考 Soybean Admin 的断点设计（Tauri 桌面端适用）：**

```css
/* 桌面超宽 (Tauri 最大化) */
@media (min-width: 1600px) { /* 显示全部面板 */ }

/* 桌面标准 (Tauri 默认窗口 ~1200-1400px) */
@media (min-width: 1200px) { /* 当前默认状态 */ }

/* 桌面窄窗 (窗口缩小到 ~900-1200px) */
@media (min-width: 900px) and (max-width: 1199px) {
  /* 隐藏右侧次级面板，侧边栏折叠为图标模式 */
}

/* 平板/小窗 (~600-900px) */
@media (min-width: 600px) and (max-width: 899px) {
  /* 单列布局，活动栏 + 内容区 */
}

/* 移动端 (Tauri 移动版预留) */
@media (max-width: 599px) {
  /* 底部导航 + 全屏内容 */
}
```

### 5.3 侧边栏自适应策略

**参考 Obsidian 的响应式侧边栏：**

```vue
<!-- composables/useResponsive.ts -->
<script setup>
const windowWidth = ref(window.innerWidth)
const leftSidebarVisible = ref(true)
const rightPanelVisible = ref(false)

// 窗口缩小时自动折叠侧边栏
watch(windowWidth, (w) => {
  if (w < 900) {
    leftSidebarVisible.value = false
    rightPanelVisible.value = false
  }
})

// 侧边栏可拖拽调整宽度 (200px - 400px)
const sidebarWidth = ref(260)
const isResizing = ref(false)
</script>
```

### 5.4 跨端适配：Tauri 桌面端特性

```typescript
// composables/useTauri.ts
import { appWindow } from '@tauri-apps/api/window'

// 窗口状态管理
export function useTauriWindow() {
  const isMaximized = ref(false)
  const isFullscreen = ref(false)
  
  // 监听窗口大小变化
  appWindow.onResized(({ payload: size }) => {
    windowWidth.value = size.width
  })
  
  // 原生标题栏集成
  const toggleMaximize = () => appWindow.toggleMaximize()
  const minimize = () => appWindow.minimize()
  const close = () => appWindow.close()
}
```

### 5.5 web/ 与 frontend/ 的整合策略

**当前**: 两套完全独立的 UI → **建议**: 统一为 Vue 前端

| web/ 功能 | 迁移到 Vue |
|-----------|-----------|
| Vibe Writing 聊天页面 | → `VibeChatView.vue`，使用 Naive UI 组件 |
| 配置中心 | → 已存在 `ConfigCenter.vue`，合并差异 |
| 纯文本导出 | → `ExportView.vue` 已有雏形 |

---

## 6. 实施路线图

### Phase 1：配色统一 (1-2天)

```
□ 创建 styles/tokens.css (CSS 变量)
□ 创建 composables/useTheme.ts (Naive UI 主题覆盖)
□ 迁移 RichEditor.vue 配色 (旧金 → 新蓝)
□ 迁移 DashboardView.vue 配色
□ 迁移 ContentTree.vue 配色
□ 迁移 BookManager.vue 配色
□ 迁移 BookWizard.vue 配色
□ 全量检查：搜索 #c9a959, #141414, #0d0d0d, #222 确保无残留
```

### Phase 2：信息架构重构 (2-3天)

```
□ 重构 MainLayout 为 VS Code 风格四区布局
□ Activity Bar 组件 (48px 图标栏)
□ Primary Sidebar 组件 (可拖拽宽度)
□ 将右侧面板内容合并到主侧边栏
□ 侧边栏数据接入真实 Store/API
□ DashboardView 假数据替换为真实 API 数据
□ 删除 ContentTree.vue 的冗余手写版本，统一使用组件
```

### Phase 3：交互增强 (2-3天)

```
□ SkeletonLoader 组件开发
□ 路由过渡动画 (fade-slide)
□ 全局反馈系统 (FeedbackStore + 三层反馈)
□ AI Pipeline 实时状态可视化
□ 键盘快捷键系统 (useKeyboard.ts)
□ 命令面板 (CommandPalette.vue)
□ 乐观更新模式 (草稿保存先更新 UI 再同步后端)
```

### Phase 4：图标+排版+响应式 (1-2天)

```
□ Emoji → @vicons/antd 图标迁移 (40+处)
□ 排版规范统一 (字体大小层级 + 行高)
□ 响应式断点实现 + 侧边栏自适应
□ Tauri 窗口集成 (原生标题栏)
□ web/ 功能评估并整合到 Vue 前端
```

### 预估总工期：6-10天

---

## 附录：关键文件变更清单

| 文件 | Phase | 变更类型 |
|------|-------|---------|
| `frontend/src/styles/tokens.css` | 1 | **新建** |
| `frontend/src/composables/useTheme.ts` | 1 | **新建** |
| `frontend/src/layouts/MainLayout.vue` | 2 | 重构 |
| `frontend/src/layouts/ActivityBar.vue` | 2 | **新建** |
| `frontend/src/layouts/PrimarySidebar.vue` | 2 | **新建** |
| `frontend/src/components/RichEditor.vue` | 1 | 配色重写 |
| `frontend/src/components/SkeletonLoader.vue` | 3 | **新建** |
| `frontend/src/components/CommandPalette.vue` | 3 | **新建** |
| `frontend/src/views/DashboardView.vue` | 1+2 | 配色+数据源 |
| `frontend/src/views/CreateCenter.vue` | 2+3 | 布局+动效 |
| `frontend/src/components/ContentTree.vue` | 1 | 配色 |
| `frontend/src/stores/feedback.ts` | 3 | **新建** |
| `frontend/src/composables/useKeyboard.ts` | 3 | **新建** |
| `frontend/src/composables/useResponsive.ts` | 4 | **新建** |
| `web/index.html` | - | 评估后整合或保留 |

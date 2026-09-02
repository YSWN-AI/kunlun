<script setup lang="ts">import { ref, onMounted, onUnmounted } from 'vue';
import { NButton, NCard, NInput, NProgress, NMessageProvider, NSpace, NDivider, NTag, NList, NListItem, NIcon } from 'naive-ui';
import { MessageOutlined, SendOutlined, PlayCircleOutlined, CheckCircleOutlined, ClockCircleOutlined, LeftCircleOutlined, RestOutlined, RocketOutlined, ShakeOutlined } from '@vicons/antd';
import { api } from '../../api';
import { useUIStore } from '../../stores/ui';
const uiStore = useUIStore();
// 状态
const inputText = ref('');
const conversation = ref<Array<{
 role: string;
 content: string;
 timestamp: Date;
}>>([]);
const isProcessing = ref(false);
const progress = ref(0);
const currentTask = ref('');
const taskSteps = ref<Array<{
 id: string;
 name: string;
 status: 'pending' | 'running' | 'completed' | 'failed';
 message: string;
}>>([]);
const showApproval = ref(false);
const approvalTask = ref<{
 taskId: string;
 subtaskId: string;
 name: string;
} | null>(null);
// 示例指令
const examples = [
 '我想写一本玄幻小说，主角从废柴开始逆袭',
 '构建一个东方玄幻世界观',
 '设计三个主要角色',
 '写第一章，主角获得奇遇',
 '让节奏更快一些',
 '检查质量',
 '这本书怎么样了',
];
// WebSocket连接
let ws: WebSocket | null = null;
function connectWS() {
 if (ws)
 ws.close();
 const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
 const host = window.location.host;
 ws = new WebSocket(`${protocol}//${host}/api/orchestrator/ws/${Date.now()}`);
 ws.onmessage = (event) => {
 const data = event.data;
 console.log('WebSocket message:', data);
 // 更新进度显示
 try {
 const [taskId, message] = data.split(': ', 2);
 if (message.includes('执行')) {
 const stepName = message.replace('执行: ', '');
 const step = taskSteps.value.find(s => s.name === stepName);
 if (step) {
 step.status = 'running';
 step.message = '执行中...';
 }
 }
 else if (message.includes('完成')) {
 const stepName = message.replace('完成: ', '');
 const step = taskSteps.value.find(s => s.name === stepName);
 if (step) {
 step.status = 'completed';
 step.message = '已完成';
 }
 // 更新进度
 const completed = taskSteps.value.filter(s => s.status === 'completed').length;
 progress.value = Math.round((completed / taskSteps.value.length) * 100);
 }
 }
 catch (e) {
 console.error('WebSocket parse error:', e);
 }
 };
 ws.onclose = () => {
 setTimeout(connectWS, 5000);
 };
}
// 发送指令
async function sendInstruction() {
 if (!inputText.value.trim() || isProcessing.value)
 return;
 const text = inputText.value.trim();
 inputText.value = '';
 // 添加用户消息
 conversation.value.push({
 role: 'user',
 content: text,
 timestamp: new Date(),
 });
 isProcessing.value = true;
 currentTask.value = text;
 try {
 // 调用API
 const response = await api.rawRequest('/orchestrator/say', {
 method: 'POST',
 body: JSON.stringify({ instruction: text }),
 });
 const result = response as any;
 // 添加AI响应
 conversation.value.push({
 role: 'assistant',
 content: result.message || '操作完成',
 timestamp: new Date(),
 });
 // 显示提示
 uiStore.showToast(result.message || '操作完成', result.success ? 'success' : 'error');
 }
 catch (error: any) {
 conversation.value.push({
 role: 'assistant',
 content: `错误: ${error.message || '未知错误'}`,
 timestamp: new Date(),
 });
 uiStore.showToast(`操作失败: ${error.message}`, 'error');
 }
 finally {
 isProcessing.value = false;
 currentTask.value = '';
 }
}
// 执行章节生成
async function executeChapterGeneration() {
 isProcessing.value = true;
 progress.value = 0;
 currentTask.value = '章节生成中...';
 // 初始化步骤
 taskSteps.value = [
 { id: 'snapshot', name: 'KG快照拍摄', status: 'pending', message: '' },
 { id: 'society', name: '社会推演', status: 'pending', message: '' },
 { id: 'architect', name: '架构师蓝图', status: 'pending', message: '' },
 { id: 'writer', name: 'Writer抽卡', status: 'pending', message: '' },
 { id: 'auditor', name: '8门禁审计', status: 'pending', message: '' },
 { id: 'style', name: '去AI味润色', status: 'pending', message: '' },
 { id: 'kg_update', name: '知识图谱更新', status: 'pending', message: '' },
 { id: 'publish', name: '章节发布', status: 'pending', message: '' },
 ];
 try {
 const response = await api.rawRequest('/orchestrator/execute-chapter', {
 method: 'POST',
 body: JSON.stringify({
 book_id: 'default',
 chapter: 1,
 mode: 'gacha_parallel_3',
 auto_approve: true,
 }),
 });
 const result = response as any;
 uiStore.showToast(result.message, result.success ? 'success' : 'error');
 }
 catch (error: any) {
 uiStore.showToast(`章节生成失败: ${error.message}`, 'error');
 }
 finally {
 isProcessing.value = false;
 }
}
// 获取状态
async function fetchStatus() {
 try {
 const response = await api.rawRequest('/orchestrator/status', { method: 'GET' });
 console.log('Status:', response);
 }
 catch (error) {
 console.error('Fetch status error:', error);
 }
}
// 获取对话历史
async function fetchConversation() {
 try {
 const response = await api.rawRequest('/orchestrator/conversation', { method: 'GET' });
 conversation.value = (response as any).map((msg: any) => ({
 role: msg.role,
 content: msg.content,
 timestamp: new Date(),
 }));
 }
 catch (error) {
 console.error('Fetch conversation error:', error);
 }
}
// 重置系统
async function resetSystem() {
 try {
 await api.rawRequest('/orchestrator/reset', { method: 'POST' });
 conversation.value = [];
 taskSteps.value = [];
 progress.value = 0;
 uiStore.showToast('创作系统已重置', 'success');
 }
 catch (error: any) {
 uiStore.showToast(`重置失败: ${error.message}`, 'error');
 }
}
// 审批处理
function handleApproval(approved: boolean) {
 showApproval.value = false;
 approvalTask.value = null;
 uiStore.showToast(approved ? '已通过审批' : '已拒绝', approved ? 'success' : 'warning');
}
// 获取状态图标
function getStatusIcon(status: string) {
 switch (status) {
 case 'completed':
 return CheckCircleOutlined;
 case 'running':
 return RestOutlined;
 case 'failed':
 return LeftCircleOutlined;
 default:
 return ClockCircleOutlined;
 }
}
// 获取状态颜色
function getStatusColor(status: string) {
 switch (status) {
 case 'completed':
 return 'success';
 case 'running':
 return 'primary';
 case 'failed':
 return 'error';
 default:
 return 'default';
 }
}
onMounted(() => {
 connectWS();
 fetchConversation();
});
onUnmounted(() => {
 if (ws)
 ws.close();
});
</script>

<template>
  <div class="orchestrator-view">
    <!-- 头部 -->
    <div class="header">
      <div class="header-content">
        <div class="title-section">
          <NIcon :size="32" class="title-icon">
            <RocketOutlined />
          </NIcon>
          <div>
            <h1 class="title">智能创作中心</h1>
            <p class="subtitle">用自然语言驱动你的创造力</p>
          </div>
        </div>
        <NButton type="primary" @click="executeChapterGeneration" :disabled="isProcessing">
          <template #icon><PlayCircleOutlined /></template>
          一键生成章节
        </NButton>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧：对话区域 -->
      <div class="conversation-panel">
        <NCard title="创作对话" class="conversation-card">
          <!-- 示例指令 -->
          <div class="examples-section">
            <span class="examples-label">试试这些指令：</span>
            <div class="examples-tags">
              <NTag
                v-for="example in examples"
                :key="example"
                :closable="false"
                class="example-tag"
                @click="inputText = example"
              >
                {{ example }}
              </NTag>
            </div>
          </div>

          <!-- 对话历史 -->
          <div class="conversation-list">
            <NList v-if="conversation.length > 0">
              <NListItem
                v-for="(msg, index) in conversation"
                :key="index"
                class="message-item"
                :class="msg.role"
              >
                <template #prefix>
                  <NIcon :size="20">
                    <MessageOutlined />
                  </NIcon>
                </template>
                <div class="message-content">
                  <span class="message-role">{{ msg.role === 'user' ? '你' : 'AI' }}</span>
                  <p class="message-text">{{ msg.content }}</p>
                  <span class="message-time">{{ msg.timestamp.toLocaleTimeString() }}</span>
                </div>
              </NListItem>
            </NList>
            <div v-else class="empty-state">
              <NIcon :size="48" class="empty-icon">
                <ShakeOutlined />
              </NIcon>
              <p>开始你的创作之旅吧！</p>
              <p class="empty-hint">输入你想创作的内容，AI会自动帮你完成</p>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="input-section">
            <NInput
              v-model:value="inputText"
              type="textarea"
              :placeholder="isProcessing ? 'AI正在处理...' : '输入你的创作需求，例如：我想写一本玄幻小说'"
              :disabled="isProcessing"
              :rows="3"
              class="input-textarea"
              @keyup.enter.ctrl="sendInstruction"
            />
            <NButton
              type="primary"
              @click="sendInstruction"
              :disabled="!inputText.trim() || isProcessing"
              class="send-btn"
            >
              <template #icon><SendOutlined /></template>
              发送
            </NButton>
          </div>
        </NCard>
      </div>

      <!-- 右侧：进度面板 -->
      <div class="progress-panel">
        <!-- 当前任务 -->
        <NCard title="当前任务" class="task-card">
          <div v-if="currentTask" class="current-task">
            <NProgress :percentage="progress" :show-indicator="true" />
            <p class="task-name">{{ currentTask }}</p>
          </div>
          <div v-else class="no-task">
            <NIcon :size="32" class="no-task-icon">
              <ClockCircleOutlined />
            </NIcon>
            <p>暂无进行中的任务</p>
            <p class="no-task-hint">输入指令或点击"一键生成章节"开始创作</p>
          </div>
        </NCard>

        <!-- 任务步骤 -->
        <NCard title="任务流程" class="steps-card">
          <div v-if="taskSteps.length > 0" class="steps-list">
            <div
              v-for="step in taskSteps"
              :key="step.id"
              class="step-item"
              :class="step.status"
            >
              <NIcon :size="20" :class="`step-icon step-${step.status}`">
                <component :is="getStatusIcon(step.status)" />
              </NIcon>
              <div class="step-info">
                <span class="step-name">{{ step.name }}</span>
                <span class="step-message">{{ step.message }}</span>
              </div>
              <NTag :type="getStatusColor(step.status)" :round="true" class="step-status">
                {{ step.status === 'pending' ? '等待' : step.status === 'running' ? '执行中' : step.status === 'completed' ? '完成' : '失败' }}
              </NTag>
            </div>
          </div>
          <div v-else class="empty-steps">
            <p>任务步骤将在这里显示</p>
          </div>
        </NCard>

        <!-- 快捷操作 -->
        <NCard title="快捷操作" class="actions-card">
          <NSpace vertical>
            <NButton @click="fetchStatus" size="small">
              刷新状态
            </NButton>
            <NButton @click="fetchConversation" size="small">
              加载对话
            </NButton>
            <NButton @click="resetSystem" size="small" type="warning">
              重置系统
            </NButton>
          </NSpace>
        </NCard>
      </div>
    </div>

    <!-- 审批弹窗 -->
    <div v-if="showApproval && approvalTask" class="approval-modal">
      <NCard class="approval-card" title="需要人工确认">
        <p>子任务「{{ approvalTask.name }}」需要你的确认才能继续执行。</p>
        <NSpace class="approval-actions">
          <NButton @click="handleApproval(true)" type="primary">
            <template #icon><CheckCircleOutlined /></template>
            通过
          </NButton>
          <NButton @click="handleApproval(false)" type="warning">
            <template #icon><LeftCircleOutlined /></template>
            拒绝
          </NButton>
        </NSpace>
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.orchestrator-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  color: white;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  color: white;
}

.title {
  font-size: 24px;
  font-weight: bold;
  margin: 0;
}

.subtitle {
  font-size: 14px;
  opacity: 0.8;
  margin: 4px 0 0 0;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.conversation-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.conversation-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.examples-section {
  margin-bottom: 16px;
}

.examples-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 8px;
  display: block;
}

.examples-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-tag {
  cursor: pointer;
  padding: 4px 12px;
  font-size: 12px;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
}

.example-tag:hover {
  background: #e6f7ff;
  border-color: #91d5ff;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.message-item {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 8px;
}

.message-item.user {
  background: #e6f7ff;
}

.message-item.assistant {
  background: #f6ffed;
}

.message-content {
  margin-left: 8px;
}

.message-role {
  font-size: 12px;
  font-weight: bold;
  color: #666;
}

.message-text {
  margin: 4px 0;
  font-size: 14px;
  line-height: 1.6;
}

.message-time {
  font-size: 11px;
  color: #999;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  margin-bottom: 16px;
  color: #d9d9d9;
}

.empty-hint {
  font-size: 12px;
  margin-top: 8px;
}

.input-section {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
}

.input-textarea {
  flex: 1;
}

.send-btn {
  align-self: flex-end;
}

.progress-panel {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-card, .steps-card, .actions-card {
  flex-shrink: 0;
}

.current-task {
  padding: 16px;
}

.task-name {
  margin: 12px 0 0 0;
  font-size: 14px;
  color: #666;
}

.no-task {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px;
  color: #999;
}

.no-task-icon {
  margin-bottom: 12px;
}

.no-task-hint {
  font-size: 12px;
  margin-top: 8px;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #fafafa;
}

.step-item.running {
  background: #fff7e6;
}

.step-item.completed {
  background: #f6ffed;
}

.step-item.failed {
  background: #fff2f0;
}

.step-icon {
  flex-shrink: 0;
}

.step-icon.step-completed {
  color: #52c41a;
}

.step-icon.step-running {
  color: #fa8c16;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-icon.step-failed {
  color: #ff4d4f;
}

.step-icon.step-pending {
  color: #d9d9d9;
}

.step-info {
  flex: 1;
  min-width: 0;
}

.step-name {
  font-size: 14px;
  font-weight: 500;
}

.step-message {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

.step-status {
  flex-shrink: 0;
  font-size: 12px;
  padding: 2px 8px;
}

.empty-steps {
  padding: 24px;
  text-align: center;
  color: #999;
}

.approval-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.approval-card {
  width: 480px;
}

.approval-actions {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>

<template>
  <div class="world-view">
    <div class="world-view__header">
      <h2 class="world-view__title">世界设定</h2>
    </div>

    <!-- Tab 导航 -->
    <n-tabs v-model:value="activeTab" type="line" animated>
      <n-tab-pane name="characters" tab="角色">
        <SkeletonLoader v-if="loading.characters" type="cards" />
        <div v-else-if="characters.length === 0" class="world-view__empty">
          <h3>暂无角色</h3>
          <p>创建你的世界观角色，让创作更连贯。</p>
          <n-button @click="onAdd('character')">添加角色</n-button>
        </div>
        <div v-else class="world-view__grid">
          <n-card v-for="char in characters" :key="char.name" class="entity-card" :bordered="true" size="small">
            <div class="entity-card__header">
              <div class="entity-card__avatar">{{ char.name?.[0] || '?' }}</div>
              <div>
                <h4>{{ char.name || '未命名' }}</h4>
                <p class="entity-card__type">角色</p>
              </div>
            </div>
          </n-card>
        </div>
      </n-tab-pane>

      <n-tab-pane name="locations" tab="地点">
        <SkeletonLoader v-if="loading.locations" type="cards" />
        <div v-else-if="locations.length === 0" class="world-view__empty">
          <h3>暂无地点</h3>
          <p>设定故事发生的地点和场景。</p>
        </div>
        <div v-else class="world-view__grid">
          <n-card v-for="loc in locations" :key="loc.name" class="entity-card" :bordered="true" size="small">
            <div class="entity-card__header">
              <div class="entity-card__icon">📍</div>
              <div>
                <h4>{{ loc.name || '未命名' }}</h4>
                <p class="entity-card__type">地点</p>
              </div>
            </div>
          </n-card>
        </div>
      </n-tab-pane>

      <n-tab-pane name="factions" tab="势力">
        <SkeletonLoader v-if="loading.factions" type="cards" />
        <div v-else-if="factions.length === 0" class="world-view__empty">
          <h3>暂无势力</h3>
          <p>设定故事中的组织与势力关系。</p>
        </div>
        <div v-else class="world-view__grid">
          <n-card v-for="fac in factions" :key="fac.name" class="entity-card" :bordered="true" size="small">
            <div class="entity-card__header">
              <div class="entity-card__icon">🏴</div>
              <div>
                <h4>{{ fac.name || '未命名' }}</h4>
                <p class="entity-card__type">势力</p>
              </div>
            </div>
          </n-card>
        </div>
      </n-tab-pane>

      <n-tab-pane name="relations" tab="关系网络">
        <div class="relation-graph-container">
          <SkeletonLoader v-if="loading.relations" type="chart" />
          <div v-else-if="graphData.nodes.length === 0" class="world-view__empty">
            <h3>暂无关系数据</h3>
            <p>添加角色后即可查看关系网络图。</p>
          </div>
          <v-chart v-else :option="relationGraphOption" :autoresize="true" class="relation-graph" />
          <div v-if="graphData.nodes.length > 0" class="relation-legend">
            <span class="legend-item"><span class="legend-dot" style="background: #5B8FF9" /> 角色</span>
            <span class="legend-item"><span class="legend-dot" style="background: #5AD8A6" /> 地点</span>
            <span class="legend-item"><span class="legend-dot" style="background: #F6BD16" /> 势力</span>
          </div>
        </div>
      </n-tab-pane>

      <n-tab-pane name="rules" tab="规则">
        <div class="world-view__empty">
          <h3>世界规则</h3>
          <p>定义这个世界的底层逻辑与法则。</p>
          <n-button @click="onAdd('rule')">添加规则</n-button>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { NTabs, NTabPane, NCard, NButton } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { api } from '../../api'
import { useUIStore } from '../../stores/ui'
import type { KGEntity } from '../../types/api'
import SkeletonLoader from '../../components/shared/SkeletonLoader.vue'
import { useChartTheme } from '../../composables/useChartTheme'

const { palette } = useChartTheme()

use([CanvasRenderer, GraphChart, TooltipComponent])

const uiStore = useUIStore()
const activeTab = ref('characters')

const loading = reactive({
  characters: false,
  locations: false,
  factions: false,
  relations: false,
})

const characters = ref<KGEntity[]>([])
const locations = ref<KGEntity[]>([])
const factions = ref<KGEntity[]>([])

// 关系图数据
interface GraphNode { id: string; name: string; symbolSize: number; category: number }
interface GraphLink { source: string; target: string; label?: string }
const graphData = reactive<{ nodes: GraphNode[]; links: GraphLink[] }>({
  nodes: [],
  links: [],
})

const categories = [
  { name: '角色' },
  { name: '地点' },
  { name: '势力' },
]

const relationGraphOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    backgroundColor: palette.value.tooltipBg,
    borderColor: palette.value.tooltipBorder,
    textStyle: { color: palette.value.tooltipText, fontSize: 12 },
    formatter: (params: any) => {
      if (params.dataType === 'edge') {
        return `${params.data.source} → ${params.data.target}`
      }
      return `<b>${params.name}</b>`
    },
  },
  legend: {
    bottom: 0,
    textStyle: { color: palette.value.text, fontSize: 12 },
    data: categories.map(c => c.name),
  },
  color: [palette.value.series, '#5AD8A6', '#F6BD16'],
  series: [{
    type: 'graph' as const,
    layout: 'force',
    roam: true,
    draggable: true,
    categories,
    data: graphData.nodes,
    links: graphData.links,
    force: {
      repulsion: 200,
      gravity: 0.1,
      edgeLength: [100, 200],
      layoutAnimation: true,
    },
    label: {
      show: true,
      position: 'right' as const,
      color: palette.value.text,
      fontSize: 12,
    },
    lineStyle: {
      color: palette.value.split,
      curveness: 0.3,
      opacity: 0.6,
    },
    itemStyle: {
      borderColor: palette.value.split,
      borderWidth: 2,
    },
    emphasis: {
      focus: 'adjacency' as const,
      lineStyle: { width: 2, opacity: 1 },
    },
  }],
}))

async function loadEntity(type: string) {
  try {
    const res = await api.listEntities(type)
    if (type === 'Character') characters.value = res.entities || []
    else if (type === 'Location') locations.value = res.entities || []
    else if (type === 'Faction') factions.value = res.entities || []
  } catch {
    // 静默处理
  }
}

function buildRelationGraph() {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []

  // 角色节点 (category 0)
  characters.value.forEach((c, i) => {
    nodes.push({
      id: c.name || `char-${i}`,
      name: c.name || '未命名',
      symbolSize: 36,
      category: 0,
    })
  })

  // 地点节点 (category 1)
  locations.value.forEach((l, i) => {
    nodes.push({
      id: l.name || `loc-${i}`,
      name: l.name || '未命名',
      symbolSize: 28,
      category: 1,
    })
  })

  // 势力节点 (category 2)
  factions.value.forEach((f, i) => {
    nodes.push({
      id: f.name || `fac-${i}`,
      name: f.name || '未命名',
      symbolSize: 32,
      category: 2,
    })
  })

  // 构建关系：角色 ↔ 角色（演示：相邻角色间建立连接）
  const charNames = characters.value.map(c => c.name)
  for (let i = 0; i < charNames.length - 1; i++) {
    links.push({ source: charNames[i], target: charNames[i + 1] })
  }

  // 角色 ↔ 地点（第一个角色与所有地点关联）
  if (charNames.length > 0 && locations.value.length > 0) {
    locations.value.forEach(l => {
      links.push({ source: charNames[0], target: l.name })
    })
  }

  // 角色 ↔ 势力（最后一个角色与所有势力关联）
  if (charNames.length > 1 && factions.value.length > 0) {
    factions.value.forEach(f => {
      links.push({ source: charNames[charNames.length - 1], target: f.name })
    })
  }

  graphData.nodes = nodes
  graphData.links = links
}

function onAdd(type: string) {
  uiStore.showToast(`添加${type}功能将在后续版本开放`, 'info')
}

onMounted(async () => {
  loading.characters = true
  loading.locations = true
  loading.factions = true
  loading.relations = true

  await Promise.all([
    loadEntity('Character'),
    loadEntity('Location'),
    loadEntity('Faction'),
  ])

  buildRelationGraph()

  loading.characters = false
  loading.locations = false
  loading.factions = false
  loading.relations = false
})
</script>

<style scoped>
.world-view {
  height: 100%;
  padding: var(--space-6);
  overflow: auto;
}

.world-view__header {
  margin-bottom: var(--space-4);
}

.world-view__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.world-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
  padding: var(--space-3) 0;
}

.entity-card {
  cursor: pointer;
  transition: transform var(--transition-fast);
}
.entity-card:hover {
  transform: translateY(-2px);
}

.entity-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.entity-card__header h4 {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.entity-card__avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-primary-suppl);
  color: var(--color-primary);
  font-weight: var(--font-bold);
  font-size: var(--text-lg);
}

.entity-card__icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-bg-overlay);
  font-size: 20px;
}

.entity-card__type {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.world-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-10) var(--space-8);
  text-align: center;
}
.world-view__empty h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}
.world-view__empty p {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 关系网络图 */
.relation-graph-container {
  position: relative;
  padding: var(--space-3) 0;
}

.relation-graph {
  width: 100%;
  height: 480px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
}

.relation-legend {
  display: flex;
  justify-content: center;
  gap: var(--space-6);
  margin-top: var(--space-3);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
</style>

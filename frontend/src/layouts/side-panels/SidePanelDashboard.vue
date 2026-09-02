<template>
  <div class="panel-section">
    <div class="panel-section__header">
      <span class="panel-section__title">筛选</span>
    </div>
    <div class="panel-section__body">
      <n-select
        v-model:value="filter"
        :options="filterOptions"
        placeholder="选择作品"
        size="small"
        clearable
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NSelect } from 'naive-ui'

const props = defineProps<{
  books?: { uid: string; title: string; chapters?: number; total_words?: number }[]
}>()

const filter = ref<string | null>(null)
const filterOptions = computed(() =>
  (props.books || []).map(b => ({ label: b.title, value: b.uid }))
)
</script>

/**
 * 昆仑创作引擎 — 配置状态管理
 * 类型安全 + 关键操作错误反馈
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'
import type { ModelParamDef, AgentParams, BookConfig, Genre, PromptStatus } from '../types/api'

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

export const useConfigStore = defineStore('config', () => {
  const paramDefs = ref<ModelParamDef[]>([])
  const agents = ref<string[]>([])
  const allParams = ref<Record<string, AgentParams>>({})
  const bookConfig = ref<BookConfig | null>(null)
  const genres = ref<Genre[]>([])
  const prompts = ref<PromptStatus[]>([])
  const loading = ref(false)
  const error = ref('')

  async function loadParamDefs() {
    try {
      const res = await api.getParamDefs()
      paramDefs.value = res.params || []
      agents.value = res.agents || []
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    }
  }

  async function loadAllParams(bookId = 'default') {
    try {
      const res = await api.getAllParams(bookId)
      allParams.value = res.params || {}
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    }
  }

  async function setParam(bookId: string, param: string, value: number, agent: string) {
    try {
      await api.setParam(bookId, param, value, agent)
      if (allParams.value[agent]) allParams.value[agent][param] = value
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    }
  }

  async function loadBookConfig(bookId: string) {
    loading.value = true
    try {
      const res = await api.getBookConfig(bookId)
      bookConfig.value = res.config || null
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function saveBookConfig(bookId: string, updates: Record<string, unknown>) {
    try {
      await api.updateBookConfig(bookId, updates)
      await loadBookConfig(bookId)
      return true
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
      return false
    }
  }

  async function loadGenres() {
    try {
      const res = await api.listGenres()
      genres.value = res.genres || []
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    }
  }

  async function loadPrompts(bookId: string) {
    try {
      const res = await api.listPrompts(bookId)
      prompts.value = res.prompts || []
    } catch (e: unknown) {
      error.value = getErrorMessage(e)
    }
  }

  return {
    paramDefs, agents, allParams, bookConfig, genres, prompts, loading, error,
    loadParamDefs, loadAllParams, setParam, loadBookConfig, saveBookConfig,
    loadGenres, loadPrompts,
  }
})

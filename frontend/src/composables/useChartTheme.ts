/**
 * 昆仑创作引擎 — 共享 ECharts 主题
 * 根据当前明暗主题输出图表通用配色，避免各视图硬编码暗色字面量。
 * 配色与 tokens.css / useTheme.ts 的体系保持一致；切主题时图表随之刷新。
 */
import { computed } from 'vue'
import { useTheme } from './useTheme'

export interface ChartPalette {
  /** 坐标轴/图例文字 */
  text: string
  /** 坐标轴线条 */
  axis: string
  /** 分割线 */
  split: string
  /** Tooltip 背景 */
  tooltipBg: string
  /** Tooltip 边框 */
  tooltipBorder: string
  /** Tooltip 文字 */
  tooltipText: string
  /** 主系列色 */
  series: string
  /** 面积渐变起止 */
  seriesArea: [string, string]
  /** 雷达区域填充 */
  seriesArea2: string
}

const darkPalette: ChartPalette = {
  text: '#B0B3BD',
  axis: '#252839',
  split: '#1E2030',
  tooltipBg: '#161822',
  tooltipBorder: '#252839',
  tooltipText: '#E8EAED',
  series: '#5B8FF9',
  seriesArea: ['rgba(91,143,249,0.25)', 'rgba(91,143,249,0.02)'],
  seriesArea2: 'rgba(91,143,249,0.15)',
}

const lightPalette: ChartPalette = {
  text: '#4A4F62',
  axis: '#D0D3DD',
  split: '#E8EBF0',
  tooltipBg: '#FFFFFF',
  tooltipBorder: '#D0D3DD',
  tooltipText: '#1A1D2E',
  series: '#4A7DE8',
  seriesArea: ['rgba(74,125,232,0.22)', 'rgba(74,125,232,0.02)'],
  seriesArea2: 'rgba(74,125,232,0.12)',
}

export function useChartTheme() {
  const { isDark } = useTheme()
  const palette = computed<ChartPalette>(() => (isDark.value ? darkPalette : lightPalette))
  return { palette }
}

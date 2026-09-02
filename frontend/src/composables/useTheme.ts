/**
 * 昆仑创作引擎 — Naive UI 主题系统
 * 支持亮色/暗色切换，偏好持久化到 localStorage
 */
import { ref, watch, computed } from 'vue'
import { darkTheme, lightTheme } from 'naive-ui'
import { useStorage } from '@vueuse/core'
import type { GlobalThemeOverrides } from 'naive-ui'

// ─── 暗色主题覆盖 ──────────────────
export const darkThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#5B8FF9',
    primaryColorHover: '#6DA0FA',
    primaryColorPressed: '#4A7DE8',
    primaryColorSuppl: 'rgba(91, 143, 249, 0.1)',
    successColor: '#52C41A',
    successColorHover: '#65D32B',
    successColorSuppl: 'rgba(82, 196, 26, 0.1)',
    warningColor: '#FAAD14',
    warningColorHover: '#FCC12E',
    warningColorSuppl: 'rgba(250, 173, 20, 0.1)',
    errorColor: '#FF4D4F',
    errorColorHover: '#FF6F71',
    errorColorSuppl: 'rgba(255, 77, 79, 0.1)',
    infoColor: '#5B8FF9',
    bodyColor: '#0F1117',
    cardColor: '#161822',
    modalColor: '#161822',
    popoverColor: '#161822',
    borderColor: '#252839',
    dividerColor: '#252839',
    textColor1: '#E8EAED',
    textColor2: '#B0B3BD',
    textColor3: '#6B6F7B',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: "'PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif",
    fontSizeSmall: '12px',
    fontSizeMedium: '14px',
    fontSizeLarge: '16px',
    fontSizeHuge: '20px',
    heightSmall: '28px',
    heightMedium: '32px',
    heightLarge: '40px',
  },
  Layout: {
    headerColor: '#0F1117',
    siderColor: '#0F1117',
    siderBorderColor: '#1E2030',
    footerColor: '#0F1117',
  },
  Button: {
    colorPrimary: '#5B8FF9',
    colorHoverPrimary: '#6DA0FA',
    colorPressedPrimary: '#4A7DE8',
    textColorPrimary: '#FFFFFF',
    borderColorPrimary: '#5B8FF9',
    borderRadiusSmall: '4px',
    borderRadiusMedium: '6px',
    borderRadiusLarge: '8px',
  },
  Card: {
    color: '#161822',
    borderColor: '#252839',
    borderRadius: '10px',
    paddingMedium: '20px',
    titleTextColor: '#E8EAED',
    titleFontSizeSmall: '14px',
    titleFontSizeMedium: '16px',
    titleFontSizeLarge: '18px',
  },
  Input: {
    color: '#1A1D2E',
    colorFocus: '#1A1D2E',
    borderColor: '#252839',
    borderHoverColor: '#3A3F55',
    borderFocusColor: '#5B8FF9',
    textColor: '#E8EAED',
    placeholderColor: '#6B6F7B',
    borderRadius: '6px',
    lineHeight: '1.5',
  },
  Select: {
    peers: {
      InternalSelection: {
        color: '#1A1D2E',
        border: '#252839',
        borderHover: '#3A3F55',
        borderFocus: '#5B8FF9',
        textColor: '#E8EAED',
      },
    },
  },
  Switch: { railColorActive: '#5B8FF9' },
  Slider: { fillColor: '#5B8FF9', fillColorHover: '#6DA0FA' },
  Progress: { fillColor: '#5B8FF9', railColor: '#1E2030' },
  Tag: { borderRadius: '4px' },
  Menu: {
    itemTextColor: '#B0B3BD',
    itemTextColorHover: '#E8EAED',
    itemTextColorActive: '#5B8FF9',
    itemColorActive: 'rgba(91, 143, 249, 0.1)',
    itemColorActiveHover: 'rgba(91, 143, 249, 0.15)',
    itemIconColor: '#6B6F7B',
    itemIconColorHover: '#B0B3BD',
    itemIconColorActive: '#5B8FF9',
  },
  Tabs: {
    tabTextColorLine: '#B0B3BD',
    tabTextColorActiveLine: '#5B8FF9',
    barColor: '#5B8FF9',
  },
  DataTable: {
    thColor: '#161822',
    tdColor: '#0F1117',
    thTextColor: '#B0B3BD',
    tdTextColor: '#E8EAED',
    borderColor: '#1E2030',
  },
  Modal: {
    color: '#161822',
    textColor: '#E8EAED',
    headerBorderColor: '#1E2030',
    footerBorderColor: '#1E2030',
  },
  Tooltip: {
    color: '#1A1D2E',
    textColor: '#E8EAED',
    borderColor: '#252839',
  },
  Notification: {
    color: '#1A1D2E',
    textColor: '#E8EAED',
    headerBorderColor: '#1E2030',
    footerBorderColor: '#1E2030',
  },
  Drawer: {
    color: '#161822',
    textColor: '#E8EAED',
    borderColor: '#1E2030',
  },
  Dropdown: {
    color: '#1A1D2E',
    textColor: '#E8EAED',
    borderColor: '#252839',
  },
  Checkbox: {
    borderRadius: '4px',
    colorChecked: '#5B8FF9',
    borderColor: '#3A3F55',
    borderChecked: '#5B8FF9',
  },
  Radio: { colorActive: '#5B8FF9' },
  Skeleton: { color: '#1E2030', colorEnd: '#252839' },
  Scrollbar: { color: '#252839', colorHover: '#3A3F55' },
}

// ─── 亮色主题覆盖 ──────────────────
export const lightThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#4A7DE8',
    primaryColorHover: '#5B8FF9',
    primaryColorPressed: '#3D6FD4',
    primaryColorSuppl: 'rgba(74, 125, 232, 0.08)',
    successColor: '#52C41A',
    successColorHover: '#65D32B',
    successColorSuppl: 'rgba(82, 196, 26, 0.08)',
    warningColor: '#FAAD14',
    warningColorHover: '#FCC12E',
    warningColorSuppl: 'rgba(250, 173, 20, 0.08)',
    errorColor: '#FF4D4F',
    errorColorHover: '#FF6F71',
    errorColorSuppl: 'rgba(255, 77, 79, 0.08)',
    infoColor: '#4A7DE8',
    bodyColor: '#F5F6FA',
    cardColor: '#FFFFFF',
    modalColor: '#FFFFFF',
    popoverColor: '#FFFFFF',
    borderColor: '#E2E4EA',
    dividerColor: '#E2E4EA',
    textColor1: '#1A1D2E',
    textColor2: '#4A4F62',
    textColor3: '#8B8FA3',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: "'PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif",
    fontSizeSmall: '12px',
    fontSizeMedium: '14px',
    fontSizeLarge: '16px',
    fontSizeHuge: '20px',
    heightSmall: '28px',
    heightMedium: '32px',
    heightLarge: '40px',
  },
  Layout: {
    headerColor: '#FFFFFF',
    siderColor: '#FAFBFC',
    siderBorderColor: '#E2E4EA',
    footerColor: '#FFFFFF',
  },
  Button: {
    colorPrimary: '#4A7DE8',
    colorHoverPrimary: '#5B8FF9',
    colorPressedPrimary: '#3D6FD4',
    textColorPrimary: '#FFFFFF',
    borderColorPrimary: '#4A7DE8',
    borderRadiusSmall: '4px',
    borderRadiusMedium: '6px',
    borderRadiusLarge: '8px',
  },
  Card: {
    color: '#FFFFFF',
    borderColor: '#E2E4EA',
    borderRadius: '10px',
    paddingMedium: '20px',
    titleTextColor: '#1A1D2E',
    titleFontSizeSmall: '14px',
    titleFontSizeMedium: '16px',
    titleFontSizeLarge: '18px',
  },
  Input: {
    color: '#FFFFFF',
    colorFocus: '#FFFFFF',
    borderColor: '#D0D3DD',
    borderHoverColor: '#B0B3BD',
    borderFocusColor: '#4A7DE8',
    textColor: '#1A1D2E',
    placeholderColor: '#8B8FA3',
    borderRadius: '6px',
    lineHeight: '1.5',
  },
  Select: {
    peers: {
      InternalSelection: {
        color: '#FFFFFF',
        border: '#D0D3DD',
        borderHover: '#B0B3BD',
        borderFocus: '#4A7DE8',
        textColor: '#1A1D2E',
      },
    },
  },
  Switch: { railColorActive: '#4A7DE8' },
  Slider: { fillColor: '#4A7DE8', fillColorHover: '#5B8FF9' },
  Progress: { fillColor: '#4A7DE8', railColor: '#E8EBF0' },
  Tag: { borderRadius: '4px' },
  Menu: {
    itemTextColor: '#4A4F62',
    itemTextColorHover: '#1A1D2E',
    itemTextColorActive: '#4A7DE8',
    itemColorActive: 'rgba(74, 125, 232, 0.08)',
    itemColorActiveHover: 'rgba(74, 125, 232, 0.12)',
    itemIconColor: '#8B8FA3',
    itemIconColorHover: '#4A4F62',
    itemIconColorActive: '#4A7DE8',
  },
  Tabs: {
    tabTextColorLine: '#4A4F62',
    tabTextColorActiveLine: '#4A7DE8',
    barColor: '#4A7DE8',
  },
  DataTable: {
    thColor: '#FAFBFC',
    tdColor: '#FFFFFF',
    thTextColor: '#4A4F62',
    tdTextColor: '#1A1D2E',
    borderColor: '#E2E4EA',
  },
  Modal: {
    color: '#FFFFFF',
    textColor: '#1A1D2E',
    headerBorderColor: '#E2E4EA',
    footerBorderColor: '#E2E4EA',
  },
  Tooltip: {
    color: '#FFFFFF',
    textColor: '#1A1D2E',
    borderColor: '#D0D3DD',
  },
  Notification: {
    color: '#FFFFFF',
    textColor: '#1A1D2E',
    headerBorderColor: '#E2E4EA',
    footerBorderColor: '#E2E4EA',
  },
  Drawer: {
    color: '#FFFFFF',
    textColor: '#1A1D2E',
    borderColor: '#E2E4EA',
  },
  Dropdown: {
    color: '#FFFFFF',
    textColor: '#1A1D2E',
    borderColor: '#D0D3DD',
  },
  Checkbox: {
    borderRadius: '4px',
    colorChecked: '#4A7DE8',
    borderColor: '#B0B3BD',
    borderChecked: '#4A7DE8',
  },
  Radio: { colorActive: '#4A7DE8' },
  Skeleton: { color: '#E8EBF0', colorEnd: '#F0F2F6' },
  Scrollbar: { color: '#D0D3DD', colorHover: '#B0B3BD' },
}

// ─── 主题 Composable ────────────────
export function useTheme() {
  // 使用 @vueuse/core useStorage 持久化到 localStorage
  const isDark = useStorage('kunlun-theme-dark', true)

  function toggleTheme() {
    isDark.value = !isDark.value
  }

  function setTheme(dark: boolean) {
    isDark.value = dark
  }

  // 响应式计算当前主题
  const themeOverrides = computed(() =>
    isDark.value ? darkThemeOverrides : lightThemeOverrides
  )

  const naiveTheme = computed(() =>
    isDark.value ? darkTheme : lightTheme
  )

  return {
    isDark,
    toggleTheme,
    setTheme,
    themeOverrides,
    naiveTheme,
    darkTheme: naiveTheme,  // 向后兼容（App.vue 中使用 :theme="darkTheme"）
  }
}

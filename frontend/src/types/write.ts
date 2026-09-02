export interface ChapterItem {
  id: string
  title: string
  wordCount: number
}

export interface Volume {
  id: string
  name: string
  expanded: boolean
  chapters: ChapterItem[]
}

export interface SettingItem {
  id: string
  name: string
  type: string
}

export interface SettingGroup {
  id: string
  name: string
  expanded: boolean
  items: SettingItem[]
}

export interface Snippet {
  id: string
  title: string
  content: string
}

export interface Scene {
  summary: string
  tags: string[]
}

export interface AiTool {
  id: string
  name: string
  icon: any
}

export interface SelectOption {
  label: string
  value: string
}

export interface AiMessage {
  id: string
  content: string
  isAI: boolean
}

export interface OutlineOption {
  title: string
  description: string
  score: number
}

export interface SettingDetail {
  id: string
  name: string
  type: string
  description: string
  attributes: Record<string, string>
  relationships: Array<{ id: string; type: string; target: string }>
}

/**
 * 飞书文档 - 块级编辑器类型定义
 * 完全独立的块编辑架构，不依赖 Tiptap
 */

// ========== 块类型定义 ==========

export type BlockType =
  // 文本块
  | 'text'          // 普通文本段落
  | 'h1'            // 标题 1
  | 'h2'            // 标题 2
  | 'h3'            // 标题 3
  | 'h4'            // 标题 4
  | 'h5'            // 标题 5
  | 'h6'            // 标题 6
  | 'quote'         // 引用块
  | 'code'          // 代码块
  | 'callout'       // 高亮块/提示框
  // 列表块
  | 'bulletList'    // 无序列表容器
  | 'orderedList'   // 有序列表容器
  | 'taskList'      // 任务列表容器
  | 'listItem'      // 列表项
  | 'taskItem'      // 任务项
  // 媒体块
  | 'image'         // 图片
  | 'video'         // 视频
  | 'file'          // 文件
  // 结构块
  | 'divider'       // 分割线
  | 'table'         // 表格
  | 'grid'          // 分栏
  // 特殊块
  | 'toggle'        // 折叠块

// 文本格式类型
export type TextFormatType =
  | 'bold'
  | 'italic'
  | 'underline'
  | 'strikethrough'
  | 'code'
  | 'link'
  | 'color'
  | 'bgColor'
  | 'fontSize'
  | 'fontFamily'

// 文本格式
export interface TextFormat {
  type: TextFormatType
  value?: string | boolean
}

// 文本片段
export interface TextSegment {
  text: string
  formats: TextFormat[]
}

// 行内内容（可以是纯文本或带格式的文本片段数组）
export type InlineContent = string | TextSegment[]

// 块数据
export interface BlockData {
  id: string
  type: BlockType
  // 文本内容
  content?: InlineContent
  // 块属性
  attrs?: Record<string, any>
  // 子块ID列表
  children?: string[]
  // 父块ID
  parentId?: string
}

// 文档数据
export interface DocumentData {
  id: string
  blocks: Record<string, BlockData>
  rootBlockIds: string[]
  createdAt: string
  updatedAt: string
  title?: string
}

// 选择状态
export interface SelectionState {
  blockId: string | null
  startOffset: number
  endOffset: number
  isCollapsed: boolean
}

// 编辑器状态
export interface EditorState {
  documentId: string | null
  document: DocumentData | null
  selection: SelectionState
  focusedBlockId: string | null
  isEditing: boolean
  isDragging: boolean
  history: {
    past: DocumentData[]
    future: DocumentData[]
  }
  slashMenu: {
    visible: boolean
    query: string
    position: { x: number; y: number }
  }
}

// 斜杠命令定义
export interface SlashCommand {
  id: string
  title: string
  description?: string
  icon?: string
  keywords?: string[]
  category: SlashCommandCategory
  action: (editor: any) => void
}

// 斜杠命令分类
export type SlashCommandCategory =
  | 'basic'
  | 'list'
  | 'media'
  | 'structure'
  | 'insert'

// 块组件 Props
export interface BlockProps {
  blockId: string
  data: BlockData
  isFocused: boolean
  isEditable: boolean
}

// 块组件 Emits
export interface BlockEmits {
  (e: 'update', data: Partial<BlockData>): void
  (e: 'focus'): void
  (e: 'blur'): void
  (e: 'enter', shiftKey: boolean): void
  (e: 'backspace', atStart: boolean): void
  (e: 'delete', atEnd: boolean): void
  (e: 'arrow', direction: 'up' | 'down' | 'left' | 'right'): void
  (e: 'slash'): void
}

// 工具栏配置
export interface ToolbarItem {
  id: string
  label: string
  icon?: string
  shortcut?: string
  isActive?: () => boolean
  isDisabled?: () => boolean
  action: () => void
}

// ========== 常量定义 ==========

// 块类型显示名称
export const BLOCK_TYPE_NAMES: Record<BlockType, string> = {
  text: '正文',
  h1: '标题 1',
  h2: '标题 2',
  h3: '标题 3',
  h4: '标题 4',
  h5: '标题 5',
  h6: '标题 6',
  quote: '引用',
  code: '代码块',
  callout: '高亮块',
  bulletList: '无序列表',
  orderedList: '有序列表',
  taskList: '任务列表',
  listItem: '列表项',
  taskItem: '任务项',
  image: '图片',
  video: '视频',
  file: '文件',
  divider: '分割线',
  table: '表格',
  grid: '分栏',
  toggle: '折叠块',
}

// 块类型图标
export const BLOCK_TYPE_ICONS: Record<BlockType, string> = {
  text: '¶',
  h1: 'H1',
  h2: 'H2',
  h3: 'H3',
  h4: 'H4',
  h5: 'H5',
  h6: 'H6',
  quote: '"',
  code: '{ }',
  callout: '💡',
  bulletList: '•',
  orderedList: '1.',
  taskList: '☐',
  listItem: '•',
  taskItem: '☐',
  image: '🖼',
  video: '🎬',
  file: '📎',
  divider: '—',
  table: '⊞',
  grid: '▥',
  toggle: '▶',
}

// 高亮块类型
export const CALLOUT_TYPES = {
  info: { icon: 'ℹ️', color: '#1890ff', bgColor: '#e6f7ff' },
  success: { icon: '✅', color: '#52c41a', bgColor: '#f6ffed' },
  warning: { icon: '⚠️', color: '#fa8c16', bgColor: '#fff7e6' },
  error: { icon: '❌', color: '#ff4d4f', bgColor: '#fff2f0' },
  tip: { icon: '💡', color: '#722ed1', bgColor: '#f9f0ff' },
} as const

// 代码语言列表
export const CODE_LANGUAGES = [
  'plaintext', 'javascript', 'typescript', 'python', 'java', 'go',
  'rust', 'c', 'cpp', 'csharp', 'php', 'ruby', 'swift', 'kotlin',
  'html', 'css', 'scss', 'sql', 'bash', 'shell', 'json', 'yaml',
  'markdown', 'vue', 'jsx', 'tsx', 'graphql', 'dockerfile',
]

// 颜色预设
export const COLOR_PRESETS = {
  text: [
    '#1a1a1a', '#434343', '#666666', '#999999',
    '#c41d7f', '#eb2f96', '#f5222d', '#fa541c',
    '#fa8c16', '#fadb14', '#a0d911', '#52c41a',
    '#13c2c2', '#1890ff', '#2f54eb', '#722ed1',
  ],
  background: [
    'transparent', '#fafafa', '#f5f5f5', '#f0f0f0',
    '#fff1f0', '#fff0f6', '#fffbe6', '#fcffe6',
    '#e6fffb', '#e6f7ff', '#f0f5ff', '#f9f0ff',
  ],
}

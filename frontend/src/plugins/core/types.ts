// Block 类型定义
export type BlockType =
  // 文本类型
  | 'paragraph' | 'heading1' | 'heading2' | 'heading3' | 'heading4' | 'heading5' | 'heading6'
  | 'quote' | 'code-block' | 'callout'
  // 列表类型
  | 'bullet-list' | 'ordered-list' | 'task-list' | 'toggle-list'
  // 媒体类型
  | 'image' | 'video' | 'audio' | 'file' | 'embed'
  // 结构类型
  | 'divider' | 'table' | 'grid' | 'column'
  // 智能类型
  | 'mindmap' | 'flowchart' | 'formula' | 'diagram'

// 文本元素（富文本）
export interface TextElement {
  type: 'text'
  text: string
  bold?: boolean
  italic?: boolean
  underline?: boolean
  strike?: boolean
  code?: boolean
  color?: string
  backgroundColor?: string
  link?: { href: string; title?: string }
}

// 块样式
export interface BlockStyle {
  textAlign?: 'left' | 'center' | 'right' | 'justify'
  indent?: number
  lineHeight?: number
  color?: string
  backgroundColor?: string
}

// Block 结构
export interface Block {
  id: string
  type: BlockType
  content?: string
  elements?: TextElement[]
  attrs?: Record<string, any>
  style?: BlockStyle
  children?: Block[]
}

// 文档元数据
export interface DocumentMetadata {
  title?: string
  createdAt?: string
  updatedAt?: string
  author?: string
  [key: string]: any
}

// 文档内容
export interface DocumentContent {
  version: string
  type: 'doc'
  id: string
  blocks: Block[]
  blockOrder: string[]
  metadata: DocumentMetadata
}

// 编辑器类型
export type EditorType = 'docx' | 'docx-blocks' | 'feishu-docs' | 'excel' | 'mindmap' | 'flowchart'

// 编辑器插件接口
export interface EditorPlugin {
  id?: string // 插件 ID
  name: string
  type?: EditorType
  version?: string
  component: any // Vue 组件
  extensions?: any[] // Tiptap 扩展
  toolbar?: any // 工具栏组件
  icon?: string
  description?: string
  supportedBlocks?: string[]
  fileExtensions?: string[]
  onLoad?: () => Promise<void>
  onUnload?: () => void
}

// 插件注册信息
export interface PluginRegistry {
  [key: string]: EditorPlugin
}

// 编辑器状态
export interface EditorState {
  isReady: boolean
  isEditable: boolean
  activePlugin: EditorType | null
  content: DocumentContent | null
  selection: {
    startBlock: string | null
    endBlock: string | null
    startOffset: number
    endOffset: number
  }
}

// 编辑器事件
export interface EditorEvents {
  onContentChange: (content: DocumentContent) => void
  onSelectionChange: (selection: EditorState['selection']) => void
  onPluginChange: (plugin: EditorType) => void
  onReady: () => void
}

/**
 * 斜杠命令配置
 */
import type { SlashCommand, SlashCommandCategory } from '../types'
import { useDocumentStore } from '../stores/document'

// 基础命令
const basicCommands: SlashCommand[] = [
  {
    id: 'text',
    title: '正文',
    description: '普通文本段落',
    icon: '¶',
    keywords: ['text', 'paragraph', 'p', '正文', '段落'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'text'),
  },
  {
    id: 'h1',
    title: '标题 1',
    description: '大标题',
    icon: 'H1',
    keywords: ['h1', 'heading1', 'title', '标题'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'h1'),
  },
  {
    id: 'h2',
    title: '标题 2',
    description: '中标题',
    icon: 'H2',
    keywords: ['h2', 'heading2', '标题'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'h2'),
  },
  {
    id: 'h3',
    title: '标题 3',
    description: '小标题',
    icon: 'H3',
    keywords: ['h3', 'heading3', '标题'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'h3'),
  },
  {
    id: 'h4',
    title: '标题 4',
    description: '更小的标题',
    icon: 'H4',
    keywords: ['h4', 'heading4', '标题'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'h4'),
  },
  {
    id: 'quote',
    title: '引用',
    description: '引用块',
    icon: '"',
    keywords: ['quote', 'blockquote', '引用'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'quote'),
  },
  {
    id: 'code',
    title: '代码块',
    description: '代码块，支持语法高亮',
    icon: '{ }',
    keywords: ['code', 'codeblock', '代码'],
    category: 'basic',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'code'),
  },
  {
    id: 'callout',
    title: '高亮块',
    description: '带图标和颜色的提示框',
    icon: '💡',
    keywords: ['callout', 'alert', 'notice', '提示', '高亮'],
    category: 'basic',
    action: (editor) => {
      const store = useDocumentStore()
      store.updateBlock(editor.focusedBlockId, {
        type: 'callout',
        attrs: { calloutType: 'info' },
      })
    },
  },
  {
    id: 'divider',
    title: '分割线',
    description: '水平分割线',
    icon: '—',
    keywords: ['divider', 'hr', '分割线', 'horizontal'],
    category: 'basic',
    action: (editor) => editor.insertNewBlock('divider'),
  },
]

// 列表命令
const listCommands: SlashCommand[] = [
  {
    id: 'bulletList',
    title: '无序列表',
    description: '项目符号列表',
    icon: '•',
    keywords: ['bullet', 'ul', 'unordered', '无序', '列表'],
    category: 'list',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'bulletList'),
  },
  {
    id: 'orderedList',
    title: '有序列表',
    description: '编号列表',
    icon: '1.',
    keywords: ['ordered', 'ol', 'numbered', '有序', '列表'],
    category: 'list',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'orderedList'),
  },
  {
    id: 'taskList',
    title: '任务列表',
    description: '可勾选的任务列表',
    icon: '☐',
    keywords: ['task', 'todo', 'checkbox', '任务', '待办'],
    category: 'list',
    action: (editor) => editor.convertBlock(editor.focusedBlockId, 'taskList'),
  },
]

// 媒体命令
const mediaCommands: SlashCommand[] = [
  {
    id: 'image',
    title: '图片',
    description: '插入图片',
    icon: '🖼',
    keywords: ['image', 'img', 'picture', '图片', 'photo'],
    category: 'media',
    action: (editor) => {
      // 触发图片上传对话框
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = 'image/*'
      input.onchange = async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0]
        if (file) {
          // 这里应该调用上传 API
          const reader = new FileReader()
          reader.onload = () => {
            const store = useDocumentStore()
            store.insertBlock({
              type: 'image',
              attrs: { src: reader.result, alt: file.name },
            }, { afterId: editor.focusedBlockId })
          }
          reader.readAsDataURL(file)
        }
      }
      input.click()
    },
  },
  {
    id: 'image-url',
    title: '网络图片',
    description: '从 URL 插入图片',
    icon: '🔗',
    keywords: ['image', 'url', 'link', '网络图片'],
    category: 'media',
    action: (editor) => {
      const url = prompt('请输入图片 URL:')
      if (url && url.trim()) {
        const store = useDocumentStore()
        store.insertBlock({
          type: 'image',
          attrs: { src: url.trim() },
        }, { afterId: editor.focusedBlockId })
      }
    },
  },
  {
    id: 'file',
    title: '文件',
    description: '插入文件附件',
    icon: '📎',
    keywords: ['file', 'attachment', '文件', '附件'],
    category: 'media',
    action: (editor) => {
      const url = prompt('请输入文件 URL:')
      const name = prompt('请输入文件名:', '文件')
      if (url && url.trim()) {
        const store = useDocumentStore()
        store.insertBlock({
          type: 'file',
          attrs: { src: url.trim(), name: name || '文件' },
        }, { afterId: editor.focusedBlockId })
      }
    },
  },
]

// 结构命令
const structureCommands: SlashCommand[] = [
  {
    id: 'table',
    title: '表格',
    description: '插入表格',
    icon: '⊞',
    keywords: ['table', '表格'],
    category: 'structure',
    action: (editor) => {
      const store = useDocumentStore()
      // 创建简单表格
      store.insertBlock({
        type: 'table',
        attrs: { rows: 3, cols: 3 },
      }, { afterId: editor.focusedBlockId })
    },
  },
  {
    id: 'grid-2',
    title: '两栏布局',
    description: '分两栏显示',
    icon: '▥',
    keywords: ['grid', 'column', '分栏', '两栏'],
    category: 'structure',
    action: (editor) => {
      const store = useDocumentStore()
      store.insertBlock({
        type: 'grid',
        attrs: { columns: 2 },
      }, { afterId: editor.focusedBlockId })
    },
  },
  {
    id: 'grid-3',
    title: '三栏布局',
    description: '分三栏显示',
    icon: '▦',
    keywords: ['grid', 'column', '分栏', '三栏'],
    category: 'structure',
    action: (editor) => {
      const store = useDocumentStore()
      store.insertBlock({
        type: 'grid',
        attrs: { columns: 3 },
      }, { afterId: editor.focusedBlockId })
    },
  },
  {
    id: 'toggle',
    title: '折叠块',
    description: '可展开/收起的块',
    icon: '▶',
    keywords: ['toggle', 'collapse', '折叠', '展开'],
    category: 'structure',
    action: (editor) => {
      const store = useDocumentStore()
      store.insertBlock({
        type: 'toggle',
        attrs: { collapsed: true },
        content: '点击展开...',
      }, { afterId: editor.focusedBlockId })
    },
  },
]

// 插入命令
const insertCommands: SlashCommand[] = [
  {
    id: 'date',
    title: '日期',
    description: '插入当前日期',
    icon: '📅',
    keywords: ['date', '日期'],
    category: 'insert',
    action: (editor) => {
      const date = new Date().toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
      const store = useDocumentStore()
      store.insertBlock({
        type: 'text',
        content: date,
      }, { afterId: editor.focusedBlockId })
    },
  },
  {
    id: 'time',
    title: '时间',
    description: '插入当前时间',
    icon: '🕐',
    keywords: ['time', '时间'],
    category: 'insert',
    action: (editor) => {
      const time = new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })
      const store = useDocumentStore()
      store.insertBlock({
        type: 'text',
        content: time,
      }, { afterId: editor.focusedBlockId })
    },
  },
  {
    id: 'datetime',
    title: '日期时间',
    description: '插入当前日期和时间',
    icon: '📆',
    keywords: ['datetime', '日期时间', 'now'],
    category: 'insert',
    action: (editor) => {
      const datetime = new Date().toLocaleString('zh-CN')
      const store = useDocumentStore()
      store.insertBlock({
        type: 'text',
        content: datetime,
      }, { afterId: editor.focusedBlockId })
    },
  },
]

// 命令分类
export const commandCategories: { id: SlashCommandCategory; name: string; icon: string }[] = [
  { id: 'basic', name: '基础', icon: '📝' },
  { id: 'list', name: '列表', icon: '📋' },
  { id: 'media', name: '媒体', icon: '🖼' },
  { id: 'structure', name: '结构', icon: '🏗' },
  { id: 'insert', name: '插入', icon: '➕' },
]

// 所有命令
export const slashCommands: SlashCommand[] = [
  ...basicCommands,
  ...listCommands,
  ...mediaCommands,
  ...structureCommands,
  ...insertCommands,
]

export default slashCommands

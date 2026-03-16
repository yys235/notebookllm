// @ts-nocheck
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import type { Editor } from '@tiptap/vue-3'

// 命令定义
export interface SlashCommand {
  title: string
  description: string
  icon?: string
  keywords?: string[]
  action: (editor: Editor) => void
}

// 预定义命令
export const defaultCommands: SlashCommand[] = [
  {
    title: '标题 1',
    description: '大标题',
    icon: 'H1',
    keywords: ['h1', 'heading', 'heading1', 'title'],
    action: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run()
  },
  {
    title: '标题 2',
    description: '中标题',
    icon: 'H2',
    keywords: ['h2', 'heading', 'heading2', 'subtitle'],
    action: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run()
  },
  {
    title: '标题 3',
    description: '小标题',
    icon: 'H3',
    keywords: ['h3', 'heading', 'heading3'],
    action: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run()
  },
  {
    title: '无序列表',
    description: '创建无序列表',
    icon: 'List',
    keywords: ['bullet', 'ul', 'list', 'unordered'],
    action: (editor) => editor.chain().focus().toggleBulletList().run()
  },
  {
    title: '有序列表',
    description: '创建有序列表',
    icon: 'OrderedList',
    keywords: ['ordered', 'ol', 'list', 'numbered'],
    action: (editor) => editor.chain().focus().toggleOrderedList().run()
  },
  {
    title: '任务列表',
    description: '创建任务列表',
    icon: 'CheckSquare',
    keywords: ['task', 'todo', 'checkbox'],
    action: (editor) => editor.chain().focus().toggleTaskList().run()
  },
  {
    title: '代码块',
    description: '插入代码块',
    icon: 'Code',
    keywords: ['code', 'codeblock', 'pre'],
    action: (editor) => editor.chain().focus().toggleCodeBlock().run()
  },
  {
    title: '引用',
    description: '插入引用块',
    icon: 'Quote',
    keywords: ['quote', 'blockquote', 'citation'],
    action: (editor) => editor.chain().focus().toggleBlockquote().run()
  },
  {
    title: '分割线',
    description: '插入分割线',
    icon: 'Minus',
    keywords: ['divider', 'hr', 'separator', 'line'],
    action: (editor) => editor.chain().focus().setHorizontalRule().run()
  },
  {
    title: '图片',
    description: '插入图片',
    icon: 'Image',
    keywords: ['image', 'img', 'photo'],
    action: (editor) => {
      const url = window.prompt('请输入图片 URL:')
      if (url) {
        editor.chain().focus().setImage({ src: url }).run()
      }
    }
  },
  {
    title: '表格',
    description: '插入表格',
    icon: 'Table',
    keywords: ['table', 'grid'],
    action: (editor) => {
      // 检查是否有表格扩展
      try {
        editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
      } catch (e) {
        console.warn('表格扩展未安装')
      }
    }
  }
]

// 模糊搜索函数
export function fuzzySearch(query: string, commands: SlashCommand[]): SlashCommand[] {
  if (!query.trim()) {
    return commands
  }

  const lowerQuery = query.toLowerCase()

  return commands
    .map(command => {
      let score = 0
      const title = command.title.toLowerCase()
      const keywords = command.keywords || []

      // 完全匹配标题
      if (title === lowerQuery) {
        score = 100
      }
      // 标题开头匹配
      else if (title.startsWith(lowerQuery)) {
        score = 80
      }
      // 标题包含
      else if (title.includes(lowerQuery)) {
        score = 60
      }
      // 关键词匹配
      else {
        for (const keyword of keywords) {
          if (keyword === lowerQuery) {
            score = Math.max(score, 70)
          } else if (keyword.startsWith(lowerQuery)) {
            score = Math.max(score, 50)
          } else if (keyword.includes(lowerQuery)) {
            score = Math.max(score, 30)
          }
        }
      }

      return { command, score }
    })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .map(item => item.command)
}

// 斜杠命令状态
export interface SlashCommandState {
  active: boolean
  query: string
  range: { from: number; to: number } | null
  filteredCommands: SlashCommand[]
  selectedIndex: number
}

// 事件类型
export type SlashCommandEventType = 'open' | 'close' | 'select' | 'update'

export interface SlashCommandEvent {
  type: SlashCommandEventType
  state: SlashCommandState
  command?: SlashCommand
}

// 回调类型
type SlashCommandCallback = (event: SlashCommandEvent) => void

// 全局回调存储
const callbacks = new Set<SlashCommandCallback>()
let currentState: SlashCommandState = {
  active: false,
  query: '',
  range: null,
  filteredCommands: [],
  selectedIndex: 0
}

// 订阅状态变化
export function subscribe(callback: SlashCommandCallback): () => void {
  callbacks.add(callback)
  return () => callbacks.delete(callback)
}

// 获取当前状态
export function getState(): SlashCommandState {
  return { ...currentState }
}

// 更新状态并通知
function updateState(updates: Partial<SlashCommandState>, eventType: SlashCommandEventType, command?: SlashCommand) {
  currentState = { ...currentState, ...updates }
  const event: SlashCommandEvent = {
    type: eventType,
    state: { ...currentState },
    command
  }
  callbacks.forEach(cb => cb(event))
}

// 执行命令
export function executeCommand(command: SlashCommand, editor: Editor): void {
  // 删除斜杠和查询文本
  if (currentState.range) {
    editor.chain()
      .focus()
      .deleteRange(currentState.range)
      .run()
  }

  // 执行命令
  command.action(editor)

  // 关闭菜单
  closeMenu()
}

// 关闭菜单
export function closeMenu(): void {
  updateState({
    active: false,
    query: '',
    range: null,
    filteredCommands: [],
    selectedIndex: 0
  }, 'close')
}

// 选择下一个
export function selectNext(): void {
  if (!currentState.active || currentState.filteredCommands.length === 0) return
  const newIndex = (currentState.selectedIndex + 1) % currentState.filteredCommands.length
  updateState({ selectedIndex: newIndex }, 'update')
}

// 选择上一个
export function selectPrevious(): void {
  if (!currentState.active || currentState.filteredCommands.length === 0) return
  const newIndex = currentState.selectedIndex === 0
    ? currentState.filteredCommands.length - 1
    : currentState.selectedIndex - 1
  updateState({ selectedIndex: newIndex }, 'update')
}

// 确认选择
export function confirmSelection(editor: Editor): void {
  if (!currentState.active || currentState.filteredCommands.length === 0) return
  const command = currentState.filteredCommands[currentState.selectedIndex]
  if (command) {
    executeCommand(command, editor)
  }
}

// 插件 Key
export const slashCommandPluginKey = new PluginKey('slashCommand')

// 自定义命令选项
interface SlashCommandOptions {
  commands?: SlashCommand[]
  char?: string
}

// 创建扩展
export const SlashCommandExtension = Extension.create<SlashCommandOptions>({
  name: 'slashCommand',

  addOptions() {
    return {
      commands: defaultCommands,
      char: '/'
    }
  },

  addProseMirrorPlugins() {
    const self = this
    const commands = this.options.commands || defaultCommands
    const triggerChar = this.options.char || '/'

    return [
      new Plugin({
        key: slashCommandPluginKey,

        state: {
          init() {
            return null
          },
          apply(tr, _prev, _oldState, newState) {
            // 检查是否有变化
            if (!tr.docChanged && !tr.selectionSet) return null

            const { from, to } = newState.selection

            // 只处理光标选择（非选区）
            if (from !== to) return null

            // 获取当前行
            const $from = newState.doc.resolve(from)
            const start = $from.before()
            const end = $from.after()
            const text = newState.doc.textBetween(start, from, '\0')

            // 查找最后一个触发字符
            const lastTriggerIndex = text.lastIndexOf(triggerChar)

            if (lastTriggerIndex === -1) {
              // 如果菜单激活且没有触发字符，关闭菜单
              if (currentState.active) {
                closeMenu()
              }
              return null
            }

            // 检查触发字符前是否是空格或行首
            const charBefore = lastTriggerIndex > 0 ? text[lastTriggerIndex - 1] : ' '
            if (charBefore !== ' ' && charBefore !== '\n' && charBefore !== '\0') {
              if (currentState.active) {
                closeMenu()
              }
              return null
            }

            // 获取查询字符串
            const query = text.slice(lastTriggerIndex + 1)
            const range = {
              from: start + lastTriggerIndex,
              to: from
            }

            // 检查查询字符串是否包含空格（如果有空格则关闭）
            if (query.includes(' ')) {
              if (currentState.active) {
                closeMenu()
              }
              return null
            }

            // 过滤命令
            const filteredCommands = fuzzySearch(query, commands)

            if (filteredCommands.length === 0) {
              if (currentState.active) {
                closeMenu()
              }
              return null
            }

            // 更新状态
            updateState({
              active: true,
              query,
              range,
              filteredCommands,
              selectedIndex: 0
            }, 'open')

            return { query, range }
          }
        },

        props: {
          handleKeyDown(view, event) {
            const state = currentState

            if (!state.active) return false

            // 向下箭头
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              selectNext()
              return true
            }

            // 向上箭头
            if (event.key === 'ArrowUp') {
              event.preventDefault()
              selectPrevious()
              return true
            }

            // Enter 选择
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              confirmSelection(self.editor)
              return true
            }

            // Esc 关闭
            if (event.key === 'Escape') {
              event.preventDefault()
              closeMenu()
              return true
            }

            return false
          }
        }
      })
    ]
  }
})

export default SlashCommandExtension

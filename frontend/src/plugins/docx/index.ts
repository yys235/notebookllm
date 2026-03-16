import type { EditorPlugin } from '../core/types'
import DocxEditor from './DocxEditor.vue'

// Docx Plugin Definition
export const DocxPlugin: EditorPlugin = {
  name: 'Docx Editor',
  type: 'docx',
  component: DocxEditor,
  icon: 'doc',
  description: '富文本文档编辑器',
  async onLoad() {
    console.log('Docx plugin loaded')
  },
  onUnload() {
    console.log('Docx plugin unloaded')
  }
}

// Export DocxEditor component
export { DocxEditor }
export default DocxPlugin

// Slash Command Extension
export {
  SlashCommandExtension,
  defaultCommands,
  fuzzySearch,
  subscribe,
  getState,
  executeCommand,
  closeMenu,
  selectNext,
  selectPrevious,
  confirmSelection,
  slashCommandPluginKey,
  type SlashCommand,
  type SlashCommandState,
  type SlashCommandEvent,
  type SlashCommandEventType
} from './extensions/SlashCommand'

// Components
export { default as SlashCommandMenu } from './components/SlashCommandMenu.vue'

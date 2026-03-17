/**
 * 块文档编辑器插件
 * 完全独立的块级编辑器，不依赖 Tiptap
 */
import type { EditorPlugin } from '../core/types'

// 导出组件
export { default as FeishuDocsEditor } from './FeishuDocsEditor.vue'

// 导出类型
export * from './types'

// 导出 store
export { useDocumentStore } from './stores/document'

// 导出 composable
export { useBlockEditor } from './composables/useBlockEditor'

// 导出命令
export { slashCommands, commandCategories } from './commands/slashCommands'

// 插件定义
const FeishuDocsPlugin: EditorPlugin = {
  id: 'feishu-docs',
  name: '块文档',
  description: '块级编辑器，支持丰富的块类型和格式',
  version: '1.0.0',
  icon: '📝',
  supportedBlocks: [
    'text', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'quote', 'code', 'callout',
    'bulletList', 'orderedList', 'taskList', 'listItem', 'taskItem',
    'image', 'video', 'file',
    'divider', 'table', 'grid', 'toggle',
  ],
  fileExtensions: ['.json', '.html'],
  component: () => import('./FeishuDocsEditor.vue'),
}

export default FeishuDocsPlugin

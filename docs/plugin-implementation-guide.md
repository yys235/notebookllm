# Plugin Implementation Guide

**Companion to:** plugin-architecture.md
**Purpose:** Detailed code examples and implementation patterns

---

## 1. Quick Start - Creating Your First Plugin

### 1.1 Minimal Plugin Template

```typescript
// src/plugins/my-plugin/my-plugin.ts
import { type EditorPlugin, type ActivationContext } from '@/core/types'
import { BasePlugin } from '@/plugins/base/base-plugin'

export class MyPlugin extends BasePlugin implements EditorPlugin {
  readonly id = 'my-plugin'
  readonly name = 'My Custom Plugin'
  readonly version = '1.0.0'
  readonly description = 'A simple example plugin'
  readonly icon = 'StarOutlined'

  // Define what formats this plugin supports
  readonly supportedFormats = [DocumentFormat.HTML]

  // Define capabilities
  readonly capabilities = {
    editable: true,
    collaborative: false,
    realtimeSync: false,
    versionControl: false,
    exportFormats: [ExportFormat.HTML],
    importFormats: [DocumentFormat.HTML],
    features: {
      formatting: false,
      tables: false,
      images: false,
      code: false,
      math: false,
      diagrams: false,
    },
  }

  // Private state
  private container: HTMLElement | null = null
  private content = ''

  async install(app: any): Promise<void> {
    console.log('MyPlugin installing...')
    // Load any dependencies here
    // await import('some-library')
  }

  async activate(context: ActivationContext): Promise<void> {
    this.container = context.container
    this.content = context.content as string

    // Initialize your editor UI
    this.render()
  }

  async deactivate(): Promise<void> {
    this.container = null
    this.content = ''
  }

  private render(): void {
    if (!this.container) return
    this.container.innerHTML = `
      <div class="my-plugin-editor">
        <textarea>${this.content}</textarea>
        <button onclick="save()">Save</button>
      </div>
    `
  }

  async getContent(format: ExportFormat): Promise<string> {
    return this.content
  }

  renderEditor(): VNode {
    return h('div', { class: 'my-plugin' }, 'My Plugin Editor')
  }

  renderToolbar(): VNode {
    return h('div', { class: 'my-toolbar' }, 'Toolbar')
  }
}
```

### 1.2 Registering Your Plugin

```typescript
// src/plugins/index.ts
import { PluginManager } from '@/core/plugin-manager'
import { MyPlugin } from './my-plugin/my-plugin'
import { TiptapPlugin } from './richtext/tiptap-plugin'

export async function registerAllPlugins(manager: PluginManager): Promise<void> {
  const plugins = [
    new MyPlugin(),
    new TiptapPlugin(),
  ]

  for (const plugin of plugins) {
    await plugin.install(app)
    manager.register(plugin)
  }
}
```

---

## 2. Core Implementation Patterns

### 2.1 Plugin Manager - Complete Implementation

```typescript
// src/core/plugin-manager.ts
import { EventEmitter } from 'eventemitter3'
import { type EditorPlugin, type ActivationContext, type DocumentFormat } from './types'

export class PluginManager extends EventEmitter {
  private plugins = new Map<string, EditorPlugin>()
  private activePlugin: EditorPlugin | null = null
  private app: any

  constructor(app: any) {
    super()
    this.app = app
  }

  /**
   * Register a plugin
   */
  register(plugin: EditorPlugin): void {
    if (this.plugins.has(plugin.id)) {
      throw new Error(`Plugin already registered: ${plugin.id}`)
    }

    this.plugins.set(plugin.id, plugin)
    this.emit('plugin:registered', { plugin })
    console.log(`Plugin registered: ${plugin.name} (${plugin.id})`)
  }

  /**
   * Unregister a plugin
   */
  async unregister(pluginId: string): Promise<void> {
    const plugin = this.plugins.get(pluginId)
    if (!plugin) {
      throw new Error(`Plugin not found: ${pluginId}`)
    }

    if (this.activePlugin?.id === pluginId) {
      await this.deactivatePlugin()
    }

    await plugin.uninstall()
    this.plugins.delete(pluginId)
    this.emit('plugin:unregistered', { pluginId })
  }

  /**
   * Get a plugin by ID
   */
  getPlugin(id: string): EditorPlugin | undefined {
    return this.plugins.get(id)
  }

  /**
   * List all registered plugins
   */
  listPlugins(): EditorPlugin[] {
    return Array.from(this.plugins.values())
  }

  /**
   * List plugins that support a specific format
   */
  listPluginsByFormat(format: DocumentFormat): EditorPlugin[] {
    return this.listPlugins().filter(plugin =>
      plugin.supportedFormats.includes(format)
    )
  }

  /**
   * Check if a plugin can be activated
   */
  canActivatePlugin(id: string): boolean {
    const plugin = this.getPlugin(id)
    return plugin?.capabilities.editable ?? false
  }

  /**
   * Activate a plugin
   */
  async activatePlugin(
    id: string,
    context: ActivationContext
  ): Promise<void> {
    const plugin = this.getPlugin(id)
    if (!plugin) {
      throw new Error(`Plugin not found: ${id}`)
    }

    // Deactivate current plugin if any
    if (this.activePlugin) {
      await this.deactivatePlugin()
    }

    // Activate the new plugin
    await plugin.activate(context)
    this.activePlugin = plugin

    // Set up content change listener
    plugin.on('content:change', this.handleContentChange)

    this.emit('plugin:activated', { plugin })
  }

  /**
   * Deactivate the current plugin
   */
  async deactivatePlugin(): Promise<void> {
    if (!this.activePlugin) return

    const plugin = this.activePlugin
    plugin.off('content:change', this.handleContentChange)
    await plugin.deactivate()

    this.activePlugin = null
    this.emit('plugin:deactivated', { plugin })
  }

  /**
   * Get the currently active plugin
   */
  getActivePlugin(): EditorPlugin | null {
    return this.activePlugin
  }

  /**
   * Switch from one plugin to another
   */
  async switchPlugin(
    fromFormat: DocumentFormat,
    toFormat: DocumentFormat,
    content: string
  ): Promise<string> {
    const fromPlugins = this.listPluginsByFormat(fromFormat)
    const toPlugins = this.listPluginsByFormat(toFormat)

    if (fromPlugins.length === 0 || toPlugins.length === 0) {
      throw new Error('No suitable plugin for format conversion')
    }

    const fromPlugin = fromPlugins[0]
    const toPlugin = toPlugins[0]

    // Get content from source plugin
    const exportContent = await fromPlugin.getContent(ExportFormat.HTML)

    // Activate target plugin with converted content
    await this.activatePlugin(toPlugin.id, {
      container: document.createElement('div'),
      content: exportContent as string,
      metadata: {},
    })

    return await toPlugin.getContent(ExportFormat.HTML) as string
  }

  private handleContentChange = (data: any): void => {
    this.emit('content:change', data)
  }
}

// Re-export types
export * from './types'
```

### 2.2 Event Bus Implementation

```typescript
// src/core/event-bus.ts
import { EventEmitter } from 'eventemitter3'

export type EventHandler<T = any> = (data: T) => void

export class EventBus {
  private emitter: EventEmitter
  private namespace: string

  constructor(namespace = '') {
    this.emitter = new EventEmitter()
    this.namespace = namespace
  }

  /**
   * Subscribe to an event
   * @returns Unsubscribe function
   */
  on<T = any>(event: string, handler: EventHandler<T>): () => void {
    const fullEvent = this.namespaced(event)
    this.emitter.on(fullEvent, handler)
    return () => this.off(event, handler)
  }

  /**
   * Subscribe to an event once
   * @returns Unsubscribe function
   */
  once<T = any>(event: string, handler: EventHandler<T>): () => void {
    const fullEvent = this.namespaced(event)
    this.emitter.once(fullEvent, handler)
    return () => this.off(event, handler)
  }

  /**
   * Unsubscribe from an event
   */
  off(event: string, handler?: EventHandler): void {
    const fullEvent = this.namespaced(event)
    if (handler) {
      this.emitter.off(fullEvent, handler)
    } else {
      this.emitter.removeAllListeners(fullEvent)
    }
  }

  /**
   * Emit an event
   */
  emit<T = any>(event: string, data?: T): void {
    const fullEvent = this.namespaced(event)
    this.emitter.emit(fullEvent, data)
  }

  /**
   * Create a namespaced event bus
   */
  namespace(ns: string): EventBus {
    return new EventBus(this.namespace ? `${this.namespace}:${ns}` : ns)
  }

  private namespaced(event: string): string {
    return this.namespace ? `${this.namespace}:${event}` : event
  }
}

// Global event bus instance
export const globalEventBus = new EventBus()
```

### 2.3 Base Plugin Class

```typescript
// src/plugins/base/base-plugin.ts
import { h, type VNode } from 'vue'
import { EventBus } from '@/core/event-bus'
import {
  type EditorPlugin,
  type ActivationContext,
  type ExportFormat,
  type DocumentFormat,
  type PluginCapabilities,
  type PluginEvent,
} from '@/core/types'

export abstract class BasePlugin implements EditorPlugin {
  abstract readonly id: string
  abstract readonly name: string
  abstract readonly version: string
  abstract readonly description: string
  abstract readonly author: string
  abstract readonly icon: string
  abstract readonly supportedFormats: DocumentFormat[]
  abstract readonly capabilities: PluginCapabilities

  protected eventBus = new EventBus()
  protected state: Record<string, any> = {}
  protected app: any = null

  async install(app: any): Promise<void> {
    this.app = app
    this.emit('installed')
  }

  async uninstall(): Promise<void> {
    this.eventBus.removeAllListeners()
    this.state = {}
    this.app = null
  }

  abstract activate(context: ActivationContext): Promise<void> | void

  async deactivate(): Promise<void> {
    this.emit('deactivate')
  }

  abstract getContent(format: ExportFormat): Promise<string | ArrayBuffer>

  abstract renderEditor(): VNode

  abstract renderToolbar(): VNode

  // Event methods
  on(event: PluginEvent, handler: (...args: any[]) => void): void {
    this.eventBus.on(event, handler)
  }

  off(event: PluginEvent, handler?: (...args: any[]) => void): void {
    this.eventBus.off(event, handler)
  }

  protected emit(event: string, data?: any): void {
    this.eventBus.emit(event, data)
  }

  // State management
  getState(): Record<string, any> {
    return { ...this.state }
  }

  setState(state: Record<string, any>): void {
    this.state = { ...this.state, ...state }
    this.emit('state:change', this.state)
  }

  hasUnsavedChanges(): boolean {
    return this.state.unsavedChanges ?? false
  }

  // Default implementations (can be overridden)
  createContent(options?: any): { success: boolean; data?: any } {
    return { success: true, data: '' }
  }

  loadContent(data: string | ArrayBuffer): { success: boolean; data?: any } {
    return { success: true, data }
  }

  isEmpty(): boolean {
    return !this.state.content || this.state.content.trim() === ''
  }

  canEdit(): boolean {
    return this.capabilities.editable
  }

  focus(): void {
    // Default: do nothing
  }

  blur(): void {
    // Default: do nothing
  }

  getSelection(): any {
    return null
  }

  insertContent(content: string): void {
    // Default: do nothing
  }

  enableCollaboration(config: any): void {
    if (!this.capabilities.collaborative) {
      throw new Error('Collaboration not supported')
    }
    this.setState({ collaborationEnabled: true, collaborationConfig: config })
  }

  disableCollaboration(): void {
    this.setState({ collaborationEnabled: false })
  }

  renderSettings?(): VNode {
    return h('div', { class: 'plugin-settings' }, 'No settings available')
  }
}
```

---

## 3. Tiptap Plugin Implementation

### 3.1 Complete Tiptap Plugin

```typescript
// src/plugins/richtext/tiptap-plugin.ts
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Highlight from '@tiptap/extension-highlight'
import Underline from '@tiptap/extension-underline'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import Collaboration from '@tiptap/extension-collaboration'
import CollaborationCursor from '@tiptap/extension-collaboration-cursor'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'

import { BasePlugin } from '@/plugins/base/base-plugin'
import type { EditorPlugin, ActivationContext, ExportFormat } from '@/core/types'
import TiptapToolbar from './components/TiptapToolbar.vue'
import { exportAsHtml, exportAsMarkdown, exportAsPdf } from '@/utils/export'

export class TiptapPlugin extends BasePlugin implements EditorPlugin {
  readonly id = 'richtext-tiptap'
  readonly name = 'Rich Text Editor'
  readonly version = '1.0.0'
  readonly description = 'Full-featured rich text editor powered by Tiptap'
  readonly author = 'NotebookLLM Team'
  readonly icon = 'FileTextOutlined'
  readonly supportedFormats = [
    DocumentFormat.HTML,
    DocumentFormat.MARKDOWN,
    DocumentFormat.JSON,
  ]
  readonly capabilities = {
    editable: true,
    collaborative: true,
    realtimeSync: true,
    versionControl: true,
    exportFormats: [
      ExportFormat.PDF,
      ExportFormat.HTML,
      ExportFormat.MARKDOWN,
    ],
    importFormats: [
      DocumentFormat.HTML,
      DocumentFormat.MARKDOWN,
      DocumentFormat.TXT,
    ],
    features: {
      formatting: true,
      tables: true,
      images: true,
      code: true,
      math: false,
      diagrams: false,
    },
  }

  private editor: any = null
  private ydoc: Y.Doc | null = null
  private provider: WebsocketProvider | null = null
  private container: HTMLElement | null = null

  async install(app: any): Promise<void> {
    await super.install(app)
    // Tiptap is tree-shaken, extensions are loaded on demand
  }

  async activate(context: ActivationContext): Promise<void> {
    this.container = context.container

    // Create Y.js document for collaboration
    if (context.collaborationState) {
      this.ydoc = new Y.Doc()
      this.provider = new WebsocketProvider(
        context.collaborationState.websocketUrl,
        context.collaborationState.roomId,
        this.ydoc
      )
    }

    // Initialize editor
    const { createEditor } = await import('@tiptap/vue-3')
    this.editor = createEditor({
      element: this.container,
      extensions: this.getExtensions(),
      content: context.content as string || '',
      editable: this.capabilities.editable,
      onUpdate: () => this.handleUpdate(),
      onSelectionUpdate: () => this.handleSelectionUpdate(),
    })

    this.emit('ready')
  }

  async deactivate(): Promise<void> {
    if (this.editor) {
      this.editor.destroy()
      this.editor = null
    }
    if (this.provider) {
      this.provider.destroy()
      this.provider = null
    }
    if (this.ydoc) {
      this.ydoc.destroy()
      this.ydoc = null
    }
    this.container = null
    await super.deactivate()
  }

  private getExtensions() {
    const extensions = [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4, 5, 6] },
      }),
      Placeholder.configure({
        placeholder: 'Start typing...',
      }),
      Highlight.configure({ multicolor: true }),
      Underline,
      TaskList,
      TaskItem.configure({ nested: true }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      Image.configure({
        inline: false,
        allowBase64: true,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          target: '_blank',
          rel: 'noopener noreferrer',
        },
      }),
    ]

    // Add collaboration if enabled
    if (this.ydoc && this.provider) {
      extensions.push(
        Collaboration.configure({
          document: this.ydoc,
        }),
        CollaborationCursor.configure({
          provider: this.provider,
          user: {
            name: this.state.userName || 'Anonymous',
            color: this.getUserColor(),
          },
        })
      )
    }

    return extensions
  }

  async getContent(format: ExportFormat): Promise<string> {
    const html = this.editor?.getHTML() || ''

    switch (format) {
      case ExportFormat.HTML:
        return html
      case ExportFormat.MARKDOWN:
        return this.htmlToMarkdown(html)
      case ExportFormat.PDF:
        await exportAsPdf(html, this.state.title || 'document')
        return ''
      default:
        throw new Error(`Unsupported export format: ${format}`)
    }
  }

  private htmlToMarkdown(html: string): string {
    const TurndownService = require('turndown').default
    const turndownService = new TurndownService({
      headingStyle: 'atx',
      codeBlockStyle: 'fenced',
    })
    return turndownService.turndown(html)
  }

  private handleUpdate(): void {
    const html = this.editor?.getHTML() || ''
    this.setState({ content: html, unsavedChanges: true })
    this.emit('content:change', { html })
  }

  private handleSelectionUpdate(): void {
    const { from, to } = this.editor?.state.selection || { from: 0, to: 0 }
    this.emit('selection:change', { from, to })
  }

  focus(): void {
    this.editor?.view.focus()
  }

  blur(): void {
    this.editor?.view.blur()
  }

  getSelection(): any {
    return this.editor?.state.selection
  }

  insertContent(content: string): void {
    this.editor?.chain().focus().insertContent(content).run()
  }

  renderEditor(): VNode {
    return h(EditorContent, { editor: this.editor })
  }

  renderToolbar(): VNode {
    return h(TiptapToolbar, {
      editor: this.editor,
      onAction: (action: string, data?: any) => this.handleToolbarAction(action, data),
    })
  }

  private handleToolbarAction(action: string, data?: any): void {
    switch (action) {
      case 'bold':
        this.editor?.chain().focus().toggleBold().run()
        break
      case 'italic':
        this.editor?.chain().focus().toggleItalic().run()
        break
      case 'heading':
        this.editor?.chain().focus().toggleHeading({ level: data }).run()
        break
      case 'link':
        this.editor?.chain().focus().setLink({ href: data }).run()
        break
      case 'image':
        this.editor?.chain().focus().setImage({ src: data }).run()
        break
      // ... more actions
    }
  }

  private getUserColor(): string {
    const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae']
    return colors[Math.floor(Math.random() * colors.length)]
  }
}
```

### 3.2 Tiptap Toolbar Component

```vue
<!-- src/plugins/richtext/components/TiptapToolbar.vue -->
<script setup lang="ts">
import { h } from 'vue'
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  LinkOutlined,
  PictureOutlined,
} from '@ant-design/icons-vue'

interface Props {
  editor: any
  onAction: (action: string, data?: any) => void
}

const props = defineProps<Props>()

const isActive = (name: string, attrs?: any) =>
  props.editor?.isActive(name, attrs)

const can = (name: string) =>
  props.editor?.can()[name]?.()

const actions = [
  { key: 'bold', icon: BoldOutlined, title: 'Bold', active: () => isActive('bold') },
  { key: 'italic', icon: ItalicOutlined, title: 'Italic', active: () => isActive('italic') },
  { key: 'underline', icon: UnderlineOutlined, title: 'Underline', active: () => isActive('underline') },
]

const headings = [
  { level: 1, label: 'H1' },
  { level: 2, label: 'H2' },
  { level: 3, label: 'H3' },
]
</script>

<template>
  <div class="tiptap-toolbar">
    <div class="toolbar-group">
      <button
        v-for="action in actions"
        :key="action.key"
        :class="{ active: action.active() }"
        :title="action.title"
        @click="onAction(action.key)"
      >
        <component :is="action.icon" />
      </button>
    </div>

    <div class="toolbar-divider"></div>

    <div class="toolbar-group">
      <button
        v-for="heading in headings"
        :key="heading.level"
        :class="{ active: isActive('heading', { level: heading.level }) }"
        :title="`Heading ${heading.level}`"
        @click="onAction('heading', heading.level)"
      >
        {{ heading.label }}
      </button>
    </div>

    <div class="toolbar-divider"></div>

    <div class="toolbar-group">
      <button title="Insert link" @click="onAction('link', prompt('Enter URL:'))">
        <LinkOutlined />
      </button>
      <button title="Insert image" @click="$refs.imageInput?.click()">
        <PictureOutlined />
      </button>
      <input
        ref="imageInput"
        type="file"
        accept="image/*"
        style="display: none"
        @change="(e) => onAction('image', e.target.files[0])"
      />
    </div>
  </div>
</template>

<style scoped>
.tiptap-toolbar {
  display: flex;
  gap: 4px;
  padding: 8px;
  background: #f5f5f5;
  border-bottom: 1px solid #e8e8e8;
}

.toolbar-group {
  display: flex;
  gap: 2px;
}

.toolbar-divider {
  width: 1px;
  background: #d9d9d9;
  margin: 0 8px;
}

button {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

button:hover {
  background: #e6e6e6;
}

button.active {
  background: #1890ff;
  color: white;
}
</style>
```

---

## 4. Mindmap Plugin Implementation

### 4.1 Mindmap Plugin Core

```typescript
// src/plugins/mindmap/mindmap-plugin.ts
import * as Y from 'yjs'
import * as d3 from 'd3'
import { WebsocketProvider } from 'y-websocket'

import { BasePlugin } from '@/plugins/base/base-plugin'
import type { EditorPlugin, ActivationContext, ExportFormat } from '@/core/types'
import MindmapToolbar from './components/MindmapToolbar.vue'
import { MindmapRenderer } from './renderer'

export class MindmapPlugin extends BasePlugin implements EditorPlugin {
  readonly id = 'mindmap-yjs'
  readonly name = 'Mindmap Editor'
  readonly version = '1.0.0'
  readonly description = 'Collaborative mind mapping with Y.js'
  readonly author = 'NotebookLLM Team'
  readonly icon = 'NodeIndexOutlined'
  readonly supportedFormats = [
    DocumentFormat.MM,
    DocumentFormat.MARKDOWN,
    DocumentFormat.JSON,
  ]
  readonly capabilities = {
    editable: true,
    collaborative: true,
    realtimeSync: true,
    versionControl: true,
    exportFormats: [
      ExportFormat.PNG,
      ExportFormat.SVG,
      ExportFormat.MARKDOWN,
      ExportFormat.PDF,
    ],
    importFormats: [DocumentFormat.MM, DocumentFormat.MARKDOWN],
    features: {
      formatting: false,
      tables: false,
      images: true,
      code: false,
      math: false,
      diagrams: true,
    },
  }

  private ydoc: Y.Doc | null = null
  private provider: WebsocketProvider | null = null
  private renderer: MindmapRenderer | null = null
  private container: HTMLElement | null = null

  async activate(context: ActivationContext): Promise<void> {
    this.container = context.container

    // Create Y.js document
    this.ydoc = new Y.Doc()
    const ymap = this.ydoc.getMap('mindmap')

    // Setup WebSocket provider for collaboration
    if (context.collaborationState) {
      this.provider = new WebsocketProvider(
        context.collaborationState.websocketUrl,
        context.collaborationState.roomId,
        this.ydoc
      )

      // Listen for remote changes
      ymap.observe(() => this.handleRemoteChange())
    }

    // Initialize renderer
    this.renderer = new MindmapRenderer(this.container, {
      ymap,
      editable: this.capabilities.editable,
      onNodeSelect: (node) => this.handleNodeSelect(node),
      onNodeUpdate: (node) => this.handleNodeUpdate(node),
    })

    // Load initial content
    if (context.content) {
      await this.loadContent(context.content)
    } else {
      // Create empty mindmap
      ymap.set('root', {
        id: 'root',
        text: 'Central Idea',
        children: [],
      })
    }

    this.emit('ready')
  }

  async loadContent(data: string | ArrayBuffer): Promise<{ success: boolean; data?: any }> {
    const content = typeof data === 'string' ? data : new TextDecoder().decode(data)
    const ymap = this.ydoc?.getMap('mindmap')

    if (!ymap) {
      return { success: false }
    }

    let mindmapData: any

    // Detect format
    if (content.trim().startsWith('#')) {
      // Markdown format (indented list)
      mindmapData = this.parseMarkdownToMindmap(content)
    } else if (content.trim().startsWith('{')) {
      // JSON format
      mindmapData = JSON.parse(content)
    } else {
      // Mindmap markdown format
      mindmapData = this.parseMindmapMarkdown(content)
    }

    ymap.set('root', mindmapData)
    this.renderer?.render()

    return { success: true, data: mindmapData }
  }

  private parseMarkdownToMindmap(markdown: string): any {
    const lines = markdown.split('\n')
    const root = { id: 'root', text: 'Mindmap', children: [] }
    const stack = [{ node: root, level: -1 }]

    for (const line of lines) {
      if (!line.trim()) continue

      // Count leading spaces/tabs to determine level
      const match = line.match(/^(\s*)(.+)$/)
      if (!match) continue

      const level = match[1].length
      const text = match[2].replace(/^#+\s*/, '').replace(/^\*\s*/, '').replace(/^-\s*/, '')

      const node = { id: `${Date.now()}-${Math.random()}`, text, children: [] }

      // Find parent
      while (stack.length > 1 && stack[stack.length - 1].level >= level) {
        stack.pop()
      }

      stack[stack.length - 1].node.children.push(node)
      stack.push({ node, level })
    }

    return root
  }

  private parseMindmapMarkdown(markdown: string): any {
    // Parse mindmap-specific markdown format
    // Example:
    // # Root
    // ## Child 1
    // ### Grandchild 1
    // ## Child 2

    const lines = markdown.split('\n')
    const root = { id: 'root', text: 'Mindmap', children: [] }
    const stack: Array<{ node: any; level: number }> = [
      { node: root, level: 0 },
    ]

    for (const line of lines) {
      const match = line.match(/^(#+)\s*(.+)$/)
      if (!match) continue

      const level = match[1].length
      const text = match[2]

      const node = { id: `${Date.now()}-${Math.random()}`, text, children: [] }

      while (stack.length > 1 && stack[stack.length - 1].level >= level) {
        stack.pop()
      }

      stack[stack.length - 1].node.children.push(node)
      stack.push({ node, level })
    }

    return root
  }

  async getContent(format: ExportFormat): Promise<string | ArrayBuffer> {
    const ymap = this.ydoc?.getMap('mindmap')
    const data = ymap?.toJSON() || {}

    switch (format) {
      case ExportFormat.MARKDOWN:
        return this.mindmapToMarkdown(data)
      case ExportFormat.SVG:
        return this.renderer?.toSvg() || ''
      case ExportFormat.PNG:
        return await this.renderer?.toPng() || new ArrayBuffer(0)
      default:
        return JSON.stringify(data)
    }
  }

  private mindmapToMarkdown(data: any): string {
    const lines: string[] = []
    const traverse = (node: any, level: number = 0) => {
      const prefix = '#'.repeat(level + 1)
      lines.push(`${prefix} ${node.text}`)
      for (const child of node.children || []) {
        traverse(child, level + 1)
      }
    }
    traverse(data)
    return lines.join('\n')
  }

  private handleRemoteChange(): void {
    this.renderer?.render()
    this.emit('content:change', {})
  }

  private handleNodeSelect(node: any): void {
    this.emit('selection:change', { node })
  }

  private handleNodeUpdate(node: any): void {
    const ymap = this.ydoc?.getMap('mindmap')
    if (ymap) {
      ymap.set('root', ymap.get('root'))
    }
    this.emit('content:change', { node })
  }

  renderEditor(): VNode {
    return h('div', { class: 'mindmap-editor' })
  }

  renderToolbar(): VNode {
    return h(MindmapToolbar, {
      onAddNode: () => this.addNode(),
      onRemoveNode: () => this.removeSelectedNode(),
      onLayoutChange: (layout: string) => this.renderer?.setLayout(layout),
    })
  }

  addNode(): void {
    const selectedNode = this.renderer?.getSelectedNode()
    const ymap = this.ydoc?.getMap('mindmap')
    const root = ymap?.get('root')

    if (!root) return

    const newNode = {
      id: `node-${Date.now()}`,
      text: 'New Node',
      children: [],
    }

    if (selectedNode) {
      // Add as child of selected node
      selectedNode.children.push(newNode)
    } else {
      // Add to root
      root.children.push(newNode)
    }

    ymap?.set('root', root)
    this.renderer?.render()
  }

  removeSelectedNode(): void {
    const selectedNode = this.renderer?.getSelectedNode()
    if (!selectedNode || selectedNode.id === 'root') return

    const ymap = this.ydoc?.getMap('mindmap')
    const root = ymap?.get('root')

    const removeFromParent = (parent: any): boolean => {
      const index = parent.children?.findIndex((c: any) => c.id === selectedNode.id)
      if (index !== -1) {
        parent.children.splice(index, 1)
        return true
      }
      for (const child of parent.children || []) {
        if (removeFromParent(child)) return true
      }
      return false
    }

    if (root && removeFromParent(root)) {
      ymap?.set('root', root)
      this.renderer?.render()
    }
  }
}
```

### 4.2 Mindmap Renderer

```typescript
// src/plugins/mindmap/renderer.ts
import * as d3 from 'd3'

export interface MindmapNode {
  id: string
  text: string
  children?: MindmapNode[]
  x?: number
  y?: number?
}

export interface MindmapRendererOptions {
  ymap: Y.Map<any>
  editable?: boolean
  onNodeSelect?: (node: MindmapNode) => void
  onNodeUpdate?: (node: MindmapNode) => void
}

export class MindmapRenderer {
  private container: HTMLElement
  private options: MindmapRendererOptions
  private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>
  private g: d3.Selection<SVGGElement, unknown, null, undefined>
  private zoom: d3.ZoomBehavior<SVGElement, unknown>
  private root: d3.HierarchyNode<MindmapNode>
  private treemap: d3.TreeLayout<MindmapNode>
  private selectedNode: MindmapNode | null = null
  private layout: 'horizontal' | 'radial' = 'horizontal'

  constructor(container: HTMLElement, options: MindmapRendererOptions) {
    this.container = container
    this.options = options

    // Setup SVG
    const { width, height } = container.getBoundingClientRect()
    this.svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [-width / 2, -height / 2, width, height])

    // Setup zoom
    this.zoom = d3
      .zoom<SVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (e) => {
        this.g.attr('transform', e.transform)
      })

    this.svg.call(this.zoom as any)

    // Main group
    this.g = this.svg.append('g')

    // Setup tree layout
    this.treemap = d3.tree<MindmapNode>().size([2 * Math.PI, Math.min(width, height) / 2 - 100])

    // Initial render
    this.render()
  }

  render(): void {
    const data = this.options.ymap.get('root')
    if (!data) return

    // Convert to D3 hierarchy
    this.root = d3.hierarchy<MindmapNode>(data)

    if (this.layout === 'horizontal') {
      this.renderHorizontal()
    } else {
      this.renderRadial()
    }
  }

  private renderHorizontal(): void {
    // Clear previous content
    this.g.selectAll('*').remove()

    // Create tree layout
    const treeData = d3.tree<MindmapNode>().size([
      this.container.offsetWidth - 200,
      this.container.offsetHeight - 100,
    ])(this.root)

    // Draw links
    this.g
      .append('g')
      .attr('class', 'links')
      .selectAll('path')
      .data(treeData.links())
      .join('path')
      .attr('d', d3.linkHorizontal<any, MindmapNode>(
        d => [d.y, d.x],
        d => [d.source.y + 180, d.x]
      ))
      .attr('fill', 'none')
      .attr('stroke', '#ccc')
      .attr('stroke-width', 2)

    // Draw nodes
    const nodes = this.g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(treeData.descendants())
      .join('g')
      .attr('transform', d => `translate(${d.y},${d.x})`)
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .on('click', (e, d) => this.selectNode(d.data))

    // Node rectangles
    nodes
      .append('rect')
      .attr('x', -60)
      .attr('y', -15)
      .attr('width', 120)
      .attr('height', 30)
      .attr('rx', 5)
      .attr('fill', d => (d.data === this.selectedNode ? '#1890ff' : '#fff'))
      .attr('stroke', '#1890ff')
      .attr('stroke-width', 2)

    // Node text
    nodes
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .text(d => d.data.text)
      .attr('fill', d => (d.data === this.selectedNode ? '#fff' : '#000'))
      .style('font-size', '12px')
  }

  private renderRadial(): void {
    // Clear previous content
    this.g.selectAll('*').remove()

    // Create radial tree layout
    const treeData = this.treemap(this.root)

    // Draw links
    this.g
      .append('g')
      .attr('class', 'links')
      .selectAll('path')
      .data(treeData.links())
      .join('path')
      .attr(
        'd',
        d3
          .linkRadial<any, MindmapNode>(d => d.y, d => d.x)
          .angle(d => (d.x + Math.PI / 2))
          .radius(d => d.y)
      )
      .attr('fill', 'none')
      .attr('stroke', '#ccc')
      .attr('stroke-width', 2)

    // Draw nodes
    const nodes = this.g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(treeData.descendants())
      .join('g')
      .attr('transform', d => `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`)
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .on('click', (e, d) => this.selectNode(d.data))

    // Node rectangles
    nodes
      .append('rect')
      .attr('x', -40)
      .attr('y', -12)
      .attr('width', 80)
      .attr('height', 24)
      .attr('rx', 4)
      .attr('fill', '#fff')
      .attr('stroke', '#1890ff')
      .attr('stroke-width', 2)

    // Node text
    nodes
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .text(d => d.data.text)
      .attr('fill', '#000')
      .style('font-size', '11px')
      .attr('transform', d => (d.x < Math.PI === false ? 'rotate(180)' : null))
  }

  selectNode(node: MindmapNode): void {
    this.selectedNode = node
    this.options.onNodeSelect?.(node)
    this.render()
  }

  getSelectedNode(): MindmapNode | null {
    return this.selectedNode
  }

  setLayout(layout: 'horizontal' | 'radial'): void {
    this.layout = layout
    this.render()
  }

  async toPng(): Promise<ArrayBuffer> {
    const svgData = new XMLSerializer().serializeToString(this.svg.node()!)
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    const img = document.createElement('img')

    return new Promise((resolve) => {
      img.onload = () => {
        canvas.width = img.width * 2
        canvas.height = img.height * 2
        ctx?.scale(2, 2)
        ctx?.drawImage(img, 0, 0)
        resolve(canvas.toBuffer())
      }
      img.src = 'data:image/svg+xml;base64,' + btoa(svgData)
    })
  }

  toSvg(): string {
    return new XMLSerializer().serializeToString(this.svg.node()!)
  }
}
```

---

## 5. Testing Guidelines

### 5.1 Plugin Test Template

```typescript
// src/plugins/__tests__/my-plugin.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { MyPlugin } from '../my-plugin'
import { PluginManager } from '@/core/plugin-manager'

describe('MyPlugin', () => {
  let plugin: MyPlugin
  let manager: PluginManager

  beforeEach(() => {
    plugin = new MyPlugin()
    manager = new PluginManager()
  })

  describe('metadata', () => {
    it('should have correct id', () => {
      expect(plugin.id).toBe('my-plugin')
    })

    it('should have supported formats', () => {
      expect(plugin.supportedFormats).toContain(DocumentFormat.HTML)
    })

    it('should have capabilities', () => {
      expect(plugin.capabilities.editable).toBe(true)
    })
  })

  describe('installation', () => {
    it('should install successfully', async () => {
      await plugin.install({})
      expect(plugin.getState().installed).toBe(true)
    })
  })

  describe('content handling', () => {
    it('should load content', async () => {
      await plugin.activate({
        container: document.createElement('div'),
        content: '<p>Hello</p>',
        metadata: {},
      })

      const result = await plugin.getContent(ExportFormat.HTML)
      expect(result).toContain('Hello')
    })

    it('should detect empty content', () => {
      expect(plugin.isEmpty()).toBe(true)
    })
  })

  describe('collaboration', () => {
    it('should enable collaboration if supported', () => {
      if (plugin.capabilities.collaborative) {
        expect(() => {
          plugin.enableCollaboration({
            websocketUrl: 'ws://localhost:1234',
            roomId: 'test-room',
          })
        }).not.toThrow()
      }
    })

    it('should throw if collaboration not supported', () => {
      const noCollabPlugin = new MyPlugin()
      noCollabPlugin.capabilities.collaborative = false

      expect(() => {
        noCollabPlugin.enableCollaboration({})
      }).toThrow()
    })
  })
})
```

---

## 6. Migration Guide

### 6.1 Migrating Existing TiptapEditor

**Before:**

```vue
<!-- Old TiptapEditor.vue -->
<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'

const editor = useEditor({
  content: props.modelValue,
  extensions: [StarterKit, Placeholder],
})
</script>

<template>
  <EditorContent :editor="editor" />
</template>
```

**After:**

```vue
<!-- New UnifiedEditor.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { UnifiedEditor } from '@/components/UnifiedEditor.vue'

const editorRef = ref()
</script>

<template>
  <UnifiedEditor
    ref="editorRef"
    v-model="content"
    format="html"
    @ready="handleReady"
  />
</template>
```

### 6.2 Migrating Custom Extensions

**Before:**

```typescript
// Custom extension directly in editor
import { Extension } from '@tiptap/core'

const CustomExtension = Extension.create({
  name: 'custom',
  // ...
})
```

**After:**

```typescript
// src/plugins/richtext/extensions/custom.ts
import { Extension } from '@tiptap/core'

export const CustomExtension = Extension.create({
  name: 'custom',
  // ...
})

// Register with plugin
const plugin = new TiptapPlugin()
plugin.registerExtension(CustomExtension)
```

---

This implementation guide provides everything needed to build out the plugin architecture. The core patterns can be adapted for any document type.

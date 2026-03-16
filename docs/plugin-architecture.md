# Document Editor Plugin Architecture

**Version**: 1.0
**Date**: 2026-03-13
**Author**: Security Engineer (ux-designer-2)
**Status**: Design Document

---

## 1. Overview

This document outlines a comprehensive plugin-based architecture for the NotebookLLM document editor system. The architecture enables extensible editor support for multiple document types (Rich Text, Word, Excel, Mindmap, Flowchart) through a unified plugin interface.

### 1.1 Goals

- **Modularity**: Each editor type is a self-contained plugin
- **Extensibility**: New editor types can be added without modifying core code
- **Consistency**: All plugins follow a common interface and interaction pattern
- **Performance**: Plugins are loaded on-demand
- **Maintainability**: Clear separation of concerns

### 1.2 Design Principles

1. **Plugin Isolation**: Each plugin manages its own state, dependencies, and lifecycle
2. **Core Abstraction**: Common editor operations are abstracted through a unified interface
3. **Event Bus**: Plugins communicate through a typed event system
4. **Registry Pattern**: Plugins are discovered and registered dynamically
5. **Sandboxing**: Plugin code is isolated to prevent conflicts

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Document Editor Layer                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Rich Text   │  │    Word      │  │   Excel      │          │
│  │   (Tiptap)   │  │   (DOCX)     │  │  (SheetJS)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   Mindmap    │  │  Flowchart   │                            │
│  │   (Y.js)     │  │  (Mermaid)   │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Plugin Manager Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Registry   │  │  Event Bus   │  │  State Mgr   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Loader     │  │   Resolver   │  │   Validator  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Core Editor Interface                     │
│  - Content Management  - Selection  - Undo/Redo  - Formatting  │
│  - Collaboration      - Export    - Import      - Search      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Interfaces

### 3.1 Base Plugin Interface

```typescript
/**
 * Base interface that all editor plugins must implement
 */
interface EditorPlugin {
  // Plugin metadata
  readonly id: string
  readonly name: string
  readonly version: string
  readonly description: string
  readonly author: string
  readonly icon: string
  readonly supportedFormats: DocumentFormat[]
  readonly capabilities: PluginCapabilities

  // Lifecycle hooks
  install(app: PluginApp): void | Promise<void>
  uninstall(): void | Promise<void>
  activate(context: ActivationContext): void | Promise<void>
  deactivate(): void | Promise<void>

  // Content operations
  createContent(options?: ContentOptions): ContentResult
  loadContent(data: string | ArrayBuffer): ContentResult
  getContent(format: ExportFormat): Promise<string | ArrayBuffer>
  isEmpty(): boolean

  // Editor operations
  canEdit(): boolean
  focus(): void
  blur(): void
  getSelection(): Selection | null
  insertContent(content: string): void

  // State
  getState(): EditorState
  setState(state: EditorState): void
  hasUnsavedChanges(): boolean

  // Collaboration
  enableCollaboration(config: CollaborationConfig): void
  disableCollaboration(): void

  // UI Components
  renderToolbar(): VNode
  renderEditor(): VNode
  renderSettings?(): VNode

  // Events
  on(event: PluginEvent, handler: EventHandler): void
  off(event: PluginEvent, handler?: EventHandler): void
  emit(event: PluginEvent, data?: any): void
}

/**
 * Supported document formats
 */
enum DocumentFormat {
  HTML = 'html',
  MARKDOWN = 'markdown',
  JSON = 'json',
  DOCX = 'docx',
  XLSX = 'xlsx',
  PDF = 'pdf',
  TXT = 'txt',
  MM = 'mindmap',      // Mindmap format
  MMD = 'mermaid',     // Mermaid flowchart
  GRAPHML = 'graphml', // GraphML for diagrams
}

/**
 * Plugin capabilities flags
 */
interface PluginCapabilities {
  editable: boolean
  collaborative: boolean
  realtimeSync: boolean
  versionControl: boolean
  exportFormats: ExportFormat[]
  importFormats: DocumentFormat[]
  features: {
    formatting: boolean
    tables: boolean
    images: boolean
    code: boolean
    math: boolean
    diagrams: boolean
  }
}

/**
 * Export format options
 */
enum ExportFormat {
  PDF = 'pdf',
  HTML = 'html',
  MARKDOWN = 'markdown',
  PNG = 'png',
  SVG = 'svg',
  DOCX = 'docx',
  XLSX = 'xlsx',
}

/**
 * Content creation options
 */
interface ContentOptions {
  template?: string
  initialData?: any
  metadata?: Record<string, any>
}

/**
 * Content result wrapper
 */
interface ContentResult {
  success: boolean
  data?: any
  error?: Error
  metadata?: ContentMetadata
}

/**
 * Content metadata
 */
interface ContentMetadata {
  format: DocumentFormat
  size: number
  created: Date
  modified: Date
  version: string
}
```

### 3.2 Plugin Manager Interface

```typescript
/**
 * Plugin Manager - Central registry and lifecycle manager
 */
class PluginManager {
  private plugins: Map<string, EditorPlugin>
  private activePlugin: EditorPlugin | null
  private eventBus: EventBus
  private stateManager: StateManager

  // Registration
  register(plugin: EditorPlugin): void
  unregister(pluginId: string): void
  getPlugin(id: string): EditorPlugin | undefined
  listPlugins(): EditorPlugin[]
  listPluginsByFormat(format: DocumentFormat): EditorPlugin[]

  // Activation
  activatePlugin(id: string, context: ActivationContext): Promise<void>
  deactivatePlugin(): Promise<void>
  getActivePlugin(): EditorPlugin | null
  canActivatePlugin(id: string): boolean

  // Content switching
  switchPlugin(
    fromPluginId: string,
    toPluginId: string,
    content: string
  ): Promise<ContentResult>

  // Events
  on(event: ManagerEvent, handler: EventHandler): void
  off(event: ManagerEvent, handler?: EventHandler): void
}

/**
 * Context passed when activating a plugin
 */
interface ActivationContext {
  container: HTMLElement
  content: string | ArrayBuffer
  metadata: Record<string, any>
  collaborationState?: CollaborationState
  toolbarContainer: HTMLElement
  settingsContainer?: HTMLElement
}

/**
 * Events emitted by plugin manager
 */
enum ManagerEvent {
  PLUGIN_REGISTERED = 'plugin:registered',
  PLUGIN_UNREGISTERED = 'plugin:unregistered',
  PLUGIN_ACTIVATED = 'plugin:activated',
  PLUGIN_DEACTIVATED = 'plugin:deactivated',
  CONTENT_CHANGED = 'content:changed',
  STATE_CHANGED = 'state:changed',
  ERROR = 'error',
}
```

### 3.3 Event Bus Interface

```typescript
/**
 * Typed event bus for plugin communication
 */
class EventBus {
  // Subscribe to events
  on<T = any>(event: string, handler: (data: T) => void): () => void
  once<T = any>(event: string, handler: (data: T) => void): () => void

  // Unsubscribe
  off(event: string, handler?: Function): void

  // Emit events
  emit<T = any>(event: string, data?: T): void

  // Event namespaces
  namespace(namespace: string): EventBus
}

/**
 * Standard plugin events
 */
enum PluginEvent {
  // Content events
  CONTENT_CHANGE = 'content:change',
  CONTENT_SAVE = 'content:save',
  CONTENT_LOAD = 'content:load',
  CONTENT_EXPORT = 'content:export',

  // Selection events
  SELECTION_CHANGE = 'selection:change',
  CURSOR_MOVE = 'cursor:move',

  // Editor events
  EDITOR_READY = 'editor:ready',
  EDITOR_FOCUS = 'editor:focus',
  EDITOR_BLUR = 'editor:blur',
  EDITOR_DESTROY = 'editor:destroy',

  // Collaboration events
  COLLABORATION_JOIN = 'collab:join',
  COLLABORATION_LEAVE = 'collab:leave',
  COLLABORATION_CURSOR = 'collab:cursor',
  COLLABORATION_EDIT = 'collab:edit',

  // Format events
  FORMAT_APPLY = 'format:apply',
  FORMAT_REMOVE = 'format:remove',

  // Error events
  ERROR = 'error',
  WARNING = 'warning',
}
```

---

## 4. Plugin Implementations

### 4.1 Rich Text Plugin (Tiptap)

```typescript
/**
 * Rich Text Editor Plugin using Tiptap
 */
class TiptapPlugin implements EditorPlugin {
  readonly id = 'richtext-tiptap'
  readonly name = 'Rich Text Editor'
  readonly version = '1.0.0'
  readonly supportedFormats = [
    DocumentFormat.HTML,
    DocumentFormat.MARKDOWN,
    DocumentFormat.JSON,
  ]
  readonly capabilities: PluginCapabilities = {
    editable: true,
    collaborative: true,
    realtimeSync: true,
    versionControl: true,
    exportFormats: [ExportFormat.PDF, ExportFormat.HTML, ExportFormat.MARKDOWN],
    importFormats: [DocumentFormat.HTML, DocumentFormat.MARKDOWN, DocumentFormat.TXT],
    features: {
      formatting: true,
      tables: true,
      images: true,
      code: true,
      math: false,
      diagrams: true,
    },
  }

  private editor: Editor | null = null
  private ydoc: Y.Doc | null = null
  private provider: WebsocketProvider | null = null

  async install(app: PluginApp): Promise<void> {
    // Load Tiptap dependencies dynamically
    const { Editor } = await import('@tiptap/vue-3')
    const StarterKit = await import('@tiptap/starter-kit')
    // ... other extensions
  }

  async activate(context: ActivationContext): Promise<void> {
    // Initialize Tiptap editor with extensions
    this.editor = new Editor({
      element: context.container,
      extensions: [
        StarterKit,
        Table,
        Image,
        CodeBlock,
        // ... custom extensions
      ],
      content: context.content as string,
      collaborations: context.collaborationState
        ? this.createCollaboration(context.collaborationState)
        : undefined,
    })
  }

  renderToolbar(): VNode {
    return h(TiptapToolbar, {
      editor: this.editor,
      onAction: this.handleToolbarAction,
    })
  }
}
```

### 4.2 Word Document Plugin (DOCX)

```typescript
/**
 * Word Document Plugin using mammoth.js
 */
class DocxPlugin implements EditorPlugin {
  readonly id = 'word-docx'
  readonly name = 'Word Document'
  readonly version = '1.0.0'
  readonly supportedFormats = [DocumentFormat.DOCX]
  readonly capabilities: PluginCapabilities = {
    editable: false,  // DOCX is import/export only
    collaborative: false,
    realtimeSync: false,
    versionControl: false,
    exportFormats: [ExportFormat.DOCX, ExportFormat.PDF],
    importFormats: [DocumentFormat.DOCX],
    features: {
      formatting: true,  // Preserved from DOCX
      tables: true,
      images: true,
      code: true,
      math: true,
      diagrams: false,
    },
  }

  private mammoth: any = null
  private document: Document | null = null

  async install(app: PluginApp): Promise<void> {
    this.mammoth = await import('mammoth')
  }

  async loadContent(data: ArrayBuffer): Promise<ContentResult> {
    const result = await this.mammoth.convertToHtml(
      { arrayBuffer: data },
      { includeDefaultStyleMap: true }
    )

    // Render in Tiptap for display (read-only)
    return {
      success: true,
      data: result.value,
      metadata: {
        format: DocumentFormat.DOCX,
        size: data.byteLength,
        messages: result.messages,
      },
    }
  }

  async getContent(format: ExportFormat): Promise<string | ArrayBuffer> {
    if (format === ExportFormat.HTML) {
      return this.document?.body.innerHTML || ''
    }
    // DOCX export implementation
    throw new Error('Export format not supported')
  }

  renderEditor(): VNode {
    return h('div', { class: 'docx-viewer readonly' }, [
      h('div', { innerHTML: this.document?.body.innerHTML }),
    ])
  }
}
```

### 4.3 Excel Spreadsheet Plugin

```typescript
/**
 * Excel Spreadsheet Plugin using HyperFormula + handsontable
 */
class ExcelPlugin implements EditorPlugin {
  readonly id = 'excel-sheet'
  readonly name = 'Excel Spreadsheet'
  readonly version = '1.0.0'
  readonly supportedFormats = [DocumentFormat.XLSX]
  readonly capabilities: PluginCapabilities = {
    editable: true,
    collaborative: true,
    realtimeSync: true,
    versionControl: false,
    exportFormats: [ExportFormat.XLSX, ExportFormat.CSV],
    importFormats: [DocumentFormat.XLSX, DocumentFormat.CSV],
    features: {
      formatting: true,
      tables: true,
      images: false,
      code: false,
      math: true,  // Formulas!
      diagrams: false,
    },
  }

  private hot: Handsontable | null = null
  private hyperFormula: HyperFormula | null = null

  async install(app: PluginApp): Promise<void> {
    await Promise.all([
      import('handsontable'),
      import('hyperformula'),
    ])
  }

  async activate(context: ActivationContext): Promise<void> {
    const { default: Handsontable } = await import('handsontable')
    const { HyperFormula } = await import('hyperformula')

    // Initialize HyperFormula for calculations
    this.hyperFormula = new HyperFormula({
      licenseKey: 'gpl-v3',
    })

    // Initialize Handsontable
    this.hot = new Handsontable(context.container, {
      data: this.parseData(context.content),
      formulas: {
        engine: this.hyperFormula,
      },
      colHeaders: true,
      rowHeaders: true,
      width: '100%',
      height: '100%',
    })
  }

  renderToolbar(): VNode {
    return h(ExcelToolbar, {
      onInsertRow: () => this.hot?.alter('insert_row'),
      onInsertColumn: () => this.hot?.alter('insert_col'),
      onSetFormula: (formula: string) => this.hyperFormula?.setFormula(formula),
    })
  }
}
```

### 4.4 Mindmap Plugin

```typescript
/**
 * Mindmap Plugin using Y.js + custom visualization
 */
class MindmapPlugin implements EditorPlugin {
  readonly id = 'mindmap-yjs'
  readonly name = 'Mindmap Editor'
  readonly version = '1.0.0'
  readonly supportedFormats = [
    DocumentFormat.MM,
    DocumentFormat.MARKDOWN,
    DocumentFormat.JSON,
  ]
  readonly capabilities: PluginCapabilities = {
    editable: true,
    collaborative: true,  // Y.js supports real-time collaboration!
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

  async install(app: PluginApp): Promise<void> {
    await Promise.all([
      import('yjs'),
      import('y-websocket'),
    ])
  }

  async activate(context: ActivationContext): Promise<void> {
    const Y = (await import('yjs')).default
    const { WebsocketProvider } = await import('y-websocket')

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
    }

    // Initialize renderer
    this.renderer = new MindmapRenderer(context.container, {
      ymap,
      editable: this.capabilities.editable,
      onContentChange: (data) => this.emitContentChange(data),
    })

    // Load initial content
    if (context.content) {
      await this.loadContent(context.content)
    }
  }

  async loadContent(data: string | ArrayBuffer): Promise<ContentResult> {
    const content = typeof data === 'string' ? data : new TextDecoder().decode(data)

    // Try to detect format and parse
    if (content.trim().startsWith('#')) {
      // Markdown format
      return this.loadFromMarkdown(content)
    } else if (content.trim().startsWith('{')) {
      // JSON format
      return this.loadFromJson(content)
    }

    // Mindmap markdown format
    return this.loadFromMindmapMarkdown(content)
  }

  private loadFromMarkdown(markdown: string): ContentResult {
    // Parse markdown mindmap format (indented list)
    const lines = markdown.split('\n')
    const root = this.parseIndentedList(lines)

    const ymap = this.ydoc?.getMap('mindmap')
    ymap?.set('root', root)

    return { success: true, data: root }
  }

  async getContent(format: ExportFormat): Promise<string | ArrayBuffer> {
    const ymap = this.ydoc?.getMap('mindmap')
    const data = ymap?.toJSON() || {}

    switch (format) {
      case ExportFormat.MARKDOWN:
        return this.toMarkdown(data)
      case ExportFormat.PNG:
        return await this.toPng()
      case ExportFormat.SVG:
        return this.toSvg()
      default:
        throw new Error('Export format not supported')
    }
  }

  renderToolbar(): VNode {
    return h(MindmapToolbar, {
      onAddNode: () => this.renderer?.addNode(),
      onRemoveNode: () => this.renderer?.removeSelected(),
      onLayoutChange: (layout: LayoutType) => this.renderer?.setLayout(layout),
    })
  }
}
```

### 4.5 Flowchart Plugin

```typescript
/**
 * Flowchart Plugin using Mermaid.js
 */
class FlowchartPlugin implements EditorPlugin {
  readonly id = 'flowchart-mermaid'
  readonly name = 'Flowchart Editor'
  readonly version = '1.0.0'
  readonly supportedFormats = [
    DocumentFormat.MMD,
    DocumentFormat.MARKDOWN,
  ]
  readonly capabilities: PluginCapabilities = {
    editable: true,
    collaborative: false,
    realtimeSync: false,
    versionControl: true,
    exportFormats: [
      ExportFormat.PNG,
      ExportFormat.SVG,
      ExportFormat.PDF,
    ],
    importFormats: [DocumentFormat.MMD, DocumentFormat.MARKDOWN],
    features: {
      formatting: false,
      tables: false,
      images: false,
      code: false,
      math: false,
      diagrams: true,
    },
  }

  private mermaid: any = null
  private codeEditor: CodeEditor | null = null

  async install(app: PluginApp): Promise<void> {
    this.mermaid = await import('mermaid')
    this.mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
    })
  }

  async activate(context: ActivationContext): Promise<void> {
    // Create split pane: code editor + preview
    const container = context.container

    // Code editor for Mermaid syntax
    this.codeEditor = new CodeEditor(container.querySelector('.code-pane'), {
      language: 'mermaid',
      value: context.content as string || defaultMermaidTemplate,
      onChange: this.renderPreview,
    })

    // Initial render
    await this.renderPreview(this.codeEditor.getValue())
  }

  private async renderPreview(code: string): Promise<void> {
    try {
      const { svg } = await this.mermaid.render('mermaid-chart', code)
      const previewPane = document.querySelector('.preview-pane')
      previewPane.innerHTML = svg
    } catch (error) {
      // Show error in preview
      document.querySelector('.preview-pane').innerHTML = `
        <div class="mermaid-error">
          <p>Invalid Mermaid syntax:</p>
          <pre>${error}</pre>
        </div>
      `
    }
  }

  async getContent(format: ExportFormat): Promise<string | ArrayBuffer> {
    const code = this.codeEditor?.getValue() || ''

    switch (format) {
      case ExportFormat.SVG:
        return await this.mermaid.render('export', code).then(r => r.svg)
      case ExportFormat.PNG:
        return await this.svgToPng(await this.getContent(ExportFormat.SVG) as string)
      default:
        return code
    }
  }
}

const defaultMermaidTemplate = `graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E`
```

---

## 5. Integration Architecture

### 5.1 Unified Editor Component

```typescript
/**
 * Unified Editor Component - Main entry point
 */
<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { PluginManager } from '@/core/plugin-manager'
import { type DocumentFormat, type ExportFormat } from '@/types/plugin'

interface Props {
  modelValue: string
  format?: DocumentFormat
  noteId?: string
  editable?: boolean
  collaborationEnabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  format: DocumentFormat.HTML,
  editable: true,
  collaborationEnabled: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'format-change', format: DocumentFormat): void
  (e: 'ready'): void
  (e: 'error', error: Error): void
}>()

const manager = new PluginManager()
const activePlugin = ref<EditorPlugin | null>(null)
const editorContainer = ref<HTMLElement>()
const toolbarContainer = ref<HTMLElement>()

onMounted(async () => {
  // Register all available plugins
  await registerPlugins()

  // Activate appropriate plugin based on format
  await activatePluginForFormat(props.format, props.modelValue)

  emit('ready')
})

async function registerPlugins() {
  const plugins = [
    new TiptapPlugin(),
    new DocxPlugin(),
    new ExcelPlugin(),
    new MindmapPlugin(),
    new FlowchartPlugin(),
  ]

  for (const plugin of plugins) {
    await plugin.install(getCurrentInstance()?.appContext.app)
    manager.register(plugin)
  }
}

async function activatePluginForFormat(format: DocumentFormat, content: string) {
  const plugins = manager.listPluginsByFormat(format)
  if (plugins.length === 0) {
    emit('error', new Error(`No plugin found for format: ${format}`))
    return
  }

  const plugin = plugins[0]  // Use first available plugin
  await manager.activatePlugin(plugin.id, {
    container: editorContainer.value!,
    content,
    metadata: {},
    toolbarContainer: toolbarContainer.value!,
  })

  activePlugin.value = manager.getActivePlugin()
}

// Handle content changes
manager.on(ManagerEvent.CONTENT_CHANGED, ({ data }) => {
  emit('update:modelValue', data)
})

// Export functionality
async function exportContent(format: ExportFormat) {
  if (!activePlugin.value) return
  const content = await activePlugin.value.getContent(format)

  // Download file
  const blob = new Blob([content], { type: getMimeType(format) })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `document.${getFileExtension(format)}`
  link.click()
  URL.revokeObjectURL(url)
}

defineExpose({
  exportContent,
  getPlugin: () => activePlugin.value,
  switchFormat: async (format: DocumentFormat) => {
    const currentContent = props.modelValue
    await activatePluginForFormat(format, currentContent)
    emit('format-change', format)
  },
})
</script>

<template>
  <div class="unified-editor">
    <div ref="toolbarContainer" class="editor-toolbar" />
    <div ref="editorContainer" class="editor-content" />
  </div>
</template>
```

### 5.2 File Upload Handler

```typescript
/**
 * Unified file upload handler with format detection
 */
class FileUploadHandler {
  private pluginManager: PluginManager
  private mimeTypes: Map<string, DocumentFormat>

  constructor(pluginManager: PluginManager) {
    this.pluginManager = pluginManager
    this.mimeTypes = new Map([
      ['application/msword', DocumentFormat.DOCX],
      ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', DocumentFormat.DOCX],
      ['application/vnd.ms-excel', DocumentFormat.XLSX],
      ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', DocumentFormat.XLSX],
      ['text/html', DocumentFormat.HTML],
      ['text/markdown', DocumentFormat.MARKDOWN],
      ['text/plain', DocumentFormat.TXT],
    ])
  }

  async handleFile(file: File): Promise<{
    format: DocumentFormat
    content: string | ArrayBuffer
    plugin: EditorPlugin
  }> {
    // Detect format from MIME type and extension
    const format = this.detectFormat(file)

    // Find appropriate plugin
    const plugins = this.pluginManager.listPluginsByFormat(format)
    if (plugins.length === 0) {
      throw new Error(`Unsupported file format: ${format}`)
    }

    const plugin = plugins[0]
    const content = await this.readFile(file)

    return { format, content, plugin }
  }

  private detectFormat(file: File): DocumentFormat {
    // Try MIME type first
    const mimeFormat = this.mimeTypes.get(file.type)
    if (mimeFormat) return mimeFormat

    // Fall back to extension
    const ext = file.name.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'docx': return DocumentFormat.DOCX
      case 'xlsx': return DocumentFormat.XLSX
      case 'md': return DocumentFormat.MARKDOWN
      case 'html': return DocumentFormat.HTML
      case 'mm': return DocumentFormat.MM
      case 'mmd': return DocumentFormat.MMD
      default: return DocumentFormat.TXT
    }
  }

  private async readFile(file: File): Promise<string | ArrayBuffer> {
    // For text files, read as text
    if (file.type.startsWith('text/')) {
      return file.text()
    }
    // For binary files, read as array buffer
    return file.arrayBuffer()
  }
}
```

### 5.3 Content Converter

```typescript
/**
 * Convert content between different formats
 */
class ContentConverter {
  private pluginManager: PluginManager

  constructor(pluginManager: PluginManager) {
    this.pluginManager = pluginManager
  }

  async convert(
    content: string,
    from: DocumentFormat,
    to: DocumentFormat
  ): Promise<string> {
    // Find source plugin
    const sourcePlugins = this.pluginManager.listPluginsByFormat(from)
    if (sourcePlugins.length === 0) {
      throw new Error(`No plugin for source format: ${from}`)
    }

    // Find target plugin
    const targetPlugins = this.pluginManager.listPluginsByFormat(to)
    if (targetPlugins.length === 0) {
      throw new Error(`No plugin for target format: ${to}`)
    }

    const sourcePlugin = sourcePlugins[0]
    const targetPlugin = targetPlugins[0]

    // Load content with source plugin
    const loadResult = await sourcePlugin.loadContent(content)
    if (!loadResult.success) {
      throw new Error(`Failed to load content: ${loadResult.error?.message}`)
    }

    // Export in target format
    // This requires plugins to support intermediate format conversion
    // For now, use HTML as intermediate format
    const html = await sourcePlugin.getContent(ExportFormat.HTML)

    // Load into target plugin and export
    await targetPlugin.activate({
      container: document.createElement('div'),
      content: html as string,
      metadata: {},
    })

    return await targetPlugin.getContent(to) as string
  }

  // Quick conversions without full plugin activation
  async quickConvert(content: string, to: DocumentFormat): Promise<string> {
    switch (to) {
      case DocumentFormat.MARKDOWN:
        return this.htmlToMarkdown(content)
      case DocumentFormat.HTML:
        return this.markdownToHtml(content)
      default:
        throw new Error(`Quick conversion not supported for: ${to}`)
    }
  }

  private htmlToMarkdown(html: string): string {
    // Use turndown library
    const turndownService = new TurndownService({
      headingStyle: 'atx',
      codeBlockStyle: 'fenced',
    })
    return turndownService.turndown(html)
  }

  private markdownToHtml(markdown: string): string {
    // Use marked library
    return marked(markdown)
  }
}
```

---

## 6. UI Components

### 6.1 Format Switcher

```typescript
/**
 * Format Switcher Component - Switch between editor types
 */
<script setup lang="ts">
import { ref } from 'vue'
import {
  FileTextOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  NodeIndexOutlined,
  ApiOutlined,
} from '@ant-design/icons-vue'

interface FormatOption {
  value: DocumentFormat
  label: string
  icon: any
  description: string
}

const formats: FormatOption[] = [
  {
    value: DocumentFormat.HTML,
    label: 'Rich Text',
    icon: FileTextOutlined,
    description: 'Standard rich text editor',
  },
  {
    value: DocumentFormat.DOCX,
    label: 'Word Document',
    icon: FileWordOutlined,
    description: 'Import Word documents (read-only)',
  },
  {
    value: DocumentFormat.XLSX,
    label: 'Excel Spreadsheet',
    icon: FileExcelOutlined,
    description: 'Spreadsheets with formulas',
  },
  {
    value: DocumentFormat.MM,
    label: 'Mindmap',
    icon: NodeIndexOutlined,
    description: 'Visual mind mapping',
  },
  {
    value: DocumentFormat.MMD,
    label: 'Flowchart',
    icon: ApiOutlined,
    description: 'Mermaid diagrams',
  },
]

const selectedFormat = ref<DocumentFormat>(DocumentFormat.HTML)

function handleFormatChange(format: DocumentFormat) {
  emit('change', format)
}
</script>

<template>
  <div class="format-switcher">
    <a-dropdown>
      <a-button>
        <component :is="formats.find(f => f.value === selectedFormat)?.icon" />
        {{ formats.find(f => f.value === selectedFormat)?.label }}
        <DownOutlined />
      </a-button>
      <template #overlay>
        <a-menu @click="({ key }) => handleFormatChange(key as DocumentFormat)">
          <a-menu-item
            v-for="format in formats"
            :key="format.value"
            :disabled="!isFormatSupported(format.value)"
          >
            <component :is="format.icon" />
            <span>{{ format.label }}</span>
            <small>{{ format.description }}</small>
          </a-menu-item>
        </a-menu>
      </template>
    </a-dropdown>
  </div>
</template>
```

### 6.2 Export Dialog

```typescript
/**
 * Export Dialog Component
 */
<script setup lang="ts">
import { ref, computed } from 'vue'
import { ExportFormat, type EditorPlugin } from '@/types/plugin'

interface Props {
  plugin: EditorPlugin | null
  loading?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'export', format: ExportFormat): void
}>()

const exporting = ref<ExportFormat | null>(null)

const availableFormats = computed(() => {
  return props.plugin?.capabilities.exportFormats || []
})

async function handleExport(format: ExportFormat) {
  exporting.value = format
  try {
    await emit('export', format)
  } finally {
    exporting.value = null
  }
}
</script>

<template>
  <a-modal
    v-model:open="visible"
    title="Export Document"
    :footer="null"
  >
    <div class="export-options">
      <a-button
        v-for="format in availableFormats"
        :key="format"
        :loading="exporting === format"
        @click="handleExport(format)"
        block
        size="large"
      >
        <FileTextOutlined v-if="format === ExportFormat.PDF" />
        <FileTextOutlined v-else-if="format === ExportFormat.HTML" />
        <FileMarkdownOutlined v-else-if="format === ExportFormat.MARKDOWN" />
        <FileImageOutlined v-else-if="format === ExportFormat.PNG" />
        {{ formatLabel(format) }}
      </a-button>
    </div>
  </a-modal>
</template>
```

---

## 7. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Create plugin interface definitions
- [ ] Implement PluginManager
- [ ] Implement EventBus
- [ ] Implement StateManager
- [ ] Create base plugin class
- [ ] Setup plugin loading system

### Phase 2: Rich Text Plugin (Week 2-3)
- [ ] Migrate existing TiptapEditor to plugin
- [ ] Implement plugin lifecycle
- [ ] Add toolbar integration
- [ ] Add collaboration support
- [ ] Testing

### Phase 3: Document Import Plugins (Week 3-4)
- [ ] DOCX plugin (mammoth.js)
- [ ] XLSX plugin (SheetJS + HyperFormula)
- [ ] File upload handler
- [ ] Format detection
- [ ] Testing

### Phase 4: Diagram Plugins (Week 4-5)
- [ ] Mindmap plugin (Y.js)
- [ ] Flowchart plugin (Mermaid.js)
- [ ] Visual editor components
- [ ] Export handlers
- [ ] Testing

### Phase 5: Integration & Polish (Week 5-6)
- [ ] Unified editor component
- [ ] Format switcher
- [ ] Export dialog
- [ ] Content converter
- [ ] Documentation
- [ ] End-to-end testing

---

## 8. Technical Specifications

### 8.1 Dependencies

```json
{
  "dependencies": {
    // Core
    "@tiptap/vue-3": "^2.1.0",
    "@tiptap/starter-kit": "^2.1.0",
    "@tiptap/extension-collaboration": "^2.1.0",
    "@tiptap/extension-collaboration-cursor": "^2.1.0",

    // Y.js for real-time collaboration
    "yjs": "^13.6.0",
    "y-websocket": "^1.5.0",

    // Document handling
    "mammoth": "^1.6.0",
    "xlsx": "^0.18.5",
    "turndown": "^7.1.0",
    "marked": "^9.1.0",

    // Diagrams
    "mermaid": "^10.6.0",
    "d3": "^7.8.0",

    // Spreadsheets
    "handsontable": "^14.0.0",
    "hyperformula": "^2.4.0",

    // Utilities
    "eventemitter3": "^5.0.0"
  }
}
```

### 8.2 File Structure

```
src/
├── core/
│   ├── plugin-manager.ts      # Plugin manager
│   ├── event-bus.ts            # Event system
│   ├── state-manager.ts        # State management
│   └── types.ts                # Core type definitions
├── plugins/
│   ├── base/
│   │   └── base-plugin.ts      # Base plugin class
│   ├── richtext/
│   │   ├── tiptap-plugin.ts    # Tiptap implementation
│   │   ├── extensions/         # Custom extensions
│   │   └── components/         # UI components
│   ├── word/
│   │   └── docx-plugin.ts      # DOCX implementation
│   ├── excel/
│   │   └── excel-plugin.ts     # XLSX implementation
│   ├── mindmap/
│   │   ├── mindmap-plugin.ts   # Mindmap implementation
│   │   ├── renderer.ts         # D3-based renderer
│   │   └── components/         # UI components
│   └── flowchart/
│       ├── flowchart-plugin.ts # Mermaid implementation
│       └── components/         # UI components
├── components/
│   ├── UnifiedEditor.vue       # Main editor component
│   ├── FormatSwitcher.vue      # Format selection
│   ├── ExportDialog.vue        # Export options
│   └── PluginToolbar.vue       # Dynamic toolbar
└── utils/
    ├── file-handler.ts         # File upload handling
    ├── content-converter.ts    # Format conversion
    └── format-detector.ts      # Format detection
```

### 8.3 Performance Considerations

1. **Lazy Loading**: Plugins are loaded only when needed
2. **Code Splitting**: Each plugin is a separate chunk
3. **Memory Management**: Proper cleanup on plugin deactivation
4. **Caching**: Cached parsed content for fast switching

### 8.4 Security Considerations

1. **Content Sanitization**: All user input is sanitized
2. **Sandboxed Execution**: Plugin code runs in restricted context
3. **CORS**: Proper CORS handling for cross-origin resources
4. **File Size Limits**: Configurable limits for uploaded files

---

## 9. Appendix

### 9.1 Event Reference

| Event | Data | Description |
|-------|------|-------------|
| `content:change` | `{ html: string }` | Content changed |
| `selection:change` | `{ from: number, to: number }` | Selection changed |
| `editor:ready` | - | Editor initialized |
| `collab:join` | `{ userId: string }` | User joined |
| `collab:cursor` | `{ userId: string, position: object }` | Cursor moved |

### 9.2 Format Compatibility Matrix

| Plugin | Edit | Collab | Export | Import |
|--------|------|-------|--------|--------|
| Rich Text | ✓ | ✓ | PDF, HTML, MD | HTML, MD, TXT |
| Word | ✗ | ✗ | PDF, DOCX | DOCX |
| Excel | ✓ | ✓ | XLSX, CSV | XLSX, CSV |
| Mindmap | ✓ | ✓ | PNG, SVG, MD | MM, MD |
| Flowchart | ✓ | ✗ | PNG, SVG | MMD |

### 9.3 Keyboard Shortcuts

| Shortcut | Action | Plugin |
|----------|--------|--------|
| Ctrl+B | Bold | Rich Text |
| Ctrl+I | Italic | Rich Text |
| Ctrl+K | Link | Rich Text |
| Ctrl+/ | Command Menu | Rich Text |
| Tab | Indent | Mindmap |
| Shift+Tab | Outdent | Mindmap |
| Ctrl+D | Delete Row | Excel |
| Ctrl+Shift+D | Delete Column | Excel |

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-13 | ux-designer-2 | Initial design document |

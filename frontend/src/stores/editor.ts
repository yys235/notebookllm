// @ts-nocheck
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { DocumentContent, Block, EditorType, EditorState } from '@/plugins/core/types'

// 历史记录最大保存数量
const MAX_HISTORY_SIZE = 50

/**
 * ContentSerializer - 内容格式转换工具
 * 用于 JSON 和 HTML 格式之间的转换
 */
class ContentSerializer {
  /**
   * 从 JSON 字符串解析文档内容
   */
  static fromJSON(jsonString: string): DocumentContent {
    try {
      const parsed = JSON.parse(jsonString)
      // 验证基本结构
      if (!parsed.type || parsed.type !== 'doc' || !Array.isArray(parsed.blocks)) {
        throw new Error('Invalid document structure')
      }
      return parsed as DocumentContent
    } catch (error) {
      console.error('Failed to parse JSON content:', error)
      return createEmptyDocument()
    }
  }

  /**
   * 将文档内容序列化为 JSON 字符串
   */
  static toJSON(content: DocumentContent): string {
    return JSON.stringify(content)
  }

  /**
   * 从 HTML 字符串解析文档内容
   */
  static fromHTML(htmlString: string): DocumentContent {
    const doc = createEmptyDocument()
    const blocks: Block[] = []

    // 简单的 HTML 解析逻辑
    // 将 HTML 按段落分割
    const paragraphRegex = /<p[^>]*>(.*?)<\/p>/gi
    const headingRegex = /<h([1-6])[^>]*>(.*?)<\/h\1>/gi
    const listRegex = /<li[^>]*>(.*?)<\/li>/gi

    let match

    // 解析标题
    while ((match = headingRegex.exec(htmlString)) !== null) {
      const level = match[1]
      const content = stripHtmlTags(match[2])
      if (content.trim()) {
        blocks.push({
          id: generateBlockId(),
          type: `heading${level}` as Block['type'],
          content: content.trim()
        })
      }
    }

    // 解析段落
    while ((match = paragraphRegex.exec(htmlString)) !== null) {
      const content = stripHtmlTags(match[1])
      if (content.trim()) {
        blocks.push({
          id: generateBlockId(),
          type: 'paragraph',
          content: content.trim()
        })
      }
    }

    // 解析列表项
    while ((match = listRegex.exec(htmlString)) !== null) {
      const content = stripHtmlTags(match[1])
      if (content.trim()) {
        blocks.push({
          id: generateBlockId(),
          type: 'bullet-list',
          content: content.trim()
        })
      }
    }

    // 如果没有解析到任何块，将整个 HTML 作为纯文本处理
    if (blocks.length === 0) {
      const plainText = stripHtmlTags(htmlString)
      if (plainText.trim()) {
        // 按换行符分割
        const lines = plainText.split(/\n+/)
        lines.forEach(line => {
          if (line.trim()) {
            blocks.push({
              id: generateBlockId(),
              type: 'paragraph',
              content: line.trim()
            })
          }
        })
      }
    }

    if (blocks.length > 0) {
      doc.blocks = blocks
      doc.blockOrder = blocks.map(b => b.id)
    }

    return doc
  }

  /**
   * 将文档内容转换为 HTML 字符串
   */
  static toHTML(content: DocumentContent): string {
    const htmlParts: string[] = []

    for (const block of content.blocks) {
      switch (block.type) {
        case 'heading1':
          htmlParts.push(`<h1>${escapeHtml(block.content || '')}</h1>`)
          break
        case 'heading2':
          htmlParts.push(`<h2>${escapeHtml(block.content || '')}</h2>`)
          break
        case 'heading3':
          htmlParts.push(`<h3>${escapeHtml(block.content || '')}</h3>`)
          break
        case 'heading4':
          htmlParts.push(`<h4>${escapeHtml(block.content || '')}</h4>`)
          break
        case 'heading5':
          htmlParts.push(`<h5>${escapeHtml(block.content || '')}</h5>`)
          break
        case 'heading6':
          htmlParts.push(`<h6>${escapeHtml(block.content || '')}</h6>`)
          break
        case 'quote':
          htmlParts.push(`<blockquote>${escapeHtml(block.content || '')}</blockquote>`)
          break
        case 'code-block':
          htmlParts.push(`<pre><code>${escapeHtml(block.content || '')}</code></pre>`)
          break
        case 'bullet-list':
        case 'ordered-list':
          htmlParts.push(`<li>${escapeHtml(block.content || '')}</li>`)
          break
        case 'divider':
          htmlParts.push('<hr/>')
          break
        case 'image':
          const src = block.attrs?.src || ''
          const alt = block.attrs?.alt || ''
          htmlParts.push(`<img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}"/>`)
          break
        default:
          htmlParts.push(`<p>${escapeHtml(block.content || '')}</p>`)
      }
    }

    return htmlParts.join('\n')
  }
}

// 辅助函数：生成唯一块 ID
function generateBlockId(): string {
  return `block-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

// 辅助函数：生成唯一文档 ID
function generateDocumentId(): string {
  return `doc-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

// 辅助函数：移除 HTML 标签
function stripHtmlTags(html: string): string {
  return html.replace(/<[^>]*>/g, '')
}

// 辅助函数：HTML 转义
function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, char => map[char])
}

// 辅助函数：深拷贝文档内容
function cloneDocumentContent(content: DocumentContent): DocumentContent {
  return JSON.parse(JSON.stringify(content))
}

// 辅助函数：创建空文档
function createEmptyDocument(): DocumentContent {
  const blockId = generateBlockId()
  return {
    version: '1.0',
    type: 'doc',
    id: generateDocumentId(),
    blocks: [
      {
        id: blockId,
        type: 'paragraph',
        content: '',
        elements: []
      }
    ],
    blockOrder: [blockId],
    metadata: {
      title: 'Untitled',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
  }
}

/**
 * Editor Store - Manages editor state and content
 * Provides centralized state management for all editor types
 */
export const useEditorStore = defineStore('editor', () => {
  // State
  const isReady = ref(false)
  const isEditable = ref(true)
  const activePlugin = ref<EditorType | null>(null)
  const content = ref<DocumentContent | null>(null)
  const documentId = ref<string | null>(null)

  // 历史记录（用于撤销/重做）
  const history = ref<DocumentContent[]>([])
  const historyIndex = ref(-1)

  // Selection state
  const selection = ref({
    startBlock: null as string | null,
    endBlock: null as string | null,
    startOffset: 0,
    endOffset: 0,
  })

  // Computed
  const canUndo = computed(() => historyIndex.value > 0)
  const canRedo = computed(() => historyIndex.value < history.value.length - 1)
  const currentBlocks = computed(() => content.value?.blocks ?? [])

  const editorState = computed<EditorState>(() => ({
    isReady: isReady.value,
    isEditable: isEditable.value,
    activePlugin: activePlugin.value,
    content: content.value,
    selection: selection.value,
  }))

  // Actions

  /**
   * 初始化文档
   * @param docContent 文档内容，可以是 DocumentContent 对象、JSON 字符串或 HTML 字符串
   * @param id 文档 ID（可选）
   */
  function initDocument(docContent: DocumentContent | string, id?: string) {
    let parsedContent: DocumentContent

    if (typeof docContent === 'string') {
      // 尝试判断是 JSON 还是 HTML
      const trimmed = docContent.trim()
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        // 尝试解析为 JSON
        try {
          parsedContent = ContentSerializer.fromJSON(docContent)
        } catch {
          // JSON 解析失败，尝试作为 HTML 解析
          parsedContent = ContentSerializer.fromHTML(docContent)
        }
      } else if (trimmed.startsWith('<')) {
        // 作为 HTML 解析
        parsedContent = ContentSerializer.fromHTML(docContent)
      } else {
        // 作为纯文本处理
        parsedContent = ContentSerializer.fromHTML(`<p>${docContent}</p>`)
      }
    } else {
      parsedContent = docContent
    }

    content.value = parsedContent
    documentId.value = id || parsedContent.id
    isReady.value = true

    // 初始化历史记录
    history.value = [cloneDocumentContent(parsedContent)]
    historyIndex.value = 0
  }

  /**
   * 更新文档内容
   * @param newContent 新的文档内容
   * @param addToHistory 是否添加到历史记录（默认为 true）
   */
  function updateContent(newContent: DocumentContent, addToHistory = true) {
    content.value = cloneDocumentContent(newContent)

    // 更新元数据中的修改时间
    if (content.value.metadata) {
      content.value.metadata.updatedAt = new Date().toISOString()
    }

    if (addToHistory) {
      // 如果当前不在历史记录末尾，删除当前位置之后的所有记录
      if (historyIndex.value < history.value.length - 1) {
        history.value = history.value.slice(0, historyIndex.value + 1)
      }

      // 添加新记录
      history.value.push(cloneDocumentContent(newContent))

      // 限制历史记录大小
      if (history.value.length > MAX_HISTORY_SIZE) {
        history.value = history.value.slice(-MAX_HISTORY_SIZE)
      }

      // 更新索引
      historyIndex.value = history.value.length - 1
    }
  }

  /**
   * Set editor editable state
   */
  function setEditable(editable: boolean) {
    isEditable.value = editable
  }

  /**
   * Set the active editor plugin type
   */
  function setActivePlugin(type: EditorType) {
    activePlugin.value = type
  }

  /**
   * 撤销操作
   */
  function undo() {
    if (!canUndo.value) return

    historyIndex.value--
    content.value = cloneDocumentContent(history.value[historyIndex.value])
  }

  /**
   * 重做操作
   */
  function redo() {
    if (!canRedo.value) return

    historyIndex.value++
    content.value = cloneDocumentContent(history.value[historyIndex.value])
  }

  /**
   * 根据 ID 获取块
   * @param id 块 ID
   * @returns 块对象或 undefined
   */
  function getBlockById(id: string): Block | undefined {
    return currentBlocks.value.find(block => block.id === id)
  }

  /**
   * 更新指定块的内容
   * @param id 块 ID
   * @param updates 要更新的字段
   */
  function updateBlock(id: string, updates: Partial<Block>) {
    if (!content.value) return

    const blockIndex = content.value.blocks.findIndex(block => block.id === id)
    if (blockIndex === -1) return

    // 创建新的文档内容
    const newContent = cloneDocumentContent(content.value)
    newContent.blocks[blockIndex] = {
      ...newContent.blocks[blockIndex],
      ...updates
    }

    updateContent(newContent)
  }

  /**
   * 添加新块
   * @param block 要添加的块
   * @param afterId 在此块 ID 之后添加（可选，默认添加到末尾）
   */
  function addBlock(block: Block, afterId?: string) {
    if (!content.value) return

    const newContent = cloneDocumentContent(content.value)

    if (afterId) {
      const afterIndex = newContent.blocks.findIndex(b => b.id === afterId)
      if (afterIndex !== -1) {
        newContent.blocks.splice(afterIndex + 1, 0, block)
        // 更新 blockOrder
        const orderIndex = newContent.blockOrder.indexOf(afterId)
        if (orderIndex !== -1) {
          newContent.blockOrder.splice(orderIndex + 1, 0, block.id)
        }
      } else {
        newContent.blocks.push(block)
        newContent.blockOrder.push(block.id)
      }
    } else {
      newContent.blocks.push(block)
      newContent.blockOrder.push(block.id)
    }

    updateContent(newContent)
  }

  /**
   * 删除指定块
   * @param id 块 ID
   */
  function removeBlock(id: string) {
    if (!content.value) return

    // 至少保留一个块
    if (content.value.blocks.length <= 1) {
      console.warn('Cannot remove the last block')
      return
    }

    const newContent = cloneDocumentContent(content.value)
    newContent.blocks = newContent.blocks.filter(block => block.id !== id)
    newContent.blockOrder = newContent.blockOrder.filter(blockId => blockId !== id)

    updateContent(newContent)
  }

  /**
   * 移动块到新位置
   * @param id 块 ID
   * @param newIndex 新的索引位置
   */
  function moveBlock(id: string, newIndex: number) {
    if (!content.value) return

    const currentIndex = content.value.blocks.findIndex(block => block.id === id)
    if (currentIndex === -1) return

    // 确保新索引在有效范围内
    const validIndex = Math.max(0, Math.min(newIndex, content.value.blocks.length - 1))
    if (currentIndex === validIndex) return

    const newContent = cloneDocumentContent(content.value)

    // 移动块
    const [block] = newContent.blocks.splice(currentIndex, 1)
    newContent.blocks.splice(validIndex, 0, block)

    // 更新 blockOrder
    const orderIndex = newContent.blockOrder.indexOf(id)
    if (orderIndex !== -1) {
      newContent.blockOrder.splice(orderIndex, 1)
      newContent.blockOrder.splice(validIndex, 0, id)
    }

    updateContent(newContent)
  }

  /**
   * 清除历史记录
   */
  function clearHistory() {
    if (content.value) {
      history.value = [cloneDocumentContent(content.value)]
      historyIndex.value = 0
    } else {
      history.value = []
      historyIndex.value = -1
    }
  }

  /**
   * Update selection state
   */
  function updateSelection(newSelection: Partial<typeof selection.value>) {
    selection.value = {
      ...selection.value,
      ...newSelection,
    }
  }

  /**
   * 获取当前内容的 JSON 字符串
   */
  function toJSON(): string {
    if (!content.value) return ''
    return ContentSerializer.toJSON(content.value)
  }

  /**
   * 获取当前内容的 HTML 字符串
   */
  function toHTML(): string {
    if (!content.value) return ''
    return ContentSerializer.toHTML(content.value)
  }

  /**
   * Reset editor state
   */
  function reset() {
    isReady.value = false
    isEditable.value = true
    activePlugin.value = null
    content.value = null
    documentId.value = null
    history.value = []
    historyIndex.value = -1
    selection.value = {
      startBlock: null,
      endBlock: null,
      startOffset: 0,
      endOffset: 0,
    }
  }

  /**
   * Initialize editor with default state
   */
  function initialize() {
    if (!content.value) {
      const emptyDoc = createEmptyDocument()
      initDocument(emptyDoc)
    }
    isReady.value = true
  }

  return {
    // State
    isReady,
    isEditable,
    activePlugin,
    content,
    documentId,
    history,
    historyIndex,
    selection,
    // Computed
    canUndo,
    canRedo,
    currentBlocks,
    editorState,
    // Actions
    initDocument,
    updateContent,
    setEditable,
    setActivePlugin,
    initialize,
    undo,
    redo,
    getBlockById,
    updateBlock,
    addBlock,
    removeBlock,
    moveBlock,
    clearHistory,
    updateSelection,
    // Utility
    toJSON,
    toHTML,
    reset,
  }
})

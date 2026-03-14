/**
 * 飞书文档 - Pinia 状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { BlockData, DocumentData, BlockType } from '../types'

// 生成唯一 ID
function generateId(): string {
  return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 9)}`
}

// 创建空文档
function createEmptyDocument(): DocumentData {
  const textBlockId = generateId()
  return {
    id: generateId(),
    blocks: {
      [textBlockId]: {
        id: textBlockId,
        type: 'text',
        content: '',
      },
    },
    rootBlockIds: [textBlockId],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export const useDocumentStore = defineStore('feishu-docs', () => {
  // ========== State ==========

  const document = ref<DocumentData | null>(null)
  const focusedBlockId = ref<string | null>(null)
  const isEditable = ref(true)

  // 历史记录
  const history = ref<{
    past: DocumentData[]
    future: DocumentData[]
  }>({
    past: [],
    future: [],
  })

  // 斜杠菜单状态
  const slashMenu = ref({
    visible: false,
    query: '',
    position: { x: 0, y: 0 },
  })

  // ========== Getters ==========

  const rootBlocks = computed(() => {
    if (!document.value) return []
    return document.value.rootBlockIds
      .map(id => document.value!.blocks[id])
      .filter((block): block is BlockData => !!block)
  })

  const focusedBlock = computed(() => {
    if (!document.value || !focusedBlockId.value) return null
    return document.value.blocks[focusedBlockId.value] || null
  })

  const canUndo = computed(() => history.value.past.length > 0)
  const canRedo = computed(() => history.value.future.length > 0)

  // ========== Actions ==========

  function initDocument(doc?: DocumentData) {
    if (doc) {
      document.value = doc
    } else {
      document.value = createEmptyDocument()
    }
    history.value = { past: [], future: [] }
    focusedBlockId.value = null
  }

  function $reset() {
    document.value = null
    focusedBlockId.value = null
    history.value = { past: [], future: [] }
    slashMenu.value = { visible: false, query: '', position: { x: 0, y: 0 } }
  }

  function saveSnapshot() {
    if (!document.value) return
    history.value.past.push(JSON.parse(JSON.stringify(document.value)))
    history.value.future = []
    if (history.value.past.length > 50) {
      history.value.past.shift()
    }
  }

  function undo() {
    if (!canUndo.value || !document.value) return
    history.value.future.push(JSON.parse(JSON.stringify(document.value)))
    document.value = history.value.past.pop()!
    document.value.updatedAt = new Date().toISOString()
  }

  function redo() {
    if (!canRedo.value || !document.value) return
    history.value.past.push(JSON.parse(JSON.stringify(document.value)))
    document.value = history.value.future.pop()!
    document.value.updatedAt = new Date().toISOString()
  }

  function getBlock(blockId: string): BlockData | null {
    if (!document.value) return null
    return document.value.blocks[blockId] || null
  }

  function updateBlock(blockId: string, updates: Partial<BlockData>) {
    if (!document.value) return
    const block = document.value.blocks[blockId]
    if (!block) return
    document.value.blocks[blockId] = { ...block, ...updates }
    document.value.updatedAt = new Date().toISOString()
  }

  function insertBlock(
    block: Omit<BlockData, 'id'>,
    options?: {
      afterId?: string
      beforeId?: string
      parentId?: string
    }
  ): string {
    if (!document.value) return ''

    saveSnapshot()

    const newBlockId = generateId()
    const newBlock: BlockData = {
      id: newBlockId,
      ...block,
    }

    document.value.blocks[newBlockId] = newBlock

    if (options?.parentId) {
      const parent = document.value.blocks[options.parentId]
      if (parent) {
        if (!parent.children) parent.children = []
        if (options?.afterId) {
          const idx = parent.children.indexOf(options.afterId)
          parent.children.splice(idx + 1, 0, newBlockId)
        } else if (options?.beforeId) {
          const idx = parent.children.indexOf(options.beforeId)
          parent.children.splice(idx, 0, newBlockId)
        } else {
          parent.children.push(newBlockId)
        }
        newBlock.parentId = options.parentId
      }
    } else {
      if (options?.afterId) {
        const idx = document.value.rootBlockIds.indexOf(options.afterId)
        if (idx >= 0) {
          document.value.rootBlockIds.splice(idx + 1, 0, newBlockId)
        } else {
          document.value.rootBlockIds.push(newBlockId)
        }
      } else if (options?.beforeId) {
        const idx = document.value.rootBlockIds.indexOf(options.beforeId)
        if (idx >= 0) {
          document.value.rootBlockIds.splice(idx, 0, newBlockId)
        } else {
          document.value.rootBlockIds.unshift(newBlockId)
        }
      } else {
        document.value.rootBlockIds.push(newBlockId)
      }
    }

    document.value.updatedAt = new Date().toISOString()
    return newBlockId
  }

  function deleteBlock(blockId: string) {
    if (!document.value) return
    const block = document.value.blocks[blockId]
    if (!block) return

    saveSnapshot()

    // 递归删除子块
    if (block.children) {
      [...block.children].forEach(childId => deleteBlock(childId))
    }

    // 从父块中移除
    if (block.parentId) {
      const parent = document.value.blocks[block.parentId]
      if (parent?.children) {
        parent.children = parent.children.filter(id => id !== blockId)
      }
    } else {
      document.value.rootBlockIds = document.value.rootBlockIds.filter(id => id !== blockId)
    }

    delete document.value.blocks[blockId]
    document.value.updatedAt = new Date().toISOString()

    if (focusedBlockId.value === blockId) {
      focusedBlockId.value = null
    }
  }

  function moveBlock(
    blockId: string,
    options: {
      afterId?: string
      beforeId?: string
      parentId?: string
    }
  ) {
    if (!document.value) return
    const block = document.value.blocks[blockId]
    if (!block) return

    // 不能移动到自己
    if (blockId === options.afterId || blockId === options.beforeId || blockId === options.parentId) return

    saveSnapshot()

    // 保存旧的父块 ID
    const oldParentId = block.parentId

    // 计算新位置（在移除之前计算索引）
    let insertIndex = -1
    let targetArray: string[] | null = null

    if (options.parentId) {
      // 移动到指定父块下
      const newParent = document.value.blocks[options.parentId]
      if (newParent) {
        if (!newParent.children) newParent.children = []
        targetArray = newParent.children
        if (options.afterId) {
          insertIndex = targetArray.indexOf(options.afterId) + 1
        } else if (options.beforeId) {
          insertIndex = targetArray.indexOf(options.beforeId)
        } else {
          insertIndex = targetArray.length
        }
      }
    } else {
      // 移动到根级别
      targetArray = document.value.rootBlockIds
      if (options.afterId) {
        insertIndex = targetArray.indexOf(options.afterId) + 1
      } else if (options.beforeId) {
        insertIndex = targetArray.indexOf(options.beforeId)
      } else {
        insertIndex = targetArray.length
      }
    }

    // 从原位置移除
    if (oldParentId) {
      const oldParent = document.value.blocks[oldParentId]
      if (oldParent?.children) {
        const oldIndex = oldParent.children.indexOf(blockId)
        if (oldIndex >= 0) {
          oldParent.children.splice(oldIndex, 1)
        }
      }
    } else {
      const oldIndex = document.value.rootBlockIds.indexOf(blockId)
      if (oldIndex >= 0) {
        document.value.rootBlockIds.splice(oldIndex, 1)
        // 如果目标数组是 rootBlockIds 且目标在移除位置之后，需要调整索引
        if (targetArray === document.value.rootBlockIds && insertIndex > oldIndex) {
          insertIndex--
        }
      }
    }

    // 添加到新位置
    if (targetArray && insertIndex >= 0) {
      targetArray.splice(insertIndex, 0, blockId)
    }

    // 更新父块引用
    if (options.parentId) {
      block.parentId = options.parentId
    } else {
      block.parentId = undefined
    }

    document.value.updatedAt = new Date().toISOString()
  }

  function setFocusedBlock(blockId: string | null) {
    focusedBlockId.value = blockId
  }

  function showSlashMenu(position?: { x: number; y: number }) {
    slashMenu.value.visible = true
    slashMenu.value.query = ''
    if (position) {
      slashMenu.value.position = position
    }
  }

  function hideSlashMenu() {
    slashMenu.value.visible = false
    slashMenu.value.query = ''
  }

  function updateSlashMenuQuery(query: string) {
    slashMenu.value.query = query
  }

  function getPreviousBlock(blockId: string): BlockData | null {
    if (!document.value) return null
    const block = document.value.blocks[blockId]
    if (!block) return null

    if (block.parentId) {
      const parent = document.value.blocks[block.parentId]
      if (!parent?.children) return null
      const idx = parent.children.indexOf(blockId)
      if (idx > 0) {
        const prevId = parent.children[idx - 1]
        return prevId ? document.value.blocks[prevId] || null : null
      }
    } else {
      const idx = document.value.rootBlockIds.indexOf(blockId)
      if (idx > 0) {
        const prevId = document.value.rootBlockIds[idx - 1]
        return prevId ? document.value.blocks[prevId] || null : null
      }
    }
    return null
  }

  function getNextBlock(blockId: string): BlockData | null {
    if (!document.value) return null
    const block = document.value.blocks[blockId]
    if (!block) return null

    if (block.parentId) {
      const parent = document.value.blocks[block.parentId]
      if (!parent?.children) return null
      const idx = parent.children.indexOf(blockId)
      if (idx < parent.children.length - 1) {
        const nextId = parent.children[idx + 1]
        return nextId ? document.value.blocks[nextId] || null : null
      }
    } else {
      const idx = document.value.rootBlockIds.indexOf(blockId)
      if (idx < document.value.rootBlockIds.length - 1) {
        const nextId = document.value.rootBlockIds[idx + 1]
        return nextId ? document.value.blocks[nextId] || null : null
      }
    }
    return null
  }

  function convertBlockType(blockId: string, newType: BlockType) {
    if (!document.value) return
    const block = document.value.blocks[blockId]
    if (!block) return

    saveSnapshot()
    block.type = newType
    document.value.updatedAt = new Date().toISOString()
  }

  function toJSON(): DocumentData | null {
    return document.value ? JSON.parse(JSON.stringify(document.value)) : null
  }

  function fromJSON(data: DocumentData) {
    document.value = data
    history.value = { past: [], future: [] }
  }

  function toHTML(): string {
    if (!document.value) return ''

    const renderBlock = (blockId: string): string => {
      const block = document.value!.blocks[blockId]
      if (!block) return ''

      let content = typeof block.content === 'string' ? block.content : ''

      let childrenHtml = ''
      if (block.children?.length) {
        childrenHtml = block.children.map(renderBlock).join('')
      }

      switch (block.type) {
        case 'h1': return `<h1>${content}</h1>`
        case 'h2': return `<h2>${content}</h2>`
        case 'h3': return `<h3>${content}</h3>`
        case 'h4': return `<h4>${content}</h4>`
        case 'h5': return `<h5>${content}</h5>`
        case 'h6': return `<h6>${content}</h6>`
        case 'quote': return `<blockquote>${content}${childrenHtml}</blockquote>`
        case 'code': return `<pre><code>${content}</code></pre>`
        case 'bulletList': return `<ul>${childrenHtml}</ul>`
        case 'orderedList': return `<ol>${childrenHtml}</ol>`
        case 'listItem': return `<li>${content}${childrenHtml}</li>`
        case 'taskItem': return `<div class="task-item"><input type="checkbox" ${block.attrs?.checked ? 'checked' : ''} /><span>${content}</span></div>`
        case 'image': return `<img src="${block.attrs?.src || ''}" alt="${block.attrs?.alt || ''}" />`
        case 'divider': return '<hr />'
        case 'callout': return `<div class="callout callout-${block.attrs?.type || 'info'}">${content}</div>`
        default: return `<p>${content}${childrenHtml}</p>`
      }
    }

    return document.value.rootBlockIds.map(renderBlock).join('')
  }

  function fromHTML(html: string) {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')

    const newDoc = createEmptyDocument()
    newDoc.rootBlockIds = []
    newDoc.blocks = {}

    const typeMap: Record<string, BlockType> = {
      'h1': 'h1', 'h2': 'h2', 'h3': 'h3', 'h4': 'h4', 'h5': 'h5', 'h6': 'h6',
      'p': 'text', 'div': 'text',
      'blockquote': 'quote',
      'pre': 'code',
      'ul': 'bulletList',
      'ol': 'orderedList',
      'li': 'listItem',
      'hr': 'divider',
      'img': 'image',
    }

    doc.body.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent?.trim()
        if (text) {
          const blockId = generateId()
          newDoc.blocks[blockId] = { id: blockId, type: 'text', content: text }
          newDoc.rootBlockIds.push(blockId)
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const element = node as Element
        const tagName = element.tagName.toLowerCase()
        const blockType = typeMap[tagName] || 'text'
        const blockId = generateId()

        const block: BlockData = {
          id: blockId,
          type: blockType,
          content: element.textContent || '',
        }

        if (blockType === 'image') {
          block.attrs = {
            src: element.getAttribute('src'),
            alt: element.getAttribute('alt'),
          }
        }

        newDoc.blocks[blockId] = block
        newDoc.rootBlockIds.push(blockId)
      }
    })

    if (newDoc.rootBlockIds.length === 0) {
      const emptyBlockId = generateId()
      newDoc.blocks[emptyBlockId] = { id: emptyBlockId, type: 'text', content: '' }
      newDoc.rootBlockIds.push(emptyBlockId)
    }

    document.value = newDoc
  }

  return {
    // State
    document,
    focusedBlockId,
    isEditable,
    history,
    slashMenu,

    // Getters
    rootBlocks,
    focusedBlock,
    canUndo,
    canRedo,

    // Actions
    initDocument,
    $reset,
    saveSnapshot,
    undo,
    redo,
    getBlock,
    updateBlock,
    insertBlock,
    deleteBlock,
    moveBlock,
    setFocusedBlock,
    showSlashMenu,
    hideSlashMenu,
    updateSlashMenuQuery,
    getPreviousBlock,
    getNextBlock,
    convertBlockType,
    toJSON,
    fromJSON,
    toHTML,
    fromHTML,
  }
})

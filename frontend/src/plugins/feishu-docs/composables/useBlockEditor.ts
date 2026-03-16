/**
 * 块编辑器核心 composable
 * 处理键盘事件、选择、剪贴板等
 */
import { ref, computed, nextTick } from 'vue'
import { useDocumentStore } from '../stores/document'
import type { BlockType } from '../types'

export function useBlockEditor() {
  const store = useDocumentStore()

  // 当前编辑的内容
  const editingContent = ref<Record<string, string>>({})

  // 获取块的编辑内容
  function getBlockContent(blockId: string): string {
    if (editingContent.value[blockId] !== undefined) {
      return editingContent.value[blockId]
    }
    const block = store.getBlock(blockId)
    if (!block) return ''
    return typeof block.content === 'string' ? block.content : ''
  }

  // 更新块的编辑内容
  function setBlockContent(blockId: string, content: string) {
    editingContent.value[blockId] = content
  }

  // 同步内容到 store
  function syncBlockContent(blockId: string) {
    const content = editingContent.value[blockId]
    if (content !== undefined) {
      store.updateBlock(blockId, { content })
    }
  }

  // 处理块聚焦
  function handleBlockFocus(blockId: string) {
    store.setFocusedBlock(blockId)
    store.hideSlashMenu()
  }

  // 处理块失焦
  function handleBlockBlur(blockId: string) {
    syncBlockContent(blockId)
    if (store.focusedBlockId === blockId) {
      store.setFocusedBlock(null)
    }
  }

  // 处理输入
  function handleInput(blockId: string, event: Event) {
    const target = event.target as HTMLElement
    const content = target.innerText
    setBlockContent(blockId, content)

    // 检测斜杠命令 - 只在块开头或空格后触发
    if (content.endsWith('/')) {
      // 获取 / 之前的内容
      const beforeSlash = content.slice(0, -1)

      // 只有当 / 前面是空的或只有空格时才触发命令菜单
      // 这样可以避免 URL (https://) 或文件路径 (path/to/) 中的 / 触发菜单
      if (beforeSlash === '' || /^\s*$/.test(beforeSlash)) {
        const selection = window.getSelection()
        const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null
        if (range) {
          const rect = range.getBoundingClientRect()
          if (rect) {
            store.showSlashMenu({ x: rect.left, y: rect.bottom + 8 })
          }
        }
      } else if (store.slashMenu.visible) {
        // 如果菜单已打开但输入了非命令的 /，关闭菜单
        store.hideSlashMenu()
      }
    } else if (store.slashMenu.visible) {
      // 更新查询
      const slashIndex = content.lastIndexOf('/')
      if (slashIndex >= 0) {
        const beforeSlash = content.slice(0, slashIndex)
        // 只有当 / 前面是空的或只有空格时才继续显示菜单
        if (beforeSlash === '' || /^\s*$/.test(beforeSlash)) {
          store.updateSlashMenuQuery(content.slice(slashIndex + 1))
        } else {
          store.hideSlashMenu()
        }
      } else {
        store.hideSlashMenu()
      }
    }
  }

  // 处理键盘事件
  function handleKeydown(blockId: string, event: KeyboardEvent) {
    const block = store.getBlock(blockId)
    if (!block) return

    const content = getBlockContent(blockId)
    const selection = window.getSelection()
    const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null
    const atStart = range ? range.startOffset === 0 && range.collapsed : false
    const atEnd = range ? range.endOffset === content.length && range.collapsed : false

    // 处理斜杠菜单键盘导航
    if (store.slashMenu.visible) {
      // 这些在菜单组件中处理
      return
    }

    switch (event.key) {
      case 'Enter':
        if (!event.shiftKey) {
          event.preventDefault()
          handleEnter(blockId)
        }
        break

      case 'Backspace':
        if (atStart && content === '') {
          event.preventDefault()
          handleBackspaceOnEmpty(blockId)
        } else if (atStart) {
          // 合并到上一个块
          event.preventDefault()
          handleMergeWithPrevious(blockId)
        }
        break

      case 'Delete':
        if (atEnd) {
          event.preventDefault()
          handleMergeWithNext(blockId)
        }
        break

      case 'ArrowUp':
        if (atStart) {
          event.preventDefault()
          focusPreviousBlock(blockId)
        }
        break

      case 'ArrowDown':
        if (atEnd) {
          event.preventDefault()
          focusNextBlock(blockId)
        }
        break

      case 'Tab':
        event.preventDefault()
        if (event.shiftKey) {
          handleUnindent(blockId)
        } else {
          handleIndent(blockId)
        }
        break

      // 快捷键
      case 'b':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault()
          // 应用粗体格式
        }
        break

      case 'i':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault()
          // 应用斜体格式
        }
        break

      case 'z':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault()
          if (event.shiftKey) {
            store.redo()
          } else {
            store.undo()
          }
        }
        break

      case 'y':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault()
          store.redo()
        }
        break
    }
  }

  // 处理 Enter 键
  function handleEnter(blockId: string) {
    syncBlockContent(blockId)
    const block = store.getBlock(blockId)
    if (!block) return

    // 获取当前光标位置的内容
    const selection = window.getSelection()
    const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null
    if (!range) return

    const content = getBlockContent(blockId)
    const offset = range.startOffset
    const beforeContent = content.slice(0, offset)
    const afterContent = content.slice(offset)

    // 更新当前块
    setBlockContent(blockId, beforeContent)
    store.updateBlock(blockId, { content: beforeContent })

    // 创建新块
    const newBlockId = store.insertBlock(
      { type: 'text', content: afterContent },
      { afterId: blockId, parentId: block.parentId }
    )

    // 聚焦新块
    nextTick(() => {
      focusBlock(newBlockId, 0)
    })
  }

  // 处理空块的 Backspace
  function handleBackspaceOnEmpty(blockId: string) {
    const block = store.getBlock(blockId)
    if (!block) return

    // 如果是唯一块，不删除
    if (!block.parentId && store.rootBlocks.length <= 1) {
      return
    }

    // 聚焦前一个块
    const prevBlock = store.getPreviousBlock(blockId)
    if (prevBlock) {
      focusBlock(prevBlock.id, getBlockContent(prevBlock.id).length)
    }

    // 删除当前块
    store.deleteBlock(blockId)
    delete editingContent.value[blockId]
  }

  // 合并到上一个块
  function handleMergeWithPrevious(blockId: string) {
    const block = store.getBlock(blockId)
    if (!block) return

    const prevBlock = store.getPreviousBlock(blockId)
    if (!prevBlock) return

    const prevContent = getBlockContent(prevBlock.id)
    const currentContent = getBlockContent(blockId)

    // 合并内容
    const mergedContent = prevContent + currentContent
    setBlockContent(prevBlock.id, mergedContent)
    store.updateBlock(prevBlock.id, { content: mergedContent })

    // 聚焦到合并位置
    focusBlock(prevBlock.id, prevContent.length)

    // 删除当前块
    store.deleteBlock(blockId)
    delete editingContent.value[blockId]
  }

  // 合并到下一个块
  function handleMergeWithNext(blockId: string) {
    const block = store.getBlock(blockId)
    if (!block) return

    const nextBlock = store.getNextBlock(blockId)
    if (!nextBlock) return

    const currentContent = getBlockContent(blockId)
    const nextContent = getBlockContent(nextBlock.id)

    // 合并内容
    const mergedContent = currentContent + nextContent
    setBlockContent(blockId, mergedContent)
    store.updateBlock(blockId, { content: mergedContent })

    // 删除下一个块
    store.deleteBlock(nextBlock.id)
    delete editingContent.value[nextBlock.id]
  }

  // 聚焦前一个块
  function focusPreviousBlock(blockId: string) {
    const prevBlock = store.getPreviousBlock(blockId)
    if (prevBlock) {
      focusBlock(prevBlock.id, getBlockContent(prevBlock.id).length)
    }
  }

  // 聚焦下一个块
  function focusNextBlock(blockId: string) {
    const nextBlock = store.getNextBlock(blockId)
    if (nextBlock) {
      focusBlock(nextBlock.id, 0)
    }
  }

  // 聚焦指定块
  function focusBlock(blockId: string, offset: number = 0) {
    nextTick(() => {
      const element = document.querySelector(`[data-block-id="${blockId}"] .block-content`) as HTMLElement | null
      if (element) {
        element.focus()

        // 设置光标位置
        const selection = window.getSelection()
        const range = document.createRange()

        if (element.firstChild) {
          const textNode = element.firstChild
          const textLength = textNode.textContent?.length || 0
          range.setStart(textNode, Math.min(offset, textLength))
          range.collapse(true)
        } else {
          range.setStart(element, 0)
          range.collapse(true)
        }

        selection?.removeAllRanges()
        selection?.addRange(range)

        store.setFocusedBlock(blockId)
      }
    })
  }

  // 处理缩进
  function handleIndent(blockId: string) {
    const block = store.getBlock(blockId)
    if (!block) return

    const prevBlock = store.getPreviousBlock(blockId)
    if (!prevBlock) return

    // 将当前块移到前一个块下面作为子块
    store.moveBlock(blockId, { parentId: prevBlock.id })
  }

  // 处理取消缩进
  function handleUnindent(blockId: string) {
    const block = store.getBlock(blockId)
    if (!block || !block.parentId) return

    const parent = store.getBlock(block.parentId)
    if (!parent) return

    // 将当前块移到父块之后
    store.moveBlock(blockId, { afterId: parent.id })
  }

  // 转换块类型
  function convertBlock(blockId: string, newType: BlockType) {
    store.saveSnapshot()
    store.convertBlockType(blockId, newType)
  }

  // 插入新块
  function insertNewBlock(type: BlockType = 'text', afterId?: string) {
    const targetId = afterId || store.focusedBlockId
    if (!targetId) return null

    const block = store.getBlock(targetId)
    if (!block) return null

    const newBlockId = store.insertBlock(
      { type, content: '' },
      { afterId: targetId, parentId: block.parentId }
    )

    nextTick(() => {
      focusBlock(newBlockId, 0)
    })

    return newBlockId
  }

  return {
    editingContent,
    getBlockContent,
    setBlockContent,
    syncBlockContent,
    handleBlockFocus,
    handleBlockBlur,
    handleInput,
    handleKeydown,
    focusBlock,
    focusPreviousBlock,
    focusNextBlock,
    convertBlock,
    insertNewBlock,
    handleIndent,
    handleUnindent,
    // 暴露 focusedBlockId 以便 slash commands 使用
    focusedBlockId: computed(() => store.focusedBlockId),
  }
}

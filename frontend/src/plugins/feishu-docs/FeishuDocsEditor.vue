<script setup lang="ts">
/**
 * 飞书文档编辑器 - 主组件
 * 完全独立的块级编辑器，不依赖 Tiptap
 */
import { ref, computed, watch, onMounted, onBeforeUnmount, provide, nextTick } from 'vue'
import { useDocumentStore } from './stores/document'
import { useBlockEditor } from './composables/useBlockEditor'
import SlashCommandMenu from './components/SlashCommandMenu.vue'
import BlockRenderer from './components/BlockRenderer.vue'

// Props
const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '输入 / 打开命令菜单...',
  },
  editable: {
    type: Boolean,
    default: true,
  },
})

// Emits
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'ready'): void
  (e: 'change', value: string): void
}>()

// Store
const store = useDocumentStore()

// Block editor composable
const editor = useBlockEditor()

// Refs
const editorRef = ref<HTMLElement | null>(null)
const isInitialized = ref(false)

// Provide editor context
provide('editor', {
  store,
  editor,
  isEditable: computed(() => props.editable),
})

// 初始化
onMounted(() => {
  initEditor()
})

onBeforeUnmount(() => {
  // 清理
  store.$reset()
})

// 初始化编辑器
function initEditor() {
  if (props.modelValue && props.modelValue.trim()) {
    // 从 HTML 导入
    store.fromHTML(props.modelValue)
  } else {
    // 创建空文档
    store.initDocument()
  }
  isInitialized.value = true
  emit('ready')
}

// 监听外部值变化
watch(
  () => props.modelValue,
  (newValue) => {
    if (!isInitialized.value) return
    const currentHTML = store.toHTML()
    if (newValue !== currentHTML) {
      store.fromHTML(newValue || '')
    }
  }
)

// 监听编辑器变化，同步到父组件
watch(
  () => store.document?.updatedAt,
  () => {
    if (!isInitialized.value) return
    const html = store.toHTML()
    emit('update:modelValue', html)
    emit('change', html)
  }
)

// 监听可编辑状态
watch(
  () => props.editable,
  (editable) => {
    store.isEditable = editable
  },
  { immediate: true }
)

// 处理点击空白区域
function handleContainerClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (target === editorRef.value || target.classList.contains('editor-container')) {
    // 点击空白区域，聚焦最后一个块
    const lastBlockId = store.rootBlocks[store.rootBlocks.length - 1]?.id
    if (lastBlockId) {
      editor.focusBlock(lastBlockId)
    }
  }
}

// 处理粘贴
function handlePaste(event: ClipboardEvent) {
  const clipboardData = event.clipboardData
  if (!clipboardData) return

  // 处理图片粘贴
  const items = clipboardData.items
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        handleImageUpload(file)
      }
      return
    }
  }

  // 处理文本粘贴
  const text = clipboardData.getData('text/plain')
  if (text) {
    // 默认处理文本粘贴
  }
}

// 处理图片上传
async function handleImageUpload(file: File) {
  // 这里应该调用上传 API
  const reader = new FileReader()
  reader.onload = () => {
    const newBlockId = store.insertBlock({
      type: 'image',
      attrs: { src: reader.result, alt: file.name },
    }, { afterId: store.focusedBlockId || undefined })

    nextTick(() => {
      editor.focusBlock(newBlockId)
    })
  }
  reader.readAsDataURL(file)
}

// 处理拖放
function handleDrop(event: DragEvent) {
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return

  for (const file of files) {
    if (file.type.startsWith('image/')) {
      event.preventDefault()
      handleImageUpload(file)
      return
    }
  }
}

function handleDragOver(event: DragEvent) {
  if (event.dataTransfer?.types.includes('Files')) {
    event.preventDefault()
  }
}

// 工具栏操作
const toolbarActions = {
  undo: () => store.undo(),
  redo: () => store.redo(),
  bold: () => applyFormat('bold'),
  italic: () => applyFormat('italic'),
  underline: () => applyFormat('underline'),
  strikethrough: () => applyFormat('strikethrough'),
  code: () => applyFormat('code'),
  link: () => {
    const url = prompt('请输入链接 URL:')
    if (url) {
      applyFormat('link', url)
    }
  },
  clearFormat: () => clearAllFormats(),
}

// 应用格式
function applyFormat(format: string, value?: any) {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) return

  // 使用 document.execCommand（简单实现）
  // 实际应用中应该使用更精确的格式化系统
  document.execCommand(format, false, value)
}

// 清除所有格式
function clearAllFormats() {
  document.execCommand('removeFormat', false)
}

// 检查格式是否激活
function isFormatActive(format: string): boolean {
  return document.queryCommandState(format)
}

// 处理斜杠命令选择
function handleSlashCommandSelect(cmd: any) {
  // 先隐藏菜单
  store.hideSlashMenu()

  // 清除当前块中的斜杠命令文本 (例如 "/h1")
  if (store.focusedBlockId) {
    const content = editor.getBlockContent(store.focusedBlockId)
    const slashIndex = content.lastIndexOf('/')
    if (slashIndex >= 0) {
      const newContent = content.slice(0, slashIndex)
      editor.setBlockContent(store.focusedBlockId, newContent)
      store.updateBlock(store.focusedBlockId, { content: newContent })
    }
  }

  // 执行命令
  cmd.action(editor)
}

// 暴露接口
defineExpose({
  store,
  editor,
  toHTML: () => store.toHTML(),
  toJSON: () => store.toJSON(),
  fromHTML: (html: string) => store.fromHTML(html),
  focus: () => {
    const firstBlockId = store.rootBlocks[0]?.id
    if (firstBlockId) {
      editor.focusBlock(firstBlockId)
    }
  },
})
</script>

<template>
  <div
    ref="editorRef"
    class="feishu-docs-editor"
    :class="{ 'is-editable': editable }"
    @click="handleContainerClick"
    @paste="handlePaste"
    @drop="handleDrop"
    @dragover="handleDragOver"
  >
    <!-- 工具栏 -->
    <div v-if="editable && isInitialized" class="editor-toolbar">
      <!-- 撤销/重做 -->
      <div class="toolbar-group">
        <button
          class="toolbar-btn"
          :disabled="!store.canUndo"
          @click="toolbarActions.undo"
          title="撤销 (Ctrl+Z)"
        >
          ↶
        </button>
        <button
          class="toolbar-btn"
          :disabled="!store.canRedo"
          @click="toolbarActions.redo"
          title="重做 (Ctrl+Y)"
        >
          ↷
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 标题选择 -->
      <div class="toolbar-group dropdown-group">
        <button class="toolbar-btn dropdown-trigger">
          {{ store.focusedBlock?.type || '正文' }}
          <span class="dropdown-arrow">▼</span>
        </button>
        <div class="dropdown-menu">
          <button @click="store.focusedBlockId && editor.convertBlock(store.focusedBlockId, 'text')">正文</button>
          <button @click="store.focusedBlockId && editor.convertBlock(store.focusedBlockId, 'h1')">标题 1</button>
          <button @click="store.focusedBlockId && editor.convertBlock(store.focusedBlockId, 'h2')">标题 2</button>
          <button @click="store.focusedBlockId && editor.convertBlock(store.focusedBlockId, 'h3')">标题 3</button>
          <button @click="store.focusedBlockId && editor.convertBlock(store.focusedBlockId, 'quote')">引用</button>
          <button @click="store.focusedBlockId && editor.convertBlock(store.focusedBlockId, 'code')">代码块</button>
        </div>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 文本格式 -->
      <div class="toolbar-group">
        <button
          class="toolbar-btn bold"
          :class="{ active: isFormatActive('bold') }"
          @click="toolbarActions.bold"
          title="粗体 (Ctrl+B)"
        >
          B
        </button>
        <button
          class="toolbar-btn italic"
          :class="{ active: isFormatActive('italic') }"
          @click="toolbarActions.italic"
          title="斜体 (Ctrl+I)"
        >
          I
        </button>
        <button
          class="toolbar-btn underline"
          :class="{ active: isFormatActive('underline') }"
          @click="toolbarActions.underline"
          title="下划线 (Ctrl+U)"
        >
          U
        </button>
        <button
          class="toolbar-btn strikethrough"
          :class="{ active: isFormatActive('strikethrough') }"
          @click="toolbarActions.strikethrough"
          title="删除线"
        >
          S
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 代码和链接 -->
      <div class="toolbar-group">
        <button
          class="toolbar-btn code"
          @click="toolbarActions.code"
          title="行内代码"
        >
          &lt;/&gt;
        </button>
        <button
          class="toolbar-btn"
          :class="{ active: isFormatActive('link') }"
          @click="toolbarActions.link"
          title="链接 (Ctrl+K)"
        >
          🔗
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 清除格式 -->
      <div class="toolbar-group">
        <button
          class="toolbar-btn"
          @click="toolbarActions.clearFormat"
          title="清除格式"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- 编辑区域 -->
    <div class="editor-container">
      <div v-if="!isInitialized" class="editor-loading">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else class="blocks-container">
        <BlockRenderer
          v-for="block in store.rootBlocks"
          :key="block.id"
          :block="block"
          :depth="0"
        />

        <!-- 空状态 -->
        <div
          v-if="store.rootBlocks.length === 0"
          class="empty-state"
          @click="() => store.insertBlock({ type: 'text', content: '' })"
        >
          <span class="empty-icon">📝</span>
          <span>点击开始编辑</span>
        </div>
      </div>
    </div>

    <!-- 斜杠命令菜单 -->
    <SlashCommandMenu
      :visible="store.slashMenu.visible"
      :query="store.slashMenu.query"
      :position="store.slashMenu.position"
      @select="handleSlashCommandSelect"
      @close="store.hideSlashMenu()"
    />

    <!-- 底部提示 -->
    <div v-if="editable && isInitialized" class="editor-hint">
      <span>输入 <code>/</code> 打开命令菜单</span>
      <span class="hint-divider">|</span>
      <span>快捷键: <code>Ctrl+B</code> 加粗 <code>Ctrl+I</code> 斜体 <code>Ctrl+Z</code> 撤销</span>
    </div>
  </div>
</template>

<style scoped>
@import './styles/editor.css';
</style>

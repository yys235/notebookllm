<script setup lang="ts">
/**
 * 块文档编辑器 - 主组件
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
  // 笔记元信息
  author: {
    type: String,
    default: '',
  },
  createdAt: {
    type: String,
    default: '',
  },
  updatedAt: {
    type: String,
    default: '',
  },
})

// 格式化日期
function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

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

// 处理斜杠命令选择
function handleSlashCommandSelect(cmd: any) {
  // 先隐藏菜单
  store.hideSlashMenu()

  // 清除当前块中的斜杠命令文本 (例如 "/h1")
  // 只清除块开头或空格后的 / 命令文本，避免误删 URL 中的 /
  if (store.focusedBlockId) {
    const content = editor.getBlockContent(store.focusedBlockId)

    // 查找触发命令的 / 位置（只在块开头或空格后查找）
    let commandSlashIndex = -1

    // 检查是否以 / 开头
    if (content.startsWith('/')) {
      commandSlashIndex = 0
    } else {
      // 查找空格后的 /
      const spaceSlashMatch = content.match(/\s\/[^/]*$/)
      if (spaceSlashMatch && spaceSlashMatch.index !== undefined) {
        commandSlashIndex = spaceSlashMatch.index + 1 // +1 是空格的长度
      }
    }

    if (commandSlashIndex >= 0) {
      const newContent = content.slice(0, commandSlashIndex)
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
    <!-- 元信息栏 -->
    <div v-if="isInitialized && (author || createdAt || updatedAt)" class="editor-meta">
      <span v-if="author" class="meta-item">
        <span class="meta-label">创建者</span>
        <span class="meta-value">{{ author }}</span>
      </span>
      <span v-if="createdAt" class="meta-item">
        <span class="meta-label">创建时间</span>
        <span class="meta-value">{{ formatDate(createdAt) }}</span>
      </span>
      <span v-if="updatedAt" class="meta-item">
        <span class="meta-label">最后修改</span>
        <span class="meta-value">{{ formatDate(updatedAt) }}</span>
      </span>
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

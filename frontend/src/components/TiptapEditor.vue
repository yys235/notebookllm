<script setup lang="ts">
import { watch, onBeforeUnmount, ref, computed } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Highlight from '@tiptap/extension-highlight'
import Underline from '@tiptap/extension-underline'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Image from '@tiptap/extension-image'
import { message } from 'ant-design-vue'
import { uploadApi } from '@/api/upload'

interface Props {
  modelValue: string
  placeholder?: string
  editable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '开始编写，支持 Markdown 语法...',
  editable: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)

// 图片上传处理
function handleImageUpload() {
  fileInput.value?.click()
}

async function onFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }

  // 验证文件大小 (最大 5MB)
  if (file.size > 5 * 1024 * 1024) {
    message.error('图片大小不能超过 5MB')
    return
  }

  await insertImageFile(file)
  // 清空 input
  input.value = ''
}

async function insertImageFile(file: File) {
  isUploading.value = true

  try {
    // 上传到服务器
    const result = await uploadApi.uploadImage(file)

    // 插入图片（使用服务器返回的 URL）
    editor.value?.chain().focus().setImage({ src: result.url, alt: file.name }).run()
    message.success('图片已上传')
  } catch (error: any) {
    message.error(error.message || '图片上传失败')
    console.error('Image upload error:', error)
  } finally {
    isUploading.value = false
  }
}

// 粘贴图片处理
function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const file = item.getAsFile()
      if (file) {
        insertImageFile(file)
      }
      return
    }
  }
}

// 拖拽上传处理
function handleDrop(event: DragEvent) {
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return

  for (const file of files) {
    if (file.type.startsWith('image/')) {
      event.preventDefault()
      insertImageFile(file)
      return
    }
  }
}

function handleDragOver(event: DragEvent) {
  if (event.dataTransfer?.types.includes('Files')) {
    event.preventDefault()
  }
}

const editor = useEditor({
  content: props.modelValue && props.modelValue.trim() ? props.modelValue : '<p></p>',
  extensions: [
    StarterKit.configure({
      heading: {
        levels: [1, 2, 3, 4, 5, 6],
      },
    }),
    Placeholder.configure({
      placeholder: props.placeholder,
    }),
    Highlight.configure({
      multicolor: true,
    }),
    Underline,
    TaskList,
    TaskItem.configure({
      nested: true,
    }),
    Image.configure({
      inline: false,
      allowBase64: true,
    })
  ],
  editorProps: {
    attributes: {
      class: 'tiptap-editor',
    },
    handlePaste: (_view, event) => {
      handlePaste(event)
      return false
    },
  },
  editable: props.editable,
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
})

// Computed property to check if editor is fully initialized
const isEditorReady = computed(() => {
  if (!editor.value) return false
  try {
    // Check if editor has a valid document
    const doc = editor.value.state?.doc
    return doc !== null && doc !== undefined
  } catch {
    return false
  }
})

// 监听外部值变化
watch(
  () => props.modelValue,
  (value) => {
    if (!editor.value) return
    // Skip if value is null/undefined/empty
    if (value == null || value === '') return
    // Ensure value is a string
    if (typeof value !== 'string') {
      console.warn('Invalid content type:', typeof value)
      return
    }
    // Only update if content is different
    const currentHtml = editor.value.getHTML()
    if (value !== currentHtml) {
      try {
        // Try to set content - Tiptap will auto-detect HTML vs JSON
        editor.value.commands.setContent(value, { emitUpdate: false })
      } catch (e) {
        console.warn('Failed to set editor content:', e)
        // Reset to empty paragraph on error
        try {
          editor.value.commands.clearContent()
          editor.value.commands.setContent('<p></p>')
        } catch (e2) {
          console.error('Also failed to reset content:', e2)
        }
      }
    }
  }
)

// 监听 editable 属性
watch(
  () => props.editable,
  (newEditable) => {
    if (editor.value) {
      editor.value.setEditable(newEditable)
    }
  }
)

// 清理
onBeforeUnmount(() => {
  editor.value?.destroy()
})

// 状态检查
function isActive(type: string, attrs?: Record<string, unknown>): boolean {
  if (!editor.value) return false
  try {
    return editor.value.isActive(type, attrs) ?? false
  } catch {
    return false
  }
}

// 检查编辑器是否可用
function canUndo(): boolean {
  if (!editor.value) return false
  try {
    return editor.value.can().undo()
  } catch {
    return false
  }
}

function canRedo(): boolean {
  if (!editor.value) return false
  try {
    return editor.value.can().redo()
  } catch {
    return false
  }
}

// 添加图片 URL
function addImageUrl() {
  const url = prompt('请输入图片 URL:')
  if (url && url.trim()) {
    editor.value?.chain().focus().setImage({ src: url.trim() }).run()
  }
}

// Safe editor action wrappers
function safeAction(action: () => void) {
  if (!editor.value) return
  if (!isEditorReady.value) return
  try {
    action()
  } catch (e) {
    console.warn('Editor action failed:', e)
  }
}

function undo() {
  safeAction(() => editor.value!.chain().focus().undo().run())
}

function redo() {
  safeAction(() => editor.value!.chain().focus().redo().run())
}

function toggleHeading(level: 1 | 2 | 3) {
  safeAction(() => editor.value!.chain().focus().toggleHeading({ level }).run())
}

function toggleBold() {
  safeAction(() => editor.value!.chain().focus().toggleBold().run())
}

function toggleItalic() {
  safeAction(() => editor.value!.chain().focus().toggleItalic().run())
}

function toggleUnderline() {
  safeAction(() => editor.value!.chain().focus().toggleUnderline().run())
}

function toggleStrike() {
  safeAction(() => editor.value!.chain().focus().toggleStrike().run())
}

function toggleHighlight() {
  safeAction(() => editor.value!.chain().focus().toggleHighlight().run())
}

function toggleCode() {
  safeAction(() => editor.value!.chain().focus().toggleCode().run())
}

function toggleCodeBlock() {
  safeAction(() => editor.value!.chain().focus().toggleCodeBlock().run())
}

function toggleBulletList() {
  safeAction(() => editor.value!.chain().focus().toggleBulletList().run())
}

function toggleOrderedList() {
  safeAction(() => editor.value!.chain().focus().toggleOrderedList().run())
}

function toggleTaskList() {
  safeAction(() => editor.value!.chain().focus().toggleTaskList().run())
}

function toggleBlockquote() {
  safeAction(() => editor.value!.chain().focus().toggleBlockquote().run())
}

function setHorizontalRule() {
  safeAction(() => editor.value!.chain().focus().setHorizontalRule().run())
}

function clearFormat() {
  safeAction(() => editor.value!.chain().focus().clearNodes().unsetAllMarks().run())
}

defineExpose({ editor })
</script>

<template>
  <div
    v-show="isEditorReady"
    class="tiptap-container"
    @drop="handleDrop"
    @dragover="handleDragOver"
  >
    <!-- 工具栏 -->
    <div v-if="editable" v-show="isEditorReady" class="tiptap-toolbar">
      <!-- 撤销/重做 -->
      <div class="toolbar-group">
        <button
          @click="undo"
          :disabled="!canUndo()"
          title="撤销 (Ctrl+Z)"
          class="toolbar-btn"
          type="button"
        >
          ↶
        </button>
        <button
          @click="redo"
          :disabled="!canRedo()"
          title="重做 (Ctrl+Y)"
          class="toolbar-btn"
          type="button"
        >
          ↷
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 标题 -->
      <div class="toolbar-group">
        <button
          @click="toggleHeading(1)"
          :class="{ 'is-active': isActive('heading', { level: 1 }) }"
          title="标题 1 (# + 空格)"
          class="toolbar-btn"
          type="button"
        >
          H1
        </button>
        <button
          @click="toggleHeading(2)"
          :class="{ 'is-active': isActive('heading', { level: 2 }) }"
          title="标题 2 (## + 空格)"
          class="toolbar-btn"
          type="button"
        >
          H2
        </button>
        <button
          @click="toggleHeading(3)"
          :class="{ 'is-active': isActive('heading', { level: 3 }) }"
          title="标题 3 (### + 空格)"
          class="toolbar-btn"
          type="button"
        >
          H3
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 文本格式 -->
      <div class="toolbar-group">
        <button
          @click="toggleBold"
          :class="{ 'is-active': isActive('bold') }"
          title="粗体 (**文字** 或 Ctrl+B)"
          class="toolbar-btn bold"
          type="button"
        >
          B
        </button>
        <button
          @click="toggleItalic"
          :class="{ 'is-active': isActive('italic') }"
          title="斜体 (*文字* 或 Ctrl+I)"
          class="toolbar-btn italic"
          type="button"
        >
          I
        </button>
        <button
          @click="toggleUnderline"
          :class="{ 'is-active': isActive('underline') }"
          title="下划线 (Ctrl+U)"
          class="toolbar-btn underline"
          type="button"
        >
          U
        </button>
        <button
          @click="toggleStrike"
          :class="{ 'is-active': isActive('strike') }"
          title="删除线 (~~文字~~)"
          class="toolbar-btn strike"
          type="button"
        >
          S
        </button>
        <button
          @click="toggleHighlight"
          :class="{ 'is-active': isActive('highlight') }"
          title="高亮"
          class="toolbar-btn highlight"
          type="button"
        >
          <span style="background: linear-gradient(100deg, #fff59d, #ffcc80); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">H</span>
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 图片 -->
      <div class="toolbar-group">
        <button
          @click="handleImageUpload"
          :disabled="isUploading"
          title="上传图片 (支持拖拽、粘贴)"
          class="toolbar-btn image-btn"
          type="button"
        >
          <span v-if="isUploading">⏳</span>
          <span v-else>🖼</span>
        </button>
        <button
          @click="addImageUrl"
          title="从 URL 插入图片"
          class="toolbar-btn"
          type="button"
        >
          🔗
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 代码 -->
      <div class="toolbar-group">
        <button
          @click="toggleCode"
          :class="{ 'is-active': isActive('code') }"
          title="行内代码 (`代码`)"
          class="toolbar-btn code"
          type="button"
        >
          &lt;/&gt;
        </button>
        <button
          @click="toggleCodeBlock"
          :class="{ 'is-active': isActive('codeBlock') }"
          title="代码块 (``` + 回车)"
          class="toolbar-btn code"
          type="button"
        >
          { }
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 列表 -->
      <div class="toolbar-group">
        <button
          @click="toggleBulletList"
          :class="{ 'is-active': isActive('bulletList') }"
          title="无序列表 (- + 空格)"
          class="toolbar-btn"
          type="button"
        >
          •
        </button>
        <button
          @click="toggleOrderedList"
          :class="{ 'is-active': isActive('orderedList') }"
          title="有序列表 (1. + 空格)"
          class="toolbar-btn"
          type="button"
        >
          1.
        </button>
        <button
          @click="toggleTaskList"
          :class="{ 'is-active': isActive('taskList') }"
          title="任务列表 (- [ ] + 空格)"
          class="toolbar-btn"
          type="button"
        >
          ☑
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 引用和分割线 -->
      <div class="toolbar-group">
        <button
          @click="toggleBlockquote"
          :class="{ 'is-active': isActive('blockquote') }"
          title="引用 (> + 空格)"
          class="toolbar-btn"
          type="button"
        >
          "
        </button>
        <button
          @click="setHorizontalRule"
          title="分割线 (---)"
          class="toolbar-btn"
          type="button"
        >
          —
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 清除格式 -->
      <div class="toolbar-group">
        <button
          @click="clearFormat"
          title="清除格式"
          class="toolbar-btn"
          type="button"
        >
          ×
        </button>
      </div>
    </div>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      style="display: none"
      @change="onFileSelect"
    />

    <!-- 编辑区域 -->
    <EditorContent :editor="editor" class="tiptap-content" />

    <!-- 提示 -->
    <div v-if="editable" class="editor-hint">
      <span>Markdown 快捷键：</span>
      <code>#</code> 标题
      <code>**</code> 粗体
      <code>*</code> 斜体
      <code>`</code> 代码
      <code>-</code> 列表
      <span class="hint-divider">|</span>
      <span>📷 支持拖拽、粘贴或点击 🖼 上传图片</span>
    </div>
  </div>
</template>

<style scoped>
.tiptap-container {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.tiptap-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  padding: 8px 12px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  position: sticky;
  top: 0;
  z-index: 10;
}

.toolbar-group {
  display: flex;
  gap: 2px;
}

.toolbar-btn {
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #595959;
  transition: all 0.2s;
}

.toolbar-btn:hover:not(:disabled) {
  background: #e6e6e6;
  color: #262626;
}

.toolbar-btn.is-active {
  background: #1890ff;
  color: white;
  border-color: #1890ff;
}

.toolbar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.toolbar-btn.bold {
  font-weight: bold;
}

.toolbar-btn.italic {
  font-style: italic;
}

.toolbar-btn.underline {
  text-decoration: underline;
}

.toolbar-btn.strike {
  text-decoration: line-through;
}

.toolbar-btn.code {
  font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.toolbar-btn.image-btn {
  position: relative;
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: #e8e8e8;
  margin: 0 6px;
}

.tiptap-content :deep(.tiptap-editor) {
  min-height: 400px;
  padding: 20px;
  line-height: 1.8;
  font-size: 15px;
}

.tiptap-content :deep(.tiptap-editor:focus) {
  outline: none;
}

/* Placeholder */
.tiptap-content :deep(.tiptap-editor p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: #bfbfbf;
  pointer-events: none;
  height: 0;
}

/* 图片样式 */
.tiptap-content :deep(.tiptap-editor img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 16px 0;
  cursor: default;
}

.tiptap-content :deep(.tiptap-editor img.ProseMirror-selectednode) {
  outline: 3px solid #1890ff;
}

.tiptap-content :deep(.tiptap-editor figure) {
  margin: 16px 0;
  text-align: center;
}

.tiptap-content :deep(.tiptap-editor figure img) {
  margin: 0;
}

.tiptap-content :deep(.tiptap-editor figcaption) {
  margin-top: 8px;
  font-size: 14px;
  color: #8c8c8c;
  font-style: italic;
}

/* 标题样式 */
.tiptap-content :deep(.tiptap-editor h1) {
  font-size: 2em;
  font-weight: 700;
  margin: 0.67em 0;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.tiptap-content :deep(.tiptap-editor h2) {
  font-size: 1.5em;
  font-weight: 600;
  margin: 0.83em 0;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.tiptap-content :deep(.tiptap-editor h3) {
  font-size: 1.25em;
  font-weight: 600;
  margin: 1em 0;
}

.tiptap-content :deep(.tiptap-editor h4),
.tiptap-content :deep(.tiptap-editor h5),
.tiptap-content :deep(.tiptap-editor h6) {
  font-weight: 600;
  margin: 1em 0;
}

/* 列表样式 */
.tiptap-content :deep(.tiptap-editor ul),
.tiptap-content :deep(.tiptap-editor ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.tiptap-content :deep(.tiptap-editor li) {
  margin: 0.3em 0;
}

/* 任务列表样式 */
.tiptap-content :deep(.tiptap-editor ul[data-type="taskList"]) {
  list-style: none;
  padding-left: 0;
}

.tiptap-content :deep(.tiptap-editor ul[data-type="taskList"] li) {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.tiptap-content :deep(.tiptap-editor ul[data-type="taskList"] li > label) {
  flex: 0 0 auto;
  margin-right: 0.5rem;
  user-select: none;
}

.tiptap-content :deep(.tiptap-editor ul[data-type="taskList"] li > label input[type="checkbox"]) {
  cursor: pointer;
  width: 16px;
  height: 16px;
  accent-color: #1890ff;
}

.tiptap-content :deep(.tiptap-editor ul[data-type="taskList"] li > div) {
  flex: 1 1 auto;
}

.tiptap-content :deep(.tiptap-editor ul[data-type="taskList"] li[data-checked="true"] > div) {
  text-decoration: line-through;
  color: #8c8c8c;
}

/* 代码块样式 - GitHub 风格 */
.tiptap-content :deep(.tiptap-editor pre) {
  background: #24292e;
  color: #f6f8fa;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  font-family: 'Fira Code', 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 16px 0;
}

.tiptap-content :deep(.tiptap-editor pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: inherit;
}

/* 行内代码样式 */
.tiptap-content :deep(.tiptap-editor code) {
  background: rgba(175, 184, 193, 0.2);
  border-radius: 6px;
  padding: 2px 6px;
  font-family: 'Fira Code', 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 0.9em;
  color: #d73a49;
}

/* 引用块样式 */
.tiptap-content :deep(.tiptap-editor blockquote) {
  border-left: 4px solid #1890ff;
  padding: 8px 16px;
  margin: 16px 0;
  background: #f6f8fa;
  border-radius: 0 6px 6px 0;
  color: #586069;
}

.tiptap-content :deep(.tiptap-editor blockquote p) {
  margin: 0;
}

/* 高亮样式 */
.tiptap-content :deep(.tiptap-editor mark) {
  background-color: #fff59d;
  padding: 2px 4px;
  border-radius: 2px;
}

/* 粗体、斜体、删除线、下划线 */
.tiptap-content :deep(.tiptap-editor strong) {
  font-weight: 600;
}

.tiptap-content :deep(.tiptap-editor em) {
  font-style: italic;
}

.tiptap-content :deep(.tiptap-editor s) {
  text-decoration: line-through;
  color: #6a737d;
}

.tiptap-content :deep(.tiptap-editor u) {
  text-decoration: underline;
}

/* 水平线 */
.tiptap-content :deep(.tiptap-editor hr) {
  border: none;
  border-top: 2px solid #e1e4e8;
  margin: 24px 0;
}

/* 链接样式 */
.tiptap-content :deep(.tiptap-editor a) {
  color: #1890ff;
  text-decoration: none;
}

.tiptap-content :deep(.tiptap-editor a:hover) {
  text-decoration: underline;
}

/* 段落间距 */
.tiptap-content :deep(.tiptap-editor p) {
  margin: 0.5em 0;
}

.tiptap-content :deep(.tiptap-editor p:first-child) {
  margin-top: 0;
}

.tiptap-content :deep(.tiptap-editor p:last-child) {
  margin-bottom: 0;
}

/* 提示栏 */
.editor-hint {
  padding: 8px 16px;
  background: #f9f9f9;
  border-top: 1px solid #e8e8e8;
  font-size: 12px;
  color: #8c8c8c;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.editor-hint code {
  background: #e8e8e8;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Fira Code', monospace;
  font-size: 11px;
}

.editor-hint .hint-divider {
  color: #d9d9d9;
  margin: 0 4px;
}
</style>

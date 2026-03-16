<script setup lang="ts">
/**
 * 块渲染器组件
 * 根据块类型渲染不同的内容
 *
 * 重要：contenteditable 元素不使用 Vue 模板插值
 * 避免响应式更新导致光标位置问题
 */
import { computed, ref, watch } from 'vue'
import type { BlockData } from '../types'
import { useDocumentStore } from '../stores/document'
import { useBlockEditor } from '../composables/useBlockEditor'

const props = defineProps<{
  block: BlockData
  depth: number
}>()

const store = useDocumentStore()
const editor = useBlockEditor()

// 内容元素的引用
const contentRef = ref<HTMLElement | null>(null)

const isFocused = computed(() => store.focusedBlockId === props.block.id)
const isEditable = computed(() => store.isEditable)

// 获取块内容（仅用于非编辑状态显示和初始化）
const blockContent = computed(() => editor.getBlockContent(props.block.id))

// 监听外部内容变化（如撤销/重做），更新 DOM
watch(
  () => props.block.content,
  (newContent) => {
    // 只有在非聚焦状态下才更新 DOM
    if (contentRef.value && document.activeElement !== contentRef.value) {
      const content = typeof newContent === 'string' ? newContent : ''
      if (contentRef.value.innerText !== content) {
        contentRef.value.innerText = content
      }
    }
  }
)

// 初始化内容
function initContent(el: any) {
  if (el) {
    contentRef.value = el as HTMLElement
    const content = editor.getBlockContent(props.block.id)
    if (el.innerText !== content) {
      el.innerText = content
    }
  }
}

// 处理聚焦
function handleFocus() {
  editor.handleBlockFocus(props.block.id)
}

// 处理失焦
function handleBlur() {
  editor.handleBlockBlur(props.block.id)
}

// 处理输入
function handleInput(event: Event) {
  editor.handleInput(props.block.id, event)
}

// 处理键盘事件
function handleKeydown(event: KeyboardEvent) {
  editor.handleKeydown(props.block.id, event)
}

// 处理粘贴
function handlePaste(event: ClipboardEvent) {
  const clipboardData = event.clipboardData
  if (!clipboardData) return

  const text = clipboardData.getData('text/plain')
  if (!text) return

  event.preventDefault()

  // 检测是否有多行文本
  const lines = text.split('\n')

  if (lines.length <= 1) {
    // 单行文本，直接插入
    document.execCommand('insertText', false, text)
    return
  }

  // 多行文本，分割成多个块
  // 第一行插入到当前位置
  const firstLine = lines[0]
  document.execCommand('insertText', false, firstLine)

  // 同步当前块内容
  editor.syncBlockContent(props.block.id)

  // 后续行创建新块
  let previousBlockId = props.block.id
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    const newBlockId = store.insertBlock(
      { type: 'text', content: line },
      { afterId: previousBlockId, parentId: props.block.parentId }
    )
    previousBlockId = newBlockId
  }
}

// ========== 拖拽功能 ==========
const isDragging = ref(false)
const isDragOver = ref(false)
const dragPosition = ref<'before' | 'after' | 'child'>('after')

// 全局存储当前拖拽的块 ID
let currentDraggedBlockId: string | null = null
let targetInsertAfterId: string | null = null  // 目标插入位置：放在这个块之后
let draggedBlockOriginalY = 0  // 被拖拽块原始 Y 位置
let dragOffsetY = 0  // 鼠标相对于块顶部的偏移

// 开始拖拽
function handleDragStart(event: DragEvent) {
  if (!event.dataTransfer) return

  isDragging.value = true
  currentDraggedBlockId = props.block.id

  // 给所有块添加拖拽激活状态
  document.querySelectorAll('.block-wrapper').forEach(el => {
    el.classList.add('has-drag-active')
  })

  // 设置拖拽数据
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', props.block.id)
  event.dataTransfer.setData('application/x-block-id', props.block.id)

  // 记录被拖拽块的原始位置和偏移量
  const blockWrapper = document.querySelector(`[data-block-id="${props.block.id}"]`) as HTMLElement
  if (blockWrapper) {
    const rect = blockWrapper.getBoundingClientRect()
    draggedBlockOriginalY = rect.top
    dragOffsetY = event.clientY - rect.top
  }

  // 使用透明图像作为拖拽图标
  const transparentImg = new Image()
  transparentImg.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
  event.dataTransfer.setDragImage(transparentImg, 0, 0)
}

// 拖拽移动时更新被拖拽块位置和其他块的位置
function handleDrag(event: DragEvent) {
  // drag 事件在最后会触发一次 clientX=0, clientY=0 的情况
  if (event.clientX === 0 && event.clientY === 0) return

  // 1. 让被拖拽的块跟随鼠标
  const draggedBlock = document.querySelector(`[data-block-id="${currentDraggedBlockId}"]`) as HTMLElement
  if (draggedBlock) {
    const targetY = event.clientY - dragOffsetY
    const offsetY = targetY - draggedBlockOriginalY
    draggedBlock.style.transform = `translateY(${offsetY}px)`
  }

  // 2. 根据鼠标 Y 坐标更新其他块的位置（避让）
  updateBlocksPosition(event.clientY)
}

// 根据鼠标 Y 坐标计算目标插入位置，并让其他块避让
function updateBlocksPosition(mouseY: number) {
  const allBlocks = Array.from(document.querySelectorAll('.block-wrapper')) as HTMLElement[]
  const draggedBlock = document.querySelector(`[data-block-id="${currentDraggedBlockId}"]`) as HTMLElement
  const draggedHeight = draggedBlock ? draggedBlock.offsetHeight : 0

  // 找到鼠标位置对应的插入点（应该放在哪个块之后）
  let insertAfterIndex = -1  // -1 表示放在最前面

  for (let i = 0; i < allBlocks.length; i++) {
    const block = allBlocks[i]
    if (!block) continue

    const blockId = block.getAttribute('data-block-id')
    // 跳过被拖拽的块本身
    if (blockId === currentDraggedBlockId) continue

    const rect = block.getBoundingClientRect()
    const blockMiddle = rect.top + rect.height / 2

    // 如果鼠标在块的中间位置以下，则放在这个块之后
    if (mouseY > blockMiddle) {
      insertAfterIndex = i
    } else {
      // 鼠标在这个块的中间位置以上，停止查找
      break
    }
  }

  // 更新目标插入位置
  const targetBlock = allBlocks[insertAfterIndex]
  if (insertAfterIndex >= 0 && targetBlock) {
    targetInsertAfterId = targetBlock.getAttribute('data-block-id')
  } else {
    targetInsertAfterId = null  // 放在最前面
  }

  // 更新所有块的位置：让目标位置下方的块向下滑动避让
  allBlocks.forEach((block) => {
    if (!block) return

    const blockId = block.getAttribute('data-block-id')
    // 跳过被拖拽的块本身
    if (blockId === currentDraggedBlockId) return

    // 判断这个块是否需要避让（在鼠标位置下方）
    const rect = block.getBoundingClientRect()
    if (rect.top > mouseY) {
      // 在鼠标下方，向下滑动让位
      block.classList.add('is-shifted')
      block.style.transform = `translateY(${draggedHeight + 8}px)`
    } else {
      block.classList.remove('is-shifted')
      block.style.transform = ''
    }
  })
}

// 拖拽结束
function handleDragEnd(_event: DragEvent) {
  // 执行实际的块移动
  if (currentDraggedBlockId && targetInsertAfterId !== undefined) {
    if (targetInsertAfterId === null) {
      // 放在最前面
      const firstBlock = store.rootBlocks[0]
      if (firstBlock && firstBlock.id !== currentDraggedBlockId) {
        store.moveBlock(currentDraggedBlockId, { beforeId: firstBlock.id })
      }
    } else {
      // 放在目标块之后
      store.moveBlock(currentDraggedBlockId, { afterId: targetInsertAfterId })
    }
  }

  isDragging.value = false
  isDragOver.value = false
  currentDraggedBlockId = null
  targetInsertAfterId = null

  // 移除所有块的拖拽状态和 transform
  document.querySelectorAll('.block-wrapper').forEach(el => {
    el.classList.remove('has-drag-active', 'is-shifted')
    ;(el as HTMLElement).style.transform = ''
  })
}

// 拖拽进入
function handleDragEnter(event: DragEvent) {
  event.preventDefault()
}

// 拖拽离开
function handleDragLeave(_event: DragEvent) {
  // 不需要处理
}

// 拖拽悬停
function handleDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

// 放下 - 实际移动在 handleDragEnd 中处理
function handleDrop(event: DragEvent) {
  event.preventDefault()
  event.stopPropagation()
}

// 子块
const children = computed(() => {
  if (!props.block.children?.length) return []
  return props.block.children
    .map(id => store.getBlock(id))
    .filter(Boolean) as BlockData[]
})

// 判断是否为容器类型
const isContainerType = computed(() => {
  return ['bulletList', 'orderedList', 'taskList', 'grid'].includes(props.block.type)
})

// 判断是否为标题类型
const isHeading = computed(() => {
  return ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(props.block.type)
})

// 获取块样式类
const blockClass = computed(() => {
  const classes = [
    'block',
    `block-${props.block.type}`,
    { 'block-focused': isFocused.value },
    { 'block-empty': !blockContent.value },
    { 'block-container': isContainerType.value },
  ]
  return classes
})

// 任务项勾选
function toggleTask() {
  if (props.block.type !== 'taskItem') return
  const checked = !props.block.attrs?.checked
  store.updateBlock(props.block.id, {
    attrs: { ...props.block.attrs, checked }
  })
}

// 折叠块切换
function toggleCollapse() {
  if (props.block.type !== 'toggle') return
  const collapsed = !props.block.attrs?.collapsed
  store.updateBlock(props.block.id, {
    attrs: { ...props.block.attrs, collapsed }
  })
}

// 图片加载错误
function handleImageError(event: Event) {
  const target = event.target as HTMLImageElement
  target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23f0f0f0" width="100" height="100"/%3E%3Ctext x="50%25" y="50%25" fill="%23999" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}

// 标题占位符
const headingPlaceholder = computed(() => {
  const placeholders: Record<string, string> = {
    h1: '标题 1',
    h2: '标题 2',
    h3: '标题 3',
    h4: '标题 4',
    h5: '标题 5',
    h6: '标题 6',
  }
  return placeholders[props.block.type] || '标题'
})
</script>

<template>
  <div
    class="block-wrapper"
    :class="{
      'is-focused': isFocused,
      'is-dragging': isDragging,
      'is-drag-over': isDragOver,
      [`drag-${dragPosition}`]: isDragOver
    }"
    :data-block-id="block.id"
    :style="{ '--depth': depth }"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
    @dragover="handleDragOver"
    @drop="handleDrop"
  >
    <!-- 拖拽手柄 -->
    <div
      v-if="isEditable"
      class="block-handle"
      title="拖拽移动"
      draggable="true"
      @dragstart="handleDragStart"
      @drag="handleDrag"
      @dragend="handleDragEnd"
    >
      <span class="handle-icon">⋮⋮</span>
    </div>

    <!-- 拖拽位置预览指示器 -->
    <div v-if="isDragOver" class="drag-indicator" :class="dragPosition">
      <span class="indicator-text">
        {{ dragPosition === 'before' ? '放置在上方' : dragPosition === 'after' ? '放置在下方' : '作为子块' }}
      </span>
    </div>

    <!-- 块内容 -->
    <div :class="blockClass">
      <!-- 标题块 -->
      <template v-if="isHeading">
        <component
          :is="block.type"
          :ref="initContent"
          class="block-content"
          :contenteditable="isEditable"
          :class="{ 'is-empty': !blockContent }"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
          @keydown="handleKeydown"
          @paste="handlePaste"
          :data-placeholder="headingPlaceholder"
        ></component>
      </template>

      <!-- 引用块 -->
      <template v-else-if="block.type === 'quote'">
        <blockquote
          :ref="initContent"
          class="block-content block-quote"
          :contenteditable="isEditable"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
          @keydown="handleKeydown"
          @paste="handlePaste"
          data-placeholder="引用内容"
        ></blockquote>
      </template>

      <!-- 代码块 -->
      <template v-else-if="block.type === 'code'">
        <div class="block-code">
          <div class="code-header">
            <select v-if="isEditable" class="code-language" @change="(e) => store.updateBlock(block.id, { attrs: { ...block.attrs, language: (e.target as HTMLSelectElement).value } })">
              <option value="plaintext">纯文本</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="python">Python</option>
              <option value="java">Java</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="html">HTML</option>
              <option value="css">CSS</option>
              <option value="sql">SQL</option>
              <option value="bash">Bash</option>
              <option value="json">JSON</option>
              <option value="markdown">Markdown</option>
            </select>
            <span v-else class="code-language-label">{{ block.attrs?.language || 'plaintext' }}</span>
          </div>
          <pre
            :ref="initContent"
            class="block-content code-content"
            :contenteditable="isEditable"
            @focus="handleFocus"
            @blur="handleBlur"
            @input="handleInput"
            @keydown="handleKeydown"
            @paste="handlePaste"
            data-placeholder="代码内容"
          ></pre>
        </div>
      </template>

      <!-- 高亮块 -->
      <template v-else-if="block.type === 'callout'">
        <div class="block-callout" :class="`callout-${block.attrs?.calloutType || 'info'}`">
          <span class="callout-icon">{{ block.attrs?.icon || '💡' }}</span>
          <div
            :ref="initContent"
            class="block-content callout-content"
            :contenteditable="isEditable"
            @focus="handleFocus"
            @blur="handleBlur"
            @input="handleInput"
            @keydown="handleKeydown"
            @paste="handlePaste"
            data-placeholder="提示内容"
          ></div>
        </div>
      </template>

      <!-- 列表容器 -->
      <template v-else-if="block.type === 'bulletList'">
        <ul class="block-list bullet-list">
          <BlockRenderer
            v-for="child in children"
            :key="child.id"
            :block="child"
            :depth="depth + 1"
          />
        </ul>
      </template>

      <template v-else-if="block.type === 'orderedList'">
        <ol class="block-list ordered-list">
          <BlockRenderer
            v-for="child in children"
            :key="child.id"
            :block="child"
            :depth="depth + 1"
          />
        </ol>
      </template>

      <template v-else-if="block.type === 'taskList'">
        <div class="block-list task-list">
          <BlockRenderer
            v-for="child in children"
            :key="child.id"
            :block="child"
            :depth="depth + 1"
          />
        </div>
      </template>

      <!-- 列表项 -->
      <template v-else-if="block.type === 'listItem'">
        <li class="list-item">
          <span class="list-marker">•</span>
          <div
            :ref="initContent"
            class="block-content"
            :contenteditable="isEditable"
            @focus="handleFocus"
            @blur="handleBlur"
            @input="handleInput"
            @keydown="handleKeydown"
            @paste="handlePaste"
            data-placeholder="列表项"
          ></div>
          <template v-if="children.length">
            <BlockRenderer
              v-for="child in children"
              :key="child.id"
              :block="child"
              :depth="depth + 1"
            />
          </template>
        </li>
      </template>

      <!-- 任务项 -->
      <template v-else-if="block.type === 'taskItem'">
        <div class="task-item" :class="{ 'is-completed': block.attrs?.checked }">
          <input
            type="checkbox"
            class="task-checkbox"
            :checked="block.attrs?.checked"
            @change="toggleTask"
            :disabled="!isEditable"
          />
          <div
            :ref="initContent"
            class="block-content"
            :contenteditable="isEditable"
            @focus="handleFocus"
            @blur="handleBlur"
            @input="handleInput"
            @keydown="handleKeydown"
            @paste="handlePaste"
            data-placeholder="任务内容"
          ></div>
        </div>
      </template>

      <!-- 图片 -->
      <template v-else-if="block.type === 'image'">
        <figure class="block-image">
          <img
            :src="block.attrs?.src"
            :alt="block.attrs?.alt || ''"
            @error="handleImageError"
            loading="lazy"
          />
          <figcaption
            v-if="isEditable"
            :ref="initContent"
            class="image-caption"
            :contenteditable="isEditable"
            @focus="handleFocus"
            @blur="handleBlur"
            @input="handleInput"
            data-placeholder="图片说明"
          ></figcaption>
        </figure>
      </template>

      <!-- 分割线 -->
      <template v-else-if="block.type === 'divider'">
        <hr class="block-divider" />
      </template>

      <!-- 表格 -->
      <template v-else-if="block.type === 'table'">
        <div class="block-table">
          <table>
            <tbody>
              <tr v-for="row in block.attrs?.rows || 3" :key="row">
                <td v-for="col in block.attrs?.cols || 3" :key="col" :contenteditable="isEditable">
                  单元格
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 折叠块 -->
      <template v-else-if="block.type === 'toggle'">
        <div class="block-toggle" :class="{ 'is-collapsed': block.attrs?.collapsed }">
          <div class="toggle-header" @click="toggleCollapse">
            <span class="toggle-icon">{{ block.attrs?.collapsed ? '▶' : '▼' }}</span>
            <div
              :ref="initContent"
              class="block-content"
              :contenteditable="isEditable"
              @focus="handleFocus"
              @blur="handleBlur"
              @input="handleInput"
              @keydown="handleKeydown"
              @paste="handlePaste"
              data-placeholder="折叠块标题"
            ></div>
          </div>
          <div v-if="!block.attrs?.collapsed && children.length" class="toggle-content">
            <BlockRenderer
              v-for="child in children"
              :key="child.id"
              :block="child"
              :depth="depth + 1"
            />
          </div>
        </div>
      </template>

      <!-- 默认文本块 -->
      <template v-else>
        <p
          :ref="initContent"
          class="block-content block-text"
          :contenteditable="isEditable"
          :class="{ 'is-empty': !blockContent }"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
          @keydown="handleKeydown"
          @paste="handlePaste"
          data-placeholder="输入 / 打开命令菜单..."
        ></p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.block-wrapper {
  position: relative;
  margin: 2px 0;
  padding-left: 24px;
}

.block-handle {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  opacity: 0;
  transition: opacity 0.15s;
  color: #999;
  font-size: 14px;
  border-radius: 4px;
}

.block-wrapper:hover .block-handle {
  opacity: 1;
}

.block-handle:hover {
  background: #f0f0f0;
}

.block-wrapper.is-focused {
  background: rgba(24, 144, 255, 0.04);
  border-radius: 4px;
}

/* ========== 拖拽样式 ========== */

/* 被拖拽的源块 - 可见并高亮，通过 transform 移动到目标位置 */
.block-wrapper.is-dragging {
  min-height: 28px;
  opacity: 1 !important;
  z-index: 100;
  box-shadow: 0 8px 24px rgba(24, 144, 255, 0.3);
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
  border: 2px solid #1890ff;
  transition: transform 0.15s ease-out;
}

/* 拖拽进行中时，所有块显示激活样式 */
.block-wrapper.has-drag-active {
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f4ff 100%);
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(24, 144, 255, 0.1);
  transition: transform 0.2s ease, margin 0.2s ease, box-shadow 0.2s ease;
}

.block-wrapper.has-drag-active:hover {
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

/* 拖拽放置位置 - 在上方插入 */
.block-wrapper.is-drop-before {
  margin-top: 60px;
}

/* 拖拽放置位置 - 在下方插入 */
.block-wrapper.is-drop-after {
  margin-bottom: 60px;
}

/* 被拖拽块经过时，下方的块向下滑动让位 */
.block-wrapper.is-shifted {
  transform: translateY(60px);
}

/* 拖拽放置位置指示器 */
.block-wrapper.is-drop-before::before,
.block-wrapper.is-drop-after::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 50px;
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(24, 144, 255, 0.05) 100%);
  border: 2px dashed #1890ff;
  border-radius: 6px;
  pointer-events: none;
  z-index: 5;
}

.block-wrapper.is-drop-before::before {
  top: -55px;
}

.block-wrapper.is-drop-after::before {
  bottom: -55px;
}

/* 其他块在拖拽过程中的状态 */
.block-wrapper.has-dragging {
  transition: transform 0.15s ease, margin 0.15s ease;
}

/* 拖拽手柄 */
.block-handle:active {
  cursor: grabbing;
}

/* 拖拽位置指示器 */
.drag-indicator {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 100;
  pointer-events: none;
}

.drag-indicator.before {
  top: 0;
  transform: translateY(-50%);
}

.drag-indicator.after {
  bottom: 0;
  transform: translateY(50%);
}

.drag-indicator.child {
  inset: 0;
  transform: none;
}

.drag-indicator .indicator-text {
  display: none;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 8px;
  background: #1890ff;
  color: white;
  font-size: 11px;
  border-radius: 4px;
  white-space: nowrap;
}

.drag-indicator:hover .indicator-text {
  display: block;
}

/* 拖拽目标 - 上方/下方位置 */
.block-wrapper.is-drag-over.drag-before::before,
.block-wrapper.is-drag-over.drag-after::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 3px;
  background: #1890ff;
  border-radius: 2px;
  pointer-events: none;
  z-index: 10;
  box-shadow: 0 0 8px rgba(24, 144, 255, 0.5);
}

.block-wrapper.is-drag-over.drag-before::before {
  top: -3px;
}

.block-wrapper.is-drag-over.drag-after::before {
  bottom: -3px;
}

/* 拖拽目标 - 作为子块 */
.block-wrapper.is-drag-over.drag-child {
  background: rgba(24, 144, 255, 0.15);
  border-radius: 4px;
  box-shadow: inset 0 0 0 2px #1890ff;
}

.block-wrapper.is-drag-over.drag-child::before {
  display: none;
}

.block {
  min-height: 28px;
  line-height: 1.6;
}

.block-content {
  outline: none;
  min-height: 1em;
  word-break: break-word;
  white-space: pre-wrap;
}

/* 只有激活且为空时才显示占位符 */
.block-wrapper.is-focused .block-content:empty::before {
  content: attr(data-placeholder);
  color: #bfbfbf;
  pointer-events: none;
}

/* 标题样式 */
.block-h1 .block-content { font-size: 28px; font-weight: 600; margin: 16px 0 8px; }
.block-h2 .block-content { font-size: 24px; font-weight: 600; margin: 14px 0 7px; }
.block-h3 .block-content { font-size: 20px; font-weight: 600; margin: 12px 0 6px; }
.block-h4 .block-content { font-size: 18px; font-weight: 600; margin: 10px 0 5px; }
.block-h5 .block-content { font-size: 16px; font-weight: 600; margin: 8px 0 4px; }
.block-h6 .block-content { font-size: 14px; font-weight: 600; margin: 6px 0 3px; }

/* 引用块 */
.block-quote {
  border-left: 3px solid #d9d9d9;
  padding-left: 16px;
  color: #595959;
  margin: 8px 0;
}

/* 代码块 */
.block-code {
  background: #f5f5f5;
  border-radius: 6px;
  margin: 8px 0;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #e8e8e8;
  border-bottom: 1px solid #d9d9d9;
}

.code-language {
  border: none;
  background: transparent;
  font-size: 12px;
  color: #666;
  cursor: pointer;
}

.code-language-label {
  font-size: 12px;
  color: #666;
}

.code-content {
  padding: 12px 16px;
  font-family: 'SF Mono', Monaco, 'Andale Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  tab-size: 2;
}

/* 高亮块 */
.block-callout {
  display: flex;
  padding: 12px 16px;
  border-radius: 6px;
  margin: 8px 0;
}

.callout-icon {
  margin-right: 12px;
  font-size: 18px;
}

.callout-content {
  flex: 1;
}

.callout-info { background: #e6f7ff; border-left: 3px solid #1890ff; }
.callout-success { background: #f6ffed; border-left: 3px solid #52c41a; }
.callout-warning { background: #fff7e6; border-left: 3px solid #fa8c16; }
.callout-error { background: #fff2f0; border-left: 3px solid #ff4d4f; }
.callout-tip { background: #f9f0ff; border-left: 3px solid #722ed1; }

/* 列表 */
.block-list {
  margin: 4px 0;
  padding-left: 0;
  list-style: none;
}

.list-item {
  display: flex;
  align-items: flex-start;
  margin: 2px 0;
}

.list-marker {
  margin-right: 8px;
  color: #595959;
}

/* 任务列表 */
.task-item {
  display: flex;
  align-items: flex-start;
  margin: 4px 0;
}

.task-checkbox {
  margin-right: 8px;
  margin-top: 4px;
  cursor: pointer;
}

.task-item.is-completed .block-content {
  text-decoration: line-through;
  color: #8c8c8c;
}

/* 图片 */
.block-image {
  margin: 12px 0;
  text-align: center;
}

.block-image img {
  max-width: 100%;
  border-radius: 4px;
}

.image-caption {
  margin-top: 8px;
  font-size: 13px;
  color: #8c8c8c;
  text-align: center;
}

/* 分割线 */
.block-divider {
  border: none;
  border-top: 1px solid #e8e8e8;
  margin: 16px 0;
}

/* 表格 */
.block-table {
  overflow-x: auto;
  margin: 12px 0;
}

.block-table table {
  width: 100%;
  border-collapse: collapse;
}

.block-table td {
  border: 1px solid #d9d9d9;
  padding: 8px 12px;
  min-width: 80px;
}

.block-table td:focus {
  outline: 2px solid #1890ff;
  outline-offset: -2px;
}

/* 折叠块 */
.block-toggle {
  margin: 8px 0;
}

.toggle-header {
  display: flex;
  align-items: flex-start;
  cursor: pointer;
}

.toggle-icon {
  margin-right: 8px;
  color: #595959;
  font-size: 12px;
}

.toggle-content {
  margin-left: 20px;
  padding-left: 12px;
  border-left: 1px solid #e8e8e8;
}

/* 文本块 */
.block-text {
  margin: 4px 0;
}
</style>

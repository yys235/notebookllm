<template>
  <Teleport to="body">
    <Transition name="slash-command-fade">
      <div
        v-if="state.active"
        class="slash-command-menu"
        :style="menuStyle"
        ref="menuRef"
      >
        <div class="slash-command-menu__header">
          <span class="slash-command-menu__title">基础块</span>
        </div>
        <div class="slash-command-menu__list">
          <div
            v-for="(command, index) in state.filteredCommands"
            :key="command.title"
            class="slash-command-menu__item"
            :class="{ 'is-selected': index === state.selectedIndex }"
            @click="handleSelect(command)"
            @mouseenter="handleMouseEnter(index)"
          >
            <div class="slash-command-menu__item-icon">
              <span class="icon-text">{{ command.icon || command.title[0] }}</span>
            </div>
            <div class="slash-command-menu__item-content">
              <div class="slash-command-menu__item-title">{{ command.title }}</div>
              <div class="slash-command-menu__item-description">{{ command.description }}</div>
            </div>
          </div>
        </div>
        <div class="slash-command-menu__footer">
          <span class="slash-command-menu__hint">
            <kbd>↑</kbd> <kbd>↓</kbd> 导航
            <kbd>Enter</kbd> 选择
            <kbd>Esc</kbd> 关闭
          </span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import type { Editor } from '@tiptap/vue-3'
import {
  subscribe,
  executeCommand,
  type SlashCommandState,
  type SlashCommand
} from '../extensions/SlashCommand'

// Props
interface Props {
  editor: Editor | null
}

const props = defineProps<Props>()

// Refs
const menuRef = ref<HTMLElement | null>(null)

// State
const state = reactive<SlashCommandState>({
  active: false,
  query: '',
  range: null,
  filteredCommands: [],
  selectedIndex: 0
})

// Position
const position = reactive({
  top: 0,
  left: 0
})

// 计算菜单位置样式
const menuStyle = computed(() => ({
  top: `${position.top}px`,
  left: `${position.left}px`
}))

// 计算菜单位置
function updatePosition() {
  if (!props.editor || !state.active) return

  const { view } = props.editor
  const { from } = view.state.selection

  // 获取光标位置的坐标
  const coords = view.coordsAtPos(from)

  // 创建菜单元素来获取其尺寸
  const menuWidth = 280
  const menuHeight = 300

  // 计算位置
  let top = coords.bottom + 8
  let left = coords.left

  // 确保菜单不超出视口
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight

  // 水平方向
  if (left + menuWidth > viewportWidth - 16) {
    left = viewportWidth - menuWidth - 16
  }
  if (left < 16) {
    left = 16
  }

  // 垂直方向
  if (top + menuHeight > viewportHeight - 16) {
    // 显示在光标上方
    top = coords.top - menuHeight - 8
    if (top < 16) {
      top = 16
    }
  }

  position.top = top
  position.left = left
}

// 处理选择命令
function handleSelect(command: SlashCommand) {
  if (props.editor) {
    executeCommand(command, props.editor)
  }
}

// 处理鼠标进入
function handleMouseEnter(index: number) {
  state.selectedIndex = index
}

// 滚动到选中项
function scrollToSelected() {
  nextTick(() => {
    if (!menuRef.value) return

    const selectedItem = menuRef.value.querySelector('.is-selected')
    if (selectedItem) {
      selectedItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  })
}

// 订阅状态变化
let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = subscribe((event) => {
    state.active = event.state.active
    state.query = event.state.query
    state.range = event.state.range
    state.filteredCommands = event.state.filteredCommands
    state.selectedIndex = event.state.selectedIndex

    if (event.type === 'open' || event.type === 'update') {
      updatePosition()
      scrollToSelected()
    }
  })
})

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe()
  }
})

// 监听选中索引变化，滚动到可见区域
watch(() => state.selectedIndex, scrollToSelected)
</script>

<style scoped lang="scss">
.slash-command-menu {
  position: fixed;
  z-index: 10000;
  width: 280px;
  max-height: 360px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;

  &__header {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
  }

  &__title {
    font-size: 12px;
    font-weight: 500;
    color: #8c8c8c;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  &__list {
    max-height: 260px;
    overflow-y: auto;
    padding: 4px 0;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background: #d9d9d9;
      border-radius: 3px;

      &:hover {
        background: #bfbfbf;
      }
    }
  }

  &__item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    cursor: pointer;
    transition: background-color 0.15s ease;

    &:hover,
    &.is-selected {
      background-color: #f5f5f5;
    }

    &.is-selected {
      background-color: #e6f7ff;
    }
  }

  &__item-icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fafafa;
    border: 1px solid #f0f0f0;
    border-radius: 6px;
    margin-right: 12px;
    flex-shrink: 0;
  }

  &__item-content {
    flex: 1;
    min-width: 0;
  }

  &__item-title {
    font-size: 14px;
    font-weight: 500;
    color: #262626;
    margin-bottom: 2px;
  }

  &__item-description {
    font-size: 12px;
    color: #8c8c8c;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__footer {
    padding: 8px 12px;
    border-top: 1px solid #f0f0f0;
    background: #fafafa;
  }

  &__hint {
    font-size: 11px;
    color: #8c8c8c;

    kbd {
      display: inline-block;
      padding: 2px 5px;
      font-size: 10px;
      font-family: inherit;
      line-height: 1;
      color: #595959;
      background-color: #fff;
      border: 1px solid #d9d9d9;
      border-radius: 3px;
      box-shadow: 0 1px 0 rgba(0, 0, 0, 0.05);
      margin: 0 2px;
    }
  }
}

.icon-text {
  font-size: 14px;
  font-weight: 600;
  color: #1890ff;
}

// 过渡动画
.slash-command-fade-enter-active,
.slash-command-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.slash-command-fade-enter-from,
.slash-command-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

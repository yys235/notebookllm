<script setup lang="ts">
/**
 * 斜杠命令菜单组件
 */
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { slashCommands, commandCategories } from '../commands/slashCommands'
import type { SlashCommand, SlashCommandCategory } from '../types'

const props = defineProps<{
  visible: boolean
  query: string
  position: { x: number; y: number }
}>()

const emit = defineEmits<{
  (e: 'select', command: SlashCommand): void
  (e: 'close'): void
}>()

// 当前选中的索引
const selectedIndex = ref(0)

// 当前选中的分类
const selectedCategory = ref<SlashCommandCategory | 'all'>('all')

// 过滤后的命令
const filteredCommands = computed(() => {
  let commands = slashCommands

  // 按分类过滤
  if (selectedCategory.value !== 'all') {
    commands = commands.filter(cmd => cmd.category === selectedCategory.value)
  }

  // 按关键词过滤
  if (props.query.trim()) {
    const query = props.query.toLowerCase()
    commands = commands.filter(cmd => {
      const titleMatch = cmd.title.toLowerCase().includes(query)
      const keywordMatch = cmd.keywords?.some(k => k.toLowerCase().includes(query))
      const idMatch = cmd.id.toLowerCase().includes(query)
      return titleMatch || keywordMatch || idMatch
    })
  }

  return commands
})

// 重置选中索引
watch(() => props.query, () => {
  selectedIndex.value = 0
})

watch(() => props.visible, (visible) => {
  if (visible) {
    selectedIndex.value = 0
    selectedCategory.value = 'all'
  }
})

// 键盘导航
function handleKeydown(event: KeyboardEvent) {
  if (!props.visible) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, filteredCommands.value.length - 1)
      scrollToSelected()
      break

    case 'ArrowUp':
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      scrollToSelected()
      break

    case 'Enter':
      event.preventDefault()
      {
        const cmd = filteredCommands.value[selectedIndex.value]
        if (cmd) {
          selectCommand(cmd)
        }
      }
      break

    case 'Escape':
      event.preventDefault()
      emit('close')
      break

    case 'Tab':
      event.preventDefault()
      {
        // 切换分类
        const categories: (SlashCommandCategory | 'all')[] = ['all', 'basic', 'list', 'media', 'structure', 'insert']
        const currentIdx = categories.indexOf(selectedCategory.value)
        const nextIdx = event.shiftKey
          ? (currentIdx - 1 + categories.length) % categories.length
          : (currentIdx + 1) % categories.length
        const nextCategory = categories[nextIdx]
        if (nextCategory) {
          selectedCategory.value = nextCategory
        }
        selectedIndex.value = 0
      }
      break
  }
}

// 滚动到选中项
function scrollToSelected() {
  nextTick(() => {
    const container = document.querySelector('.slash-menu-list')
    const selected = container?.querySelector('.command-item.is-selected')
    if (selected && container) {
      selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  })
}

// 选择命令
function selectCommand(command: SlashCommand) {
  emit('select', command)
}

// 选择分类
function selectCategory(category: SlashCommandCategory | 'all') {
  selectedCategory.value = category
  selectedIndex.value = 0
}

// 监听键盘事件
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// 获取分类图标
function getCategoryIcon(category: SlashCommandCategory | 'all'): string {
  if (category === 'all') return '☰'
  const cat = commandCategories.find(c => c.id === category)
  return cat?.icon || '•'
}

function getCategoryName(category: SlashCommandCategory | 'all'): string {
  if (category === 'all') return '全部'
  const cat = commandCategories.find(c => c.id === category)
  return cat?.name || category
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slash-menu">
      <div
        v-if="visible && filteredCommands.length > 0"
        class="slash-menu"
        :style="{ left: `${position.x}px`, top: `${position.y}px` }"
      >
        <!-- 分类标签 -->
        <div class="slash-menu-categories">
          <button
            v-for="cat in (['all', ...commandCategories.map(c => c.id)] as const)"
            :key="cat"
            class="category-tab"
            :class="{ 'is-active': selectedCategory === cat }"
            @click="selectCategory(cat)"
          >
            <span class="category-icon">{{ getCategoryIcon(cat) }}</span>
            <span class="category-name">{{ getCategoryName(cat) }}</span>
          </button>
        </div>

        <!-- 搜索提示 -->
        <div v-if="query" class="slash-menu-hint">
          搜索: <span class="query-text">{{ query }}</span>
        </div>

        <!-- 命令列表 -->
        <div class="slash-menu-list">
          <div
            v-for="(command, index) in filteredCommands"
            :key="command.id"
            class="command-item"
            :class="{ 'is-selected': index === selectedIndex }"
            @click="selectCommand(command)"
            @mouseenter="selectedIndex = index"
          >
            <span class="command-icon">{{ command.icon || '•' }}</span>
            <div class="command-info">
              <span class="command-title">{{ command.title }}</span>
              <span v-if="command.description" class="command-desc">{{ command.description }}</span>
            </div>
            <span class="command-category-tag">{{ getCategoryName(command.category) }}</span>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="filteredCommands.length === 0" class="slash-menu-empty">
          <span class="empty-icon">🔍</span>
          <span>没有找到匹配的命令</span>
        </div>

        <!-- 底部提示 -->
        <div class="slash-menu-footer">
          <span><kbd>↑↓</kbd> 导航</span>
          <span><kbd>Enter</kbd> 选择</span>
          <span><kbd>Tab</kbd> 切换分类</span>
          <span><kbd>Esc</kbd> 关闭</span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.slash-menu {
  position: fixed;
  z-index: 1000;
  min-width: 320px;
  max-width: 400px;
  max-height: 400px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.slash-menu-categories {
  display: flex;
  padding: 8px 12px;
  gap: 4px;
  border-bottom: 1px solid #f0f0f0;
  overflow-x: auto;
}

.category-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  background: transparent;
  border-radius: 4px;
  font-size: 12px;
  color: #595959;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.category-tab:hover {
  background: #f5f5f5;
}

.category-tab.is-active {
  background: #e6f7ff;
  color: #1890ff;
}

.category-icon {
  font-size: 14px;
}

.slash-menu-hint {
  padding: 8px 12px;
  font-size: 12px;
  color: #8c8c8c;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.query-text {
  color: #1890ff;
  font-weight: 500;
}

.slash-menu-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.command-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.command-item:hover,
.command-item.is-selected {
  background: #f5f5f5;
}

.command-item.is-selected {
  background: #e6f7ff;
}

.command-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  border-radius: 6px;
  margin-right: 12px;
  font-size: 16px;
}

.command-info {
  flex: 1;
  min-width: 0;
}

.command-title {
  display: block;
  font-size: 14px;
  color: #1a1a1a;
  font-weight: 500;
}

.command-desc {
  display: block;
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-category-tag {
  font-size: 11px;
  color: #8c8c8c;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 8px;
}

.slash-menu-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: #8c8c8c;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.slash-menu-footer {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  border-top: 1px solid #f0f0f0;
  font-size: 11px;
  color: #8c8c8c;
}

.slash-menu-footer kbd {
  display: inline-block;
  padding: 2px 5px;
  background: #f5f5f5;
  border-radius: 3px;
  font-family: inherit;
  font-size: 11px;
}

/* 过渡动画 */
.slash-menu-enter-active,
.slash-menu-leave-active {
  transition: all 0.15s ease;
}

.slash-menu-enter-from,
.slash-menu-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

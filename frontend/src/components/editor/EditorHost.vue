<script setup lang="ts">
import { ref, computed, watch, provide, onMounted, onBeforeUnmount, shallowRef } from 'vue'
import type { EditorType } from '@/plugins/core/types'
import { useEditorStore } from '@/stores/editor'
import { PluginManager } from '@/plugins/core/PluginManager'
import TiptapEditor from '@/components/TiptapEditor.vue'
import FeishuDocsEditor from '@/plugins/feishu-docs/FeishuDocsEditor.vue'

interface Props {
  modelValue: string
  placeholder?: string
  editable?: boolean
  editorType?: EditorType
  // 笔记元信息
  author?: string
  createdAt?: string
  updatedAt?: string
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '开始编写...',
  editable: true,
  editorType: 'docx',
  author: '',
  createdAt: '',
  updatedAt: '',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'ready'): void
  (e: 'change', value: string): void
}>()

const editorStore = useEditorStore()
const currentEditor = shallowRef<any>(null)
const isLoading = ref(false)
const loadError = ref<string | null>(null)

// Internal content for v-model handling
const internalContent = ref(props.modelValue)

// Provide editor context for child components
provide('editorStore', editorStore)
provide('editable', computed(() => props.editable))
provide('editorType', computed(() => props.editorType))

/**
 * Load editor component based on type
 * For 'docx' type, directly use TiptapEditor
 * For 'feishu-docs' type, use FeishuDocsEditor (new block-based editor)
 * For other types, use PluginManager to load the plugin
 */
async function loadEditor(type: EditorType) {
  isLoading.value = true
  loadError.value = null

  try {
    // For docx type, use TiptapEditor directly (simplified version)
    if (type === 'docx') {
      currentEditor.value = TiptapEditor
      editorStore.setActivePlugin(type)
      return
    }

    // For feishu-docs type, use FeishuDocsEditor (new block-based editor)
    if (type === 'feishu-docs' || type === 'docx-blocks') {
      currentEditor.value = FeishuDocsEditor
      editorStore.setActivePlugin(type)
      return
    }

    // For other editor types, try to load via PluginManager
    const plugin = await PluginManager.loadPlugin(type)
    if (plugin && plugin.component) {
      currentEditor.value = plugin.component
      editorStore.setActivePlugin(type)
    } else {
      // Fallback to TiptapEditor if plugin not found
      console.warn(`[EditorHost] Plugin "${type}" not found, falling back to docx editor`)
      currentEditor.value = TiptapEditor
      editorStore.setActivePlugin('docx')
    }
  } catch (error) {
    console.error('[EditorHost] Failed to load editor plugin:', error)
    loadError.value = `Failed to load editor: ${type}`
    // Fallback to TiptapEditor on error
    currentEditor.value = TiptapEditor
    editorStore.setActivePlugin('docx')
  } finally {
    isLoading.value = false
  }
}

/**
 * Handle content changes from child editor
 */
function handleContentUpdate(value: string) {
  internalContent.value = value
  emit('update:modelValue', value)
  emit('change', value)
}

// Initialize editor on mount
onMounted(() => {
  editorStore.setEditable(props.editable)
  editorStore.initialize()
  loadEditor(props.editorType)
})

// Watch for editor type changes
watch(() => props.editorType, (newType) => {
  if (newType !== editorStore.activePlugin) {
    loadEditor(newType)
  }
})

// Watch for editable prop changes
watch(() => props.editable, (newEditable) => {
  editorStore.setEditable(newEditable)
})

// Watch for external modelValue changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== internalContent.value) {
    internalContent.value = newValue
  }
})

// Cleanup on unmount
onBeforeUnmount(() => {
  editorStore.reset()
})

// Expose methods for parent components
defineExpose({
  editorStore,
  currentEditor,
  isLoading,
  loadError,
  loadEditor,
})
</script>

<template>
  <div class="editor-host">
    <!-- Loading state -->
    <div v-if="isLoading" class="editor-loading">
      <div class="loading-spinner"></div>
      <span class="loading-text">Loading editor...</span>
    </div>

    <!-- Error state -->
    <div v-else-if="loadError" class="editor-error">
      <span class="error-icon">!</span>
      <span class="error-text">{{ loadError }}</span>
      <button @click="loadEditor(editorType)" class="retry-btn">
        Retry
      </button>
    </div>

    <!-- Editor component -->
    <component
      v-else-if="currentEditor"
      :is="currentEditor"
      v-model="internalContent"
      :placeholder="placeholder"
      :editable="editable"
      :author="author"
      :created-at="createdAt"
      :updated-at="updatedAt"
      @update:model-value="handleContentUpdate"
    />

    <!-- Fallback when no editor is loaded -->
    <div v-else class="editor-empty">
      <span>No editor available</span>
    </div>
  </div>
</template>

<style scoped>
.editor-host {
  width: 100%;
  min-height: 400px;
  position: relative;
}

.editor-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  gap: 16px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e8e8e8;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  color: #8c8c8c;
  font-size: 14px;
}

.editor-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 8px;
  gap: 12px;
}

.error-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ff4d4f;
  color: white;
  border-radius: 50%;
  font-size: 20px;
  font-weight: bold;
}

.error-text {
  color: #cf1322;
  font-size: 14px;
}

.retry-btn {
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #40a9ff;
}

.editor-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: #fafafa;
  border: 1px dashed #d9d9d9;
  border-radius: 8px;
  color: #8c8c8c;
}
</style>

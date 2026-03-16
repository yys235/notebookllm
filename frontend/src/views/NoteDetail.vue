<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  ShareAltOutlined,
  SaveOutlined,
  DeleteOutlined,
  EditOutlined,
  CloseOutlined,
  CheckOutlined,
} from '@ant-design/icons-vue'
import { noteApi } from '@/api/notes'
import EditorHost from '@/components/editor/EditorHost.vue'
import ShareModal from '@/components/ShareModal.vue'
import type { EditorType } from '@/plugins/core/types'

const router = useRouter()
const route = useRoute()

// ========== 草稿自动保存 ==========
const DRAFT_KEY_PREFIX = 'note_draft_'
let draftSaveTimer: ReturnType<typeof setTimeout> | null = null

function getDraftKey(id: string) {
  return `${DRAFT_KEY_PREFIX}${id}`
}

function saveDraft() {
  if (!isEditing.value) return
  const id = isNew.value ? 'new' : noteId.value
  if (!id) return

  const draft = {
    title: title.value,
    content: content.value,
    isPinned: isPinned.value,
    visibility: visibility.value,
    editorType: editorType.value,
    timestamp: Date.now(),
  }
  localStorage.setItem(getDraftKey(id), JSON.stringify(draft))
}

function loadDraft(id: string): boolean {
  const key = getDraftKey(id)
  const saved = localStorage.getItem(key)
  if (!saved) return false

  try {
    const draft = JSON.parse(saved)
    // Only restore if draft is less than 24 hours old
    if (Date.now() - draft.timestamp < 24 * 60 * 60 * 1000) {
      title.value = draft.title || ''
      content.value = draft.content || '<p></p>'
      isPinned.value = draft.isPinned || false
      visibility.value = draft.visibility || 'private'
      if (draft.editorType) {
        loadedEditorType.value = draft.editorType
      }
      return true
    }
  } catch (e) {
    console.error('Failed to load draft:', e)
  }
  return false
}

function clearDraft(id: string) {
  localStorage.removeItem(getDraftKey(id))
}

// 监听内容变化，自动保存草稿
watch([title, content], () => {
  if (!isEditing.value) return
  if (draftSaveTimer) clearTimeout(draftSaveTimer)
  draftSaveTimer = setTimeout(() => {
    saveDraft()
  }, 2000)
})

// 页面加载时检查草稿
onMounted(() => {
  const id = isNew.value ? 'new' : noteId.value
  if (id) {
    // 检查是否有草稿
    const hasDraft = loadDraft(id)
    if (hasDraft) {
      Modal.confirm({
        title: '发现未保存的草稿',
        content: '检测到您之前有未保存的编辑内容，是否恢复？',
        okText: '恢复',
        cancelText: '放弃',
        onOk: () => {
          isEditing.value = true
          message.success('草稿已恢复')
        },
        onCancel: () => {
          clearDraft(id)
        },
      })
    }
  }
})

// 页面卸载时清理定时器
onMounted(() => {
  return () => {
    if (draftSaveTimer) {
      clearTimeout(draftSaveTimer)
    }
  }
})

const isNew = computed(() => route.name === 'NoteNew' || route.params.id === 'new')
const title = ref('')
const content = ref('<p></p>')
const isPinned = ref(false)
const visibility = ref<'private' | 'public'>('private')
const noteId = computed(() => route.params.id as string)
const saving = ref(false)
const shareModalVisible = ref(false)
const isEditing = ref(false) // Default to read-only mode

// 笔记元信息
const noteAuthor = ref('')
const noteCreatedAt = ref('')
const noteUpdatedAt = ref('')

// Editor type - read from query param, note data, or use default
const loadedEditorType = ref<EditorType>('docx')

const editorType = computed<EditorType>(() => {
  // First priority: URL query param (for new notes)
  const type = route.query.type as string
  if (type && ['docx', 'docx-blocks', 'feishu-docs', 'excel', 'mindmap', 'flowchart'].includes(type)) {
    return type as EditorType
  }
  // Second priority: loaded from note data (only if not default 'docx')
  if (loadedEditorType.value) {
    return loadedEditorType.value
  }
  // Default
  return 'docx'
})

// 加载笔记
async function loadNote(id: string) {
  // 验证 ID 是否有效
  if (!id || id === 'new' || id === 'undefined') {
    console.log('跳过加载笔记，ID 无效:', id)
    return
  }

  try {
    const note = await noteApi.getNote(id)
    if (note) {
      title.value = note.title
      content.value = note.content || '<p></p>'
      // Handle both camelCase and snake_case
      isPinned.value = note.isPinned ?? note.is_pinned ?? false
      visibility.value = note.visibility || 'private'
      // 保存元信息
      noteAuthor.value = note.userId || note.user_id || ''
      noteCreatedAt.value = note.createdAt || note.created_at || ''
      noteUpdatedAt.value = note.updatedAt || note.updated_at || ''
      // Load editor type from note
      loadedEditorType.value = (note.editorType || note.editor_type || 'docx') as EditorType
    }
  } catch (error: any) {
    message.error(error.message || 'Failed to load note')
    router.push('/notes')
  }
}

// 监听路由参数变化
watch(
  () => route.params.id,
  (newId) => {
    // Don't load if we're on the "new note" route or id is invalid
    if (route.name === 'NoteNew' || !newId || newId === 'new' || newId === 'undefined') {
      console.log('Skipping note load, route:', route.name, 'id:', newId)
      // New notes should be in edit mode
      isEditing.value = true
      return
    }
    loadNote(newId as string)
  },
  { immediate: true }
)

// New notes should default to edit mode
watch(isNew, (isNewNote) => {
  if (isNewNote) {
    isEditing.value = true
  }
}, { immediate: true })

function startEditing() {
  isEditing.value = true
}

function cancelEditing() {
  isEditing.value = false
  // Reload original content if canceling edit
  if (!isNew.value && noteId.value) {
    loadNote(noteId.value)
  }
}

async function finishEditing() {
  // 先保存再退出
  if (!title.value.trim()) {
    message.warning('请输入标题')
    return
  }

  saving.value = true
  try {
    if (isNew.value) {
      const note = await noteApi.createNote({
        title: title.value,
        content: content.value || '<p></p>',
        isPinned: isPinned.value,
        visibility: visibility.value,
        editorType: editorType.value,
      })

      if (note && note.id) {
        message.success('笔记已保存')
        isEditing.value = false
        clearDraft('new') // Clear draft for new notes
        router.replace(`/notes/${note.id}`)
      } else {
        message.error('保存失败')
      }
    } else {
      await noteApi.updateNote(noteId.value, {
        title: title.value,
        content: content.value || '<p></p>',
        isPinned: isPinned.value,
        visibility: visibility.value,
        editorType: editorType.value,
      })
      message.success('笔记已保存')
      isEditing.value = false
      clearDraft(noteId.value) // Clear draft after successful save
    }
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function saveNote() {
  if (!title.value.trim()) {
    message.warning('请输入标题')
    return
  }

  saving.value = true
  try {
    if (isNew.value) {
      const note = await noteApi.createNote({
        title: title.value,
        content: content.value || '<p></p>',
        isPinned: isPinned.value,
        visibility: visibility.value,
        editorType: editorType.value,
      })

      if (note && note.id) {
        message.success('笔记已创建')
        clearDraft('new') // Clear draft for new notes
        router.replace(`/notes/${note.id}`)
      } else {
        message.error('创建笔记失败')
      }
    } else {
      await noteApi.updateNote(route.params.id as string, {
        title: title.value,
        content: content.value || '<p></p>',
        isPinned: isPinned.value,
        visibility: visibility.value,
        editorType: editorType.value,
      })
      message.success('笔记已保存')
      clearDraft(route.params.id as string) // Clear draft after successful save
    }
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteNote() {
  Modal.confirm({
    title: '删除笔记',
    content: '确定要删除这篇笔记吗？',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await noteApi.deleteNote(route.params.id as string)
        message.success('笔记已删除')
        router.push('/notes')
      } catch (error: any) {
        message.error(error.message || '删除失败')
      }
    },
  })
}

function goBack() {
  router.push('/notes')
}

// Toggle pinned status (works in both read and edit mode)
async function togglePinned() {
  if (isNew.value) return // Can't toggle pinned for new notes before saving

  try {
    await noteApi.updateNote(noteId.value, { isPinned: isPinned.value })
    message.success(isPinned.value ? '已置顶' : '已取消置顶')
  } catch (error: any) {
    // Revert on error
    isPinned.value = !isPinned.value
    message.error(error.message || '操作失败')
  }
}
</script>

<template>
  <a-layout class="note-detail-layout">
    <!-- Header -->
    <a-layout-header class="header">
      <div class="header-content">
        <a-button type="text" @click="goBack">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </a-button>

        <div class="header-actions">
          <template v-if="isEditing">
            <a-switch
              v-model:checked="isPinned"
              checked-children="置顶"
              un-checked-children="普通"
            />
            <a-button @click="shareModalVisible = true">
              <template #icon><ShareAltOutlined /></template>
              分享
            </a-button>
            <a-button type="primary" :loading="saving" @click="saveNote">
              <template #icon><SaveOutlined /></template>
              保存
            </a-button>
            <a-button v-if="!isNew" type="default" :loading="saving" @click="finishEditing">
              <template #icon><CheckOutlined /></template>
              完成
            </a-button>
            <a-button v-if="!isNew" @click="cancelEditing">
              <template #icon><CloseOutlined /></template>
              取消
            </a-button>
            <a-button v-if="!isNew" danger @click="deleteNote">
              <template #icon><DeleteOutlined /></template>
              删除
            </a-button>
          </template>
          <template v-else>
            <a-switch
              v-model:checked="isPinned"
              checked-children="置顶"
              un-checked-children="普通"
              @change="togglePinned"
            />
            <a-button @click="shareModalVisible = true">
              <template #icon><ShareAltOutlined /></template>
              分享
            </a-button>
            <a-button type="primary" @click="startEditing">
              <template #icon><EditOutlined /></template>
              编辑
            </a-button>
            <a-button danger @click="deleteNote">
              <template #icon><DeleteOutlined /></template>
              删除
            </a-button>
          </template>
        </div>
      </div>
    </a-layout-header>

    <!-- Content -->
    <a-layout-content class="content">
      <div class="note-editor" :class="{ 'read-only': !isEditing }">
        <a-input
          v-model:value="title"
          placeholder="笔记标题..."
          size="large"
          :bordered="false"
          class="note-title-input"
          :readonly="!isEditing"
        />
        <EditorHost
          v-memo="[content, isEditing, editorType]"
          v-model="content"
          placeholder="开始编写笔记，支持 Markdown 语法..."
          :editable="isEditing"
          :editor-type="editorType"
          :created-at="noteCreatedAt"
          :updated-at="noteUpdatedAt"
        />
      </div>
    </a-layout-content>

    <!-- Share Modal -->
    <ShareModal
      v-model:open="shareModalVisible"
      :note-id="noteId"
      :note-visibility="visibility"
      :note-title="title || '未命名笔记'"
    />
  </a-layout>
</template>

<style scoped>
.note-detail-layout {
  min-height: 100vh;
  background: #f5f5f5;
}

.header {
  background: white;
  padding: 0 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  height: 64px;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.content {
  padding: 2rem;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.note-editor {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.note-editor.read-only {
  background: #fafafa;
}

.note-title-input {
  font-size: 1.5rem;
  font-weight: bold;
}

.note-title-input :deep(.ant-input) {
  font-size: 1.5rem;
  font-weight: bold;
}

.note-title-input[readonly] :deep(.ant-input) {
  cursor: default;
  color: #1a1a1a;
}
</style>

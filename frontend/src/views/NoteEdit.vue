<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  SaveOutlined,
  SendOutlined,
  MoreOutlined,
  FileTextOutlined,
  RobotOutlined,
  CloseOutlined,
  LoadingOutlined,
} from '@ant-design/icons-vue'
import EditorHost from '@/components/editor/EditorHost.vue'
import { useNoteStore } from '@/stores/note'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const noteStore = useNoteStore()
const userStore = useUserStore()

// Note state
const isNew = computed(() => route.params.id === 'new')
const noteId = computed(() => route.params.id as string)
const title = ref('')
const content = ref('')
const isPinned = ref(false)
const saving = ref(false)
const lastSaved = ref<Date | null>(null)

// AI Chat state
const chatQuery = ref('')
const chatMessages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([])
const isAiThinking = ref(false)
const showAiPanel = ref(true)

// Source files (mock data)
const sourceFiles = ref([
  { id: '1', title: 'Meeting Notes - Project Alpha', content: 'Discussed timeline and milestones...' },
  { id: '2', title: 'Research - AI Models', content: 'Comparison of LLM architectures...' },
  { id: '3', title: 'Ideas - New Features', content: 'Brainstorming session results...' },
])
const selectedSourceIds = ref<string[]>([])

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  if (!isNew.value) {
    await loadNote(noteId.value)
  }
})

async function loadNote(id: string) {
  try {
    await noteStore.fetchNote(id)
    const note = noteStore.currentNote
    if (note) {
      title.value = note.title
      content.value = note.content
      isPinned.value = note.isPinned
    }
  } catch (error: any) {
    message.error(error.message || 'Failed to load note')
    router.push('/notes')
  }
}

async function saveNote() {
  if (!title.value.trim()) {
    message.warning('Please enter a title')
    return
  }

  saving.value = true
  try {
    if (isNew.value) {
      const note = await noteStore.createNote({
        title: title.value,
        content: content.value,
        isPinned: isPinned.value,
      })
      if (note && note.id) {
        router.replace(`/notes/edit/${note.id}`)
      }
    } else {
      await noteStore.updateNote(noteId.value, {
        title: title.value,
        content: content.value,
        isPinned: isPinned.value,
      })
    }
    lastSaved.value = new Date()
    message.success('Note saved')
  } catch (error: any) {
    message.error(error.message || 'Failed to save note')
  } finally {
    saving.value = false
  }
}

// Auto-save with debounce
let saveTimeout: ReturnType<typeof setTimeout> | null = null
watch([title, content], () => {
  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    if (title.value.trim()) {
      saveNote()
    }
  }, 2000)
})

async function sendAiQuery() {
  if (!chatQuery.value.trim()) {
    return
  }

  // Add user message
  chatMessages.value.push({
    role: 'user',
    content: chatQuery.value,
  })

  const query = chatQuery.value
  chatQuery.value = ''
  isAiThinking.value = true

  try {
    // TODO: Replace with actual AI API call
    // const response = await aiApi.queryNotes({
    //   query,
    //   noteIds: selectedSourceIds.value,
    // })

    // Mock response
    await new Promise((resolve) => setTimeout(resolve, 1500))
    chatMessages.value.push({
      role: 'assistant',
      content: `Based on your notes, here's what I found:\n\n"${query}" is mentioned in several documents. The main points are:\n\n1. Key insight from your notes\n2. Related information from other sources\n3. Additional context you might find useful`,
    })
  } catch (error: any) {
    message.error(error.message || 'AI query failed')
    chatMessages.value.pop()
  } finally {
    isAiThinking.value = false
  }
}

function toggleSourceFile(id: string) {
  const index = selectedSourceIds.value.indexOf(id)
  if (index > -1) {
    selectedSourceIds.value.splice(index, 1)
  } else {
    selectedSourceIds.value.push(id)
  }
}

function toggleAiPanel() {
  showAiPanel.value = !showAiPanel.value
}

function goBack() {
  router.push('/notes')
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault()
    saveNote()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="note-edit-layout">
    <!-- Header -->
    <div class="edit-header">
      <div class="header-left">
        <a-button @click="goBack">
          <template #icon><FileTextOutlined /></template>
        </a-button>
        <a-input
          v-model:value="title"
          placeholder="Note title..."
          class="title-input"
          :bordered="false"
          @blur="saveNote"
        />
      </div>
      <div class="header-right">
        <span v-if="lastSaved" class="last-saved">
          Saved {{ new Date(lastSaved).toLocaleTimeString() }}
        </span>
        <a-switch
          v-model:checked="isPinned"
          checked-children="Pinned"
          un-checked-children="Normal"
          size="small"
          @change="saveNote"
        />
        <a-button type="primary" :loading="saving" @click="saveNote">
          <template #icon><SaveOutlined /></template>
          Save
        </a-button>
        <a-dropdown>
          <a-button>
            <template #icon><MoreOutlined /></template>
          </a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item>Share</a-menu-item>
              <a-menu-item>Duplicate</a-menu-item>
              <a-menu-item danger>Delete</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>

    <!-- Main Content -->
    <div class="edit-content">
      <!-- Left Panel - Source Files -->
      <div class="left-panel" :class="{ collapsed: !showAiPanel }">
        <div class="panel-header">
          <span class="panel-title">Source Files</span>
          <a-button size="small" type="text">
            <template #icon><PlusOutlined /></template>
          </a-button>
        </div>
        <div class="source-files-list">
          <div
            v-for="file in sourceFiles"
            :key="file.id"
            class="source-file-item"
            :class="{ active: selectedSourceIds.includes(file.id) }"
            @click="toggleSourceFile(file.id)"
          >
            <FileTextOutlined class="file-icon" />
            <div class="file-info">
              <div class="file-title">{{ file.title }}</div>
              <div class="file-preview">{{ file.content.substring(0, 50) }}...</div>
            </div>
            <a-checkbox
              :checked="selectedSourceIds.includes(file.id)"
              @click.stop="toggleSourceFile(file.id)"
            />
          </div>
        </div>
        <a-button block class="upload-btn">
          <template #icon><PlusOutlined /></template>
          Upload File
        </a-button>
      </div>

      <!-- Center Panel - Editor -->
      <div class="center-panel">
        <div class="editor-container">
          <EditorHost v-model="content" placeholder="Start writing..." editor-type="docx" />
        </div>
      </div>

      <!-- Right Panel - AI Chat -->
      <div v-if="showAiPanel" class="right-panel">
        <div class="panel-header">
          <span class="panel-title">
            <RobotOutlined /> AI Assistant
          </span>
          <a-button size="small" type="text" @click="toggleAiPanel">
            <template #icon><CloseOutlined /></template>
          </a-button>
        </div>

        <div class="chat-messages">
          <div v-if="chatMessages.length === 0" class="chat-empty">
            <RobotOutlined class="empty-icon" />
            <p>Ask me anything about your notes</p>
            <div class="suggestions">
              <a-tag
                v-for="suggestion in ['Summarize this note', 'Find related notes', 'Extract key points']"
                :key="suggestion"
                @click="chatQuery = suggestion"
              >
                {{ suggestion }}
              </a-tag>
            </div>
          </div>
          <div v-else class="message-list">
            <div
              v-for="(msg, index) in chatMessages"
              :key="index"
              class="message"
              :class="msg.role"
            >
              <div class="message-content">
                <div v-if="msg.role === 'assistant'" class="message-icon">
                  <RobotOutlined />
                </div>
                <div class="message-text">{{ msg.content }}</div>
              </div>
            </div>
            <div v-if="isAiThinking" class="message assistant">
              <div class="message-content">
                <div class="message-icon">
                  <LoadingOutlined spin />
                </div>
                <div class="message-text thinking">Thinking...</div>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <a-input-search
            v-model:value="chatQuery"
            placeholder="Ask AI about your notes..."
            :disabled="isAiThinking"
            @search="sendAiQuery"
          >
            <template #suffix>
              <a-button
                type="primary"
                size="small"
                :disabled="!chatQuery.trim() || isAiThinking"
                @click="sendAiQuery"
              >
                <template #icon><SendOutlined /></template>
              </a-button>
            </template>
          </a-input-search>
        </div>
      </div>

      <!-- Collapsed AI Panel Toggle -->
      <div v-if="!showAiPanel" class="ai-toggle" @click="toggleAiPanel">
        <RobotOutlined />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { PlusOutlined } from '@ant-design/icons-vue'
export default {
  components: { PlusOutlined },
}
</script>

<style scoped>
.note-edit-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: white;
  border-bottom: 1px solid #e8e8e8;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.title-input {
  flex: 1;
  max-width: 500px;
}

.title-input :deep(.ant-input) {
  font-size: 1.25rem;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.last-saved {
  color: #999;
  font-size: 0.875rem;
}

.edit-content {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 360px;
  overflow: hidden;
}

.edit-content:has(.right-panel:not(.show)) {
  grid-template-columns: 280px 1fr;
}

.left-panel {
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-panel.collapsed {
  display: none;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e8e8e8;
}

.panel-title {
  font-weight: 600;
  color: #1a1a1a;
}

.source-files-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.source-file-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.source-file-item:hover {
  background: #f5f5f5;
}

.source-file-item.active {
  background: #e6f0ff;
}

.file-icon {
  color: #666;
  margin-top: 2px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-title {
  font-weight: 500;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview {
  color: #999;
  font-size: 0.75rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-btn {
  margin: 0.5rem;
  border-style: dashed;
}

.center-panel {
  background: white;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.editor-container {
  flex: 1;
  padding: 2rem;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.right-panel {
  background: white;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #999;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  color: #d9d9d9;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 1rem;
}

.suggestions .ant-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.suggestions .ant-tag:hover {
  transform: scale(1.05);
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  display: flex;
}

.message.user .message-content {
  margin-left: auto;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message.assistant .message-content {
  background: #f5f5f5;
}

.message-content {
  display: flex;
  gap: 0.5rem;
  max-width: 85%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
}

.message.user .message-content {
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  border-bottom-left-radius: 4px;
}

.message-icon {
  color: #667eea;
  margin-top: 2px;
}

.message-text {
  flex: 1;
  white-space: pre-wrap;
  line-height: 1.5;
}

.thinking {
  color: #999;
  font-style: italic;
}

.chat-input {
  padding: 1rem;
  border-top: 1px solid #e8e8e8;
}

.ai-toggle {
  position: fixed;
  right: 1rem;
  bottom: 50%;
  transform: translateY(50%);
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transition: all 0.2s;
  z-index: 10;
}

.ai-toggle:hover {
  transform: translateY(50%) scale(1.1);
}

/* Responsive */
@media (max-width: 1200px) {
  .edit-content {
    grid-template-columns: 1fr 360px;
  }

  .left-panel {
    display: none;
  }
}

@media (max-width: 768px) {
  .edit-content {
    grid-template-columns: 1fr;
  }

  .right-panel {
    position: fixed;
    right: 0;
    top: 60px;
    bottom: 0;
    width: 100%;
    max-width: 360px;
    transform: translateX(100%);
    transition: transform 0.3s;
    z-index: 200;
  }

  .right-panel.show {
    transform: translateX(0);
  }

  .edit-header {
    padding: 0.75rem 1rem;
  }

  .header-left .ant-btn {
    display: none;
  }

  .last-saved {
    display: none;
  }
}
</style>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  AppstoreOutlined,
  BarsOutlined,
  ClockCircleOutlined,
  TagOutlined,
  PushpinFilled,
  GlobalOutlined,
  FileTextOutlined,
  TableOutlined,
  ApartmentOutlined,
  BranchesOutlined,
} from '@ant-design/icons-vue'
import { useNoteStore } from '@/stores/note'
import { useUserStore } from '@/stores/user'
import { formatRelativeTime } from '@/utils/date'
import type { EditorType } from '@/plugins/core/types'

const router = useRouter()
const noteStore = useNoteStore()
const userStore = useUserStore()

const searchQuery = ref('')
const selectedTags = ref<string[]>([])
const viewMode = ref<'grid' | 'list'>('list')
const sortBy = ref<'updated' | 'created' | 'title'>('updated')

// Document type selection
const showTypeModal = ref(false)
const selectedDocType = ref<EditorType>('docx')

// Document type options
const docTypes = [
  {
    type: 'feishu-docs' as EditorType,
    name: '块文档',
    description: '块级编辑器，支持斜杠命令、拖拽等',
    icon: FileTextOutlined,
    color: '#1890ff',
    bgColor: '#e6f7ff',
  },
  {
    type: 'docx' as EditorType,
    name: '富文本文档',
    description: '支持 Markdown、图片、代码块等',
    icon: FileTextOutlined,
    color: '#52c41a',
    bgColor: '#f6ffed',
  },
  {
    type: 'excel' as EditorType,
    name: '电子表格',
    description: '数据表格、公式计算',
    icon: TableOutlined,
    color: '#fa8c16',
    bgColor: '#fff7e6',
  },
  {
    type: 'mindmap' as EditorType,
    name: '思维导图',
    description: '脑图、知识结构图',
    icon: ApartmentOutlined,
    color: '#722ed1',
    bgColor: '#f9f0ff',
  },
  {
    type: 'flowchart' as EditorType,
    name: '流程图',
    description: '流程图、架构图',
    icon: BranchesOutlined,
    color: '#eb2f96',
    bgColor: '#fff0f6',
  },
]

// Mock tags - will be replaced with actual data from API
const availableTags = ref<string[]>([
  'work',
  'personal',
  'ideas',
  'meeting',
  'project',
])

const filteredNotes = computed(() => {
  let notes = [...noteStore.notes]

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    notes = notes.filter(
      (note) =>
        note.title.toLowerCase().includes(query) ||
        (note.content || note.preview || '').toLowerCase().includes(query)
    )
  }

  // Filter by tags (mock implementation)
  if (selectedTags.value.length > 0) {
    // TODO: Implement tag filtering when API supports it
  }

  // Sort notes - pinned first, then by selected sort
  notes.sort((a, b) => {
    // Pinned notes first
    const aPinned = a.isPinned ?? a.is_pinned ?? false
    const bPinned = b.isPinned ?? b.is_pinned ?? false
    if (aPinned !== bPinned) {
      return bPinned ? 1 : -1
    }

    // Then by selected sort
    switch (sortBy.value) {
      case 'updated':
        return new Date(b.updatedAt ?? b.updated_at).getTime() - new Date(a.updatedAt ?? a.updated_at).getTime()
      case 'created':
        return new Date(b.createdAt ?? b.created_at).getTime() - new Date(a.createdAt ?? a.created_at).getTime()
      case 'title':
        return a.title.localeCompare(b.title)
      default:
        return 0
    }
  })

  return notes
})

// Helper to check if note is pinned (handles both camelCase and snake_case)
function isNotePinned(note: any): boolean {
  return note.isPinned ?? note.is_pinned ?? false
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  await loadNotes()
})

async function loadNotes() {
  try {
    await noteStore.fetchNotes()
  } catch (error: any) {
    message.error(error.message || 'Failed to load notes')
  }
}

function openNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}

function showCreateNoteModal() {
  showTypeModal.value = true
}

function selectDocType(type: EditorType) {
  selectedDocType.value = type
}

function createNewNote() {
  showTypeModal.value = false
  // Pass editor type as query parameter
  router.push({
    path: '/notes/new',
    query: { type: selectedDocType.value }
  })
}

function toggleViewMode(mode: 'grid' | 'list') {
  viewMode.value = mode
}

function handleTagToggle(tag: string) {
  const index = selectedTags.value.indexOf(tag)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tag)
  }
}

function handleSearch() {
  // Search is handled by computed property
}

function logout() {
  userStore.logout()
  router.push('/login')
}

function goToSettings() {
  router.push('/settings')
}
</script>

<template>
  <a-layout class="notes-layout">
    <!-- Header -->
    <a-layout-header class="header">
      <div class="header-content">
        <div class="logo-section">
          <div class="logo">N</div>
          <h1>NotebookLLM</h1>
        </div>
        <div class="header-actions">
          <a-button @click="goToSettings">
            <template #icon><FilterOutlined /></template>
            Settings
          </a-button>
          <a-button type="primary" @click="showCreateNoteModal">
            <template #icon><PlusOutlined /></template>
            New Note
          </a-button>
          <a-dropdown>
            <a-avatar :size="32" class="user-avatar" style="cursor: pointer;">
              {{ userStore.userName?.charAt(0).toUpperCase() || 'U' }}
            </a-avatar>
            <template #overlay>
              <a-menu>
                <a-menu-item key="logout" @click="logout">
                  <span>Logout</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>
    </a-layout-header>

    <!-- Content -->
    <a-layout-content class="content">
      <!-- Search and Filters -->
      <div class="toolbar">
        <div class="search-section">
          <a-input-search
            v-model:value="searchQuery"
            placeholder="Search your notes..."
            size="large"
            class="search-input"
            @search="handleSearch"
          >
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input-search>
        </div>

        <div class="filter-section">
          <a-radio-group v-model:value="sortBy" button-style="solid">
            <a-radio-button value="updated">Recent</a-radio-button>
            <a-radio-button value="created">Created</a-radio-button>
            <a-radio-button value="title">Title</a-radio-button>
          </a-radio-group>

          <a-button-group>
            <a-button
              :type="viewMode === 'grid' ? 'primary' : 'default'"
              @click="toggleViewMode('grid')"
            >
              <AppstoreOutlined />
            </a-button>
            <a-button
              :type="viewMode === 'list' ? 'primary' : 'default'"
              @click="toggleViewMode('list')"
            >
              <BarsOutlined />
            </a-button>
          </a-button-group>
        </div>
      </div>

      <!-- Tags Filter -->
      <div v-if="availableTags.length > 0" class="tags-section">
        <span class="tags-label">
          <TagOutlined /> Tags:
        </span>
        <a-space wrap>
          <a-tag
            v-for="tag in availableTags"
            :key="tag"
            :color="selectedTags.includes(tag) ? 'blue' : 'default'"
            class="tag-filter"
            @click="handleTagToggle(tag)"
          >
            {{ tag }}
          </a-tag>
        </a-space>
      </div>

      <!-- Notes Display -->
      <a-spin :spinning="noteStore.loading">
        <!-- Grid View -->
        <div v-if="viewMode === 'grid'" class="notes-grid">
          <a-card
            v-for="note in filteredNotes"
            :key="note.id"
            class="note-card"
            :class="{ 'pinned-note': isNotePinned(note) }"
            hoverable
            @click="openNote(note.id)"
          >
            <template #title>
              <div class="card-title">
                <span class="title-text">
                  <PushpinFilled v-if="isNotePinned(note)" class="pinned-icon" />
                  {{ note.title || '无标题' }}
                </span>
              </div>
            </template>

            <p class="note-preview">
              {{ (note.content || note.preview || '').substring(0, 150) }}{{ (note.content || note.preview || '').length > 150 ? '...' : '' }}
            </p>

            <template #actions>
              <span class="note-meta">
                <GlobalOutlined v-if="note.visibility === 'public'" class="public-icon" />
                <ClockCircleOutlined />
                {{ formatRelativeTime(note.updatedAt ?? note.updated_at) }}
              </span>
            </template>
          </a-card>
        </div>

        <!-- List View -->
        <div v-else class="notes-list">
          <a-list
            :data-source="filteredNotes"
            item-layout="horizontal"
          >
            <template #renderItem="{ item }">
              <a-list-item class="note-list-item" :class="{ 'pinned-note': item.isPinned }" @click="openNote(item.id)">
                <a-list-item-meta>
                  <template #title>
                    <span class="list-title">
                      <PushpinFilled v-if="item.isPinned" class="pinned-icon" />
                      {{ item.title || '无标题' }}
                      <GlobalOutlined v-if="item.visibility === 'public'" class="public-icon" />
                    </span>
                  </template>
                  <template #description>
                    <span class="list-preview">
                      {{ (item.content || item.preview || '').substring(0, 100) }}{{ (item.content || item.preview || '').length > 100 ? '...' : '' }}
                    </span>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <span class="list-date">{{ formatRelativeTime(item.updatedAt) }}</span>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </div>

        <!-- Empty State -->
        <a-empty
          v-if="!noteStore.loading && filteredNotes.length === 0"
          class="empty-state"
          :description="searchQuery ? 'No notes found' : 'No notes yet'"
        >
          <a-button v-if="!searchQuery" type="primary" @click="createNewNote">
            Create your first note
          </a-button>
        </a-empty>
      </a-spin>

      <!-- Pagination -->
      <div v-if="filteredNotes.length > 0" class="pagination-section">
        <a-pagination
          :total="filteredNotes.length"
          :page-size="12"
          :show-size-changer="false"
          :show-total="(total: number) => `Total ${total} notes`"
        />
      </div>
    </a-layout-content>

    <!-- Document Type Selection Modal -->
    <a-modal
      v-model:open="showTypeModal"
      title="创建新文档"
      :footer="null"
      width="600px"
      centered
    >
      <div class="doc-type-grid">
        <div
          v-for="docType in docTypes"
          :key="docType.type"
          class="doc-type-card"
          :class="{ 'selected': selectedDocType === docType.type }"
          @click="selectDocType(docType.type)"
        >
          <div class="doc-type-icon" :style="{ backgroundColor: docType.bgColor, color: docType.color }">
            <component :is="docType.icon" />
          </div>
          <div class="doc-type-info">
            <div class="doc-type-name">{{ docType.name }}</div>
            <div class="doc-type-desc">{{ docType.description }}</div>
          </div>
          <div v-if="selectedDocType === docType.type" class="doc-type-check">
            <a-checkbox checked />
          </div>
        </div>
      </div>
      <div class="doc-type-footer">
        <a-button @click="showTypeModal = false">取消</a-button>
        <a-button type="primary" @click="createNewNote">
          <template #icon><PlusOutlined /></template>
          创建文档
        </a-button>
      </div>
    </a-modal>
  </a-layout>
</template>

<style scoped>
.notes-layout {
  min-height: 100vh;
  background: #f5f5f5;
}

.header {
  background: white;
  padding: 0 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 1rem;
}

.logo-section h1 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
}

.content {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.search-section {
  flex: 1;
  min-width: 280px;
}

.search-input {
  max-width: 500px;
}

.filter-section {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.tags-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 8px;
}

.tags-label {
  color: #666;
  font-size: 0.875rem;
  white-space: nowrap;
}

.tag-filter {
  cursor: pointer;
  transition: all 0.2s;
}

.tag-filter:hover {
  transform: scale(1.05);
}

.notes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.note-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  height: 220px;
  display: flex;
  flex-direction: column;
}

.note-card.pinned-note {
  border: 2px solid #faad14;
  background: #fffbe6;
}

.pinned-icon {
  color: #faad14;
  margin-right: 0.25rem;
}

.note-meta {
  color: #999;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.public-icon {
  color: #52c41a;
}

.note-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.note-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.note-preview {
  color: #666;
  flex: 1;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  margin-bottom: 0;
}

.note-date {
  color: #999;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.notes-list {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.note-list-item {
  cursor: pointer;
  padding: 1rem 1.5rem;
  transition: background 0.2s;
}

.note-list-item:hover {
  background: #f5f5f5;
}

.list-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.pinned-icon {
  color: #faad14;
  font-size: 1rem;
}

.pinned-note {
  background: #fffbe6;
  border-left: 3px solid #faad14;
}

.note-meta {
  color: #999;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.public-icon {
  color: #52c41a;
}

.list-preview {
  color: #666;
}

.list-date {
  color: #999;
  font-size: 0.875rem;
}

.empty-state {
  margin: 4rem 0;
}

.pagination-section {
  margin-top: 2rem;
  display: flex;
  justify-content: center;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 1rem;
  }

  .content {
    padding: 1rem;
  }

  .toolbar {
    flex-direction: column;
  }

  .search-section {
    width: 100%;
  }

  .search-input {
    max-width: 100%;
  }

  .filter-section {
    width: 100%;
    justify-content: space-between;
  }

  .notes-grid {
    grid-template-columns: 1fr;
  }

  .logo-section h1 {
    display: none;
  }
}

/* Document Type Selection Modal */
.doc-type-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 16px 0;
}

.doc-type-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.doc-type-card:hover {
  border-color: #1890ff;
  background: #fafafa;
}

.doc-type-card.selected {
  border-color: #1890ff;
  background: #e6f7ff;
}

.doc-type-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.doc-type-info {
  flex: 1;
  min-width: 0;
}

.doc-type-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.doc-type-desc {
  font-size: 13px;
  color: #8c8c8c;
}

.doc-type-check {
  flex-shrink: 0;
}

.doc-type-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e8e8e8;
}

@media (max-width: 600px) {
  .doc-type-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  LockOutlined,
  CopyOutlined,
  CalendarOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue'
import { sharesApi } from '@/api/shares'
import { formatCalendarTime } from '@/utils/date'
import EditorHost from '@/components/editor/EditorHost.vue'
import type { EditorType } from '@/plugins/core/types'

const route = useRoute()
const shareToken = route.params.shareId as string

const note = ref<any>(null)
const shareInfo = ref<any>(null)
const loading = ref(false)
const passwordModalVisible = ref(false)
const password = ref('')
const copied = ref(false)
const noteContent = ref('')

const shareUrl = computed(() => window.location.href)
const formattedDate = computed(() => {
  if (!note.value?.updated_at) return ''
  return formatCalendarTime(note.value.updated_at)
})

// 获取编辑器类型
const editorType = computed<EditorType>(() => {
  const type = note.value?.editor_type || note.value?.editorType
  if (type && ['docx', 'feishu-docs', 'docx-blocks'].includes(type)) {
    return type as EditorType
  }
  return 'feishu-docs' // 默认使用块文档编辑器
})

onMounted(async () => {
  await loadShareInfo()
})

async function loadShareInfo() {
  loading.value = true
  try {
    const info = await sharesApi.getShareLinkInfo(shareToken)
    shareInfo.value = info

    if (!info.is_valid) {
      message.error(info.error || '分享链接无效')
      return
    }

    // If note is public or no password required, load directly
    if (!info.requires_password) {
      await loadSharedNote()
    } else {
      passwordModalVisible.value = true
    }
  } catch (error: any) {
    console.error('Failed to load share info:', error)
    const errorMsg = error?.detail || error?.message || '加载分享信息失败'
    message.error(errorMsg)
  } finally {
    loading.value = false
  }
}

async function loadSharedNote() {
  loading.value = true
  try {
    const response = await sharesApi.accessSharedNote(shareToken, password.value || undefined)
    note.value = response

    // Set safe content
    const content = response?.content
    if (typeof content === 'string' && content.trim()) {
      // Validate that content looks like valid HTML
      if (content.includes('<') && content.includes('>')) {
        noteContent.value = content
      } else {
        // Wrap plain text in paragraph
        noteContent.value = `<p>${content}</p>`
      }
    } else {
      noteContent.value = '<p>暂无内容</p>'
    }

    passwordModalVisible.value = false
  } catch (error: any) {
    console.error('Failed to load shared note:', error)
    if (error.status === 401) {
      message.error('密码错误')
    } else if (error.status === 403) {
      message.error('无权访问此笔记')
      passwordModalVisible.value = false
    } else {
      message.error(error?.detail || error?.message || '加载笔记失败')
    }
  } finally {
    loading.value = false
  }
}

function copyShareLink() {
  const url = shareUrl.value

  // Method 1: Try modern clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(url).then(() => {
      copied.value = true
      message.success('链接已复制')
      setTimeout(() => {
        copied.value = false
      }, 2000)
    }).catch(() => {
      // Fallback to method 2
      fallbackCopy(url)
    })
    return
  }

  // Method 2: Fallback for non-HTTPS or when clipboard API fails
  fallbackCopy(url)
}

function fallbackCopy(url: string) {
  try {
    const textArea = document.createElement('textarea')
    textArea.value = url
    textArea.style.position = 'fixed'
    textArea.style.top = '0'
    textArea.style.left = '0'
    textArea.style.width = '2em'
    textArea.style.height = '2em'
    textArea.style.padding = '0'
    textArea.style.border = 'none'
    textArea.style.outline = 'none'
    textArea.style.boxShadow = 'none'
    textArea.style.background = 'transparent'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)

    if (successful) {
      copied.value = true
      message.success('链接已复制')
      setTimeout(() => {
        copied.value = false
      }, 2000)
    } else {
      // Method 3: Show in prompt as last resort
      prompt('请手动复制链接:', url)
    }
  } catch (err) {
    console.error('Copy failed:', err)
    // Method 3: Show in prompt as last resort
    prompt('请手动复制链接:', url)
  }
}

function handlePasswordSubmit() {
  if (!password.value.trim()) {
    message.warning('请输入访问密码')
    return
  }
  loadSharedNote()
}
</script>

<template>
  <div class="shared-note-container">
    <!-- Password Modal -->
    <a-modal
      v-model:open="passwordModalVisible"
      title="密码保护"
      :closable="false"
      :mask-closable="false"
    >
      <div class="password-content">
        <LockOutlined class="lock-icon" />
        <p>此笔记需要密码才能查看</p>
        <a-input
          v-model:value="password"
          placeholder="请输入访问密码"
          size="large"
          @keyup.enter="handlePasswordSubmit"
        >
          <template #prefix>
            <LockOutlined />
          </template>
        </a-input>
      </div>
      <template #footer>
        <a-button type="primary" size="large" block @click="handlePasswordSubmit">
          解锁笔记
        </a-button>
      </template>
    </a-modal>

    <!-- Loading State -->
    <div v-if="loading && !note" class="loading-state">
      <a-spin size="large" tip="加载中..." />
    </div>

    <!-- Note Content -->
    <div v-else-if="note" class="shared-note-wrapper">
      <!-- Header -->
      <header class="note-header">
        <div class="header-left">
          <a-tag color="blue" class="shared-tag">
            <FileTextOutlined /> 分享笔记
          </a-tag>
          <h1 class="note-title">{{ note.title || '无标题' }}</h1>
          <span v-if="note.updated_at" class="share-date">
            <CalendarOutlined /> {{ formattedDate }}
          </span>
        </div>

        <div class="header-actions">
          <a-button :type="copied ? 'primary' : 'default'" @click="copyShareLink">
            <template #icon>
              <CopyOutlined />
            </template>
            {{ copied ? '已复制' : '复制链接' }}
          </a-button>
        </div>
      </header>

      <!-- Content -->
      <main class="note-content">
        <EditorHost
          v-if="noteContent"
          v-model="noteContent"
          :editable="false"
          :editor-type="editorType"
          :created-at="note.created_at"
          :updated-at="note.updated_at"
        />
        <div v-else class="content-loading">
          <a-spin />
        </div>
      </main>

      <!-- Footer -->
      <footer class="note-footer">
        <div class="footer-content">
          <div class="powered-by">
            <span>由 </span>
            <strong>NotebookLLM</strong>
            <span> 提供支持</span>
          </div>
          <a href="/" target="_blank">
            创建我的笔记
          </a>
        </div>
      </footer>
    </div>

    <!-- Error State -->
    <div v-else-if="!loading" class="error-state">
      <a-result
        status="warning"
        title="笔记不可访问"
        sub-title="此笔记可能已被删除、分享链接已过期或无效。"
      >
        <template #extra>
          <a-button type="primary" href="/">
            返回首页
          </a-button>
        </template>
      </a-result>
    </div>
  </div>
</template>

<style scoped>
.shared-note-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.password-content {
  text-align: center;
  padding: 1rem 0;
}

.lock-icon {
  font-size: 48px;
  color: #667eea;
  margin-bottom: 1rem;
}

.password-content p {
  color: #666;
  margin-bottom: 1.5rem;
}

.shared-note-wrapper {
  max-width: 900px;
  margin: 0 auto;
  background: white;
  min-height: auto;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.05);
}

.note-header {
  padding: 1rem 2rem;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: nowrap;
  overflow: hidden;
}

.shared-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.note-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.4;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.share-date {
  color: #999;
  font-size: 0.75rem;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.author-info {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #666;
  font-size: 0.875rem;
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  border-radius: 20px;
}

.header-actions {
  flex-shrink: 0;
}

.note-content {
  padding: 1.5rem 2rem;
}

.note-html-content {
  line-height: 1.8;
  font-size: 15px;
  color: #1a1a1a;
}

.note-html-content :deep(h1) {
  font-size: 2em;
  font-weight: 700;
  margin: 0.67em 0;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.note-html-content :deep(h2) {
  font-size: 1.5em;
  font-weight: 600;
  margin: 0.83em 0;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
}

.note-html-content :deep(h3) {
  font-size: 1.25em;
  font-weight: 600;
  margin: 1em 0;
}

.note-html-content :deep(h4),
.note-html-content :deep(h5),
.note-html-content :deep(h6) {
  font-weight: 600;
  margin: 1em 0;
}

.note-html-content :deep(p) {
  margin: 0.5em 0;
}

.note-html-content :deep(ul),
.note-html-content :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.note-html-content :deep(li) {
  margin: 0.3em 0;
}

.note-html-content :deep(pre) {
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

.note-html-content :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.note-html-content :deep(code) {
  background: rgba(175, 184, 193, 0.2);
  border-radius: 6px;
  padding: 2px 6px;
  font-family: 'Fira Code', 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 0.9em;
  color: #d73a49;
}

.note-html-content :deep(blockquote) {
  border-left: 4px solid #1890ff;
  padding: 8px 16px;
  margin: 16px 0;
  background: #f6f8fa;
  border-radius: 0 6px 6px 0;
  color: #586069;
}

.note-html-content :deep(blockquote p) {
  margin: 0;
}

.note-html-content :deep(mark) {
  background-color: #fff59d;
  padding: 2px 4px;
  border-radius: 2px;
}

.note-html-content :deep(strong) {
  font-weight: 600;
}

.note-html-content :deep(em) {
  font-style: italic;
}

.note-html-content :deep(s) {
  text-decoration: line-through;
  color: #6a737d;
}

.note-html-content :deep(u) {
  text-decoration: underline;
}

.note-html-content :deep(hr) {
  border: none;
  border-top: 2px solid #e1e4e8;
  margin: 24px 0;
}

.note-html-content :deep(a) {
  color: #1890ff;
  text-decoration: none;
}

.note-html-content :deep(a:hover) {
  text-decoration: underline;
}

.note-html-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 16px 0;
}

.note-html-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.note-html-content :deep(th),
.note-html-content :deep(td) {
  border: 1px solid #e8e8e8;
  padding: 8px 12px;
  text-align: left;
}

.note-html-content :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.content-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.content-wrapper {
  line-height: 1.7;
  font-size: 1rem;
  color: #1a1a1a;
}

.content-wrapper :deep(h1),
.content-wrapper :deep(h2),
.content-wrapper :deep(h3),
.content-wrapper :deep(h4),
.content-wrapper :deep(h5),
.content-wrapper :deep(h6) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  line-height: 1.3;
}

.content-wrapper :deep(h1) {
  font-size: 1.875rem;
}

.content-wrapper :deep(h2) {
  font-size: 1.5rem;
}

.content-wrapper :deep(h3) {
  font-size: 1.25rem;
}

.content-wrapper :deep(p) {
  margin-bottom: 0.75rem;
}

.content-wrapper :deep(ul),
.content-wrapper :deep(ol) {
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
}

.content-wrapper :deep(li) {
  margin-bottom: 0.25rem;
}

.content-wrapper :deep(code) {
  background: #f4f4f4;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.875em;
}

.content-wrapper :deep(pre) {
  background: #f4f4f4;
  padding: 0.75rem;
  border-radius: 8px;
  overflow-x: auto;
  margin-bottom: 0.75rem;
}

.content-wrapper :deep(pre code) {
  background: transparent;
  padding: 0;
}

.content-wrapper :deep(blockquote) {
  border-left: 4px solid #667eea;
  padding-left: 1rem;
  margin: 0.75rem 0;
  color: #666;
  font-style: italic;
}

.content-wrapper :deep(a) {
  color: #667eea;
  text-decoration: none;
}

.content-wrapper :deep(a:hover) {
  text-decoration: underline;
}

.content-wrapper :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 0.75rem 0;
}

.content-wrapper :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0.75rem;
}

.content-wrapper :deep(th),
.content-wrapper :deep(td) {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e8e8e8;
}

.content-wrapper :deep(th) {
  font-weight: 600;
  background: #f5f5f5;
}

.note-footer {
  padding: 1rem 2rem;
  border-top: 1px solid #e8e8e8;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.powered-by {
  color: #999;
  font-size: 0.875rem;
}

.powered-by strong {
  color: #667eea;
}

.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
}

/* Responsive */
@media (max-width: 768px) {
  .shared-note-wrapper {
    margin: 0;
  }

  .note-header {
    flex-direction: column;
    padding: 1rem;
    gap: 0.75rem;
  }

  .header-left {
    flex-wrap: wrap;
    width: 100%;
  }

  .note-title {
    font-size: 1rem;
    white-space: normal;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions .ant-btn {
    width: 100%;
  }

  .note-content {
    padding: 1rem;
  }

  .footer-content {
    flex-direction: column;
    gap: 0.75rem;
    text-align: center;
  }
}
</style>

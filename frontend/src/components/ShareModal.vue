<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  ShareAltOutlined,
  LockOutlined,
  CopyOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  DeleteOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'
import { sharesApi, type ShareLink } from '@/api/shares'

const props = defineProps<{
  open: boolean
  noteId: string
  noteVisibility: 'private' | 'public'
  noteTitle: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'share-created', share: ShareLink): void
  (e: 'share-revoked'): void
}>()

// Form state
const password = ref('')
const expiresInHours = ref<number | null>(24) // Default 24 hours
const maxAccessCount = ref(3) // Default 3 times

// UI state
const loading = ref(false)
const creating = ref(false)
const existingShares = ref<ShareLink[]>([])
const sharePasswords = ref<Record<string, string>>({}) // Store passwords for newly created shares

// Expiration options
const expirationOptions: Array<{ value: number | null; label: string; key: string }> = [
  { value: 1, label: '1 小时', key: '1h' },
  { value: 24, label: '24 小时', key: '24h' },
  { value: 72, label: '3 天', key: '3d' },
  { value: 168, label: '7 天', key: '7d' },
  { value: 720, label: '30 天', key: '30d' },
  { value: null, label: '永不过期', key: 'never' },
]

// Computed
const isPublicNote = computed(() => props.noteVisibility === 'public')
const requiresPassword = computed(() => !isPublicNote.value && expiresInHours.value === null)
const canSetPassword = computed(() => !isPublicNote.value)
const canCreateShare = computed(() => {
  if (isPublicNote.value) {
    return true
  }
  if (expiresInHours.value === null) {
    return password.value.length >= 4
  }
  return true
})

// Helper function to get share URL
function getShareUrl(share: ShareLink) {
  return `${window.location.origin}/shared/${share.token}`
}

// Generate random password
function generateRandomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let result = ''
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  password.value = result
}

// Watch for modal open
watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    // Reset form
    password.value = ''
    expiresInHours.value = 24
    maxAccessCount.value = 3

    // Load existing shares
    await loadExistingShares()
  }
})

async function loadExistingShares() {
  loading.value = true
  try {
    const response = await sharesApi.listShareLinks({ noteId: props.noteId, activeOnly: true })
    existingShares.value = response.items || []
  } catch (error) {
    console.error('Failed to load share links:', error)
  } finally {
    loading.value = false
  }
}

async function createShare() {
  if (!canCreateShare.value) return

  creating.value = true
  try {
    const data: any = {
      noteId: props.noteId,
      expiresInHours: expiresInHours.value,
      maxAccessCount: maxAccessCount.value,
    }

    // Add password for private notes if provided
    if (!isPublicNote.value && password.value) {
      data.password = password.value
    }

    const share = await sharesApi.createShareLink(data)
    existingShares.value.unshift(share) // Add to beginning of list

    // Store password locally for copying (backend doesn't return it)
    if (password.value) {
      sharePasswords.value[share.id] = password.value
    }

    message.success('分享链接已创建')
    emit('share-created', share)

    // Reset form after successful creation
    password.value = ''
    expiresInHours.value = 24
    maxAccessCount.value = 3
  } catch (error: any) {
    message.error(error.detail || '创建分享链接失败')
  } finally {
    creating.value = false
  }
}

function confirmRevokeShare(shareId: string) {
  Modal.confirm({
    title: '取消分享',
    content: '确定要取消此分享链接吗？取消后该链接将无法访问。',
    okText: '确定取消',
    okType: 'danger',
    cancelText: '返回',
    onOk: () => revokeShare(shareId),
  })
}

async function revokeShare(shareId: string) {
  try {
    await sharesApi.revokeShareLink(shareId)
    existingShares.value = existingShares.value.filter(s => s.id !== shareId)
    // Also remove stored password
    delete sharePasswords.value[shareId]
    message.success('分享链接已取消')
    emit('share-revoked')
  } catch (error: any) {
    console.error('Failed to revoke share:', error)
    const errorMsg = error?.detail || error?.message || '取消分享失败'
    message.error(errorMsg)
  }
}

async function copyShareUrl(share: ShareLink) {
  const url = getShareUrl(share)
  const savedPassword = sharePasswords.value[share.id]

  // Build copy text - include password if available
  let copyText = url
  if (share.has_password && savedPassword) {
    copyText = `分享链接：${url}\n访问密码：${savedPassword}`
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(copyText)
      message.success(share.has_password && savedPassword ? '链接和密码已复制' : '链接已复制')
    } else {
      // Fallback
      const textArea = document.createElement('textarea')
      textArea.value = copyText
      textArea.style.position = 'fixed'
      textArea.style.left = '-9999px'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      message.success(share.has_password && savedPassword ? '链接和密码已复制' : '链接已复制')
    }
  } catch {
    message.error('复制失败')
  }
}

function closeModal() {
  emit('update:open', false)
}
</script>

<template>
  <a-modal
    :open="open"
    :title="null"
    :footer="null"
    :closable="false"
    :width="900"
    @update:open="$emit('update:open', $event)"
  >
    <div class="share-modal">
      <!-- Header -->
      <div class="modal-header">
        <ShareAltOutlined class="header-icon" />
        <div class="header-text">
          <div class="header-title-row">
            <h3>分享笔记</h3>
            <span class="visibility-badge" :class="noteVisibility">
              <EyeOutlined />
              {{ isPublicNote ? '公开笔记' : '私密笔记' }}
            </span>
          </div>
          <p class="note-title">{{ noteTitle }}</p>
        </div>
        <a-button type="text" class="close-btn" @click="closeModal">
          <CloseOutlined />
        </a-button>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <a-spin />
      </div>

      <div v-else class="share-content">
        <!-- Left: Existing shares list -->
        <div class="existing-shares-panel">
          <div class="section-title">已有分享链接 ({{ existingShares.length }})</div>
          <div v-if="existingShares.length > 0" class="shares-list">
            <div v-for="share in existingShares" :key="share.id" class="share-item">
              <div class="share-item-header">
                <a-input
                  :value="getShareUrl(share)"
                  readonly
                  size="small"
                  class="share-url-input"
                >
                  <template #addonAfter>
                    <a-button type="text" size="small" @click="copyShareUrl(share)">
                      <CopyOutlined />
                    </a-button>
                  </template>
                </a-input>
              </div>
              <div class="share-item-info">
                <div class="info-tags">
                  <a-tag v-if="share.has_password && sharePasswords[share.id]" color="orange">
                    <LockOutlined /> 密码: {{ sharePasswords[share.id] }}
                  </a-tag>
                  <a-tag v-else-if="share.has_password" color="orange">
                    <LockOutlined /> 已设密码
                  </a-tag>
                  <a-tag v-if="share.expires_at" color="blue">
                    <ClockCircleOutlined /> {{ new Date(share.expires_at).toLocaleString() }} 过期
                  </a-tag>
                  <a-tag v-else color="green">
                    <ClockCircleOutlined /> 永不过期
                  </a-tag>
                  <a-tag color="default">
                    <EyeOutlined /> {{ share.access_count }} 次访问
                  </a-tag>
                </div>
                <a-button type="text" danger size="small" @click="confirmRevokeShare(share.id)">
                  <DeleteOutlined />
                </a-button>
              </div>
            </div>
          </div>
          <div v-else class="empty-shares">
            <a-empty description="暂无分享链接" />
          </div>
        </div>

        <!-- Divider -->
        <a-divider type="vertical" class="panel-divider" />

        <!-- Right: Create new share form -->
        <div class="create-share-panel">
          <div class="section-title">创建新链接</div>
          <div class="create-share-form">
            <!-- Public note warning -->
            <a-alert
              v-if="isPublicNote"
              type="info"
              message="公开笔记将生成无密码分享链接"
              show-icon
              class="form-alert"
            />

            <!-- Private note with no expiration warning -->
            <a-alert
              v-if="requiresPassword"
              type="warning"
              message="私密笔记未设置有效期时必须设置访问密码"
              show-icon
              class="form-alert"
            />

            <!-- Expiration -->
            <div class="form-section">
              <label>有效期</label>
              <a-radio-group v-model:value="expiresInHours">
                <a-radio-button v-for="opt in expirationOptions" :key="opt.key" :value="opt.value">
                  {{ opt.label }}
                </a-radio-button>
              </a-radio-group>
            </div>

            <!-- Password (for private notes) -->
            <div v-if="canSetPassword" class="form-section">
              <label>
                <LockOutlined /> 访问密码
                <span v-if="requiresPassword" class="required">*</span>
              </label>
              <div class="password-inputs">
                <a-input-password
                  v-model:value="password"
                  :placeholder="requiresPassword ? '请输入访问密码' : '可选'"
                  size="large"
                />
                <a-button size="large" @click="generateRandomPassword">
                  随机
                </a-button>
              </div>
            </div>

            <!-- Access count limit -->
            <div class="form-section">
              <label>访问次数限制</label>
              <a-input-number
                v-model:value="maxAccessCount"
                :min="0"
                :max="10000"
                size="large"
                style="width: 100%"
              />
              <div class="form-hint">0 表示不限制</div>
            </div>

            <a-button
              type="primary"
              size="large"
              block
              :loading="creating"
              :disabled="!canCreateShare"
              @click="createShare"
            >
              <template #icon><ShareAltOutlined /></template>
              创建分享链接
            </a-button>
          </div>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.share-modal {
  padding: 0.5rem;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.header-icon {
  font-size: 2rem;
  color: #667eea;
}

.header-text {
  flex: 1;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-text h3 {
  margin: 0;
  font-size: 1.25rem;
}

.note-title {
  margin: 0.25rem 0 0;
  color: #666;
  font-size: 0.875rem;
}

.close-btn {
  color: #999;
}

.visibility-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.visibility-badge.public {
  background: #e6f7ff;
  color: #1890ff;
}

.visibility-badge.private {
  background: #fff7e6;
  color: #fa8c16;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.share-content {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.existing-shares-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  max-height: 350px;
}

.panel-divider {
  height: auto;
  margin: 0;
}

.create-share-panel {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  min-width: 280px;
}

.section-title {
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #333;
  font-size: 0.9375rem;
  flex-shrink: 0;
}

.shares-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
  overflow-y: auto;
  padding-right: 0.5rem;
  min-height: 0;
  max-height: 280px;
}

.shares-list::-webkit-scrollbar {
  width: 6px;
}

.shares-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.shares-list::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.shares-list::-webkit-scrollbar-thumb:hover {
  background: #aaa;
}

.empty-shares {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.share-item {
  padding: 0.75rem;
  background: #f9f9f9;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.share-item-header {
  margin-bottom: 0.5rem;
}

.share-url-input {
  font-size: 0.8125rem;
}

.share-item-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.info-tags .ant-tag {
  margin: 0;
  font-size: 0.75rem;
}

.create-share-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-alert {
  margin-bottom: 0.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-section label {
  font-weight: 500;
  color: #333;
}

.required {
  color: #ff4d4f;
  margin-left: 0.25rem;
}

.password-inputs {
  display: flex;
  gap: 0.5rem;
}

.password-inputs .ant-input-affix-wrapper {
  flex: 1;
}

.form-hint {
  font-size: 0.75rem;
  color: #999;
}

:deep(.ant-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

:deep(.ant-radio-button-wrapper) {
  border-radius: 6px !important;
}

:deep(.ant-radio-button-wrapper::before) {
  display: none;
}

:deep(.ant-divider-inner-text) {
  font-size: 0.875rem;
  color: #999;
}
</style>

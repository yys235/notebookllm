/**
 * useDraftAutoSave - 自动保存草稿
 * 在登录超时前保存编辑内容到 localStorage
 * 支持用户隔离，确保不同用户的草稿不会混淆
 */
import { ref, watch, onUnmounted, type Ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'

export interface DraftData {
  noteId: string
  title: string
  content: string
  editorType: string
  savedAt: number
  userId: string // 添加用户ID用于隔离
}

const DRAFT_KEY_PREFIX = 'note_draft_'
const DRAFT_EXPIRY_MS = 24 * 60 * 60 * 1000 // 24 hours

// Simple debounce implementation
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number) {
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const debounced = (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      fn(...args)
      timeoutId = null
    }, delay)
  }

  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  return debounced
}

export function useDraftAutoSave(noteId: Ref<string | undefined>) {
  const hasDraft = ref(false)
  const draftSavedAt = ref<Date | null>(null)
  const userStore = useUserStore()

  // 获取当前用户ID
  function getCurrentUserId(): string {
    return userStore.user?.id || 'anonymous'
  }

  // Get storage key for a note (with user isolation)
  function getDraftKey(id: string): string {
    const userId = getCurrentUserId()
    return `${DRAFT_KEY_PREFIX}${userId}_${id}`
  }

  // Save draft to localStorage
  function saveDraft(data: Omit<DraftData, 'savedAt' | 'userId'>) {
    if (!data.noteId) return

    const draft: DraftData = {
      ...data,
      savedAt: Date.now(),
      userId: getCurrentUserId(),
    }

    try {
      localStorage.setItem(getDraftKey(data.noteId), JSON.stringify(draft))
      draftSavedAt.value = new Date()
      hasDraft.value = true
    } catch (e) {
      console.error('Failed to save draft:', e)
    }
  }

  // Load draft from localStorage
  function loadDraft(id: string): DraftData | null {
    if (!id) return null

    try {
      const stored = localStorage.getItem(getDraftKey(id))
      if (!stored) return null

      const draft: DraftData = JSON.parse(stored)

      // Verify draft belongs to current user (security check)
      if (draft.userId && draft.userId !== getCurrentUserId()) {
        clearDraft(id)
        return null
      }

      // Check if draft is expired
      if (Date.now() - draft.savedAt > DRAFT_EXPIRY_MS) {
        clearDraft(id)
        return null
      }

      return draft
    } catch (e) {
      console.error('Failed to load draft:', e)
      return null
    }
  }

  // Clear draft from localStorage
  function clearDraft(id: string) {
    if (!id) return

    try {
      localStorage.removeItem(getDraftKey(id))
      hasDraft.value = false
      draftSavedAt.value = null
    } catch (e) {
      console.error('Failed to clear draft:', e)
    }
  }

  // Check if there's a draft for the current note
  function checkDraft(id: string): boolean {
    const draft = loadDraft(id)
    return draft !== null
  }

  // Debounced save function
  const debouncedSave = debounce(saveDraft, 1000)

  // Setup auto-save watcher
  function setupAutoSave(
    title: Ref<string>,
    content: Ref<string>,
    editorType: Ref<string>
  ) {
    const stopWatch = watch(
      [title, content, editorType],
      () => {
        if (noteId.value) {
          debouncedSave({
            noteId: noteId.value,
            title: title.value,
            content: content.value,
            editorType: editorType.value,
          })
        }
      },
      { deep: true }
    )

    onUnmounted(() => {
      debouncedSave.cancel()
      stopWatch()
    })
  }

  // Restore draft and ask user
  function restoreDraft(
    id: string,
    onRestore: (draft: DraftData) => void
  ): boolean {
    const draft = loadDraft(id)
    if (!draft) return false

    Modal.confirm({
      title: '发现未保存的草稿',
      content: `检测到 ${new Date(draft.savedAt).toLocaleString()} 保存的草稿，是否恢复？`,
      okText: '恢复草稿',
      cancelText: '放弃草稿',
      onOk: () => {
        onRestore(draft)
        message.success('草稿已恢复')
      },
      onCancel: () => {
        clearDraft(id)
        message.info('草稿已放弃')
      },
    })

    return true
  }

  return {
    hasDraft,
    draftSavedAt,
    saveDraft,
    loadDraft,
    clearDraft,
    checkDraft,
    setupAutoSave,
    restoreDraft,
  }
}

/**
 * useDraftAutoSave - 自动保存草稿
 * 在登录超时前保存编辑内容到 localStorage
 */
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'

export interface DraftData {
  noteId: string
  title: string
  content: string
  editorType: string
  savedAt: number
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

  // Get storage key for a note
  function getDraftKey(id: string): string {
    return `${DRAFT_KEY_PREFIX}${id}`
  }

  // Save draft to localStorage
  function saveDraft(data: Omit<DraftData, 'savedAt'>) {
    if (!data.noteId) return

    const draft: DraftData = {
      ...data,
      savedAt: Date.now(),
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

// Import ref and Modal types
import { Ref } from 'vue'
import { Modal } from 'ant-design-vue'

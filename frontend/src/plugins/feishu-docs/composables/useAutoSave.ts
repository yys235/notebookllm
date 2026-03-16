/**
 * useAutoSave - Auto-save composable for document blocks
 * Watches document changes and syncs to server with debouncing
 */
import { ref, watch, computed, onUnmounted } from 'vue'
import { useDocumentStore } from '../stores/document'

export type SyncStatus = 'idle' | 'saving' | 'saved' | 'error'

export interface AutoSaveOptions {
  /** Debounce delay in milliseconds (default: 500ms) */
  debounceMs?: number
  /** Whether to enable auto-save (default: true) */
  enabled?: boolean
  /** Note ID for the current document */
  noteId?: string | null
}

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

export function useAutoSave(options: AutoSaveOptions = {}) {
  const {
    debounceMs = 500,
    enabled = true,
    noteId: externalNoteId,
  } = options

  const documentStore = useDocumentStore()

  // Reactive state
  const isSaving = ref(false)
  const lastSavedAt = ref<Date | null>(null)
  const syncStatus = ref<SyncStatus>('idle')
  const syncError = ref<string | null>(null)

  // Get current note ID
  const currentNoteId = computed(() => {
    return externalNoteId ?? documentStore.currentNoteId
  })

  /**
   * Perform sync with server
   */
  async function performSync() {
    if (!enabled || !currentNoteId.value) {
      return
    }

    if (isSaving.value) {
      return // Already saving
    }

    isSaving.value = true
    syncStatus.value = 'saving'
    syncError.value = null

    try {
      await documentStore.syncWithServer(currentNoteId.value)
      lastSavedAt.value = new Date()
      syncStatus.value = 'saved'
    } catch (error: any) {
      syncError.value = error.message || 'Sync failed'
      syncStatus.value = 'error'
      throw error
    } finally {
      isSaving.value = false
      // Reset to idle after a short delay
      setTimeout(() => {
        if (syncStatus.value === 'saved') {
          syncStatus.value = 'idle'
        }
      }, 2000)
    }
  }

  /**
   * Debounced sync function
   */
  const debouncedSync = debounce(performSync, debounceMs)

  /**
   * Force immediate sync (bypasses debounce)
   */
  async function forceSync() {
    // Cancel any pending debounced sync
    debouncedSync.cancel()
    await performSync()
  }

  /**
   * Watch for pending changes and trigger auto-save
   */
  const stopWatch = watch(
    () => documentStore.hasPendingChanges,
    (hasPending) => {
      if (hasPending && enabled && currentNoteId.value) {
        debouncedSync()
      }
    },
    { immediate: false }
  )

  /**
   * Watch for sync errors from the store
   */
  const stopErrorWatch = watch(
    () => documentStore.syncError,
    (error) => {
      if (error) {
        syncError.value = error
        syncStatus.value = 'error'
      }
    }
  )

  /**
   * Cleanup on unmount
   */
  onUnmounted(() => {
    stopWatch()
    stopErrorWatch()
    debouncedSync.cancel()
  })

  /**
   * Format last saved time for display
   */
  const lastSavedTimeFormatted = computed(() => {
    if (!lastSavedAt.value) return null
    const now = new Date()
    const diff = now.getTime() - lastSavedAt.value.getTime()

    if (diff < 60000) {
      return 'Just now'
    } else if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000)
      return `${minutes}m ago`
    } else if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000)
      return `${hours}h ago`
    } else {
      return lastSavedAt.value.toLocaleDateString()
    }
  })

  /**
   * Status text for display
   */
  const statusText = computed(() => {
    switch (syncStatus.value) {
      case 'saving':
        return 'Saving...'
      case 'saved':
        return 'Saved'
      case 'error':
        return syncError.value || 'Sync failed'
      case 'idle':
      default:
        return lastSavedTimeFormatted.value || ''
    }
  })

  return {
    // State
    isSaving,
    lastSavedAt,
    syncStatus,
    syncError,
    currentNoteId,

    // Computed
    lastSavedTimeFormatted,
    statusText,

    // Methods
    forceSync,

    // Cleanup (manual)
    cancelPendingSync: () => debouncedSync.cancel(),
  }
}

export default useAutoSave

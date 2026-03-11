import { ref } from 'vue'

/**
 * Loading state composable
 */
export function useLoading(initialState = false) {
  const loading = ref(initialState)

  const setLoading = (state: boolean) => {
    loading.value = state
  }

  const startLoading = () => {
    loading.value = true
  }

  const stopLoading = () => {
    loading.value = false
  }

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T> => {
    startLoading()
    try {
      return await fn()
    } finally {
      stopLoading()
    }
  }

  return {
    loading,
    setLoading,
    startLoading,
    stopLoading,
    withLoading,
  }
}

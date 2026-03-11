import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value)
  const userName = computed(() => user.value?.name || '')

  function setUser(userData: User) {
    user.value = userData
  }

  function setToken(newToken: string) {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('token', newToken)
    } else {
      localStorage.removeItem('token')
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }

  async function fetchProfile() {
    // TODO: Implement profile fetching
  }

  return {
    user,
    token,
    isLoggedIn,
    userName,
    setUser,
    setToken,
    logout,
    fetchProfile,
  }
})

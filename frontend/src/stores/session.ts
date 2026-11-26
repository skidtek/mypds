import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, ApiError, setCsrfToken } from '@/api/client'
import type { Me } from '@/api/types'

export function avatarUrl(me: Me): string | null {
  return me.avatar_version ? `/api/v1/me/avatar?v=${me.avatar_version}` : null
}

export const useSession = defineStore('session', () => {
  const me = ref<Me | null>(null)
  const checked = ref(false)

  function set(value: Me | null) {
    me.value = value
    setCsrfToken(value?.csrf_token ?? '')
  }

  async function refresh(): Promise<boolean> {
    try {
      set(await api<Me>('/api/v1/auth/me'))
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401) throw e
      set(null)
    } finally {
      checked.value = true
    }
    return me.value !== null
  }

  async function login(username: string, password: string, remember: boolean) {
    set(await api<Me>('/api/v1/auth/login', { method: 'POST', json: { username, password, remember } }))
    checked.value = true
  }

  async function logout() {
    try {
      await api('/api/v1/auth/logout', { method: 'POST' })
    } finally {
      set(null)
    }
  }

  return { me, checked, refresh, login, logout, set }
})

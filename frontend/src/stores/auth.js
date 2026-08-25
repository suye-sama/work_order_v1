/**
 * 认证状态管理（Pinia）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authAPI } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || '')

  // 登录
  async function login(username, password) {
    const res = await authAPI.login(username, password)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('token', token.value)
    return res
  }

  // 获取当前用户（页面刷新后恢复）
  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await authAPI.getMe()
      user.value = res.data
    } catch {
      // Token 过期，清除
      logout()
    }
  }

  // 登出
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  return { user, token, login, fetchUser, logout }
})

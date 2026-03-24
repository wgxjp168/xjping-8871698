import { defineStore } from 'pinia'
import { login as loginApi } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('health_token') || '',
    userInfo: JSON.parse(localStorage.getItem('health_user') || 'null')
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    role: (state) => state.userInfo?.role || '',
    isAdmin: (state) => state.userInfo?.role === 'ADMIN',
    isDoctor: (state) => state.userInfo?.role === 'DOCTOR'
  },

  actions: {
    async login(username, password) {
      const res = await loginApi({ username, password })
      this.token = res.data.token
      this.userInfo = res.data
      localStorage.setItem('health_token', res.data.token)
      localStorage.setItem('health_user', JSON.stringify(res.data))
      return res
    },

    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('health_token')
      localStorage.removeItem('health_user')
    }
  }
})

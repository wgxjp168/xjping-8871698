// src/store/modules/user.js
import { defineStore } from 'pinia'
import { clearAuthCache, getPermissions, getUserInfo, setPermissions, setToken, setUserInfo } from '@/utils/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: getUserInfo() || {},
    permissions: getPermissions() || [],
    token: null
  }),
  getters: {
    isLoggedIn: (state) => !!state.token || !!state.userInfo?.id,
    isAdmin: (state) => state.userInfo?.role === 'admin',
    username: (state) => state.userInfo?.username || ''
  },
  actions: {
    /**
     * 设置用户信息
     */
    setUserInfo(info) {
      this.userInfo = info
      setUserInfo(info)
    },

    /**
     * 设置Token
     */
    setToken(token) {
      this.token = token
      setToken(token)
    },

    /**
     * 设置权限列表
     */
    setPermissions(permissions) {
      this.permissions = permissions
      setPermissions(permissions)
    },

    /**
     * 退出登录
     */
    logout() {
      this.userInfo = {}
      this.permissions = []
      this.token = null
      clearAuthCache()
    }
  }
})

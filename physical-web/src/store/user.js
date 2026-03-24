import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, logout as apiLogout } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))
  const permissions = ref(JSON.parse(localStorage.getItem('permissions') || '[]'))

  const isLoggedIn = computed(() => !!token.value)
  const doctorName = computed(() => userInfo.value?.name || '')
  const deptName = computed(() => userInfo.value?.deptName || '')

  /**
   * 登录
   */
  async function login(loginData) {
    const res = await apiLogin(loginData)
    if (res.code === 200) {
      token.value = res.data.token
      userInfo.value = {
        docId: res.data.docId,
        username: res.data.username,
        name: res.data.name,
        dept: res.data.dept,
        deptName: res.data.deptName,
        title: res.data.title,
        projectCodes: res.data.projectCodes
      }
      permissions.value = res.data.permissions || []
      localStorage.setItem('token', token.value)
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
      localStorage.setItem('permissions', JSON.stringify(permissions.value))
    }
    return res
  }

  /**
   * 退出登录
   */
  async function logout() {
    try {
      await apiLogout()
    } catch (e) {
      // 忽略退出接口异常
    }
    token.value = ''
    userInfo.value = null
    permissions.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    localStorage.removeItem('permissions')
  }

  /**
   * 校验是否有指定权限（projectCode:operateType）
   */
  function hasPermission(perm) {
    if (!perm) return true
    return permissions.value.includes(perm)
  }

  return {
    token,
    userInfo,
    permissions,
    isLoggedIn,
    doctorName,
    deptName,
    login,
    logout,
    hasPermission
  }
})

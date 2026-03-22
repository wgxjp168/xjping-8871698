// src/directives/permission.js
import { checkPermission } from '@/utils/auth'

/**
 * 权限指令
 * 用法：v-permission="['supplier:score:edit']"
 */
export default {
  mounted(el, binding) {
    const { value } = binding
    if (value && Array.isArray(value) && value.length) {
      const hasPermission = value.some(permission => checkPermission(permission))
      if (!hasPermission) {
        el.style.display = 'none'
        setTimeout(() => {
          el.parentNode?.removeChild(el)
        }, 0)
      }
    }
  }
}

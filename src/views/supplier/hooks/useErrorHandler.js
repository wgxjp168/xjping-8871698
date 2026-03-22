// src/views/supplier/hooks/useErrorHandler.js
import { ElMessage } from 'element-plus'
import { addOperationLog } from '@/api/log'

/**
 * 全局错误处理 hooks
 */
export function useErrorHandler() {
  /**
   * 处理业务错误
   * @param {Error} error
   * @param {string} context 错误上下文描述
   */
  const handleError = (error, context = '') => {
    const message = error?.message || '未知错误'
    console.error(`[${context}] 错误：`, error)
    ElMessage.error(context ? `${context}：${message}` : message)
  }

  /**
   * 异步安全包装（自动捕获错误）
   * @param {Function} fn
   * @param {string} context
   * @returns {*}
   */
  const safeAsync = async (fn, context = '') => {
    try {
      return await fn()
    } catch (error) {
      handleError(error, context)
      return null
    }
  }

  /**
   * 记录前端异常日志
   * @param {Error} error
   * @param {string} module
   */
  const logError = async (error, module = 'unknown') => {
    try {
      await addOperationLog({
        module,
        operation: 'error',
        content: error?.message || String(error),
        resourceId: ''
      })
    } catch (e) {
      console.warn('日志上报失败：', e)
    }
  }

  return { handleError, safeAsync, logError }
}

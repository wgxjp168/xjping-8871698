// src/utils/request.js
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getToken } from '@/utils/auth'

// 创建axios实例
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json;charset=utf-8'
  }
})

// 请求重试配置
const retry = 3
const retryDelay = 1000

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    config.headers['X-Request-Id'] = Math.random().toString(36).substr(2, 9)
    return config
  },
  (error) => {
    console.error('请求错误：', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.msg || '请求失败')
      if (res.code === 401) {
        ElMessageBox.confirm('登录已过期，请重新登录', '提示', {
          confirmButtonText: '重新登录',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          window.location.href = '/login'
        })
      }
      return Promise.reject(new Error(res.msg || '请求失败'))
    }
    return res
  },
  async (error) => {
    console.error('响应错误：', error)
    const config = error.config || {}
    config.__retryCount = config.__retryCount || 0

    if (
      (error.code === 'ECONNABORTED' || !error.response) &&
      config.__retryCount < retry
    ) {
      config.__retryCount += 1
      await new Promise(resolve => setTimeout(resolve, retryDelay))
      return service(config)
    }

    const status = error.response?.status
    switch (status) {
      case 400:
        ElMessage.error('参数错误')
        break
      case 403:
        ElMessage.error('权限不足')
        break
      case 404:
        ElMessage.error('接口不存在')
        break
      case 500:
        ElMessage.error('服务器内部错误')
        break
      default:
        ElMessage.error('请求失败，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default service

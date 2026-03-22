// src/utils/cache.js

/**
 * 本地缓存工具（支持过期时间）
 */
export class Cache {
  /**
   * 设置缓存
   * @param {string} key
   * @param {*} value
   * @param {number} ttl 过期时间（秒），0表示永不过期
   */
  static set(key, value, ttl = 0) {
    const item = {
      value,
      expire: ttl > 0 ? Date.now() + ttl * 1000 : 0
    }
    try {
      localStorage.setItem(key, JSON.stringify(item))
    } catch (e) {
      console.warn('Cache.set 失败：', e)
    }
  }

  /**
   * 获取缓存
   * @param {string} key
   * @returns {*} value 或 null
   */
  static get(key) {
    try {
      const raw = localStorage.getItem(key)
      if (!raw) return null
      const item = JSON.parse(raw)
      if (item.expire && Date.now() > item.expire) {
        localStorage.removeItem(key)
        return null
      }
      return item.value
    } catch (e) {
      console.warn('Cache.get 失败：', e)
      return null
    }
  }

  /**
   * 删除缓存
   * @param {string} key
   */
  static remove(key) {
    localStorage.removeItem(key)
  }

  /**
   * 清空所有缓存
   */
  static clear() {
    localStorage.clear()
  }
}

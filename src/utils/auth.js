// src/utils/auth.js
import { Cache } from '@/utils/cache'

const TOKEN_KEY = 'ILBUY_TOKEN'
const REFRESH_TOKEN_KEY = 'ILBUY_REFRESH_TOKEN'
const USER_INFO_KEY = 'ILBUY_USER_INFO'
const PERMISSIONS_KEY = 'ILBUY_PERMISSIONS'

export function getToken() {
  return Cache.get(TOKEN_KEY)
}

export function setToken(token) {
  return Cache.set(TOKEN_KEY, token, 7 * 24 * 60 * 60)
}

export function getRefreshToken() {
  return Cache.get(REFRESH_TOKEN_KEY)
}

export async function refreshToken() {
  const token = getRefreshToken()
  if (!token) return null
  return token
}

export function getUserInfo() {
  return Cache.get(USER_INFO_KEY)
}

export function setUserInfo(info) {
  return Cache.set(USER_INFO_KEY, info, 7 * 24 * 60 * 60)
}

export function getPermissions() {
  return Cache.get(PERMISSIONS_KEY) || []
}

export function setPermissions(permissions) {
  return Cache.set(PERMISSIONS_KEY, permissions, 7 * 24 * 60 * 60)
}

export function checkPermission(permission) {
  const permissions = getPermissions()
  return permissions.includes(permission)
}

export function clearAuthCache() {
  Cache.remove(TOKEN_KEY)
  Cache.remove(REFRESH_TOKEN_KEY)
  Cache.remove(USER_INFO_KEY)
  Cache.remove(PERMISSIONS_KEY)
}

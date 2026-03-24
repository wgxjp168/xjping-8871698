import request from './request'

/** 登录 */
export function login(data) {
  return request.post('/auth/login', data)
}

/** 退出登录 */
export function logout() {
  return request.post('/auth/logout')
}

/** 获取医生权限列表 */
export function getDoctorPermissions(docId) {
  return request.get(`/auth/permissions/${docId}`)
}

/** 校验权限 */
export function checkPermission(data) {
  return request.post('/auth/check', data)
}

/** 授予权限 */
export function grantPermission(data) {
  return request.post('/auth/grant', data)
}

/** 撤销权限 */
export function revokePermission(permissionId) {
  return request.delete(`/auth/revoke/${permissionId}`)
}

/** 触发县域同步 */
export function syncFromCounty() {
  return request.post('/auth/sync/county')
}

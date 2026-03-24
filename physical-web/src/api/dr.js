import request from './request'

/** DR条码扫描 */
export function scanDrBarcode(data) {
  return request.post('/dr/scan', data)
}

/** 提交DR检查结果 */
export function submitDrResult(data) {
  return request.post('/dr/submit', data)
}

/** 分页查询DR记录 */
export function getDrPage(params) {
  return request.get('/dr/page', { params })
}

/** 查询DR详情 */
export function getDrDetail(id) {
  return request.get(`/dr/${id}`)
}

/** 手动同步至县域 */
export function syncDrToCounty(id) {
  return request.post(`/dr/sync/${id}`)
}

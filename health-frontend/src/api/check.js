import request from './request'

export const getCheckOrderPage = (params) => request.get('/check/order/page', { params })

export const getCheckOrderDetail = (orderId) => request.get(`/check/order/${orderId}`)

export const createCheckOrder = (patientId, packageId) =>
  request.post('/check/order', null, { params: { patientId, packageId } })

export const updateOrderStatus = (orderId, status) =>
  request.put(`/check/order/${orderId}/status`, null, { params: { status } })

export const saveCheckResult = (data) => request.post('/check/result', data)

export const getCheckResults = (orderId) => request.get(`/check/result/${orderId}`)

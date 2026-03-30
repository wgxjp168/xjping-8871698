import request from '@/utils/request'

// 体检单
export const getCheckOrders = (params) => request.get('/check-orders', { params })
export const getCheckOrder = (id) => request.get(`/check-orders/${id}`)
export const getCheckOrderByNo = (orderNo) => request.get(`/check-orders/by-no/${orderNo}`)
export const createCheckOrder = (data) => request.post('/check-orders', data)
export const updateCheckOrder = (id, data) => request.put(`/check-orders/${id}`, data)
export const updateCheckOrderStatus = (id, status) => request.put(`/check-orders/${id}/status`, { status })
export const deleteCheckOrder = (id) => request.delete(`/check-orders/${id}`)
export const getCheckOrderYearCount = (year, deptId) => request.get('/check-orders/count/year', { params: { year, deptId } })

// 体检结果
export const getResultsByOrder = (orderId, category) => request.get(`/check-results/order/${orderId}`, { params: { category } })
export const getResultsByResident = (residentId) => request.get(`/check-results/resident/${residentId}`)
export const saveResult = (data) => request.post('/check-results', data)
export const saveBatchResults = (data) => request.post('/check-results/batch', data)

// 体征
export const getVitalSign = (orderId) => request.get(`/vital-signs/order/${orderId}`)
export const saveVitalSign = (data) => request.post('/vital-signs', data)

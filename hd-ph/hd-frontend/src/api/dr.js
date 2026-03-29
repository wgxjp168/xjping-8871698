import request from '@/utils/request'

export const getDrOrders = (params) => request.get('/dr-orders', { params })
export const getDrOrder = (id) => request.get(`/dr-orders/${id}`)
export const getDrOrderByBarcode = (barcodeNo) => request.get(`/dr-orders/barcode/${barcodeNo}`)
export const createDrOrder = (data) => request.post('/dr-orders', data)
export const scanBarcode = (data) => request.post('/dr-orders/scan', data)
export const updateDrOrderStatus = (id, status) => request.put(`/dr-orders/${id}/status`, { status })
export const deleteDrOrder = (id) => request.delete(`/dr-orders/${id}`)

export const getDrReport = (orderId) => request.get(`/dr-reports/order/${orderId}`)
export const submitDrReport = (data) => request.post('/dr-reports', data)
export const markDrReportUploaded = (id) => request.put(`/dr-reports/${id}/upload`)
export const getDrOrderMonthCount = () => request.get('/dr-orders/count/month')

import request from './request'

export const getDevicePage = (params) => request.get('/device/page', { params })

export const getDeviceById = (id) => request.get(`/device/${id}`)

export const saveDevice = (data) => request.post('/device', data)

export const updateDevice = (data) => request.put('/device', data)

export const deleteDevice = (id) => request.delete(`/device/${id}`)

export const deviceHeartbeat = (code) => request.post(`/device/heartbeat/${code}`)

export const uploadDeviceData = (code, data) => request.post(`/device/upload/${code}`, data)

export const getDeviceData = (id, limit = 20) => request.get(`/device/${id}/data`, { params: { limit } })

export const getOnlineDevices = () => request.get('/device/online')

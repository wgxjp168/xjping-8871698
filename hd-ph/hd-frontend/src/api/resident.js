import request from '@/utils/request'

export const getResidents = (params) => request.get('/residents', { params })
export const getResident = (id) => request.get(`/residents/${id}`)
export const getResidentByIdCard = (idCard) => request.get(`/residents/by-idcard/${idCard}`)
export const createResident = (data) => request.post('/residents', data)
export const updateResident = (id, data) => request.put(`/residents/${id}`, data)
export const deleteResident = (id) => request.delete(`/residents/${id}`)
export const getResidentCount = () => request.get('/residents/count')

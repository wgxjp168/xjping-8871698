import request from './request'

export const getUserPage = (params) => request.get('/user/page', { params })

export const getUserById = (id) => request.get(`/user/${id}`)

export const saveUser = (data) => request.post('/user', data)

export const updateUser = (data) => request.put('/user', data)

export const deleteUser = (id) => request.delete(`/user/${id}`)

export const toggleUserStatus = (id, status) =>
  request.put(`/user/${id}/status`, null, { params: { status } })

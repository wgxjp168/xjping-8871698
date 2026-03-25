import request from '@/utils/request'

// 用户
export const getUsers = (params) => request.get('/users', { params })
export const createUser = (data) => request.post('/users', data)
export const updateUser = (id, data) => request.put(`/users/${id}`, data)
export const deleteUser = (id) => request.delete(`/users/${id}`)
export const resetPassword = (id, password) => request.put(`/users/${id}/reset-password`, { password })

// 部门
export const getDepts = () => request.get('/depts')
export const createDept = (data) => request.post('/depts', data)
export const updateDept = (id, data) => request.put(`/depts/${id}`, data)
export const deleteDept = (id) => request.delete(`/depts/${id}`)

// 角色
export const getRoles = () => request.get('/roles')

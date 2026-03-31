import request from '@/utils/request'

// 用户
export const getUsers = (params) => request.get('/users', { params })
export const createUser = (data) => request.post('/users', data)
export const updateUser = (id, data) => request.put(`/users/${id}`, data)
export const deleteUser = (id) => request.delete(`/users/${id}`)
export const resetPassword = (id, password) => request.put(`/users/${id}/reset-password`, { password })

// 部门
export const getDepts = (params) => request.get('/depts', { params })
export const createDept = (data) => request.post('/depts', data)
export const updateDept = (id, data) => request.put(`/depts/${id}`, data)
export const deleteDept = (id) => request.delete(`/depts/${id}`)

// 角色
export const getRoles = () => request.get('/roles')
export const createRole = (data) => request.post('/roles', data)
export const updateRole = (id, data) => request.put(`/roles/${id}`, data)
export const deleteRole = (id) => request.delete(`/roles/${id}`)
export const updateRoleStatus = (id, status) => request.put(`/roles/${id}/status`, { status })
export const getRolePermissions = (id) => request.get(`/roles/${id}/permissions`)
export const assignRolePermissions = (id, permCodes) => request.put(`/roles/${id}/permissions`, { permCodes })

// 权限
export const getPermissions = () => request.get('/permissions')

// 区域地址
export const getAreas = () => request.get('/areas')
export const createArea = (data) => request.post('/areas', data)
export const updateArea = (id, data) => request.put(`/areas/${id}`, data)
export const deleteArea = (id) => request.delete(`/areas/${id}`)

// 责任医生筛选条件
export const getDoctorFilters = () => request.get('/doctor-filters')
export const createDoctorFilter = (data) => request.post('/doctor-filters', data)
export const updateDoctorFilter = (id, data) => request.put(`/doctor-filters/${id}`, data)
export const deleteDoctorFilter = (id) => request.delete(`/doctor-filters/${id}`)

// 责任医生查询
export const getDoctors = (params) => request.get('/users/doctors', { params })

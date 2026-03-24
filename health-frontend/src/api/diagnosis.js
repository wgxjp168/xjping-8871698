import request from './request'

export const getDiagnosisPage = (params) => request.get('/diagnosis/page', { params })

export const getDiagnosisDetail = (id) => request.get(`/diagnosis/${id}`)

export const saveDiagnosis = (data) => request.post('/diagnosis', data)

export const confirmDiagnosis = (id) => request.put(`/diagnosis/${id}/confirm`)

export const publishDiagnosis = (id) => request.put(`/diagnosis/${id}/publish`)

export const deleteDiagnosis = (id) => request.delete(`/diagnosis/${id}`)

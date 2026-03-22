// src/api/supplier.js
import request from '@/utils/request'

/**
 * 获取供应商评分详情
 * @param {string} supplierId
 */
export function getSupplierScore(supplierId) {
  return request({
    url: `/supplier/score/${supplierId}`,
    method: 'get'
  })
}

/**
 * 保存供应商评分
 * @param {object} data
 */
export function saveSupplierScore(data) {
  return request({
    url: '/supplier/score',
    method: 'post',
    data
  })
}

/**
 * 获取供应商评分历史
 * @param {string} supplierId
 * @param {object} params
 */
export function getSupplierScoreHistory(supplierId, params = {}) {
  return request({
    url: `/supplier/score/${supplierId}/history`,
    method: 'get',
    params
  })
}

/**
 * 批量保存供应商评分
 * @param {Array} data
 */
export function batchSaveSupplierScore(data) {
  return request({
    url: '/supplier/score/batch',
    method: 'post',
    data
  })
}

/**
 * 获取评分规则
 * @param {string} scoreType B2B / B2C_BRAND / B2C_NOBRAND
 */
export function getScoreRule(scoreType) {
  return request({
    url: '/supplier/score/rule',
    method: 'get',
    params: { scoreType }
  })
}

/**
 * 获取供应商列表（分页）
 * @param {object} params
 */
export function getSupplierList(params) {
  return request({
    url: '/supplier/list',
    method: 'get',
    params
  })
}

/**
 * 获取供应商详情
 * @param {string} supplierId
 */
export function getSupplierDetail(supplierId) {
  return request({
    url: `/supplier/${supplierId}`,
    method: 'get'
  })
}

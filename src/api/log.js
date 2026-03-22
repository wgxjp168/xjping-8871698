// src/api/log.js
import request from '@/utils/request'

/**
 * 添加操作日志
 * @param {object} data
 * @param {string} data.module 模块名
 * @param {string} data.operation 操作类型
 * @param {string} data.content 操作内容
 * @param {string} data.resourceId 关联资源ID
 */
export function addOperationLog(data) {
  return request({
    url: '/log/operation',
    method: 'post',
    data
  })
}

/**
 * 查询操作日志
 * @param {object} params
 */
export function getOperationLogs(params) {
  return request({
    url: '/log/operation',
    method: 'get',
    params
  })
}

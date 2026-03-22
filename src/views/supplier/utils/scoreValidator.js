// src/views/supplier/utils/scoreValidator.js

/**
 * 校验所有维度分值是否在合法范围内
 * @param {Array} dimensions
 * @returns {boolean}
 */
export function validateScore(dimensions = []) {
  if (!dimensions || dimensions.length === 0) return false
  return dimensions.every(item => {
    const score = Number(item.score)
    const max = Number(item.max)
    return !isNaN(score) && score >= 0 && score <= max
  })
}

/**
 * 校验单个维度分值
 * @param {number} score
 * @param {number} max
 * @returns {{ valid: boolean, message: string }}
 */
export function validateDimensionScore(score, max) {
  const val = Number(score)
  if (isNaN(val)) return { valid: false, message: '分值必须为数字' }
  if (val < 0) return { valid: false, message: '分值不能为负数' }
  if (val > max) return { valid: false, message: `分值不能超过满分 ${max}` }
  return { valid: true, message: '' }
}

/**
 * 批量评分校验（用于批量提交场景）
 * @param {Array} scoreList 供应商评分列表
 * @returns {{ valid: boolean, errors: Array }}
 */
export function validateBatchScore(scoreList = []) {
  const errors = []
  scoreList.forEach((item, idx) => {
    if (!item.supplierId) {
      errors.push({ index: idx, message: '供应商ID不能为空' })
    }
    if (!validateScore(item.dimensions)) {
      errors.push({ index: idx, message: `第${idx + 1}条评分维度数据不合法` })
    }
  })
  return { valid: errors.length === 0, errors }
}

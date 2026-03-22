// src/utils/score.js

/**
 * 计算供应商总分（加权求和）
 * @param {Array} dimensions 各维度评分数组
 * @returns {number} 总分（精确到1位小数）
 */
export function calculateTotalScore(dimensions = []) {
  if (!dimensions || dimensions.length === 0) return 0
  const total = dimensions.reduce((sum, item) => sum + (Number(item.score) || 0), 0)
  return Math.round(total * 10) / 10
}

/**
 * 将分值转换为星级（5星制）
 * @param {number} score 当前分
 * @param {number} max 满分
 * @returns {number} 1-5星
 */
export function convertScoreToStar(score, max = 100) {
  if (!max || max <= 0) return 0
  const ratio = score / max
  if (ratio >= 0.9) return 5
  if (ratio >= 0.75) return 4
  if (ratio >= 0.6) return 3
  if (ratio >= 0.4) return 2
  return 1
}

/**
 * 根据总分计算供应商等级
 * @param {number} total 总分（0-100）
 * @returns {string} S/A/B/C/D
 */
export function calcSupplierLevel(total) {
  if (total >= 90) return 'S'
  if (total >= 75) return 'A'
  if (total >= 60) return 'B'
  if (total >= 40) return 'C'
  return 'D'
}

/**
 * 获取等级对应的颜色
 * @param {string} level S/A/B/C/D
 * @returns {string} CSS颜色
 */
export function getLevelColor(level) {
  const colorMap = {
    S: '#67c23a',
    A: '#409eff',
    B: '#e6a23c',
    C: '#f56c6c',
    D: '#909399'
  }
  return colorMap[level] || '#909399'
}

/**
 * 获取等级对应的Tag类型
 * @param {string} level
 * @returns {string}
 */
export function getLevelTagType(level) {
  const typeMap = {
    S: 'success',
    A: 'primary',
    B: 'warning',
    C: 'danger',
    D: 'info'
  }
  return typeMap[level] || 'info'
}

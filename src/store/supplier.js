// src/store/supplier.js
// 基础版供应商评分状态管理（轻量级，适合单页直接引用）
// 生产环境请使用 src/store/modules/supplier.js（含缓存/日志/防重复提交）
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { getSupplierScore, saveSupplierScore } from '@/api/supplier'

export const useSupplierStore = defineStore('supplier', {
  state: () => ({
    supplierInfo: {
      id: '',
      name: '',
      platform: '' // 所属平台：淘宝/京东/1688等
    },
    scoreData: {
      totalScore: 0,
      // B2B评分维度
      dimensions: [
        { id: 'qualification', name: '供应商资质', score: 0, max: 20, desc: '营业执照/行业认证/品牌授权' },
        { id: 'storeAge',      name: '店铺年限',   score: 0, max: 15, desc: '开店时长，1年=5分，最高15分' },
        { id: 'credit',        name: '信用等级',   score: 0, max: 25, desc: '平台信用评级，AAA=25分，AA=20分' },
        { id: 'authentication',name: '认证资质',   score: 0, max: 20, desc: '企业认证/实力商家/深度验厂' },
        { id: 'service',       name: '服务能力',   score: 0, max: 20, desc: '响应速度/售后保障/发货时效' }
      ],
      // B2C已定品牌评分维度
      b2cBrandDimensions: [
        { id: 'authentic',  name: '原厂正品', score: 0, max: 30, desc: '品牌授权/正品保障' },
        { id: 'sales',      name: '销量',     score: 0, max: 20, desc: '近30天销量，越高分值越高' },
        { id: 'quality',    name: '商品质量', score: 0, max: 25, desc: '质量评分/抽检合格率' },
        { id: 'evaluation', name: '用户评价', score: 0, max: 25, desc: '好评率/评价数量' }
      ],
      // B2C未定品牌评分维度
      b2cNoBrandDimensions: [
        { id: 'price',      name: '价格竞争力', score: 0, max: 30, desc: '市场对比价格优势' },
        { id: 'quality',    name: '商品质量',   score: 0, max: 30, desc: '质量评分/抽检合格率' },
        { id: 'delivery',   name: '发货时效',   score: 0, max: 20, desc: '48小时内发货率' },
        { id: 'evaluation', name: '用户评价',   score: 0, max: 20, desc: '好评率/评价数量' }
      ],
      scoreType: 'B2B' // B2B / B2C_BRAND / B2C_NOBRAND
    },
    loading: false
  }),

  getters: {
    // 当前评分维度列表
    currentDimensions(state) {
      switch (state.scoreData.scoreType) {
        case 'B2C_BRAND':   return state.scoreData.b2cBrandDimensions
        case 'B2C_NOBRAND': return state.scoreData.b2cNoBrandDimensions
        default:            return state.scoreData.dimensions
      }
    },
    // 实时总分
    calculateTotalScore() {
      return this.currentDimensions.reduce((sum, item) => sum + (Number(item.score) || 0), 0)
    }
  },

  actions: {
    /** 获取供应商评分 */
    async fetchSupplierScore(supplierId) {
      this.loading = true
      try {
        const res = await getSupplierScore(supplierId)
        this.supplierInfo = res.data.supplierInfo
        this.scoreData = { ...this.scoreData, ...res.data.scoreData }
        this.scoreData.totalScore = this.calculateTotalScore
      } catch (error) {
        console.error('获取评分失败：', error)
        ElMessage.error('获取供应商评分失败')
      } finally {
        this.loading = false
      }
    },

    /** 保存供应商评分 */
    async saveSupplierScore() {
      this.loading = true
      try {
        await saveSupplierScore({
          supplierId: this.supplierInfo.id,
          scoreType: this.scoreData.scoreType,
          totalScore: this.calculateTotalScore,
          dimensions: this.currentDimensions
        })
        ElMessage.success('评分保存成功')
        return true
      } catch (error) {
        console.error('保存评分失败：', error)
        ElMessage.error('保存供应商评分失败')
        return false
      } finally {
        this.loading = false
      }
    },

    /** 重置当前类型评分 */
    resetScore() {
      this.currentDimensions.forEach(item => { item.score = 0 })
      this.scoreData.totalScore = 0
      ElMessage.info('评分已重置')
    },

    /** 切换评分类型 */
    changeScoreType(type) {
      this.scoreData.scoreType = type
      this.scoreData.totalScore = this.calculateTotalScore
    }
  }
})

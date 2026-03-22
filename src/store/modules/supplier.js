// src/store/modules/supplier.js
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  getSupplierScore,
  saveSupplierScore,
  getSupplierScoreHistory,
  batchSaveSupplierScore
} from '@/api/supplier'
import { addOperationLog } from '@/api/log'
import { Cache } from '@/utils/cache'
import { calculateTotalScore } from '@/utils/score'

const SCORE_DRAFT_KEY = 'ILBUY_SUPPLIER_SCORE_DRAFT_'
const SCORE_RULE_CACHE_KEY = 'ILBUY_SCORE_RULE_CACHE_'

export const useSupplierStore = defineStore('supplier', {
  state: () => ({
    supplierInfo: {
      id: '',
      name: '',
      platform: ''
    },
    scoreData: {
      totalScore: 0,
      dimensions: [],
      scoreType: 'B2B',
      lastUpdateTime: ''
    },
    loading: false,
    submitting: false,
    scoreHistory: [],
    historyLoading: false
  }),
  getters: {
    currentDimensions: (state) => {
      return state.scoreData.dimensions.filter(
        item => item.scoreType === state.scoreData.scoreType
      )
    },
    realTotalScore: (state) => {
      return calculateTotalScore(
        state.scoreData.dimensions.filter(
          item => item.scoreType === state.scoreData.scoreType
        )
      )
    }
  },
  actions: {
    async fetchSupplierScore(supplierId) {
      if (!supplierId) return

      this.loading = true
      try {
        const draft = Cache.get(SCORE_DRAFT_KEY + supplierId)
        if (draft) {
          this.scoreData = { ...this.scoreData, ...draft }
          this.supplierInfo.id = supplierId
          return
        }

        const res = await getSupplierScore(supplierId)
        this.supplierInfo = res.data.supplierInfo
        this.scoreData = {
          ...res.data.scoreData,
          totalScore: calculateTotalScore(res.data.scoreData.dimensions)
        }

        this.cacheScoreRule(this.scoreData.scoreType, res.data.scoreRule)
      } catch (error) {
        console.error('获取供应商评分失败：', error)
        this.scoreData = {
          totalScore: 0,
          dimensions: this.getDefaultDimensions(this.scoreData.scoreType),
          scoreType: this.scoreData.scoreType || 'B2B',
          lastUpdateTime: ''
        }
      } finally {
        this.loading = false
      }
    },

    async saveSupplierScore() {
      if (this.submitting) return false

      this.submitting = true
      try {
        this.scoreData.totalScore = this.realTotalScore
        this.scoreData.lastUpdateTime = new Date().toISOString()

        const params = {
          supplierId: this.supplierInfo.id,
          scoreType: this.scoreData.scoreType,
          totalScore: this.scoreData.totalScore,
          dimensions: this.currentDimensions
        }

        await saveSupplierScore(params)

        await addOperationLog({
          module: 'supplier_score',
          operation: 'edit',
          content: `修改供应商【${this.supplierInfo.name}】评分，总分：${this.scoreData.totalScore}`,
          resourceId: this.supplierInfo.id
        })

        Cache.remove(SCORE_DRAFT_KEY + this.supplierInfo.id)

        ElMessage.success('评分保存成功')
        return true
      } catch (error) {
        ElMessage.error('评分保存失败：' + (error.message || '服务器错误'))
        return false
      } finally {
        this.submitting = false
      }
    },

    async fetchScoreHistory(supplierId) {
      this.historyLoading = true
      try {
        const res = await getSupplierScoreHistory(supplierId)
        this.scoreHistory = res.data || []
      } catch (error) {
        console.error('获取评分历史失败：', error)
        this.scoreHistory = []
      } finally {
        this.historyLoading = false
      }
    },

    async batchSaveScore(data) {
      this.loading = true
      try {
        await batchSaveSupplierScore(data)
        await addOperationLog({
          module: 'supplier_score',
          operation: 'batch_edit',
          content: `批量修改${data.length}个供应商评分`,
          resourceId: data.map(item => item.supplierId).join(',')
        })
        ElMessage.success(`成功保存${data.length}个供应商评分`)
        return true
      } catch (error) {
        ElMessage.error('批量保存失败：' + (error.message || '服务器错误'))
        return false
      } finally {
        this.loading = false
      }
    },

    cacheScoreDraft() {
      if (!this.supplierInfo.id) return
      Cache.set(
        SCORE_DRAFT_KEY + this.supplierInfo.id,
        this.scoreData,
        24 * 60 * 60
      )
    },

    cacheScoreRule(type, rule) {
      Cache.set(
        SCORE_RULE_CACHE_KEY + type,
        rule,
        7 * 24 * 60 * 60
      )
    },

    getCachedScoreRule(type) {
      return Cache.get(SCORE_RULE_CACHE_KEY + type)
    },

    getDefaultDimensions(type = 'B2B') {
      const b2bDimensions = [
        { id: 'qualification', name: '供应商资质', score: 0, max: 20, desc: '营业执照/行业认证/品牌授权', scoreType: 'B2B' },
        { id: 'storeAge', name: '店铺年限', score: 0, max: 15, desc: '开店时长，1年=5分，最高15分', scoreType: 'B2B' },
        { id: 'credit', name: '信用等级', score: 0, max: 25, desc: '平台信用评级，AAA=25分，AA=20分', scoreType: 'B2B' },
        { id: 'authentication', name: '认证资质', score: 0, max: 20, desc: '企业认证/实力商家/深度验厂', scoreType: 'B2B' },
        { id: 'service', name: '服务能力', score: 0, max: 20, desc: '响应速度/售后保障/发货时效', scoreType: 'B2B' }
      ]

      const b2cBrandDimensions = [
        { id: 'authentic', name: '原厂正品', score: 0, max: 30, desc: '品牌授权/正品保障', scoreType: 'B2C_BRAND' },
        { id: 'sales', name: '销量', score: 0, max: 20, desc: '近30天销量，越高分值越高', scoreType: 'B2C_BRAND' },
        { id: 'quality', name: '商品质量', score: 0, max: 25, desc: '质量评分/抽检合格率', scoreType: 'B2C_BRAND' },
        { id: 'evaluation', name: '用户评价', score: 0, max: 25, desc: '好评率/评价数量', scoreType: 'B2C_BRAND' }
      ]

      const b2cNoBrandDimensions = [
        { id: 'price', name: '价格竞争力', score: 0, max: 30, desc: '市场对比价格优势', scoreType: 'B2C_NOBRAND' },
        { id: 'quality', name: '商品质量', score: 0, max: 30, desc: '质量评分/抽检合格率', scoreType: 'B2C_NOBRAND' },
        { id: 'delivery', name: '发货时效', score: 0, max: 20, desc: '48小时内发货率', scoreType: 'B2C_NOBRAND' },
        { id: 'evaluation', name: '用户评价', score: 0, max: 20, desc: '好评率/评价数量', scoreType: 'B2C_NOBRAND' }
      ]

      if (type === 'B2C_BRAND') return b2cBrandDimensions
      if (type === 'B2C_NOBRAND') return b2cNoBrandDimensions
      return b2bDimensions
    },

    resetScore() {
      this.scoreData.dimensions
        .filter(item => item.scoreType === this.scoreData.scoreType)
        .forEach(item => { item.score = 0 })
      this.scoreData.totalScore = 0
      Cache.remove(SCORE_DRAFT_KEY + this.supplierInfo.id)
      ElMessage.info('评分已重置')
    },

    changeScoreType(type) {
      this.scoreData.scoreType = type
      this.scoreData.totalScore = this.realTotalScore
    }
  }
})

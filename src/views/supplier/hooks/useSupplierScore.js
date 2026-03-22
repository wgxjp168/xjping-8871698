// src/views/supplier/hooks/useSupplierScore.js
import { ref, watch, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSupplierStore } from '@/store/modules/supplier'
import { useSupplierScoreAuth } from './useAuth'
import { validateScore, calculateTotalScore } from '@/utils/score'
import { getScoreRule } from '@/api/supplier'

// 自动保存间隔（30秒）
const AUTO_SAVE_INTERVAL = Number(import.meta.env.VITE_AUTO_SAVE_INTERVAL || 30) * 1000

export function useSupplierScore(supplierId) {
  const supplierStore = useSupplierStore()
  const router = useRouter()
  const { hasEditPermission } = useSupplierScoreAuth()

  const isEdit = ref(false)
  const ruleVisible = ref(false)
  const historyVisible = ref(false)
  const scoreRule = ref({})
  const autoSaveTimer = ref(null)

  const isLoading = computed(() => supplierStore.loading)
  const isSubmitting = computed(() => supplierStore.submitting)
  const canEdit = computed(() => hasEditPermission.value && !isSubmitting.value)

  const initScore = async () => {
    if (!supplierId) {
      ElMessage.error('供应商ID不能为空')
      router.push('/supplier/list')
      return
    }

    await supplierStore.fetchSupplierScore(supplierId)

    const cachedRule = supplierStore.getCachedScoreRule(supplierStore.scoreData.scoreType)
    if (cachedRule) {
      scoreRule.value = cachedRule
    } else {
      try {
        const res = await getScoreRule(supplierStore.scoreData.scoreType)
        scoreRule.value = res.data
        supplierStore.cacheScoreRule(supplierStore.scoreData.scoreType, res.data)
      } catch (error) {
        console.error('获取评分规则失败：', error)
        scoreRule.value = { title: '评分规则', rules: [] }
      }
    }

    if (isEdit.value) {
      startAutoSave()
    }
  }

  const toggleEdit = () => {
    if (!canEdit.value) {
      ElMessage.warning('暂无编辑权限或操作中，请稍后')
      return
    }

    isEdit.value = !isEdit.value

    if (isEdit.value) {
      startAutoSave()
      ElMessage.info('进入编辑模式，系统将自动保存草稿')
    } else {
      stopAutoSave()
      const currentTotal = calculateTotalScore(supplierStore.currentDimensions)
      if (currentTotal !== supplierStore.scoreData.totalScore) {
        ElMessageBox.confirm(
          '有未提交的评分修改，是否放弃？',
          '提示',
          {
            confirmButtonText: '放弃',
            cancelButtonText: '继续编辑',
            type: 'warning'
          }
        ).then(() => {
          supplierStore.fetchSupplierScore(supplierId)
        }).catch(() => {
          isEdit.value = true
          startAutoSave()
        })
      }
    }
  }

  const submitScore = async () => {
    if (!canEdit.value) return

    if (!validateScore(supplierStore.currentDimensions)) {
      ElMessage.error('评分超出范围，请检查各维度分值')
      return
    }

    try {
      await ElMessageBox.confirm(
        `确认提交供应商【${supplierStore.supplierInfo.name}】的评分？总分：${supplierStore.realTotalScore}`,
        '提交确认',
        {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'info'
        }
      )

      const success = await supplierStore.saveSupplierScore()
      if (success) {
        isEdit.value = false
        stopAutoSave()
      }
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('提交失败：' + (error.message || '未知错误'))
      }
    }
  }

  const autoSaveDraft = () => {
    if (!isEdit.value || !supplierId) return
    try {
      supplierStore.cacheScoreDraft()
      ElMessage.success({ message: '草稿已自动保存', duration: 1500 })
    } catch (error) {
      console.error('自动保存草稿失败：', error)
    }
  }

  const startAutoSave = () => {
    stopAutoSave()
    autoSaveTimer.value = setInterval(autoSaveDraft, AUTO_SAVE_INTERVAL)
  }

  const stopAutoSave = () => {
    if (autoSaveTimer.value) {
      clearInterval(autoSaveTimer.value)
      autoSaveTimer.value = null
    }
  }

  const changeScoreType = async (type) => {
    if (isSubmitting.value) return

    const currentTotal = calculateTotalScore(supplierStore.currentDimensions)
    if (isEdit.value && currentTotal !== supplierStore.scoreData.totalScore) {
      try {
        await ElMessageBox.confirm(
          '切换评分类型将清空当前修改，是否继续？',
          '提示',
          { confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning' }
        )
      } catch {
        return
      }
    }

    supplierStore.changeScoreType(type)

    const cachedRule = supplierStore.getCachedScoreRule(type)
    if (cachedRule) {
      scoreRule.value = cachedRule
    } else {
      try {
        const res = await getScoreRule(type)
        scoreRule.value = res.data
        supplierStore.cacheScoreRule(type, res.data)
      } catch (error) {
        console.error('获取评分规则失败：', error)
        scoreRule.value = { title: '评分规则', rules: [] }
      }
    }

    if (isEdit.value) {
      stopAutoSave()
      startAutoSave()
    }
  }

  const viewHistory = async () => {
    historyVisible.value = true
    await supplierStore.fetchScoreHistory(supplierId)
  }

  const resetScore = () => {
    if (isSubmitting.value) return
    ElMessageBox.confirm(
      '确认重置所有评分？',
      '重置确认',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' }
    ).then(() => {
      supplierStore.resetScore()
    })
  }

  watch(
    () => supplierStore.currentDimensions,
    () => {
      supplierStore.scoreData.totalScore = supplierStore.realTotalScore
    },
    { deep: true }
  )

  onUnmounted(() => {
    stopAutoSave()
  })

  return {
    isEdit,
    ruleVisible,
    historyVisible,
    scoreRule,
    isLoading,
    isSubmitting,
    canEdit,
    initScore,
    toggleEdit,
    submitScore,
    changeScoreType,
    viewHistory,
    resetScore
  }
}

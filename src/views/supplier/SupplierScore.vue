<template>
  <div class="supplier-score-page">
    <!-- 页面头部 -->
    <el-page-header
      :content="`供应商评分 - ${supplierStore.supplierInfo.name || '加载中...'}`"
      @back="goBack"
    />

    <!-- 操作栏 -->
    <div class="operation-bar">
      <div class="left-actions">
        <el-select
          v-model="scoreType"
          placeholder="选择评分类型"
          :disabled="isSubmitting"
          style="width: 200px; margin-right: 16px"
          @change="changeScoreType"
        >
          <el-option label="B2B企业采购" value="B2B" />
          <el-option label="B2C已定品牌" value="B2C_BRAND" />
          <el-option label="B2C未定品牌" value="B2C_NOBRAND" />
        </el-select>

        <el-button text @click="ruleVisible = true" :icon="QuestionFilled">
          评分规则
        </el-button>

        <el-button text @click="viewHistory" :icon="Clock">
          评分历史
        </el-button>
      </div>

      <div class="operation-buttons">
        <el-button
          v-if="!isEdit && canEdit"
          v-permission="['supplier:score:edit']"
          type="primary"
          :icon="Edit"
          :loading="isLoading"
          @click="toggleEdit"
        >
          编辑评分
        </el-button>

        <template v-if="isEdit">
          <el-button
            type="success"
            :icon="Check"
            :loading="isSubmitting"
            @click="submitScore"
          >
            提交评分
          </el-button>

          <el-button
            type="warning"
            :icon="Refresh"
            :disabled="isSubmitting"
            @click="resetScore"
          >
            重置
          </el-button>

          <el-button
            type="info"
            :icon="Close"
            :disabled="isSubmitting"
            @click="toggleEdit"
          >
            取消
          </el-button>
        </template>
      </div>
    </div>

    <!-- 评分内容区 -->
    <div class="score-content">
      <!-- 加载骨架屏 -->
      <ScoreSkeleton v-if="isLoading" />

      <!-- 查看模式 -->
      <ScoreCard
        v-else-if="!isEdit"
        :total-score="supplierStore.scoreData.totalScore"
        :dimensions="supplierStore.currentDimensions"
        :supplier-name="supplierStore.supplierInfo.name"
        :score-data="supplierStore.scoreData"
      />

      <!-- 编辑模式 -->
      <el-card v-else class="score-edit-card" shadow="never">
        <el-form
          ref="scoreFormRef"
          :model="scoreForm"
          label-width="120px"
          class="score-form"
        >
          <el-form-item
            v-for="item in supplierStore.currentDimensions"
            :key="item.id"
            :label="item.name"
            :rules="[
              { required: true, message: '请输入分值', trigger: 'blur' },
              { type: 'number', min: 0, max: item.max,
                message: `分值必须在0-${item.max}之间`, trigger: 'blur' }
            ]"
          >
            <el-input-number
              v-model="item.score"
              :min="0"
              :max="item.max"
              controls-position="right"
              style="width: 200px"
              :disabled="isSubmitting"
            />
            <span class="dimension-desc">
              （满分{{ item.max }}分：{{ item.desc }}）
            </span>
          </el-form-item>

          <el-form-item label="总分" class="total-score-item">
            <el-input
              :model-value="supplierStore.scoreData.totalScore"
              disabled
              style="width: 200px"
            />
            <span class="total-score-tips">总分根据各维度分值自动计算</span>
          </el-form-item>
        </el-form>

        <div class="auto-save-tip">
          <el-icon><Clock /></el-icon>
          编辑模式下，系统每30秒自动保存草稿
        </div>
      </el-card>

      <!-- 空数据状态 -->
      <div
        v-if="!isLoading && supplierStore.currentDimensions.length === 0"
        class="empty-state"
      >
        <el-empty description="暂无评分数据" />
        <el-button
          v-if="canEdit"
          type="primary"
          style="margin-top: 16px"
          @click="initDefaultScore"
        >
          初始化默认评分维度
        </el-button>
      </div>
    </div>

    <!-- 评分规则弹窗 -->
    <ScoreRuleModal
      v-model="ruleVisible"
      :rule-data="scoreRule"
      :score-type="supplierStore.scoreData.scoreType"
    />

    <!-- 评分历史弹窗 -->
    <ScoreHistory
      v-model="historyVisible"
      :history-list="supplierStore.scoreHistory"
      :loading="supplierStore.historyLoading"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Check, Refresh, Close, Clock, QuestionFilled } from '@element-plus/icons-vue'
import { useSupplierStore } from '@/store/modules/supplier'
import { useSupplierScore } from './hooks/useSupplierScore'
import ScoreCard from './components/ScoreCard.vue'
import ScoreRuleModal from './components/ScoreRuleModal.vue'
import ScoreHistory from './components/ScoreHistory.vue'
import ScoreSkeleton from './components/ScoreSkeleton.vue'

const route = useRoute()
const router = useRouter()
const supplierId = route.params.supplierId
const supplierStore = useSupplierStore()

const {
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
} = useSupplierScore(supplierId)

const scoreType = ref(supplierStore.scoreData.scoreType)
const scoreFormRef = ref(null)
const scoreForm = ref({ dimensions: {} })

const goBack = () => router.back()

const initDefaultScore = () => {
  supplierStore.scoreData.dimensions = supplierStore.getDefaultDimensions(
    supplierStore.scoreData.scoreType
  )
  ElMessage.success('已初始化默认评分维度')
}

onMounted(async () => {
  if (!supplierId) {
    ElMessage.error('供应商ID不能为空')
    router.push('/supplier/list')
    return
  }
  await initScore()
  scoreType.value = supplierStore.scoreData.scoreType
})
</script>

<style scoped lang="scss">
.supplier-score-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0;
  padding: 16px;
  background: #fff;
  border-radius: 4px;
}

.left-actions {
  display: flex;
  align-items: center;
}

.operation-buttons {
  display: flex;
  gap: 8px;
}

.score-content {
  background: #fff;
  border-radius: 4px;
  padding: 24px;
  min-height: 500px;
}

.score-edit-card {
  border: none;
}

.score-form {
  max-width: 800px;
  margin: 0 auto;
}

.dimension-desc {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.total-score-item {
  margin-top: 24px;
  border-top: 1px dashed #e6e6e6;
  padding-top: 16px;
}

.total-score-tips {
  margin-left: 12px;
  font-size: 12px;
  color: #409eff;
}

.auto-save-tip {
  margin-top: 24px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 4px;
  font-size: 12px;
  color: #409eff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-state {
  text-align: center;
  padding: 48px 0;
}
</style>

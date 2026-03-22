<template>
  <div class="score-card-container">
    <!-- 供应商信息 -->
    <div class="supplier-header">
      <h3 class="supplier-name">{{ supplierName || '未知供应商' }}</h3>
      <span class="update-time" v-if="scoreData && scoreData.lastUpdateTime">
        最后更新：{{ formatTime(scoreData.lastUpdateTime) }}
      </span>
    </div>

    <!-- 总分展示 -->
    <div class="total-score-section">
      <div class="total-score">
        <span class="score-value">{{ totalScore }}</span>
        <span class="score-label">总分</span>
      </div>
      <el-rate
        v-model="starRating"
        disabled
        :max="5"
        class="score-star"
        show-text
        text-color="#409eff"
      />
      <div class="score-grade">{{ getGradeText(starRating) }}</div>
    </div>

    <!-- 维度评分列表 -->
    <div class="dimensions-section">
      <h4 class="section-title">评分维度明细</h4>
      <el-table
        :data="dimensions"
        border
        size="default"
        :empty-text="emptyText"
        class="dimensions-table"
      >
        <el-table-column prop="name" label="评分维度" width="120" />
        <el-table-column label="分值" width="200">
          <template #default="{ row }">
            <div class="score-progress">
              <el-progress
                :percentage="Math.round((row.score / row.max) * 100)"
                :stroke-width="16"
                :show-text="false"
                :color="getProgressColor(row.score / row.max)"
              />
              <span class="score-text">{{ row.score }}/{{ row.max }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="desc" label="评分说明" show-overflow-tooltip />
        <el-table-column label="星级" width="130">
          <template #default="{ row }">
            <el-rate
              :model-value="getDimensionStar(row.score, row.max)"
              disabled
              :max="5"
              size="small"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { convertScoreToStar } from '@/utils/score'

const props = defineProps({
  totalScore: {
    type: Number,
    default: 0
  },
  dimensions: {
    type: Array,
    default: () => []
  },
  supplierName: {
    type: String,
    default: ''
  },
  scoreData: {
    type: Object,
    default: () => ({})
  }
})

const starRating = computed(() => convertScoreToStar(props.totalScore, 100))
const emptyText = '暂无评分维度数据'

const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN', { hour12: false })
}

const getGradeText = (star) => {
  const grades = ['极差', '较差', '一般', '良好', '优秀', '极佳']
  return grades[Math.round(star)] || '一般'
}

const getProgressColor = (ratio) => {
  if (ratio >= 0.8) return '#67c23a'
  if (ratio >= 0.6) return '#e6a23c'
  if (ratio >= 0.4) return '#f56c6c'
  return '#909399'
}

const getDimensionStar = (score, max) => convertScoreToStar(score, max)
</script>

<style scoped lang="scss">
.score-card-container {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.supplier-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e6e6e6;
}

.supplier-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.update-time {
  font-size: 12px;
  color: #909399;
}

.total-score-section {
  text-align: center;
  padding: 24px 0;
  margin-bottom: 24px;
  background: #f8f9fa;
  border-radius: 8px;
}

.total-score {
  margin-bottom: 16px;
}

.score-value {
  font-size: 48px;
  font-weight: 700;
  color: #409eff;
  margin-right: 8px;
}

.score-label {
  font-size: 16px;
  color: #606266;
}

.score-star {
  margin-bottom: 8px;
}

.score-grade {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}

.dimensions-section {
  margin-top: 32px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 4px solid #409eff;
}

.score-progress {
  position: relative;
  padding-right: 60px;
}

.score-text {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: #606266;
}
</style>

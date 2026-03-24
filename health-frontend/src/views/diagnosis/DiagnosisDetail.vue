<template>
  <div class="page-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h3>诊断报告详情</h3>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>诊断信息</span>
              <div class="header-actions">
                <el-tag :type="getStatusType(diagnosis.status)" size="large">
                  {{ getStatusLabel(diagnosis.status) }}
                </el-tag>
                <el-tag :type="getRiskType(diagnosis.riskLevel)" size="large" style="margin-left:8px">
                  {{ getRiskLabel(diagnosis.riskLevel) }}
                </el-tag>
              </div>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="体检单号">{{ diagnosis.orderNo }}</el-descriptions-item>
            <el-descriptions-item label="患者姓名">{{ diagnosis.patientName }}</el-descriptions-item>
            <el-descriptions-item label="诊断医生">{{ diagnosis.doctorName }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ diagnosis.createTime }}</el-descriptions-item>
            <el-descriptions-item label="确认时间">{{ diagnosis.confirmTime || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ diagnosis.publishTime || '-' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 健康评分 -->
          <div class="score-section">
            <div class="score-title">健康评分</div>
            <div class="score-display">
              <el-progress
                type="dashboard"
                :percentage="diagnosis.healthScore || 0"
                :color="getScoreColor(diagnosis.healthScore)"
                :width="140"
              />
              <div class="score-label">{{ getScoreText(diagnosis.healthScore) }}</div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">诊断结论</div>
            <div class="section-content">{{ diagnosis.conclusion || '暂无' }}</div>
          </div>

          <div class="section">
            <div class="section-title">健康建议</div>
            <div class="section-content">{{ diagnosis.suggestion || '暂无' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header><span>异常指标</span></template>
          <div v-if="abnormalItems.length === 0" class="empty-tip">
            <el-icon size="40" color="#c0c4cc"><CircleCheck /></el-icon>
            <p>无异常指标</p>
          </div>
          <div v-else>
            <div v-for="item in abnormalItems" :key="item.name" class="abnormal-item">
              <div class="ai-name">{{ item.name }}</div>
              <div class="ai-value" :class="item.flag === 'HIGH' ? 'val-high' : 'val-low'">
                {{ item.value }} {{ item.unit }}
                <el-icon><component :is="item.flag === 'HIGH' ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
              </div>
              <div class="ai-range">参考: {{ item.normalRange }}</div>
            </div>
          </div>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header><span>操作</span></template>
          <el-button type="success" style="width:100%;margin-bottom:10px"
            v-if="diagnosis.status === 'DRAFT'" @click="handleConfirm">
            确认报告
          </el-button>
          <el-button type="primary" style="width:100%;margin-bottom:10px"
            v-if="diagnosis.status === 'CONFIRMED'" @click="handlePublish">
            发布报告
          </el-button>
          <el-button style="width:100%" @click="$router.push(`/diagnosis/edit/${diagnosis.id}`)">
            编辑报告
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDiagnosisDetail, confirmDiagnosis, publishDiagnosis } from '@/api/diagnosis'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const diagnosis = ref({})

const abnormalItems = computed(() => {
  if (!diagnosis.value.abnormalItems) return []
  try { return JSON.parse(diagnosis.value.abnormalItems) } catch { return [] }
})

const getStatusType = (s) => ({ DRAFT: 'info', CONFIRMED: 'warning', PUBLISHED: 'success' }[s] || '')
const getStatusLabel = (s) => ({ DRAFT: '草稿', CONFIRMED: '已确认', PUBLISHED: '已发布' }[s] || s)
const getRiskType = (r) => ({ LOW: 'success', MEDIUM: 'warning', HIGH: 'danger' }[r] || 'info')
const getRiskLabel = (r) => ({ LOW: '低风险', MEDIUM: '中风险', HIGH: '高风险' }[r] || r)
const getScoreColor = (score) => {
  if (!score) return '#909399'
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}
const getScoreText = (score) => {
  if (!score) return '暂无'
  if (score >= 80) return '良好'
  if (score >= 60) return '一般'
  return '需关注'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDiagnosisDetail(route.params.id)
    diagnosis.value = res.data
  } finally {
    loading.value = false
  }
}

const handleConfirm = async () => {
  await ElMessageBox.confirm('确认后报告将不可修改，是否继续？', '提示', { type: 'warning' })
  await confirmDiagnosis(route.params.id)
  ElMessage.success('已确认')
  loadData()
}

const handlePublish = async () => {
  await ElMessageBox.confirm('发布后患者可查看该报告，是否发布？', '提示', { type: 'warning' })
  await publishDiagnosis(route.params.id)
  ElMessage.success('已发布')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h3 { margin: 0; font-size: 18px; }
.score-section { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
.score-title { font-weight: 600; margin-bottom: 12px; }
.score-display { display: flex; flex-direction: column; align-items: center; }
.score-label { margin-top: 8px; font-size: 16px; font-weight: 600; color: #666; }
.section { margin-top: 20px; }
.section-title { font-weight: 600; margin-bottom: 8px; color: #333; }
.section-content { background: #f5f7fa; padding: 12px; border-radius: 6px; line-height: 1.8; color: #555; }
.empty-tip { text-align: center; padding: 30px; color: #c0c4cc; }
.empty-tip p { margin-top: 8px; }
.abnormal-item { padding: 10px; border-bottom: 1px solid #f0f0f0; }
.abnormal-item:last-child { border-bottom: none; }
.ai-name { font-weight: 600; color: #333; }
.ai-value { font-size: 16px; display: flex; align-items: center; gap: 4px; }
.ai-range { font-size: 12px; color: #909399; margin-top: 2px; }
.val-high { color: #f56c6c; }
.val-low { color: #409eff; }
.header-actions { display: flex; }
</style>

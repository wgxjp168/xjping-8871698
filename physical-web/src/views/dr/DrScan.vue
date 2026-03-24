<template>
  <div class="dr-scan-page">
    <el-card class="scan-card">
      <template #header>
        <div class="card-header">
          <el-icon color="#409EFF" size="20"><Camera /></el-icon>
          <span>DR条码扫描</span>
          <el-tag type="info" size="small">请使用扫码枪扫描DR条码</el-tag>
        </div>
      </template>

      <!-- 扫码输入区 -->
      <div class="scan-input-area">
        <el-input
          ref="scanInputRef"
          v-model="drCode"
          placeholder="扫描DR条码（扫码枪自动触发）"
          size="large"
          clearable
          :prefix-icon="Scan"
          @keyup.enter="handleScan"
          class="scan-input"
        >
          <template #append>
            <el-button type="primary" :loading="scanLoading" @click="handleScan">
              扫描确认
            </el-button>
          </template>
        </el-input>
        <div class="scan-tip">
          <el-icon><InfoFilled /></el-icon>
          将扫码枪对准DR条码扫描，系统自动识别居民信息
        </div>
      </div>
    </el-card>

    <!-- 居民信息展示（扫码成功后） -->
    <el-card v-if="scanResult" class="resident-card" :class="{ 'cannot-exam': !canExam }">
      <template #header>
        <div class="card-header">
          <el-icon :color="canExam ? '#67C23A' : '#F56C6C'" size="20">
            <component :is="canExam ? 'CircleCheck' : 'CircleClose'" />
          </el-icon>
          <span>居民信息确认</span>
          <el-tag :type="canExam ? 'success' : 'danger'">
            {{ canExam ? '可以检查' : '不可检查' }}
          </el-tag>
        </div>
      </template>

      <div v-if="!canExam" class="cannot-reason">
        <el-alert :title="scanResult.cannotReason" type="warning" :closable="false" show-icon />
      </div>

      <el-descriptions :column="3" border class="resident-desc">
        <el-descriptions-item label="DR条码">
          <el-tag>{{ scanResult.drCode }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请单号">{{ scanResult.applyNo }}</el-descriptions-item>
        <el-descriptions-item label="检查部位">
          <el-tag type="warning">{{ scanResult.examPart }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="居民姓名">
          <strong>{{ scanResult.residentName }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="身份证号">{{ scanResult.idCard }}</el-descriptions-item>
        <el-descriptions-item label="扫码时间">{{ formatTime(scanResult.scanTime) }}</el-descriptions-item>
      </el-descriptions>

      <!-- 检查结果录入表单（可检查时显示） -->
      <div v-if="canExam" class="result-form">
        <el-divider content-position="left">录入检查结果</el-divider>
        <el-form ref="resultFormRef" :model="resultForm" :rules="resultRules" label-width="120px">
          <el-form-item label="检查结论" prop="conclusion">
            <el-radio-group v-model="resultForm.conclusion" size="large">
              <el-radio-button label="NORMAL">
                <el-icon><Select /></el-icon> 正常
              </el-radio-button>
              <el-radio-button label="ABNORMAL">
                <el-icon><WarningFilled /></el-icon> 异常
              </el-radio-button>
              <el-radio-button label="RECHECK">
                <el-icon><Refresh /></el-icon> 需复查
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="检查结果描述" prop="drResult">
            <el-input
              v-model="resultForm.drResult"
              type="textarea"
              :rows="4"
              placeholder="请输入DR检查结果描述（如：两肺纹理清晰，未见明显实质性病变...）"
            />
          </el-form-item>

          <el-form-item label="备注">
            <el-input v-model="resultForm.remark" placeholder="可选，特殊情况备注" />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="submitLoading"
              @click="handleSubmit"
            >
              提交检查结果
            </el-button>
            <el-button size="large" @click="resetScan">重新扫码</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- 今日DR检查统计 -->
    <el-card class="stat-card">
      <template #header>
        <span>今日DR检查统计</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6" v-for="stat in stats" :key="stat.label">
          <div class="stat-item" :style="{ borderLeft: `4px solid ${stat.color}` }">
            <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Scan } from '@element-plus/icons-vue'
import { scanDrBarcode, submitDrResult, getDrPage } from '@/api/dr'
import { useUserStore } from '@/store/user'
import dayjs from 'dayjs'

const userStore = useUserStore()
const scanInputRef = ref(null)
const resultFormRef = ref(null)
const drCode = ref('')
const scanResult = ref(null)
const canExam = ref(false)
const scanLoading = ref(false)
const submitLoading = ref(false)

const resultForm = reactive({
  id: null,
  drCode: '',
  conclusion: 'NORMAL',
  drResult: '',
  examDoctorId: userStore.userInfo?.docId,
  examDoctor: userStore.userInfo?.name,
  remark: ''
})

const resultRules = {
  conclusion: [{ required: true, message: '请选择检查结论' }],
  drResult: [{ required: true, message: '请输入检查结果描述', trigger: 'blur' }]
}

const stats = ref([
  { label: '待检查', value: 0, color: '#909399' },
  { label: '已完成', value: 0, color: '#67C23A' },
  { label: '异常', value: 0, color: '#F56C6C' },
  { label: '已同步', value: 0, color: '#409EFF' }
])

onMounted(async () => {
  // 自动聚焦扫码输入框，适配扫码枪
  nextTick(() => scanInputRef.value?.focus())
  await loadStats()
})

async function handleScan() {
  if (!drCode.value.trim()) {
    ElMessage.warning('请输入或扫描DR条码')
    return
  }
  scanLoading.value = true
  scanResult.value = null
  try {
    const res = await scanDrBarcode({ drCode: drCode.value.trim() })
    if (res.code === 200) {
      scanResult.value = res.data
      canExam.value = res.data.canExam === 1
      resultForm.id = res.data.id
      resultForm.drCode = res.data.drCode
      if (canExam.value) {
        ElMessage.success(`扫码成功：${res.data.residentName}，请录入检查结果`)
      } else {
        ElMessage.warning(res.data.cannotReason)
      }
    }
  } finally {
    scanLoading.value = false
  }
}

async function handleSubmit() {
  const valid = await resultFormRef.value.validate().catch(() => false)
  if (!valid) return

  await ElMessageBox.confirm(
    `确认提交【${scanResult.value.residentName}】的DR检查结果？`,
    '提交确认',
    { type: 'warning' }
  )

  submitLoading.value = true
  try {
    const res = await submitDrResult({ ...resultForm })
    if (res.code === 200) {
      ElMessage.success('DR检查结果提交成功，已触发同步至县域系统')
      resetScan()
      await loadStats()
    }
  } finally {
    submitLoading.value = false
  }
}

function resetScan() {
  drCode.value = ''
  scanResult.value = null
  canExam.value = false
  Object.assign(resultForm, {
    id: null, drCode: '', conclusion: 'NORMAL', drResult: '', remark: ''
  })
  nextTick(() => scanInputRef.value?.focus())
}

async function loadStats() {
  try {
    const today = dayjs().format('YYYY-MM-DD')
    const res = await getDrPage({ current: 1, size: 1, startDate: today, endDate: today })
    // 这里简化统计，实际可以按status分别查询
  } catch (e) { /* 静默失败 */ }
}

function formatTime(t) {
  return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'
}
</script>

<style scoped lang="less">
.dr-scan-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.scan-input-area {
  .scan-input {
    font-size: 16px;
    :deep(.el-input__inner) {
      font-size: 18px;
      height: 52px;
    }
  }
  .scan-tip {
    margin-top: 8px;
    color: #909399;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.resident-card {
  &.cannot-exam {
    border: 2px solid #F56C6C;
  }
  .cannot-reason {
    margin-bottom: 16px;
  }
  .resident-desc {
    margin-bottom: 16px;
  }
}

.result-form {
  margin-top: 16px;
}

.stat-card {
  .stat-item {
    padding: 16px 20px;
    background: #f8f9fa;
    border-radius: 8px;
    .stat-value {
      font-size: 28px;
      font-weight: 700;
    }
    .stat-label {
      font-size: 13px;
      color: #666;
      margin-top: 4px;
    }
  }
}
</style>

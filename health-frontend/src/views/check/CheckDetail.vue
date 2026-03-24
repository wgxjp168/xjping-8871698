<template>
  <div class="page-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h3>体检详情</h3>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <!-- 基本信息 -->
      <el-col :span="24">
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <span>基本信息</span>
              <el-tag :type="getStatusType(order.status)">{{ getStatusLabel(order.status) }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="体检单号">{{ order.orderNo }}</el-descriptions-item>
            <el-descriptions-item label="患者姓名">{{ order.patientName }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ order.patientPhone }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ order.patientGender === 1 ? '男' : '女' }}</el-descriptions-item>
            <el-descriptions-item label="检查套餐">{{ order.packageName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="体检日期">{{ order.checkDate }}</el-descriptions-item>
            <el-descriptions-item label="负责医生">{{ order.doctorName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="健康评分">
              <span :class="getScoreClass(order.totalScore)" style="font-size:18px;font-weight:bold">
                {{ order.totalScore ?? '-' }}
              </span>
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="order.summary" style="margin-top:12px">
            <strong>体检总结：</strong>{{ order.summary }}
          </div>
        </el-card>
      </el-col>

      <!-- 检查结果 -->
      <el-col :span="24" style="margin-top:16px">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>检查结果明细</span>
              <el-button type="primary" :icon="Plus" @click="showResultForm = true"
                v-if="['CREATED','IN_PROGRESS'].includes(order.status)">
                录入结果
              </el-button>
            </div>
          </template>

          <el-table :data="results" border stripe>
            <el-table-column prop="category" label="分类" width="80" />
            <el-table-column prop="itemName" label="检查项目" width="150" />
            <el-table-column prop="value" label="检测值" width="100">
              <template #default="{ row }">
                <span :class="getFlagClass(row.flag)">{{ row.value }} {{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="normalRange" label="参考范围" />
            <el-table-column prop="flag" label="标记" width="80">
              <template #default="{ row }">
                <el-tag :type="getFlagTagType(row.flag)" size="small">{{ getFlagLabel(row.flag) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="deviceName" label="采集设备" width="130" />
            <el-table-column prop="dataSource" label="来源" width="80">
              <template #default="{ row }">
                <el-tag :type="row.dataSource === 'DEVICE' ? 'success' : 'info'" size="small">
                  {{ row.dataSource === 'DEVICE' ? '设备' : '手动' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="checkTime" label="检查时间" width="150" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 录入结果对话框 -->
    <el-dialog v-model="showResultForm" title="录入检查结果" width="520px">
      <el-form :model="resultForm" label-width="100px">
        <el-form-item label="检查项ID" required>
          <el-input-number v-model="resultForm.itemId" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="检测值" required>
          <el-input v-model="resultForm.value" placeholder="请输入检测值" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-radio-group v-model="resultForm.dataSource">
            <el-radio value="MANUAL">手动录入</el-radio>
            <el-radio value="DEVICE">设备采集</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="采集设备" v-if="resultForm.dataSource === 'DEVICE'">
          <el-select v-model="resultForm.deviceId" placeholder="选择设备" style="width:100%">
            <el-option v-for="d in onlineDevices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="resultForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResultForm = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitResult">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getCheckOrderDetail, saveCheckResult } from '@/api/check'
import { getOnlineDevices } from '@/api/device'

const route = useRoute()
const loading = ref(false)
const order = ref({})
const results = ref([])
const showResultForm = ref(false)
const submitting = ref(false)
const onlineDevices = ref([])

const resultForm = reactive({
  orderId: null, itemId: null, value: '',
  dataSource: 'MANUAL', deviceId: null, remark: ''
})

const getStatusType = (s) => ({ CREATED: '', IN_PROGRESS: 'warning', REVIEWING: 'info', COMPLETED: 'success' }[s] || '')
const getStatusLabel = (s) => ({ CREATED: '待检查', IN_PROGRESS: '检查中', REVIEWING: '待审核', COMPLETED: '已完成' }[s] || s)
const getScoreClass = (score) => !score ? '' : score >= 80 ? 'score-good' : score >= 60 ? 'score-mid' : 'score-bad'
const getFlagClass = (flag) => ({ HIGH: 'val-high', LOW: 'val-low', ABNORMAL: 'val-abnormal' }[flag] || '')
const getFlagTagType = (flag) => ({ NORMAL: 'success', HIGH: 'danger', LOW: 'warning', ABNORMAL: 'danger' }[flag] || 'info')
const getFlagLabel = (flag) => ({ NORMAL: '正常', HIGH: '偏高', LOW: '偏低', ABNORMAL: '异常' }[flag] || flag)

const loadData = async () => {
  loading.value = true
  try {
    const [orderRes, deviceRes] = await Promise.all([
      getCheckOrderDetail(route.params.id),
      getOnlineDevices()
    ])
    order.value = orderRes.data
    results.value = orderRes.data.results || []
    onlineDevices.value = deviceRes.data || []
    resultForm.orderId = Number(route.params.id)
  } finally {
    loading.value = false
  }
}

const submitResult = async () => {
  if (!resultForm.itemId || !resultForm.value) {
    ElMessage.warning('请填写检查项ID和检测值')
    return
  }
  submitting.value = true
  try {
    await saveCheckResult({ ...resultForm })
    ElMessage.success('录入成功')
    showResultForm.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h3 { margin: 0; font-size: 18px; }
.info-card { margin-bottom: 0; }
.score-good { color: #67c23a; }
.score-mid { color: #e6a23c; }
.score-bad { color: #f56c6c; }
.val-high { color: #f56c6c; font-weight: 600; }
.val-low { color: #409eff; font-weight: 600; }
.val-abnormal { color: #f56c6c; font-weight: 600; }
</style>

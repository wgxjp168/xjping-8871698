<template>
  <div class="page-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      <h3>设备详情</h3>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>基本信息</span>
              <el-tag :type="getStatusType(device.status)" size="large">
                {{ getStatusLabel(device.status) }}
              </el-tag>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="设备名称">{{ device.name }}</el-descriptions-item>
            <el-descriptions-item label="设备编码">{{ device.code }}</el-descriptions-item>
            <el-descriptions-item label="设备类型">{{ getTypeLabel(device.type) }}</el-descriptions-item>
            <el-descriptions-item label="设备型号">{{ device.model }}</el-descriptions-item>
            <el-descriptions-item label="生产厂商">{{ device.manufacturer }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ device.serialNo }}</el-descriptions-item>
            <el-descriptions-item label="IP地址">{{ device.ipAddress }}:{{ device.port }}</el-descriptions-item>
            <el-descriptions-item label="通信协议">{{ device.protocol }}</el-descriptions-item>
            <el-descriptions-item label="最后心跳">{{ device.lastHeartbeat || '-' }}</el-descriptions-item>
            <el-descriptions-item label="校准日期">{{ device.calibrationDate || '-' }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ device.description || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="action-buttons">
            <el-button type="primary" @click="sendHeartbeat" :loading="hbLoading">模拟心跳</el-button>
            <el-button type="success" @click="showDataUpload = true">上传数据</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>历史数据</span>
              <el-button link @click="loadDeviceData">刷新</el-button>
            </div>
          </template>
          <el-table :data="deviceData" size="small" max-height="400">
            <el-table-column prop="itemCode" label="检查项编码" width="120" />
            <el-table-column prop="value" label="数值" width="100" />
            <el-table-column prop="unit" label="单位" width="70" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'CONFIRMED' ? 'success' : 'info'" size="small">
                  {{ row.status === 'CONFIRMED' ? '已确认' : '待确认' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="measureTime" label="测量时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据上传对话框 -->
    <el-dialog v-model="showDataUpload" title="上传设备数据" width="440px">
      <el-form :model="uploadForm" label-width="110px">
        <el-form-item label="检查项编码">
          <el-input v-model="uploadForm.itemCode" placeholder="如: CI004" />
        </el-form-item>
        <el-form-item label="数值" required>
          <el-input v-model="uploadForm.value" placeholder="请输入测量值" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="uploadForm.unit" placeholder="如: mmHg" />
        </el-form-item>
        <el-form-item label="体检单ID">
          <el-input-number v-model="uploadForm.orderId" :min="1" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDataUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDeviceById, getDeviceData, deviceHeartbeat, uploadDeviceData } from '@/api/device'

const route = useRoute()
const loading = ref(false)
const hbLoading = ref(false)
const uploading = ref(false)
const device = ref({})
const deviceData = ref([])
const showDataUpload = ref(false)
const uploadForm = reactive({ itemCode: '', value: '', unit: '', orderId: null })

const deviceTypes = [
  { value: 'BLOOD_PRESSURE', label: '血压计' }, { value: 'ECG', label: '心电图仪' },
  { value: 'GLUCOMETER', label: '血糖仪' }, { value: 'OXIMETER', label: '血氧仪' },
  { value: 'XRAY', label: 'X光机' }, { value: 'ULTRASOUND', label: '超声诊断仪' }
]

const getTypeLabel = (type) => deviceTypes.find(t => t.value === type)?.label || type
const getStatusType = (s) => ({ ONLINE: 'success', OFFLINE: 'info', FAULT: 'danger' }[s] || 'info')
const getStatusLabel = (s) => ({ ONLINE: '在线', OFFLINE: '离线', FAULT: '故障' }[s] || s)

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDeviceById(route.params.id)
    device.value = res.data
    await loadDeviceData()
  } finally {
    loading.value = false
  }
}

const loadDeviceData = async () => {
  const res = await getDeviceData(route.params.id)
  deviceData.value = res.data || []
}

const sendHeartbeat = async () => {
  hbLoading.value = true
  try {
    await deviceHeartbeat(device.value.code)
    ElMessage.success('心跳发送成功，设备已标记为在线')
    loadData()
  } finally {
    hbLoading.value = false
  }
}

const submitUpload = async () => {
  if (!uploadForm.value) { ElMessage.warning('请填写测量值'); return }
  uploading.value = true
  try {
    await uploadDeviceData(device.value.code, { ...uploadForm })
    ElMessage.success('数据上传成功')
    showDataUpload.value = false
    loadDeviceData()
  } finally {
    uploading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h3 { margin: 0; font-size: 18px; }
.action-buttons { display: flex; gap: 12px; margin-top: 20px; }
</style>

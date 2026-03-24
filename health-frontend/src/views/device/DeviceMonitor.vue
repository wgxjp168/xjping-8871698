<template>
  <div class="page-container">
    <el-row :gutter="20" class="header-row">
      <el-col :span="24">
        <el-card class="monitor-header">
          <div class="monitor-title">
            <el-icon size="24" color="#409eff"><Monitor /></el-icon>
            <h3>设备实时监控</h3>
            <el-tag type="success">实时更新</el-tag>
          </div>
          <div class="monitor-stats">
            <div class="stat-item">
              <div class="stat-num online">{{ stats.online }}</div>
              <div class="stat-label">在线</div>
            </div>
            <div class="stat-item">
              <div class="stat-num offline">{{ stats.offline }}</div>
              <div class="stat-label">离线</div>
            </div>
            <div class="stat-item">
              <div class="stat-num fault">{{ stats.fault }}</div>
              <div class="stat-label">故障</div>
            </div>
            <div class="stat-item">
              <div class="stat-num total">{{ stats.total }}</div>
              <div class="stat-label">总计</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="8" v-for="device in devices" :key="device.id">
        <el-card class="device-card" :class="getCardClass(device.status)" shadow="hover">
          <div class="device-header">
            <div class="device-icon">
              <el-icon size="32"><component :is="getDeviceIcon(device.type)" /></el-icon>
            </div>
            <div class="device-info">
              <div class="device-name">{{ device.name }}</div>
              <div class="device-code">{{ device.code }}</div>
            </div>
            <el-badge is-dot :type="getStatusType(device.status)" class="status-dot" />
          </div>

          <el-divider style="margin: 10px 0" />

          <div class="device-metrics">
            <div class="metric">
              <span class="metric-label">类型</span>
              <span class="metric-value">{{ getTypeLabel(device.type) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">IP</span>
              <span class="metric-value">{{ device.ipAddress }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">状态</span>
              <el-tag :type="getStatusType(device.status)" size="small">
                {{ getStatusLabel(device.status) }}
              </el-tag>
            </div>
            <div class="metric">
              <span class="metric-label">心跳</span>
              <span class="metric-value text-sm">{{ device.lastHeartbeat ? formatTime(device.lastHeartbeat) : '从未' }}</span>
            </div>
          </div>

          <div class="device-actions">
            <el-button size="small" @click="sendHeartbeat(device)" :loading="device._loading">
              测试连接
            </el-button>
            <el-button size="small" type="primary" @click="$router.push(`/device/detail/${device.id}`)">
              查看详情
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDevicePage, deviceHeartbeat } from '@/api/device'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const devices = ref([])
let timer = null

const stats = computed(() => ({
  online: devices.value.filter(d => d.status === 'ONLINE').length,
  offline: devices.value.filter(d => d.status === 'OFFLINE').length,
  fault: devices.value.filter(d => d.status === 'FAULT').length,
  total: devices.value.length
}))

const deviceTypes = [
  { value: 'BLOOD_PRESSURE', label: '血压计', icon: 'FirstAidKit' },
  { value: 'ECG', label: '心电图仪', icon: 'Odometer' },
  { value: 'GLUCOMETER', label: '血糖仪', icon: 'DataAnalysis' },
  { value: 'OXIMETER', label: '血氧仪', icon: 'Histogram' },
  { value: 'XRAY', label: 'X光机', icon: 'Picture' },
  { value: 'ULTRASOUND', label: '超声仪', icon: 'Monitor' }
]

const getTypeLabel = (type) => deviceTypes.find(t => t.value === type)?.label || type
const getDeviceIcon = (type) => deviceTypes.find(t => t.value === type)?.icon || 'Monitor'
const getStatusType = (s) => ({ ONLINE: 'success', OFFLINE: 'info', FAULT: 'danger' }[s] || 'info')
const getStatusLabel = (s) => ({ ONLINE: '在线', OFFLINE: '离线', FAULT: '故障' }[s] || s)
const getCardClass = (s) => ({ ONLINE: 'card-online', OFFLINE: 'card-offline', FAULT: 'card-fault' }[s] || '')
const formatTime = (t) => dayjs(t).fromNow()

const loadData = async () => {
  try {
    const res = await getDevicePage({ pageNum: 1, pageSize: 50 })
    devices.value = res.data.records.map(d => ({ ...d, _loading: false }))
  } catch (e) {
    // silent
  }
}

const sendHeartbeat = async (device) => {
  device._loading = true
  try {
    await deviceHeartbeat(device.code)
    device.status = 'ONLINE'
    ElMessage.success(`${device.name} 连接正常`)
  } catch (e) {
    device.status = 'FAULT'
    ElMessage.error(`${device.name} 连接失败`)
  } finally {
    device._loading = false
  }
}

onMounted(() => {
  loadData()
  timer = setInterval(loadData, 30000) // 每30秒刷新
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.monitor-header {
  margin-bottom: 20px;
}

.monitor-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.monitor-title h3 { margin: 0; font-size: 20px; }

.monitor-stats {
  display: flex;
  gap: 40px;
}

.stat-item { text-align: center; }
.stat-num { font-size: 36px; font-weight: 700; line-height: 1; }
.stat-label { font-size: 12px; color: #909399; margin-top: 4px; }
.online { color: #67c23a; }
.offline { color: #909399; }
.fault { color: #f56c6c; }
.total { color: #409eff; }

.device-card { margin-bottom: 16px; transition: transform 0.2s; }
.device-card:hover { transform: translateY(-3px); }

.card-online { border-top: 3px solid #67c23a; }
.card-offline { border-top: 3px solid #909399; }
.card-fault { border-top: 3px solid #f56c6c; }

.device-header { display: flex; align-items: center; gap: 12px; position: relative; }
.device-icon { width: 48px; height: 48px; background: #f0f2f5; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; color: #409eff; flex-shrink: 0; }
.device-info { flex: 1; }
.device-name { font-weight: 600; font-size: 15px; }
.device-code { font-size: 12px; color: #909399; margin-top: 2px; }
.status-dot { position: absolute; top: 0; right: 0; }

.device-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.metric { display: flex; flex-direction: column; gap: 2px; }
.metric-label { font-size: 11px; color: #909399; }
.metric-value { font-size: 13px; color: #333; }
.text-sm { font-size: 11px; }

.device-actions { display: flex; gap: 8px; margin-top: 12px; }
.header-row { margin-bottom: 0; }
</style>

<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.key">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-desc" :class="stat.trend > 0 ? 'up' : 'down'">
                <el-icon><component :is="stat.trend > 0 ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
                较昨日 {{ Math.abs(stat.trend) }}%
              </div>
            </div>
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon size="30" color="#fff"><component :is="stat.icon" /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <!-- 体检趋势图 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <span class="card-title">近7日体检趋势</span>
          </template>
          <div ref="trendChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>

      <!-- 设备状态 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span class="card-title">设备状态分布</span>
          </template>
          <div ref="deviceChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="table-row">
      <!-- 最新体检单 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">最新体检单</span>
              <el-button link type="primary" @click="$router.push('/check/list')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentOrders" size="small" :show-header="true">
            <el-table-column prop="orderNo" label="单号" width="150" />
            <el-table-column prop="patientName" label="患者" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getOrderStatusType(row.status)" size="small">
                  {{ getOrderStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="checkDate" label="日期" width="100" />
          </el-table>
        </el-card>
      </el-col>

      <!-- 在线设备 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">在线设备</span>
              <el-button link type="primary" @click="$router.push('/device/list')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="onlineDevices" size="small">
            <el-table-column prop="name" label="设备名称" />
            <el-table-column prop="type" label="类型" />
            <el-table-column prop="status" label="状态">
              <template #default>
                <el-badge is-dot type="success"><span style="padding-left:12px">在线</span></el-badge>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { getCheckOrderPage } from '@/api/check'
import { getOnlineDevices } from '@/api/device'
import * as echarts from 'echarts'

const stats = ref([
  { key: 'today', label: '今日体检', value: 28, trend: 12, icon: 'Document', color: '#409eff' },
  { key: 'week', label: '本周体检', value: 156, trend: 8, icon: 'Calendar', color: '#67c23a' },
  { key: 'device', label: '在线设备', value: 5, trend: -1, icon: 'Monitor', color: '#e6a23c' },
  { key: 'abnormal', label: '异常指标', value: 12, trend: 3, icon: 'Warning', color: '#f56c6c' }
])

const recentOrders = ref([])
const onlineDevices = ref([])
const trendChartRef = ref()
const deviceChartRef = ref()

const getOrderStatusType = (status) => {
  const map = { CREATED: '', IN_PROGRESS: 'warning', REVIEWING: 'info', COMPLETED: 'success' }
  return map[status] || ''
}

const getOrderStatusLabel = (status) => {
  const map = { CREATED: '待检查', IN_PROGRESS: '检查中', REVIEWING: '待审核', COMPLETED: '已完成' }
  return map[status] || status
}

const initTrendChart = () => {
  const chart = echarts.init(trendChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['体检人数', '异常人数'] },
    xAxis: {
      type: 'category',
      data: ['3/18', '3/19', '3/20', '3/21', '3/22', '3/23', '3/24']
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '体检人数',
        type: 'line',
        smooth: true,
        data: [18, 22, 25, 20, 28, 30, 28],
        itemStyle: { color: '#409eff' },
        areaStyle: { opacity: 0.1 }
      },
      {
        name: '异常人数',
        type: 'line',
        smooth: true,
        data: [3, 4, 5, 2, 6, 4, 5],
        itemStyle: { color: '#f56c6c' },
        areaStyle: { opacity: 0.1 }
      }
    ]
  })
  window.addEventListener('resize', () => chart.resize())
}

const initDeviceChart = () => {
  const chart = echarts.init(deviceChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: false, position: 'center' },
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold' }
      },
      data: [
        { value: 5, name: '在线', itemStyle: { color: '#67c23a' } },
        { value: 1, name: '离线', itemStyle: { color: '#909399' } },
        { value: 0, name: '故障', itemStyle: { color: '#f56c6c' } }
      ]
    }]
  })
}

onMounted(async () => {
  try {
    const [orderRes, deviceRes] = await Promise.all([
      getCheckOrderPage({ pageNum: 1, pageSize: 5 }),
      getOnlineDevices()
    ])
    recentOrders.value = orderRes.data?.records || []
    onlineDevices.value = deviceRes.data || []
  } catch (e) {
    // ignore - use mock data already in stats
  }

  await nextTick()
  initTrendChart()
  initDeviceChart()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-row { margin-bottom: 20px; }
.chart-row { margin-bottom: 20px; }

.stat-card {
  cursor: default;
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-desc {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 2px;
}

.stat-desc.up { color: #67c23a; }
.stat-desc.down { color: #f56c6c; }

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

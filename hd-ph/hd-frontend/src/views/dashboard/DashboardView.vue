<template>
  <div class="dashboard">
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="6" v-for="item in stats" :key="item.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: item.color }">
              <el-icon :size="28"><component :is="item.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ item.value }}</div>
              <div class="stat-label">{{ item.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :span="16">
        <el-card title="近7天体检量趋势">
          <template #header><span class="card-title">近7天体检量趋势</span></template>
          <div ref="chartRef" style="height:280px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span class="card-title">体检类型分布</span></template>
          <div ref="pieRef" style="height:280px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-card">
      <template #header><span class="card-title">最新体检单</span></template>
      <el-table :data="recentOrders" stripe size="small">
        <el-table-column prop="orderNo" label="体检单号" width="160" />
        <el-table-column prop="residentName" label="居民姓名" width="100" />
        <el-table-column prop="idCard" label="身份证号" width="180" />
        <el-table-column prop="checkYear" label="年度" width="70" />
        <el-table-column prop="checkDate" label="体检日期" width="120" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, markRaw } from 'vue'
import { getCheckOrders, getCheckOrderYearCount } from '@/api/check'
import { getResidentCount } from '@/api/resident'
import { getDrOrderMonthCount } from '@/api/dr'
import { getDeviceOnlineCount } from '@/api/device'
import * as echarts from 'echarts'

const chartRef = ref()
const pieRef = ref()
const recentOrders = ref([])

const stats = ref([
  { label: '居民档案总数', value: '—', icon: 'UserFilled', color: '#1a73e8' },
  { label: '本年体检人次', value: '—', icon: 'Document', color: '#52c41a' },
  { label: '本月DR申请', value: '—', icon: 'Camera', color: '#fa8c16' },
  { label: '在线设备数', value: '—', icon: 'Monitor', color: '#722ed1' }
])

const statusText = (s) => ['待体检','体检中','已完成','已作废'][s] || '未知'
const statusType = (s) => ['info','warning','success','danger'][s] || 'info'

onMounted(async () => {
  // 加载统计数据
  try {
    const [residentRes, checkRes, drRes, deviceRes] = await Promise.allSettled([
      getResidentCount(),
      getCheckOrderYearCount(),
      getDrOrderMonthCount(),
      getDeviceOnlineCount()
    ])
    if (residentRes.status === 'fulfilled') stats.value[0].value = residentRes.value.data ?? '0'
    if (checkRes.status === 'fulfilled') stats.value[1].value = checkRes.value.data ?? '0'
    if (drRes.status === 'fulfilled') stats.value[2].value = drRes.value.data ?? '0'
    if (deviceRes.status === 'fulfilled') stats.value[3].value = deviceRes.value.data ?? '0'
  } catch {}

  // 加载最新体检单
  try {
    const res = await getCheckOrders({ current: 1, size: 8 })
    recentOrders.value = res.data?.records || res.records || []
  } catch {}

  // 趋势图
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['3-19','3-20','3-21','3-22','3-23','3-24','3-25']
    },
    yAxis: { type: 'value' },
    series: [{
      name: '体检人次',
      type: 'line',
      smooth: true,
      data: [12, 28, 35, 22, 41, 38, 25],
      areaStyle: { opacity: 0.1 },
      itemStyle: { color: '#1a73e8' }
    }]
  })

  // 饼图
  const pie = echarts.init(pieRef.value)
  pie.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '65%',
      data: [
        { value: 350, name: '老年人健康体检' },
        { value: 180, name: '高血压随访' },
        { value: 120, name: '糖尿病随访' },
        { value: 60, name: '孕产妇检查' }
      ]
    }]
  })
})
</script>

<style scoped>
.dashboard { }
.stat-cards { margin-bottom: 16px; }
.stat-card .stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
.stat-value { font-size: 28px; font-weight: 700; color: #333; }
.stat-label { font-size: 13px; color: #999; }
.chart-row { margin-bottom: 16px; }
.card-title { font-weight: 600; }
.recent-card { }
</style>

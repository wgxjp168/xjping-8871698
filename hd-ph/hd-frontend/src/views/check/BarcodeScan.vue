<template>
  <div class="barcode-scan">
    <el-card>
      <template #header><b>扫码查询居民体检信息</b></template>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
        使用扫码枪扫描萤火虫县域智慧公卫平台打印的二维码，系统自动查询居民信息和体检单
      </el-alert>

      <el-form inline>
        <el-form-item label="扫码/体检单号">
          <el-input
            ref="scanInputRef"
            v-model="scanCode"
            placeholder="请扫描二维码或输入体检单号/身份证号"
            style="width:400px"
            clearable
            @keyup.enter="handleScan"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleScan" :loading="loading">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 查询结果 -->
    <template v-if="found">
      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="10">
          <el-card>
            <template #header><b>居民信息</b></template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="姓名">{{ resident.name || order.residentName }}</el-descriptions-item>
              <el-descriptions-item label="身份证号">{{ resident.idCard || order.idCard }}</el-descriptions-item>
              <el-descriptions-item label="性别">{{ resident.gender === 1 ? '男' : '女' }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ resident.phone || '—' }}</el-descriptions-item>
              <el-descriptions-item label="地址">{{ resident.address || '—' }}</el-descriptions-item>
              <el-descriptions-item label="村/社区">{{ resident.village || '—' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :span="14">
          <el-card>
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <b>体检单信息</b>
                <el-button v-if="order.id" type="primary" size="small" @click="goDetail(order.id)">进入体检详情</el-button>
              </div>
            </template>
            <el-descriptions :column="2" border v-if="order.id">
              <el-descriptions-item label="体检单号">{{ order.orderNo }}</el-descriptions-item>
              <el-descriptions-item label="体检年度">{{ order.checkYear }}</el-descriptions-item>
              <el-descriptions-item label="体检日期">{{ order.checkDate }}</el-descriptions-item>
              <el-descriptions-item label="体检类型">{{ typeText(order.checkType) }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="statusType(order.status)" size="small">{{ statusText(order.status) }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="未找到关联的体检单" />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-if="searched && !found" description="未找到匹配的居民或体检单，请检查扫码内容" style="margin-top:40px" />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getCheckOrderByNo, getCheckOrders } from '@/api/check'
import { getResidentByIdCard } from '@/api/resident'

const router = useRouter()
const scanInputRef = ref()
const scanCode = ref('')
const loading = ref(false)
const searched = ref(false)
const found = ref(false)
const resident = ref({})
const order = ref({})

const typeText = (t) => ['','老年人体检','高血压随访','糖尿病随访','孕产妇'][t] || '未知'
const statusText = (s) => ['待体检','体检中','已完成','已作废'][s] || '未知'
const statusType = (s) => ['info','warning','success','danger'][s] || 'info'

const handleScan = async () => {
  const code = scanCode.value.trim()
  if (!code) { ElMessage.warning('请扫描二维码或输入查询内容'); return }

  loading.value = true
  searched.value = true
  found.value = false
  resident.value = {}
  order.value = {}

  try {
    // 策略1: 按体检单号查询（二维码可能包含体检单号）
    try {
      const orderRes = await getCheckOrderByNo(code)
      const orderData = orderRes.data || orderRes
      if (orderData && orderData.id) {
        order.value = orderData
        // 用身份证号查居民信息
        if (orderData.idCard) {
          try {
            const resRes = await getResidentByIdCard(orderData.idCard)
            resident.value = resRes.data || resRes || {}
          } catch {}
        }
        found.value = true
        return
      }
    } catch {}

    // 策略2: 按身份证号查询（二维码可能包含身份证号）
    if (code.length >= 15) {
      try {
        const resRes = await getResidentByIdCard(code)
        const resData = resRes.data || resRes
        if (resData && resData.id) {
          resident.value = resData
          // 查该居民最新体检单
          try {
            const ordersRes = await getCheckOrders({ idCard: code, current: 1, size: 1 })
            const ordersData = ordersRes.data || ordersRes
            const records = ordersData.records || []
            if (records.length > 0) order.value = records[0]
          } catch {}
          found.value = true
          return
        }
      } catch {}
    }

    ElMessage.warning('未找到匹配记录')
  } finally {
    loading.value = false
    // 自动聚焦等待下一次扫码
    nextTick(() => { scanInputRef.value?.focus() })
  }
}

const goDetail = (id) => router.push(`/check-orders/${id}`)

onMounted(() => { scanInputRef.value?.focus() })
</script>

<style scoped>
.barcode-scan { }
</style>

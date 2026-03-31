<template>
  <div class="barcode-scan">
    <el-card>
      <template #header><b>扫码查询 - 院内检验操作</b></template>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px">
        扫描县级智慧公卫平台下乡体检生成的二维码，自动带出居民身份信息，选择检验项目进行操作
      </el-alert>

      <el-form inline>
        <el-form-item label="扫码/编号">
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
          <el-button @click="resetScan">清除</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 查询结果 -->
    <template v-if="found">
      <!-- 居民信息卡片 -->
      <el-card style="margin-top:16px">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <b>居民信息</b>
            <el-tag type="success" size="large">{{ order.orderNo || '—' }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="姓名">
            <span style="font-size:16px;font-weight:700">{{ resident.name || order.residentName }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="性别">{{ resident.gender === 1 ? '男' : (resident.gender === 2 ? '女' : '—') }}</el-descriptions-item>
          <el-descriptions-item label="年龄">{{ calcAge(resident.birthDate) }}</el-descriptions-item>
          <el-descriptions-item label="身份证号">{{ resident.idCard || order.idCard }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ resident.phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="村/社区">{{ resident.village || '—' }}</el-descriptions-item>
          <el-descriptions-item label="乡镇">{{ resident.town || '—' }}</el-descriptions-item>
          <el-descriptions-item label="体检状态">
            <el-tag v-if="order.id" :type="statusType(order.status)" size="small">{{ statusText(order.status) }}</el-tag>
            <span v-else>—</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 检验操作快捷入口 -->
      <el-card style="margin-top:16px" v-if="order.id">
        <template #header><b>选择检验项目</b></template>
        <el-row :gutter="16">
          <el-col :span="6" v-for="item in examItems" :key="item.category">
            <el-card
              shadow="hover"
              class="exam-card"
              :class="{ disabled: !hasPermForExam(item) }"
              @click="goExam(item)"
            >
              <div class="exam-content">
                <div class="exam-icon" :style="{ background: item.color }">
                  <el-icon :size="24"><component :is="item.icon" /></el-icon>
                </div>
                <div class="exam-info">
                  <div class="exam-name">{{ item.name }}</div>
                  <div class="exam-desc">{{ item.desc }}</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-card>
    </template>

    <el-empty v-if="searched && !found" description="未找到匹配的居民或体检单，请检查扫码内容" style="margin-top:40px" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
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

const userInfo = computed(() => {
  try { return JSON.parse(localStorage.getItem('userInfo') || '{}') } catch { return {} }
})
const permissions = computed(() => userInfo.value.permissions || [])
const isSuperAdmin = computed(() => userInfo.value.userType === 3)
const isHospitalAdmin = computed(() => userInfo.value.userType === 4)

// 7个检验项目快捷入口
const examItems = [
  { category: 'BIOCHEM', name: '生化检验', desc: '肝功、肾功、血脂等', icon: 'Document', color: '#1a73e8', perm: 'BIOCHEM:VIEW' },
  { category: 'BLOOD', name: '血常规', desc: '血细胞分析', icon: 'Document', color: '#e91e63', perm: 'BLOOD:VIEW' },
  { category: 'URINE', name: '尿常规', desc: '尿液分析', icon: 'Document', color: '#ff9800', perm: 'URINE:VIEW' },
  { category: 'HBA1C', name: '糖化血红蛋白', desc: 'HbA1c检测', icon: 'Document', color: '#9c27b0', perm: 'HBA1C:VIEW' },
  { category: 'DR', name: 'DR放射', desc: '胸部X光等', icon: 'Camera', color: '#00bcd4', perm: 'DR:VIEW' },
  { category: 'ULTRASOUND', name: 'B超', desc: '腹部超声检查', icon: 'Monitor', color: '#4caf50', perm: 'ULTRASOUND:VIEW' },
  { category: 'ECG', name: '心电图', desc: '12导联心电图', icon: 'Monitor', color: '#795548', perm: 'ECG:VIEW' }
]

const hasPermForExam = (item) => {
  if (isSuperAdmin.value || isHospitalAdmin.value) return true
  return permissions.value.includes(item.perm)
}

const statusText = (s) => ['待体检','体检中','已完成','已作废'][s] || '未知'
const statusType = (s) => ['info','warning','success','danger'][s] || 'info'

const calcAge = (birthDate) => {
  if (!birthDate) return '—'
  const birth = new Date(birthDate)
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  if (now.getMonth() < birth.getMonth() || (now.getMonth() === birth.getMonth() && now.getDate() < birth.getDate())) age--
  return age + '岁'
}

const resetScan = () => {
  scanCode.value = ''
  searched.value = false
  found.value = false
  resident.value = {}
  order.value = {}
  nextTick(() => { scanInputRef.value?.focus() })
}

const handleScan = async () => {
  const code = scanCode.value.trim()
  if (!code) { ElMessage.warning('请扫描二维码或输入查询内容'); return }

  loading.value = true
  searched.value = true
  found.value = false
  resident.value = {}
  order.value = {}

  try {
    // 策略1: 按体检单号查询
    try {
      const orderRes = await getCheckOrderByNo(code)
      const orderData = orderRes.data || orderRes
      if (orderData && orderData.id) {
        order.value = orderData
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

    // 策略2: 按身份证号查询
    if (code.length >= 15) {
      try {
        const resRes = await getResidentByIdCard(code)
        const resData = resRes.data || resRes
        if (resData && resData.id) {
          resident.value = resData
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
    nextTick(() => { scanInputRef.value?.focus() })
  }
}

const goExam = (item) => {
  if (!hasPermForExam(item)) {
    ElMessage.warning('您没有该检验项目的操作权限')
    return
  }
  if (item.category === 'DR') {
    // DR走单独的DR申请流程
    router.push({ path: '/dr-orders', query: { checkOrderId: order.value.id, residentName: order.value.residentName, idCard: order.value.idCard } })
  } else {
    // 其他检验项目跳转到体检详情页，并带上category参数自动切换到对应tab
    router.push({ path: `/check-orders/${order.value.id}`, query: { category: item.category } })
  }
}

onMounted(() => { scanInputRef.value?.focus() })
</script>

<style scoped>
.exam-card {
  cursor: pointer;
  margin-bottom: 12px;
  transition: transform 0.2s;
}
.exam-card:hover { transform: translateY(-2px); }
.exam-card.disabled { opacity: 0.4; cursor: not-allowed; }
.exam-content {
  display: flex;
  align-items: center;
  gap: 12px;
}
.exam-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}
.exam-name { font-size: 15px; font-weight: 600; color: #333; }
.exam-desc { font-size: 12px; color: #999; margin-top: 2px; }
</style>

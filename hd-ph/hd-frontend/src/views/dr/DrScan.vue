<template>
  <div class="dr-scan">
    <el-card class="scan-card">
      <template #header><b>DR扫码签到</b></template>
      <div class="scan-area">
        <el-input
          v-model="barcodeNo"
          placeholder="扫描条形码或手动输入条码号，按回车确认"
          size="large"
          ref="inputRef"
          :prefix-icon="Barcode"
          @keyup.enter="handleScan"
          style="max-width:500px"
          clearable
          autofocus
        />
        <el-button type="primary" size="large" @click="handleScan" :loading="scanning">
          确认签到
        </el-button>
      </div>
      <div class="scan-hint">
        <el-icon><InfoFilled /></el-icon>
        请将光标置于输入框，使用扫码枪扫描贴在申请单上的条形码，系统将自动完成签到。
      </div>
    </el-card>

    <!-- 签到成功展示 -->
    <el-card v-if="scannedOrder" class="result-card">
      <template #header>
        <div style="display:flex;align-items:center;gap:8px">
          <el-icon color="#52c41a"><SuccessFilled /></el-icon>
          <b>签到成功</b>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="DR申请单号">{{ scannedOrder.drOrderNo }}</el-descriptions-item>
        <el-descriptions-item label="条码号">{{ scannedOrder.barcodeNo }}</el-descriptions-item>
        <el-descriptions-item label="居民姓名">{{ scannedOrder.residentName }}</el-descriptions-item>
        <el-descriptions-item label="身份证号">{{ scannedOrder.idCard }}</el-descriptions-item>
        <el-descriptions-item label="检查部位">{{ scannedOrder.bodyPart }}</el-descriptions-item>
        <el-descriptions-item label="签到时间">{{ scannedOrder.scanTime }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="2">
          <el-tag type="warning">已签到，等待检查</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div style="margin-top:16px;display:flex;gap:12px">
        <el-button type="success" @click="finishCheck">标记检查完成</el-button>
        <el-button @click="scannedOrder = null; barcodeNo = ''">继续扫码</el-button>
      </div>
    </el-card>

    <!-- 扫码历史 -->
    <el-card class="history-card">
      <template #header><b>今日签到记录</b></template>
      <el-table :data="history" stripe size="small">
        <el-table-column prop="barcodeNo" label="条码号" width="180" />
        <el-table-column prop="drOrderNo" label="申请单号" width="180" />
        <el-table-column prop="residentName" label="居民" width="90" />
        <el-table-column prop="bodyPart" label="检查部位" />
        <el-table-column prop="scanTime" label="签到时间" width="160" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 2 ? 'success' : 'warning'" size="small">
              {{ row.status === 1 ? '待检查' : row.status === 2 ? '已完成' : '—' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search as Barcode } from '@element-plus/icons-vue'
import { scanBarcode, getDrOrders, updateDrOrderStatus } from '@/api/dr'

const barcodeNo = ref('')
const scanning = ref(false)
const scannedOrder = ref(null)
const history = ref([])

const handleScan = async () => {
  if (!barcodeNo.value.trim()) { ElMessage.warning('请输入条码号'); return }
  scanning.value = true
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const res = await scanBarcode({ barcodeNo: barcodeNo.value.trim(), scanUserId: userInfo.userId })
    scannedOrder.value = res.data || res
    ElMessage.success('签到成功')
    loadHistory()
  } catch (e) {
    ElMessage.error(e.message || '签到失败')
  } finally {
    scanning.value = false
  }
}

const finishCheck = async () => {
  await updateDrOrderStatus(scannedOrder.value.id, 2)
  ElMessage.success('已标记完成')
  scannedOrder.value = null
  barcodeNo.value = ''
  loadHistory()
}

const loadHistory = async () => {
  try {
    const res = await getDrOrders({ status: 1, current: 1, size: 20 })
    const data = res.data || res
    history.value = data.records || []
  } catch {}
}

onMounted(loadHistory)
</script>

<style scoped>
.dr-scan { max-width: 900px; }
.scan-card { margin-bottom: 16px; }
.scan-area {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
  padding: 24px;
  background: #f9fafb;
  border-radius: 8px;
}
.scan-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
  font-size: 13px;
}
.result-card { margin-bottom: 16px; }
</style>

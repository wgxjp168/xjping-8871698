<template>
  <div>
    <el-page-header @back="$router.back()" content="DR报告" />
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="10">
        <el-card>
          <template #header><b>申请单信息</b></template>
          <el-descriptions :column="1" border size="small" v-if="drOrder">
            <el-descriptions-item label="申请单号">{{ drOrder.drOrderNo }}</el-descriptions-item>
            <el-descriptions-item label="条码号">{{ drOrder.barcodeNo }}</el-descriptions-item>
            <el-descriptions-item label="居民姓名">{{ drOrder.residentName }}</el-descriptions-item>
            <el-descriptions-item label="检查部位">{{ drOrder.bodyPart }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag size="small">{{ drOrder.status }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <b>DR报告</b>
              <el-button type="success" @click="handleSubmit">提交报告</el-button>
            </div>
          </template>
          <el-form :model="report" label-width="90px">
            <el-form-item label="影像所见">
              <el-input v-model="report.findings" type="textarea" :rows="4"
                        placeholder="描述影像所见..." />
            </el-form-item>
            <el-form-item label="诊断意见">
              <el-input v-model="report.diagnosis" type="textarea" :rows="3"
                        placeholder="填写诊断意见..." />
            </el-form-item>
            <el-form-item label="影像文件">
              <el-upload action="#" :auto-upload="false" accept=".jpg,.png,.dcm">
                <el-button>选择影像文件</el-button>
                <template #tip>
                  <div class="el-upload__tip">支持 jpg/png/dcm 格式</div>
                </template>
              </el-upload>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDrOrder, getDrReport, submitDrReport } from '@/api/dr'

const route = useRoute()
const drOrder = ref(null)
const report = reactive({ drOrderId: null, findings: '', diagnosis: '' })

const handleSubmit = async () => {
  report.drOrderId = drOrder.value?.id
  await submitDrReport(report)
  ElMessage.success('报告提交成功')
}

onMounted(async () => {
  const orderId = route.params.orderId
  const [orderRes, reportRes] = await Promise.allSettled([
    getDrOrder(orderId),
    getDrReport(orderId)
  ])
  if (orderRes.status === 'fulfilled') drOrder.value = orderRes.value.data || orderRes.value
  if (reportRes.status === 'fulfilled' && reportRes.value.data) {
    Object.assign(report, reportRes.value.data)
  }
})
</script>

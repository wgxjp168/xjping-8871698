<template>
  <div>
    <el-card class="search-card">
      <el-form :model="query" inline>
        <el-form-item label="姓名">
          <el-input v-model="query.residentName" clearable style="width:130px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width:110px">
            <el-option :value="0" label="待扫码" />
            <el-option :value="1" label="已扫码" />
            <el-option :value="2" label="已完成" />
            <el-option :value="3" label="已上传" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button type="success" :icon="Plus" @click="dialogVisible = true">新建DR申请</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="drOrderNo" label="申请单号" width="185" />
        <el-table-column prop="barcodeNo" label="条码号" width="175" />
        <el-table-column prop="residentName" label="居民" width="90" />
        <el-table-column prop="idCard" label="身份证" width="185" />
        <el-table-column prop="bodyPart" label="检查部位" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="drStatusType(row.status)" size="small">{{ drStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applyTime" label="申请时间" width="155" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="goReport(row.id)">报告</el-button>
            <el-button type="warning" size="small" link @click="printBarcode(row)">打印条码</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.current" v-model:page-size="query.size"
                     :total="total" layout="total, prev, pager, next" class="pagination" @change="loadData" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建DR申请" width="460px">
      <el-form :model="form" ref="formRef" label-width="90px">
        <el-form-item label="居民姓名" prop="residentName">
          <el-input v-model="form.residentName" />
        </el-form-item>
        <el-form-item label="身份证号">
          <el-input v-model="form.idCard" />
        </el-form-item>
        <el-form-item label="检查部位">
          <el-select v-model="form.bodyPart" style="width:100%">
            <el-option value="胸部" label="胸部正位" />
            <el-option value="腹部" label="腹部" />
            <el-option value="脊柱" label="脊柱" />
            <el-option value="四肢" label="四肢" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDrOrders, createDrOrder, deleteDrOrder } from '@/api/dr'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()

const query = reactive({ current: 1, size: 10, residentName: '', status: null })
const form = reactive({ checkOrderId: null, residentName: '', idCard: '', bodyPart: '胸部', description: '' })

const drStatusText = (s) => ['待扫码','已扫码','已完成','已上传','已作废'][s] || '—'
const drStatusType = (s) => ['info','warning','success','primary','danger'][s] || 'info'

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDrOrders(query)
    const data = res.data || res
    list.value = data.records || []
    total.value = data.total || 0
  } finally { loading.value = false }
}

const handleCreate = async () => {
  form.checkOrderId = route.query.checkOrderId || null
  await createDrOrder(form)
  ElMessage.success('DR申请单已创建，条码号已生成')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await deleteDrOrder(id)
  ElMessage.success('删除成功')
  loadData()
}

const goReport = (id) => router.push(`/dr-report/${id}`)

const printBarcode = (row) => {
  ElMessage.info(`条码号：${row.barcodeNo}（实际生产中调用打印机API）`)
}

onMounted(loadData)
</script>

<style scoped>
.search-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>

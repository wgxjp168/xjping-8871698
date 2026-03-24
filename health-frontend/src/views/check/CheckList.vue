<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>体检单管理</span>
          <el-button type="primary" :icon="Plus" @click="handleCreate">新建体检单</el-button>
        </div>
      </template>

      <!-- 搜索区域 -->
      <el-form :model="query" inline class="search-form">
        <el-form-item label="单号">
          <el-input v-model="query.orderNo" placeholder="输入体检单号" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="患者">
          <el-input v-model="query.patientName" placeholder="输入患者姓名" clearable style="width:140px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width:240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="orderNo" label="体检单号" width="170" />
        <el-table-column prop="patientName" label="患者姓名" width="100" />
        <el-table-column prop="patientPhone" label="手机号" width="120" />
        <el-table-column prop="packageName" label="套餐" />
        <el-table-column prop="checkDate" label="体检日期" width="110" />
        <el-table-column prop="doctorName" label="负责医生" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalScore" label="健康评分" width="90">
          <template #default="{ row }">
            <span v-if="row.totalScore !== null" :class="getScoreClass(row.totalScore)">
              {{ row.totalScore }}
            </span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDetail(row)">详情</el-button>
            <el-button link type="success" @click="handleRecord(row)"
              v-if="['CREATED','IN_PROGRESS'].includes(row.status)">录入</el-button>
            <el-button link type="danger" @click="handleDelete(row)"
              v-if="row.status === 'CREATED'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="query.pageNum"
        v-model:page-size="query.pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @change="loadData"
      />
    </el-card>

    <!-- 新建对话框 -->
    <el-dialog v-model="createVisible" title="新建体检单" width="480px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="患者ID" required>
          <el-input-number v-model="createForm.patientId" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="检查套餐">
          <el-select v-model="createForm.packageId" placeholder="选择套餐" style="width:100%" clearable>
            <el-option :value="1" label="基础体检套餐 ¥199" />
            <el-option :value="2" label="标准健康套餐 ¥399" />
            <el-option :value="3" label="全面健康套餐 ¥799" />
            <el-option :value="4" label="心血管专项套餐 ¥599" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCheckOrderPage, createCheckOrder } from '@/api/check'

const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const createVisible = ref(false)
const submitting = ref(false)
const dateRange = ref([])

const query = reactive({
  orderNo: '', patientName: '', status: '',
  checkDateStart: '', checkDateEnd: '',
  pageNum: 1, pageSize: 10
})

const createForm = reactive({ patientId: null, packageId: null })

const statusOptions = [
  { value: 'CREATED', label: '待检查' },
  { value: 'IN_PROGRESS', label: '检查中' },
  { value: 'REVIEWING', label: '待审核' },
  { value: 'COMPLETED', label: '已完成' }
]

const getStatusType = (s) => ({ CREATED: '', IN_PROGRESS: 'warning', REVIEWING: 'info', COMPLETED: 'success' }[s] || '')
const getStatusLabel = (s) => ({ CREATED: '待检查', IN_PROGRESS: '检查中', REVIEWING: '待审核', COMPLETED: '已完成' }[s] || s)
const getScoreClass = (score) => score >= 80 ? 'score-good' : score >= 60 ? 'score-mid' : 'score-bad'

const loadData = async () => {
  if (dateRange.value?.length === 2) {
    query.checkDateStart = dateRange.value[0]
    query.checkDateEnd = dateRange.value[1]
  }
  loading.value = true
  try {
    const res = await getCheckOrderPage(query)
    tableData.value = res.data.records
    total.value = Number(res.data.total)
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  Object.assign(query, { orderNo: '', patientName: '', status: '', checkDateStart: '', checkDateEnd: '', pageNum: 1 })
  dateRange.value = []
  loadData()
}

const handleDetail = (row) => router.push(`/check/detail/${row.id}`)

const handleRecord = (row) => router.push(`/check/detail/${row.id}?mode=record`)

const handleCreate = () => {
  Object.assign(createForm, { patientId: null, packageId: null })
  createVisible.value = true
}

const submitCreate = async () => {
  if (!createForm.patientId) { ElMessage.warning('请输入患者ID'); return }
  submitting.value = true
  try {
    await createCheckOrder(createForm.patientId, createForm.packageId)
    ElMessage.success('创建成功')
    createVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确定要删除体检单 ${row.orderNo} 吗？`, '提示', { type: 'warning' })
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
.score-good { color: #67c23a; font-weight: 600; }
.score-mid { color: #e6a23c; font-weight: 600; }
.score-bad { color: #f56c6c; font-weight: 600; }
.text-gray { color: #c0c4cc; }
</style>

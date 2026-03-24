<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>诊断报告管理</span>
          <el-button type="primary" :icon="Plus" @click="handleCreate">新建报告</el-button>
        </div>
      </template>

      <el-form :model="query" inline class="search-form">
        <el-form-item label="患者">
          <el-input v-model="query.patientId" placeholder="患者ID" clearable style="width:120px" type="number" />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="query.riskLevel" placeholder="全部" clearable style="width:110px">
            <el-option value="LOW" label="低风险" />
            <el-option value="MEDIUM" label="中风险" />
            <el-option value="HIGH" label="高风险" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:110px">
            <el-option value="DRAFT" label="草稿" />
            <el-option value="CONFIRMED" label="已确认" />
            <el-option value="PUBLISHED" label="已发布" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="orderNo" label="体检单号" width="160" />
        <el-table-column prop="patientName" label="患者" width="100" />
        <el-table-column prop="doctorName" label="诊断医生" width="100" />
        <el-table-column prop="healthScore" label="健康评分" width="90">
          <template #default="{ row }">
            <span :class="getScoreClass(row.healthScore)" style="font-weight:600">
              {{ row.healthScore ?? '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="riskLevel" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskType(row.riskLevel)" size="small">{{ getRiskLabel(row.riskLevel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="conclusion" label="诊断结论" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDetail(row)">详情</el-button>
            <el-button link type="success" @click="handleConfirm(row)"
              v-if="row.status === 'DRAFT'">确认</el-button>
            <el-button link type="warning" @click="handlePublish(row)"
              v-if="row.status === 'CONFIRMED'">发布</el-button>
            <el-button link type="danger" @click="handleDelete(row)"
              v-if="row.status === 'DRAFT'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.pageNum"
        v-model:page-size="query.pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @change="loadData"
      />
    </el-card>

    <!-- 新建报告对话框 -->
    <el-dialog v-model="createVisible" title="新建诊断报告" width="600px">
      <el-form :model="createForm" label-width="110px">
        <el-form-item label="体检单ID" required>
          <el-input-number v-model="createForm.orderId" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="健康评分">
          <el-slider v-model="createForm.healthScore" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-radio-group v-model="createForm.riskLevel">
            <el-radio value="LOW">低风险</el-radio>
            <el-radio value="MEDIUM">中风险</el-radio>
            <el-radio value="HIGH">高风险</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="诊断结论" required>
          <el-input v-model="createForm.conclusion" type="textarea" :rows="4" placeholder="请填写诊断结论..." />
        </el-form-item>
        <el-form-item label="健康建议">
          <el-input v-model="createForm.suggestion" type="textarea" :rows="4" placeholder="请填写健康建议..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">保存草稿</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDiagnosisPage, saveDiagnosis, confirmDiagnosis, publishDiagnosis, deleteDiagnosis } from '@/api/diagnosis'

const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const createVisible = ref(false)
const submitting = ref(false)

const query = reactive({ patientId: null, riskLevel: '', status: '', pageNum: 1, pageSize: 10 })
const createForm = reactive({ orderId: null, healthScore: 80, riskLevel: 'LOW', conclusion: '', suggestion: '' })

const getStatusType = (s) => ({ DRAFT: 'info', CONFIRMED: 'warning', PUBLISHED: 'success' }[s] || '')
const getStatusLabel = (s) => ({ DRAFT: '草稿', CONFIRMED: '已确认', PUBLISHED: '已发布' }[s] || s)
const getRiskType = (r) => ({ LOW: 'success', MEDIUM: 'warning', HIGH: 'danger' }[r] || 'info')
const getRiskLabel = (r) => ({ LOW: '低风险', MEDIUM: '中风险', HIGH: '高风险' }[r] || r)
const getScoreClass = (score) => !score ? '' : score >= 80 ? 'score-good' : score >= 60 ? 'score-mid' : 'score-bad'

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDiagnosisPage(query)
    tableData.value = res.data.records
    total.value = Number(res.data.total)
  } finally {
    loading.value = false
  }
}

const reset = () => { Object.assign(query, { patientId: null, riskLevel: '', status: '', pageNum: 1 }); loadData() }
const handleDetail = (row) => router.push(`/diagnosis/detail/${row.id}`)
const handleCreate = () => { Object.assign(createForm, { orderId: null, healthScore: 80, riskLevel: 'LOW', conclusion: '', suggestion: '' }); createVisible.value = true }

const submitCreate = async () => {
  if (!createForm.orderId || !createForm.conclusion) { ElMessage.warning('请填写必填项'); return }
  submitting.value = true
  try {
    await saveDiagnosis(createForm)
    ElMessage.success('保存成功')
    createVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const handleConfirm = async (row) => {
  await ElMessageBox.confirm('确认该诊断报告？确认后不可修改', '提示', { type: 'warning' })
  await confirmDiagnosis(row.id)
  ElMessage.success('已确认')
  loadData()
}

const handlePublish = async (row) => {
  await ElMessageBox.confirm('发布后患者可查看该报告，是否发布？', '提示', { type: 'warning' })
  await publishDiagnosis(row.id)
  ElMessage.success('已发布')
  loadData()
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm('确定删除该诊断报告？', '提示', { type: 'warning' })
  await deleteDiagnosis(row.id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
.score-good { color: #67c23a; }
.score-mid { color: #e6a23c; }
.score-bad { color: #f56c6c; }
</style>

<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增设备</el-button>
        </div>
      </template>

      <el-form :model="query" inline class="search-form">
        <el-form-item label="设备名称">
          <el-input v-model="query.name" placeholder="输入名称" clearable style="width:150px" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="query.type" placeholder="全部" clearable style="width:130px">
            <el-option v-for="t in deviceTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:110px">
            <el-option value="ONLINE" label="在线" />
            <el-option value="OFFLINE" label="离线" />
            <el-option value="FAULT" label="故障" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="code" label="设备编码" width="110" />
        <el-table-column prop="type" label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ getTypeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="型号" width="120" />
        <el-table-column prop="manufacturer" label="厂商" width="100" />
        <el-table-column prop="deptName" label="所属科室" width="100" />
        <el-table-column prop="ipAddress" label="IP地址" width="130" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <div class="status-cell">
              <el-badge is-dot :type="getStatusType(row.status)" />
              <span style="margin-left:8px">{{ getStatusLabel(row.status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lastHeartbeat" label="最后心跳" width="150" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDetail(row)">详情</el-button>
            <el-button link type="success" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑设备' : '新增设备'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备编码" prop="code">
              <el-input v-model="form.code" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备类型">
              <el-select v-model="form.type" style="width:100%">
                <el-option v-for="t in deviceTypes" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备型号">
              <el-input v-model="form.model" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生产厂商">
              <el-input v-model="form.manufacturer" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="序列号">
              <el-input v-model="form.serialNo" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="IP地址">
              <el-input v-model="form.ipAddress" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口">
              <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通信协议">
              <el-select v-model="form.protocol" style="width:100%">
                <el-option value="HTTP" label="HTTP" />
                <el-option value="TCP" label="TCP" />
                <el-option value="UDP" label="UDP" />
                <el-option value="HL7" label="HL7" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="校准日期">
              <el-date-picker v-model="form.calibrationDate" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.description" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDevicePage, saveDevice, updateDevice, deleteDevice } from '@/api/device'

const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()

const query = reactive({ name: '', type: '', status: '', pageNum: 1, pageSize: 10 })
const form = reactive({ id: null, name: '', code: '', type: '', model: '', manufacturer: '',
  serialNo: '', ipAddress: '', port: 8080, protocol: 'HTTP', calibrationDate: null, description: '' })

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入设备编码', trigger: 'blur' }]
}

const deviceTypes = [
  { value: 'BLOOD_PRESSURE', label: '血压计' },
  { value: 'ECG', label: '心电图仪' },
  { value: 'GLUCOMETER', label: '血糖仪' },
  { value: 'OXIMETER', label: '血氧仪' },
  { value: 'XRAY', label: 'X光机' },
  { value: 'ULTRASOUND', label: '超声诊断仪' }
]

const getTypeLabel = (type) => deviceTypes.find(t => t.value === type)?.label || type
const getStatusType = (s) => ({ ONLINE: 'success', OFFLINE: 'info', FAULT: 'danger' }[s] || 'info')
const getStatusLabel = (s) => ({ ONLINE: '在线', OFFLINE: '离线', FAULT: '故障' }[s] || s)

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDevicePage(query)
    tableData.value = res.data.records
    total.value = Number(res.data.total)
  } finally {
    loading.value = false
  }
}

const reset = () => { Object.assign(query, { name: '', type: '', status: '', pageNum: 1 }); loadData() }
const handleDetail = (row) => router.push(`/device/detail/${row.id}`)

const handleAdd = () => {
  Object.assign(form, { id: null, name: '', code: '', type: '', model: '', manufacturer: '',
    serialNo: '', ipAddress: '', port: 8080, protocol: 'HTTP', calibrationDate: null, description: '' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(form, row)
  dialogVisible.value = true
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (form.id) {
      await updateDevice(form)
    } else {
      await saveDevice(form)
    }
    ElMessage.success(form.id ? '更新成功' : '新增成功')
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确定删除设备 "${row.name}" 吗？`, '提示', { type: 'warning' })
  await deleteDevice(row.id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
.status-cell { display: flex; align-items: center; }
</style>

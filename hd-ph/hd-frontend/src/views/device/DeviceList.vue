<template>
  <div>
    <el-card class="search-card">
      <div style="display:flex;justify-content:space-between">
        <span style="font-size:15px;font-weight:600">医疗设备管理</span>
        <el-button type="success" :icon="Plus" @click="openCreate">添加设备</el-button>
      </div>
    </el-card>

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="deviceNo" label="设备编号" width="130" />
        <el-table-column prop="deviceName" label="设备名称" width="180" />
        <el-table-column prop="deviceModel" label="型号" width="140" />
        <el-table-column prop="manufacturer" label="厂家" width="120" />
        <el-table-column prop="deviceType" label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ row.deviceType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="protocol" label="协议" width="80" />
        <el-table-column prop="ipAddress" label="IP地址" width="130" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-badge :is-dot="true" :type="row.status === 1 ? 'success' : 'danger'" style="margin-right:8px" />
            {{ row.status === 1 ? '在线' : '离线' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑设备' : '添加设备'" width="500px">
      <el-form :model="form" ref="formRef" label-width="90px">
        <el-form-item label="设备编号"><el-input v-model="form.deviceNo" /></el-form-item>
        <el-form-item label="设备名称"><el-input v-model="form.deviceName" /></el-form-item>
        <el-form-item label="设备型号"><el-input v-model="form.deviceModel" /></el-form-item>
        <el-form-item label="厂家"><el-input v-model="form.manufacturer" /></el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="form.deviceType" style="width:100%">
            <el-option value="BIOCHEM" label="生化仪" />
            <el-option value="BLOOD" label="血常规仪" />
            <el-option value="URINE" label="尿分析仪" />
            <el-option value="HBA1C" label="糖化血红蛋白仪" />
          </el-select>
        </el-form-item>
        <el-form-item label="协议">
          <el-select v-model="form.protocol" style="width:100%">
            <el-option value="ASTM" label="ASTM E1394" />
            <el-option value="MINDRAY" label="迈瑞自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP地址"><el-input v-model="form.ipAddress" placeholder="192.168.1.x" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDevices, createDevice, updateDevice, deleteDevice } from '@/api/device'

const loading = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({ id: null, deviceNo: '', deviceName: '', deviceModel: '', manufacturer: '', deviceType: 'BIOCHEM', protocol: 'ASTM', ipAddress: '', status: 1 })

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDevices()
    list.value = res.data || res || []
  } finally { loading.value = false }
}

const openCreate = () => { Object.assign(form, { id: null, deviceNo: '', deviceName: '', deviceModel: '', manufacturer: '', deviceType: 'BIOCHEM', protocol: 'ASTM', ipAddress: '' }); dialogVisible.value = true }
const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  if (form.id) { await updateDevice(form.id, form) } else { await createDevice(form) }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除设备？', '提示', { type: 'warning' })
  await deleteDevice(id); ElMessage.success('删除成功'); loadData()
}

onMounted(loadData)
</script>
<style scoped>
.search-card { margin-bottom: 12px; }
</style>

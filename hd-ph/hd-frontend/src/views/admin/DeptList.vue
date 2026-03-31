<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <b>{{ isHospitalAdmin ? (deptName + ' - 下级村卫生室') : '机构管理' }}</b>
          <el-button type="success" :icon="Plus" @click="openCreate">
            {{ isHospitalAdmin ? '新增村卫生室' : '新增机构' }}
          </el-button>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="deptName" label="机构名称" width="220" />
        <el-table-column prop="deptCode" label="机构编码" width="140" />
        <el-table-column prop="deptType" label="类型" width="100">
          <template #default="{ row }">{{ ['','卫生院','村卫生室','社区卫生中心'][row.deptType] || '其他' }}</template>
        </el-table-column>
        <el-table-column prop="address" label="地址" />
        <el-table-column prop="contactPhone" label="联系电话" width="130" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑机构' : (isHospitalAdmin ? '新增村卫生室' : '新增机构')" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="机构名称"><el-input v-model="form.deptName" /></el-form-item>
        <el-form-item label="机构编码"><el-input v-model="form.deptCode" /></el-form-item>
        <el-form-item label="机构类型" v-if="!isHospitalAdmin">
          <el-select v-model="form.deptType" style="width:100%">
            <el-option :value="1" label="卫生院" />
            <el-option :value="2" label="村卫生室" />
            <el-option :value="3" label="社区卫生中心" />
            <el-option :value="9" label="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.contactPhone" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDepts, createDept, updateDept, deleteDept } from '@/api/admin'

const loading = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const form = reactive({ id: null, deptName: '', deptCode: '', deptType: 2, parentId: 0, address: '', contactPhone: '', status: 1 })

const userInfo = computed(() => {
  try { return JSON.parse(localStorage.getItem('userInfo') || '{}') } catch { return {} }
})
const isHospitalAdmin = computed(() => userInfo.value.userType === 4)
const deptId = computed(() => userInfo.value.deptId)
const deptName = computed(() => userInfo.value.deptName || '')

const loadData = async () => {
  loading.value = true
  try {
    // 卫生院管理员只加载以自己医院为parentId的下级机构
    const params = isHospitalAdmin.value ? { parentId: deptId.value } : {}
    const res = await getDepts(params)
    list.value = res.data || res || []
  } finally { loading.value = false }
}

const openCreate = () => {
  Object.assign(form, {
    id: null, deptName: '', deptCode: '', address: '', contactPhone: '', status: 1,
    // 卫生院管理员新增的默认为村卫生室，parentId设为本院
    deptType: isHospitalAdmin.value ? 2 : 1,
    parentId: isHospitalAdmin.value ? deptId.value : 0
  })
  dialogVisible.value = true
}
const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  // 卫生院管理员创建的机构强制设置parentId和deptType
  if (isHospitalAdmin.value) {
    form.parentId = deptId.value
    form.deptType = 2
  }
  if (form.id) { await updateDept(form.id, form) } else { await createDept(form) }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除机构？', '提示', { type: 'warning' })
  await deleteDept(id); ElMessage.success('删除成功'); loadData()
}

onMounted(loadData)
</script>

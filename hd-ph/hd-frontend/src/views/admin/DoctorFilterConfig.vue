<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <b>责任医生筛选条件配置</b>
          <el-button type="success" :icon="Plus" @click="openCreate">新增条件</el-button>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="filterName" label="条件名称" width="140" />
        <el-table-column prop="filterField" label="对应字段" width="130" />
        <el-table-column prop="filterType" label="筛选类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.filterType === 'SELECT' ? 'warning' : row.filterType === 'NUMBER' ? 'info' : ''">
              {{ row.filterType }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="filterOptions" label="选项配置（JSON）" />
        <el-table-column prop="sort" label="排序" width="70" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="handleStatusChange(row)"
            />
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑筛选条件' : '新增筛选条件'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="条件名称"><el-input v-model="form.filterName" placeholder="如：姓名" /></el-form-item>
        <el-form-item label="对应字段">
          <el-input v-model="form.filterField" placeholder="如：realName, deptId" />
        </el-form-item>
        <el-form-item label="筛选类型">
          <el-select v-model="form.filterType" style="width:100%">
            <el-option value="TEXT" label="文本输入 (TEXT)" />
            <el-option value="SELECT" label="下拉选择 (SELECT)" />
            <el-option value="NUMBER" label="数字范围 (NUMBER)" />
          </el-select>
        </el-form-item>
        <el-form-item label="选项配置" v-if="form.filterType === 'SELECT'">
          <el-input
            v-model="form.filterOptions"
            type="textarea"
            :rows="3"
            placeholder='[{"label":"启用","value":1},{"label":"禁用","value":0}]'
          />
          <div style="font-size:12px;color:#999;margin-top:4px">JSON格式，如：[{"label":"启用","value":1}]</div>
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" style="width:100%" /></el-form-item>
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
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDoctorFilters, createDoctorFilter, updateDoctorFilter, deleteDoctorFilter } from '@/api/admin'

const loading = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const form = reactive({ id: null, filterName: '', filterField: '', filterType: 'TEXT', filterOptions: '', sort: 0, status: 1 })

const loadData = async () => {
  loading.value = true
  try {
    const res = await getDoctorFilters()
    list.value = res.data || res || []
  } finally { loading.value = false }
}

const openCreate = () => {
  Object.assign(form, { id: null, filterName: '', filterField: '', filterType: 'TEXT', filterOptions: '', sort: 0, status: 1 })
  dialogVisible.value = true
}
const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  if (form.id) { await updateDoctorFilter(form.id, form) } else { await createDoctorFilter(form) }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除筛选条件？', '提示', { type: 'warning' })
  await deleteDoctorFilter(id); ElMessage.success('删除成功'); loadData()
}

const handleStatusChange = async (row) => {
  await updateDoctorFilter(row.id, row)
  ElMessage.success(row.status === 1 ? '已启用' : '已禁用')
}

onMounted(loadData)
</script>

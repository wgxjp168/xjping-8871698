<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <b>区域地址管理</b>
          <el-button type="success" :icon="Plus" @click="openCreate">新增区域</el-button>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" stripe row-key="id" default-expand-all>
        <el-table-column prop="areaName" label="区域名称" width="200" />
        <el-table-column prop="areaCode" label="区域编码" width="130" />
        <el-table-column prop="areaLevel" label="级别" width="100">
          <template #default="{ row }">
            {{ ['', '市', '区县', '镇街道', '村'][row.areaLevel] || row.areaLevel }}
          </template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="80" />
        <el-table-column prop="remark" label="备注" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openEdit(row)">编辑</el-button>
            <el-button type="success" size="small" link @click="openCreateChild(row)">添加下级</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑区域' : '新增区域'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="区域名称"><el-input v-model="form.areaName" /></el-form-item>
        <el-form-item label="区域编码"><el-input v-model="form.areaCode" /></el-form-item>
        <el-form-item label="上级区域">
          <el-select v-model="form.parentId" clearable placeholder="不选表示顶级" style="width:100%">
            <el-option v-for="a in flatList" :key="a.id" :value="a.id" :label="a.areaName" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.areaLevel" style="width:100%">
            <el-option :value="1" label="市" />
            <el-option :value="2" label="区县" />
            <el-option :value="3" label="镇街道" />
            <el-option :value="4" label="村" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
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
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAreas, createArea, updateArea, deleteArea } from '@/api/admin'

const loading = ref(false)
const flatList = ref([])
const dialogVisible = ref(false)
const form = reactive({ id: null, areaName: '', areaCode: '', parentId: 0, areaLevel: 3, sort: 0, remark: '', status: 1 })

// 构造树形数据
const list = computed(() => {
  const map = {}
  flatList.value.forEach(a => { map[a.id] = { ...a, children: [] } })
  const roots = []
  flatList.value.forEach(a => {
    if (a.parentId && a.parentId !== 0 && map[a.parentId]) {
      map[a.parentId].children.push(map[a.id])
    } else {
      roots.push(map[a.id])
    }
  })
  return roots
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAreas()
    flatList.value = res.data || res || []
  } finally { loading.value = false }
}

const openCreate = () => {
  Object.assign(form, { id: null, areaName: '', areaCode: '', parentId: 0, areaLevel: 3, sort: 0, remark: '', status: 1 })
  dialogVisible.value = true
}
const openCreateChild = (parent) => {
  Object.assign(form, { id: null, areaName: '', areaCode: '', parentId: parent.id, areaLevel: (parent.areaLevel || 3) + 1, sort: 0, remark: '', status: 1 })
  dialogVisible.value = true
}
const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  if (!form.parentId) form.parentId = 0
  if (form.id) { await updateArea(form.id, form) } else { await createArea(form) }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除区域？若有下级区域请先删除下级。', '提示', { type: 'warning' })
  await deleteArea(id); ElMessage.success('删除成功'); loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>科室管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增科室</el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" border row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }">
        <el-table-column prop="name" label="科室名称" width="200" />
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="sort" label="排序" width="80" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑科室' : '新增科室'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="科室名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="编码">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="上级科室">
          <el-select v-model="form.parentId" style="width:100%" clearable>
            <el-option :value="0" label="顶级科室" />
            <el-option v-for="d in topDepts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ id: null, name: '', code: '', parentId: 0, sort: 0, description: '', status: 1 })

const tableData = ref([
  { id: 1, name: '体检中心', code: 'DEPT001', parentId: 0, sort: 1, description: '综合体检中心', status: 1, children: [
    { id: 2, name: '内科', code: 'DEPT002', parentId: 1, sort: 2, description: '内科检查', status: 1 },
    { id: 3, name: '外科', code: 'DEPT003', parentId: 1, sort: 3, description: '外科检查', status: 1 },
    { id: 4, name: '心血管科', code: 'DEPT004', parentId: 1, sort: 4, description: '心血管检查', status: 1 },
    { id: 5, name: '影像科', code: 'DEPT005', parentId: 1, sort: 5, description: '影像学检查', status: 1 },
    { id: 6, name: '检验科', code: 'DEPT006', parentId: 1, sort: 6, description: '实验室检查', status: 1 },
  ]}
])

const topDepts = computed(() => tableData.value.filter(d => d.parentId === 0))

const handleAdd = () => { Object.assign(form, { id: null, name: '', code: '', parentId: 0, sort: 0, description: '', status: 1 }); dialogVisible.value = true }
const handleEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }
const submitForm = () => { ElMessage.success(form.id ? '更新成功' : '新增成功'); dialogVisible.value = false }
const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确定删除科室 "${row.name}" 吗？`, '提示', { type: 'warning' })
  ElMessage.success('删除成功')
}
</script>

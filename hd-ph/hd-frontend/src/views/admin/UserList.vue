<template>
  <div>
    <el-card class="search-card">
      <el-form :model="query" inline>
        <el-form-item label="用户名">
          <el-input v-model="query.username" clearable style="width:140px" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="query.realName" clearable style="width:130px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button type="success" :icon="Plus" @click="openCreate">新增用户</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="realName" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="deptName" label="机构" />
        <el-table-column prop="userType" label="类型" width="90">
          <template #default="{ row }">{{ ['','普通','医生','管理员'][row.userType] }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginTime" label="最后登录" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openEdit(row)">编辑</el-button>
            <el-button type="warning" size="small" link @click="handleResetPwd(row.id)">重置密码</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.current" v-model:page-size="query.size"
                     :total="total" layout="total, prev, pager, next" class="pagination" @change="loadData" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑用户' : '新增用户'" width="480px">
      <el-form :model="form" ref="formRef" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item v-if="!form.id" label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.realName" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="用户类型">
          <el-select v-model="form.userType" style="width:100%">
            <el-option :value="1" label="普通用户" />
            <el-option :value="2" label="医生" />
            <el-option :value="3" label="管理员" />
          </el-select>
        </el-form-item>
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
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser, resetPassword } from '@/api/admin'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()

const query = reactive({ current: 1, size: 10, username: '', realName: '' })
const form = reactive({ id: null, username: '', password: 'hd2024', realName: '', phone: '', userType: 1, status: 1 })

const loadData = async () => {
  loading.value = true
  try {
    const res = await getUsers(query)
    const data = res.data || res
    list.value = data.records || []
    total.value = data.total || 0
  } finally { loading.value = false }
}

const openCreate = () => { Object.assign(form, { id: null, username: '', password: 'hd2024', realName: '', phone: '', userType: 1, status: 1 }); dialogVisible.value = true }
const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  if (form.id) { await updateUser(form.id, form) } else { await createUser(form) }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除用户？', '提示', { type: 'warning' })
  await deleteUser(id); ElMessage.success('删除成功'); loadData()
}

const handleResetPwd = async (id) => {
  await ElMessageBox.confirm('确认重置密码为 hd2024？', '重置密码', { type: 'warning' })
  await resetPassword(id, 'hd2024'); ElMessage.success('密码已重置为 hd2024')
}

onMounted(loadData)
</script>
<style scoped>
.search-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>

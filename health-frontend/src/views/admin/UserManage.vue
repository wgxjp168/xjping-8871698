<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增用户</el-button>
        </div>
      </template>

      <el-form :model="query" inline class="search-form">
        <el-form-item label="用户名">
          <el-input v-model="query.username" placeholder="输入用户名" clearable style="width:150px" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="query.role" placeholder="全部" clearable style="width:120px">
            <el-option value="ADMIN" label="管理员" />
            <el-option value="DOCTOR" label="医生" />
            <el-option value="USER" label="普通用户" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="头像" width="70">
          <template #default>
            <el-avatar :size="36" icon="UserFilled" />
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="realName" label="真实姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="70">
          <template #default="{ row }">{{ row.gender === 1 ? '男' : '女' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="role" label="角色" width="90">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">{{ getRoleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0"
              @change="(val) => toggleStatus(row, val)" />
          </template>
        </el-table-column>
        <el-table-column prop="lastLogin" label="最后登录" width="160" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
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
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑用户' : '新增用户'" width="520px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码" :prop="form.id ? '' : 'password'">
              <el-input v-model="form.password" type="password" show-password
                :placeholder="form.id ? '不填则不修改' : '请输入密码'" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="真实姓名">
              <el-input v-model="form.realName" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别">
              <el-radio-group v-model="form.gender">
                <el-radio :value="1">男</el-radio>
                <el-radio :value="2">女</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="form.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="form.email" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select v-model="form.role" style="width:100%">
                <el-option value="ADMIN" label="管理员" />
                <el-option value="DOCTOR" label="医生" />
                <el-option value="USER" label="普通用户" />
              </el-select>
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
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUserPage, saveUser, updateUser, deleteUser, toggleUserStatus } from '@/api/user'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()

const query = reactive({ username: '', role: '', pageNum: 1, pageSize: 10 })
const form = reactive({ id: null, username: '', password: '', realName: '', gender: 1, phone: '', email: '', role: 'USER' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const getRoleType = (r) => ({ ADMIN: 'danger', DOCTOR: 'warning', USER: 'success' }[r] || 'info')
const getRoleLabel = (r) => ({ ADMIN: '管理员', DOCTOR: '医生', USER: '用户' }[r] || r)

const loadData = async () => {
  loading.value = true
  try {
    const res = await getUserPage(query)
    tableData.value = res.data.records
    total.value = Number(res.data.total)
  } finally {
    loading.value = false
  }
}

const reset = () => { Object.assign(query, { username: '', role: '', pageNum: 1 }); loadData() }
const handleAdd = () => { Object.assign(form, { id: null, username: '', password: '', realName: '', gender: 1, phone: '', email: '', role: 'USER' }); dialogVisible.value = true }
const handleEdit = (row) => { Object.assign(form, { ...row, password: '' }); dialogVisible.value = true }

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (form.id) {
      await updateUser(form)
    } else {
      await saveUser(form)
    }
    ElMessage.success(form.id ? '更新成功' : '新增成功')
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确定删除用户 "${row.username}" 吗？`, '提示', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('删除成功')
  loadData()
}

const toggleStatus = async (row, val) => {
  try {
    await toggleUserStatus(row.id, val)
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (e) {
    row.status = val ? 0 : 1
  }
}

onMounted(loadData)
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>

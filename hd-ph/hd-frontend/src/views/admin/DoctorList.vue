<template>
  <div>
    <el-card class="search-card">
      <el-form :model="query" inline>
        <el-form-item label="姓名">
          <el-input v-model="query.realName" clearable style="width:140px" />
        </el-form-item>
        <el-form-item label="所属机构" v-if="!isHospitalAdmin">
          <el-select v-model="query.deptId" clearable placeholder="全部机构" style="width:160px">
            <el-option v-for="d in depts" :key="d.id" :value="d.id" :label="d.deptName" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width:120px">
            <el-option :value="1" label="启用" />
            <el-option :value="0" label="禁用" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <b>{{ isHospitalAdmin ? (deptName + ' - 责任医生') : '责任医生查询' }}</b>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="realName" label="姓名" width="100" />
        <el-table-column prop="username" label="登录账号" width="120" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="deptName" label="所属机构" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginTime" label="最后登录" width="160" />
      </el-table>
      <div style="margin-top:10px;color:#666;font-size:13px">共 {{ list.length }} 名责任医生</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getDoctors, getDepts } from '@/api/admin'

const loading = ref(false)
const list = ref([])
const depts = ref([])

const userInfo = computed(() => {
  try { return JSON.parse(localStorage.getItem('userInfo') || '{}') } catch { return {} }
})
const isHospitalAdmin = computed(() => userInfo.value.userType === 4)
const myDeptId = computed(() => userInfo.value.deptId)
const deptName = computed(() => userInfo.value.deptName || '')

const query = reactive({ realName: '', deptId: null, status: null })

const resetQuery = () => {
  Object.assign(query, { realName: '', deptId: null, status: null })
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (query.realName) params.realName = query.realName
    if (query.status !== null && query.status !== '') params.status = query.status
    // 卫生院管理员强制只查本院医生
    if (isHospitalAdmin.value) {
      params.deptId = myDeptId.value
    } else if (query.deptId) {
      params.deptId = query.deptId
    }
    const res = await getDoctors(params)
    list.value = res.data || res || []
  } finally { loading.value = false }
}

onMounted(async () => {
  if (!isHospitalAdmin.value) {
    const deptsRes = await getDepts()
    depts.value = deptsRes.data || deptsRes || []
  }
  loadData()
})
</script>
<style scoped>
.search-card { margin-bottom: 12px; }
</style>

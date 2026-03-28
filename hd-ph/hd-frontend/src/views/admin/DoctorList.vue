<template>
  <div>
    <el-card class="search-card">
      <el-form :model="query" inline>
        <el-form-item v-for="filter in activeFilters" :key="filter.id" :label="filter.filterName">
          <el-input
            v-if="filter.filterType === 'TEXT'"
            v-model="query[filter.filterField]"
            clearable
            style="width:140px"
          />
          <el-select
            v-else-if="filter.filterType === 'SELECT' && filter.filterField === 'deptId'"
            v-model="query.deptId"
            clearable
            placeholder="全部机构"
            style="width:160px"
          >
            <el-option v-for="d in depts" :key="d.id" :value="d.id" :label="d.deptName" />
          </el-select>
          <el-select
            v-else-if="filter.filterType === 'SELECT'"
            v-model="query[filter.filterField]"
            clearable
            style="width:120px"
          >
            <el-option
              v-for="opt in parseOptions(filter.filterOptions)"
              :key="opt.value"
              :value="opt.value"
              :label="opt.label"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
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
import { ref, reactive, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getDoctors, getDoctorFilters, getDepts } from '@/api/admin'

const loading = ref(false)
const list = ref([])
const activeFilters = ref([])
const depts = ref([])

const query = reactive({ realName: '', phone: '', deptId: null, status: null })

const parseOptions = (optStr) => {
  try { return optStr ? JSON.parse(optStr) : [] } catch { return [] }
}

const resetQuery = () => {
  Object.assign(query, { realName: '', phone: '', deptId: null, status: null })
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (query.realName) params.realName = query.realName
    if (query.deptId) params.deptId = query.deptId
    if (query.status !== null && query.status !== '') params.status = query.status
    const res = await getDoctors(params)
    list.value = res.data || res || []
  } finally { loading.value = false }
}

onMounted(async () => {
  const [filtersRes, deptsRes] = await Promise.all([getDoctorFilters(), getDepts()])
  const filters = filtersRes.data || filtersRes || []
  activeFilters.value = filters.filter(f => f.status === 1)
  depts.value = deptsRes.data || deptsRes || []
  loadData()
})
</script>
<style scoped>
.search-card { margin-bottom: 12px; }
</style>

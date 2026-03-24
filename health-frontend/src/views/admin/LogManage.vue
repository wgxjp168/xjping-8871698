<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <el-button type="danger" plain :icon="Delete" @click="handleClear">清空日志</el-button>
        </div>
      </template>

      <el-form :model="query" inline class="search-form">
        <el-form-item label="操作人">
          <el-input v-model="query.username" placeholder="用户名" clearable style="width:130px" />
        </el-form-item>
        <el-form-item label="模块">
          <el-input v-model="query.module" placeholder="操作模块" clearable style="width:130px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:100px">
            <el-option :value="1" label="成功" />
            <el-option :value="0" label="失败" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="username" label="操作人" width="100" />
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="action" label="操作" width="100" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="ip" label="IP地址" width="130" />
        <el-table-column prop="costTime" label="耗时(ms)" width="90">
          <template #default="{ row }">
            <el-tag :type="row.costTime > 1000 ? 'danger' : row.costTime > 500 ? 'warning' : 'success'" size="small">
              {{ row.costTime }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="时间" width="160" />
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Delete, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const query = reactive({ username: '', module: '', status: null, pageNum: 1, pageSize: 15 })

const mockLogs = [
  { id:1, username:'admin', module:'用户管理', action:'新增', description:'新增用户 doctor01', ip:'192.168.1.10', costTime:120, status:1, createTime:'2024-03-24 09:00:01' },
  { id:2, username:'admin', module:'设备管理', action:'更新', description:'更新设备 血压计-001 状态', ip:'192.168.1.10', costTime:95, status:1, createTime:'2024-03-24 09:05:30' },
  { id:3, username:'doctor01', module:'体检管理', action:'录入', description:'录入体检单 HC2024032400001 结果', ip:'192.168.1.20', costTime:230, status:1, createTime:'2024-03-24 10:15:00' },
  { id:4, username:'doctor01', module:'诊断管理', action:'确认', description:'确认诊断报告 ID:5', ip:'192.168.1.20', costTime:88, status:1, createTime:'2024-03-24 11:00:00' },
  { id:5, username:'user01', module:'认证', action:'登录', description:'用户登录', ip:'192.168.1.30', costTime:1200, status:1, createTime:'2024-03-24 08:30:00' },
  { id:6, username:'unknown', module:'认证', action:'登录', description:'登录失败: 密码错误', ip:'192.168.2.100', costTime:50, status:0, createTime:'2024-03-24 08:25:00' },
]

const loadData = () => {
  loading.value = true
  setTimeout(() => {
    tableData.value = mockLogs.filter(l => {
      if (query.username && !l.username.includes(query.username)) return false
      if (query.module && !l.module.includes(query.module)) return false
      if (query.status !== null && l.status !== query.status) return false
      return true
    })
    total.value = tableData.value.length
    loading.value = false
  }, 300)
}

const reset = () => { Object.assign(query, { username: '', module: '', status: null, pageNum: 1 }); loadData() }

const handleClear = async () => {
  await ElMessageBox.confirm('确定清空所有日志吗？此操作不可恢复', '警告', { type: 'warning' })
  tableData.value = []
  total.value = 0
  ElMessage.success('日志已清空')
}

onMounted(loadData)
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>

<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;gap:8px;font-size:16px;font-weight:600">
          <el-icon color="#409EFF"><Document /></el-icon>
          <span>体检记录查询</span>
        </div>
      </template>
      <el-form inline :model="query">
        <el-form-item label="批次号">
          <el-input v-model="query.batchNo" placeholder="体检批次号" style="width:180px" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
            <el-option label="进行中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已取消" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">查询</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="list" stripe border v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="batchNo" label="批次号" width="150" />
        <el-table-column prop="orgName" label="组织单位" />
        <el-table-column prop="examDate" label="体检日期" width="120" />
        <el-table-column prop="syncStatus" label="同步状态" width="100">
          <template #default="{ row }">
            <el-tag :type="[null,'info','success','danger'][row.syncStatus] || 'info'" size="small">
              {{ ['未同步','已同步','失败'][row.syncStatus] }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.current" v-model:page-size="query.size" :total="total"
        layout="total, prev, pager, next" @change="loadList" style="margin-top:16px" />
    </el-card>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/api/request'
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ current: 1, size: 20, batchNo: '', status: null })
onMounted(loadList)
async function loadList() {
  loading.value = true
  try {
    const res = await request.get('/core/physical/page', { params: query })
    if (res.code === 200) { list.value = res.data.records; total.value = res.data.total }
  } finally { loading.value = false }
}
</script>

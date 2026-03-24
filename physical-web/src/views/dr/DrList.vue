<template>
  <div class="dr-list-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon color="#409EFF"><List /></el-icon>
          <span>DR检查记录</span>
        </div>
      </template>

      <!-- 查询条件 -->
      <el-form :model="query" inline class="query-form">
        <el-form-item label="体检批次">
          <el-input v-model="query.batchNo" placeholder="批次号" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="检查日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width:240px"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
            <el-option label="待检查" :value="0" />
            <el-option label="检查中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已同步" :value="3" />
            <el-option label="已取消" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 列表 -->
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="drCode" label="DR条码" width="180" />
        <el-table-column prop="residentName" label="居民姓名" width="100" />
        <el-table-column prop="examPart" label="检查部位" width="120" />
        <el-table-column prop="examDoctor" label="检查医生" width="100" />
        <el-table-column prop="examTime" label="检查时间" width="160" />
        <el-table-column prop="conclusion" label="结论" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.conclusion" :type="conclusionType(row.conclusion)">
              {{ conclusionLabel(row.conclusion) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 2"
              link type="warning" size="small"
              @click="handleSync(row)"
            >同步</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.current"
        v-model:page-size="query.size"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="loadList"
        class="pagination"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="DR记录详情" width="640px">
      <el-descriptions :column="2" border v-if="currentRecord">
        <el-descriptions-item label="DR条码">{{ currentRecord.drCode }}</el-descriptions-item>
        <el-descriptions-item label="申请单号">{{ currentRecord.applyNo }}</el-descriptions-item>
        <el-descriptions-item label="居民姓名">{{ currentRecord.residentName }}</el-descriptions-item>
        <el-descriptions-item label="检查部位">{{ currentRecord.examPart }}</el-descriptions-item>
        <el-descriptions-item label="检查医生">{{ currentRecord.examDoctor }}</el-descriptions-item>
        <el-descriptions-item label="检查时间">{{ currentRecord.examTime }}</el-descriptions-item>
        <el-descriptions-item label="DR结论" :span="2">
          <el-tag v-if="currentRecord.conclusion" :type="conclusionType(currentRecord.conclusion)">
            {{ conclusionLabel(currentRecord.conclusion) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检查结果" :span="2">{{ currentRecord.drResult }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getDrPage, syncDrToCounty } from '@/api/dr'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dateRange = ref([])
const detailVisible = ref(false)
const currentRecord = ref(null)

const query = reactive({ current: 1, size: 20, batchNo: '', status: null, startDate: '', endDate: '' })

watch(dateRange, val => {
  query.startDate = val?.[0] || ''
  query.endDate = val?.[1] || ''
})

onMounted(loadList)

async function loadList() {
  loading.value = true
  try {
    const res = await getDrPage({ ...query })
    if (res.code === 200) {
      tableData.value = res.data.records
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  Object.assign(query, { current: 1, batchNo: '', status: null, startDate: '', endDate: '' })
  dateRange.value = []
  loadList()
}

function showDetail(row) {
  currentRecord.value = row
  detailVisible.value = true
}

async function handleSync(row) {
  const res = await syncDrToCounty(row.id)
  if (res.code === 200) {
    ElMessage.success('同步已触发')
    loadList()
  }
}

const conclusionMap = { NORMAL: { label: '正常', type: 'success' }, ABNORMAL: { label: '异常', type: 'danger' }, RECHECK: { label: '需复查', type: 'warning' } }
const statusMap = { 0: { label: '待检查', type: 'info' }, 1: { label: '检查中', type: '' }, 2: { label: '已完成', type: 'success' }, 3: { label: '已同步', type: 'success' }, 4: { label: '已取消', type: 'danger' } }

const conclusionType = k => conclusionMap[k]?.type || ''
const conclusionLabel = k => conclusionMap[k]?.label || k
const statusType = k => statusMap[k]?.type || ''
const statusLabel = k => statusMap[k]?.label || k
</script>

<style scoped lang="less">
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.query-form { margin-bottom: 16px; }
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>

<template>
  <div class="supplier-score-list-page">
    <div class="page-header">
      <h2>供应商评分管理</h2>
    </div>

    <!-- 搜索/筛选栏 -->
    <el-card class="filter-card" shadow="never">
      <el-form :model="filterForm" inline>
        <el-form-item label="供应商名称">
          <el-input
            v-model="filterForm.name"
            placeholder="请输入供应商名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="评分类型">
          <el-select
            v-model="filterForm.scoreType"
            placeholder="全部"
            clearable
            style="width: 160px"
          >
            <el-option label="B2B企业采购" value="B2B" />
            <el-option label="B2C已定品牌" value="B2C_BRAND" />
            <el-option label="B2C未定品牌" value="B2C_NOBRAND" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级">
          <el-select
            v-model="filterForm.level"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option
              v-for="lvl in ['S','A','B','C','D']"
              :key="lvl"
              :label="lvl"
              :value="lvl"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 批量操作栏 -->
    <div class="batch-bar" v-if="selectedRows.length > 0">
      <span class="selected-tip">已选择 {{ selectedRows.length }} 条</span>
      <el-button
        v-permission="['supplier:score:batch']"
        type="primary"
        size="small"
        @click="handleBatchScore"
      >
        批量评分
      </el-button>
    </div>

    <!-- 供应商列表 -->
    <el-table
      v-loading="tableLoading"
      :data="tableData"
      border
      @selection-change="handleSelectionChange"
      class="supplier-table"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="name" label="供应商名称" min-width="160" />
      <el-table-column prop="code" label="供应商编码" width="140" />
      <el-table-column label="最新评分" width="100" align="center">
        <template #default="{ row }">
          <el-tag
            v-if="row.latestScore"
            :type="getLevelTagType(row.latestScore.level)"
            effect="dark"
          >
            {{ row.latestScore.total_score }}
          </el-tag>
          <span v-else class="text-muted">未评分</span>
        </template>
      </el-table-column>
      <el-table-column label="等级" width="80" align="center">
        <template #default="{ row }">
          <el-tag
            v-if="row.latestScore"
            :type="getLevelTagType(row.latestScore.level)"
            size="small"
          >
            {{ row.latestScore.level }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="最近评分时间" width="160">
        <template #default="{ row }">
          {{ row.latestScore ? formatTime(row.latestScore.created_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="goScore(row.id)">
            评分
          </el-button>
          <el-button text size="small" @click="goScoreHistory(row.id)">
            历史
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :page-sizes="[20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchList"
        @current-change="fetchList"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getSupplierList } from '@/api/supplier'
import { useSupplierStore } from '@/store/modules/supplier'
import { getLevelTagType } from '@/utils/score'

const router = useRouter()
const supplierStore = useSupplierStore()

const tableLoading = ref(false)
const tableData = ref([])
const selectedRows = ref([])

const filterForm = reactive({
  name: '',
  scoreType: '',
  level: ''
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const fetchList = async () => {
  tableLoading.value = true
  try {
    const res = await getSupplierList({
      page: pagination.page,
      size: pagination.size,
      ...filterForm
    })
    tableData.value = res.data?.list || []
    pagination.total = res.data?.total || 0
  } catch (error) {
    console.error('获取供应商列表失败：', error)
    tableData.value = []
  } finally {
    tableLoading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchList()
}

const handleReset = () => {
  Object.assign(filterForm, { name: '', scoreType: '', level: '' })
  pagination.page = 1
  fetchList()
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleBatchScore = async () => {
  const ids = selectedRows.value.map(row => row.id)
  ElMessage.info(`批量评分功能开发中，已选 ${ids.length} 个供应商`)
}

const goScore = (supplierId) => {
  router.push(`/supplier/score/${supplierId}`)
}

const goScoreHistory = (supplierId) => {
  router.push({ path: `/supplier/score/${supplierId}`, query: { tab: 'history' } })
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', { hour12: false })
}

const getStatusType = (status) => {
  const map = { active: 'success', pending: 'warning', suspended: 'danger', blacklisted: 'info' }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const map = { active: '活跃', pending: '待审核', suspended: '已暂停', blacklisted: '黑名单' }
  return map[status] || status
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped lang="scss">
.supplier-score-list-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 16px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #303133;
  }
}

.filter-card {
  margin-bottom: 16px;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 16px;
  background: #ecf5ff;
  border-radius: 4px;
}

.selected-tip {
  font-size: 13px;
  color: #409eff;
}

.supplier-table {
  width: 100%;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 4px;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}
</style>

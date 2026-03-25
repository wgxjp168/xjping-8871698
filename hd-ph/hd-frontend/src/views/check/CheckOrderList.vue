<template>
  <div>
    <el-card class="search-card">
      <el-form :model="query" inline>
        <el-form-item label="姓名">
          <el-input v-model="query.residentName" placeholder="居民姓名" clearable style="width:130px" />
        </el-form-item>
        <el-form-item label="身份证">
          <el-input v-model="query.idCard" placeholder="身份证号" clearable style="width:190px" />
        </el-form-item>
        <el-form-item label="年度">
          <el-input-number v-model="query.checkYear" :min="2020" :max="2030" style="width:120px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width:110px">
            <el-option :value="0" label="待体检" />
            <el-option :value="1" label="体检中" />
            <el-option :value="2" label="已完成" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
          <el-button type="success" :icon="Plus" @click="openCreate">新建体检单</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="orderNo" label="体检单号" width="155" />
        <el-table-column prop="residentName" label="居民" width="90" />
        <el-table-column prop="idCard" label="身份证" width="185" />
        <el-table-column prop="checkYear" label="年度" width="65" />
        <el-table-column prop="checkDate" label="体检日期" width="115" />
        <el-table-column prop="checkType" label="类型" width="100">
          <template #default="{ row }">{{ typeText(row.checkType) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="goDetail(row.id)">详情</el-button>
            <el-button type="warning" size="small" link @click="createDrOrder(row)">DR申请</el-button>
            <el-button v-if="row.status === 0" type="success" size="small" link @click="startCheck(row.id)">开始体检</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="query.current"
        v-model:page-size="query.size"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @change="loadData"
      />
    </el-card>

    <!-- 新建体检单弹窗 -->
    <el-dialog v-model="dialogVisible" title="新建体检单" width="500px">
      <el-form :model="form" ref="formRef" label-width="90px">
        <el-form-item label="居民姓名" prop="residentName">
          <el-input v-model="form.residentName" placeholder="居民姓名" />
        </el-form-item>
        <el-form-item label="身份证号" prop="idCard">
          <el-input v-model="form.idCard" placeholder="身份证号" />
        </el-form-item>
        <el-form-item label="体检年度">
          <el-input-number v-model="form.checkYear" :min="2020" :max="2030" style="width:100%" />
        </el-form-item>
        <el-form-item label="体检类型">
          <el-select v-model="form.checkType" style="width:100%">
            <el-option :value="1" label="老年人健康体检" />
            <el-option :value="2" label="高血压患者随访" />
            <el-option :value="3" label="糖尿病患者随访" />
            <el-option :value="4" label="孕产妇检查" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCheckOrders, createCheckOrder, updateCheckOrderStatus, deleteCheckOrder } from '@/api/check'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()

const query = reactive({ current: 1, size: 10, residentName: '', idCard: '', checkYear: new Date().getFullYear(), status: null })
const form = reactive({ residentId: null, residentName: '', idCard: '', checkYear: new Date().getFullYear(), checkType: 1 })

const typeText = (t) => ['','老年人体检','高血压随访','糖尿病随访','孕产妇'][t] || '未知'
const statusText = (s) => ['待体检','体检中','已完成','已作废'][s] || '未知'
const statusType = (s) => ['info','warning','success','danger'][s] || 'info'

const loadData = async () => {
  loading.value = true
  try {
    const res = await getCheckOrders(query)
    const data = res.data || res
    list.value = data.records || []
    total.value = data.total || 0
  } finally { loading.value = false }
}

const resetQuery = () => { Object.assign(query, { residentName: '', idCard: '', status: null, current: 1 }); loadData() }

const openCreate = () => {
  Object.assign(form, {
    residentId: route.query.residentId || null,
    residentName: route.query.residentName || '',
    idCard: route.query.idCard || '',
    checkYear: new Date().getFullYear(), checkType: 1
  })
  dialogVisible.value = true
}

const handleSave = async () => {
  await createCheckOrder(form)
  ElMessage.success('体检单创建成功')
  dialogVisible.value = false
  loadData()
}

const goDetail = (id) => router.push(`/check-orders/${id}`)
const startCheck = async (id) => { await updateCheckOrderStatus(id, 1); ElMessage.success('已开始体检'); loadData() }
const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await deleteCheckOrder(id); ElMessage.success('删除成功'); loadData()
}
const createDrOrder = (row) => router.push({ path: '/dr-orders', query: { checkOrderId: row.id, residentName: row.residentName, idCard: row.idCard } })

onMounted(loadData)
</script>

<style scoped>
.search-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>

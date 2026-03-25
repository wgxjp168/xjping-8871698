<template>
  <div>
    <el-card class="search-card">
      <el-form :model="query" inline>
        <el-form-item label="姓名">
          <el-input v-model="query.name" placeholder="居民姓名" clearable style="width:150px" />
        </el-form-item>
        <el-form-item label="身份证">
          <el-input v-model="query.idCard" placeholder="身份证号" clearable style="width:200px" />
        </el-form-item>
        <el-form-item label="乡镇">
          <el-input v-model="query.town" placeholder="乡镇/街道" clearable style="width:150px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
          <el-button type="success" :icon="Plus" @click="openCreate">新增</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="archiveNo" label="档案号" width="130" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column prop="gender" label="性别" width="60">
          <template #default="{ row }">{{ row.gender === 1 ? '男' : '女' }}</template>
        </el-table-column>
        <el-table-column prop="idCard" label="身份证号" width="185" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="town" label="乡镇" />
        <el-table-column prop="village" label="村/社区" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openEdit(row)">编辑</el-button>
            <el-button type="success" size="small" link @click="createOrder(row)">建体检单</el-button>
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

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑居民' : '新增居民'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别" prop="gender">
              <el-select v-model="form.gender" style="width:100%">
                <el-option :value="1" label="男" />
                <el-option :value="2" label="女" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="身份证号" prop="idCard">
              <el-input v-model="form.idCard" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="form.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="乡镇">
              <el-input v-model="form.town" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="村/社区">
              <el-input v-model="form.village" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="住址">
              <el-input v-model="form.address" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { getResidents, createResident, updateResident, deleteResident } from '@/api/resident'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()

const query = reactive({ current: 1, size: 10, name: '', idCard: '', town: '' })
const form = reactive({ id: null, name: '', gender: 1, idCard: '', phone: '', town: '', village: '', address: '', district: '惠东县' })

const rules = {
  name: [{ required: true, message: '请输入姓名' }],
  idCard: [{ required: true, message: '请输入身份证号' }],
  gender: [{ required: true }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getResidents(query)
    const data = res.data || res
    list.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

const resetQuery = () => { Object.assign(query, { name: '', idCard: '', town: '', current: 1 }); loadData() }

const openCreate = () => {
  Object.assign(form, { id: null, name: '', gender: 1, idCard: '', phone: '', town: '', village: '', address: '', district: '惠东县' })
  dialogVisible.value = true
}

const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  await formRef.value.validate()
  if (form.id) {
    await updateResident(form.id, form)
  } else {
    await createResident(form)
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await deleteResident(id)
  ElMessage.success('删除成功')
  loadData()
}

const createOrder = (row) => {
  router.push({ path: '/check-orders', query: { residentId: row.id, residentName: row.name, idCard: row.idCard } })
}

onMounted(loadData)
</script>

<style scoped>
.search-card { margin-bottom: 12px; }
.pagination { margin-top: 12px; justify-content: flex-end; }
</style>

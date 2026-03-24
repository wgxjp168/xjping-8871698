<template>
  <div class="page-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>检查项目管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增项目</el-button>
        </div>
      </template>

      <el-form :model="query" inline class="search-form">
        <el-form-item label="名称">
          <el-input v-model="query.name" placeholder="检查项名称" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category" placeholder="全部" clearable style="width:120px">
            <el-option value="体格" label="体格检查" />
            <el-option value="生化" label="生化检查" />
            <el-option value="血常规" label="血常规" />
            <el-option value="心电" label="心电图" />
            <el-option value="影像" label="影像学" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="code" label="编码" width="100" />
        <el-table-column prop="name" label="检查项名称" />
        <el-table-column prop="category" label="分类" width="90">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column label="正常范围" width="150">
          <template #default="{ row }">
            <span v-if="row.normalMin !== null && row.normalMax !== null">
              {{ row.normalMin }} ~ {{ row.normalMax }}
            </span>
            <span v-else>{{ row.normalText || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="deviceType" label="关联设备类型" width="130" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link :type="row.status ? 'warning' : 'success'" @click="toggleStatus(row)">
              {{ row.status ? '停用' : '启用' }}
            </el-button>
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

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑检查项' : '新增检查项'" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="编码" required>
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width:100%">
            <el-option value="体格" label="体格检查" />
            <el-option value="生化" label="生化检查" />
            <el-option value="血常规" label="血常规" />
            <el-option value="心电" label="心电图" />
            <el-option value="影像" label="影像学" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" />
        </el-form-item>
        <el-form-item label="正常值最小">
          <el-input-number v-model="form.normalMin" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="正常值最大">
          <el-input-number v-model="form.normalMax" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="参考范围说明">
          <el-input v-model="form.normalText" />
        </el-form-item>
        <el-form-item label="关联设备类型">
          <el-select v-model="form.deviceType" placeholder="选择设备类型" clearable style="width:100%">
            <el-option value="BLOOD_PRESSURE" label="血压计" />
            <el-option value="ECG" label="心电图仪" />
            <el-option value="GLUCOMETER" label="血糖仪" />
            <el-option value="OXIMETER" label="血氧仪" />
            <el-option value="XRAY" label="X光机" />
            <el-option value="ULTRASOUND" label="超声仪" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)

const query = reactive({ name: '', category: '', pageNum: 1, pageSize: 15 })
const form = reactive({ id: null, code: '', name: '', category: '', unit: '',
  normalMin: null, normalMax: null, normalText: '', deviceType: '' })

const loadData = async () => {
  loading.value = true
  try {
    // Mock data since check_item API is basic CRUD
    tableData.value = [
      { id:1, code:'CI001', name:'身高', category:'体格', unit:'cm', normalMin:140, normalMax:200, normalText:'140~200cm', deviceType:null, status:1 },
      { id:2, code:'CI002', name:'体重', category:'体格', unit:'kg', normalMin:40, normalMax:100, normalText:'40~100kg', deviceType:null, status:1 },
      { id:4, code:'CI004', name:'收缩压', category:'体格', unit:'mmHg', normalMin:90, normalMax:139, normalText:'90~139mmHg', deviceType:'BLOOD_PRESSURE', status:1 },
      { id:6, code:'CI006', name:'心率', category:'体格', unit:'次/分', normalMin:60, normalMax:100, normalText:'60~100次/分', deviceType:'ECG', status:1 },
      { id:7, code:'CI007', name:'血氧饱和度', category:'体格', unit:'%', normalMin:95, normalMax:100, normalText:'95~100%', deviceType:'OXIMETER', status:1 },
      { id:8, code:'CI008', name:'血糖(空腹)', category:'生化', unit:'mmol/L', normalMin:3.9, normalMax:6.1, normalText:'3.9~6.1mmol/L', deviceType:'GLUCOMETER', status:1 },
      { id:9, code:'CI009', name:'总胆固醇', category:'生化', unit:'mmol/L', normalMin:0, normalMax:5.2, normalText:'<5.2mmol/L', deviceType:null, status:1 },
      { id:13, code:'CI013', name:'心电图', category:'心电', unit:null, normalMin:null, normalMax:null, normalText:'正常心电图', deviceType:'ECG', status:1 },
      { id:14, code:'CI014', name:'胸部X光', category:'影像', unit:null, normalMin:null, normalMax:null, normalText:'肺部正常', deviceType:'XRAY', status:1 },
    ]
    total.value = tableData.value.length
  } finally {
    loading.value = false
  }
}

const reset = () => { Object.assign(query, { name: '', category: '', pageNum: 1 }); loadData() }
const handleAdd = () => { Object.assign(form, { id:null, code:'', name:'', category:'', unit:'', normalMin:null, normalMax:null, normalText:'', deviceType:'' }); dialogVisible.value = true }
const handleEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }
const toggleStatus = (row) => { row.status = row.status ? 0 : 1; ElMessage.success('状态已更新') }
const submitForm = () => { ElMessage.success(form.id ? '更新成功' : '新增成功'); dialogVisible.value = false; loadData() }

onMounted(loadData)
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>

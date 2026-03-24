<template>
  <div class="permissions-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon color="#E6A23C"><Key /></el-icon>
          <span>医生权限管理</span>
          <el-button type="primary" size="small" @click="handleSyncCounty" :loading="syncing">
            <el-icon><Refresh /></el-icon> 同步县域账号
          </el-button>
        </div>
      </template>

      <el-form :model="query" inline>
        <el-form-item label="医生ID">
          <el-input v-model="query.docId" placeholder="医生ID" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="科室">
          <el-select v-model="query.dept" placeholder="全部" clearable style="width:130px">
            <el-option label="化验室" value="LAB" />
            <el-option label="DR室" value="DR_ROOM" />
            <el-option label="公卫科" value="PUBLIC_HEALTH" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">查询</el-button>
          <el-button type="success" @click="showGrantDialog">
            <el-icon><Plus /></el-icon> 授予权限
          </el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="docId" label="医生ID" width="120" />
        <el-table-column prop="docName" label="医生姓名" width="100" />
        <el-table-column prop="deptName" label="科室" width="100" />
        <el-table-column prop="projectName" label="项目名称" width="140" />
        <el-table-column prop="operateType" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="operateTypeColor(row.operateType)" size="small">
              {{ operateTypeLabel(row.operateType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scope" label="权限范围" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ scopeLabel(row.scope) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '有效' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="grantedBy" label="授权人" width="100" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleRevoke(row)">撤权</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.current"
        v-model:page-size="query.size"
        :total="total"
        layout="total, prev, pager, next"
        @change="loadList"
        class="pagination"
      />
    </el-card>

    <!-- 授予权限弹窗 -->
    <el-dialog v-model="grantVisible" title="授予权限" width="520px">
      <el-form :model="grantForm" :rules="grantRules" ref="grantFormRef" label-width="100px">
        <el-form-item label="医生ID" prop="docId">
          <el-input v-model="grantForm.docId" placeholder="输入医生ID" />
        </el-form-item>
        <el-form-item label="医生姓名" prop="docName">
          <el-input v-model="grantForm.docName" placeholder="输入医生姓名" />
        </el-form-item>
        <el-form-item label="科室" prop="dept">
          <el-select v-model="grantForm.dept" placeholder="选择科室" style="width:100%">
            <el-option label="化验室" value="LAB" />
            <el-option label="DR室" value="DR_ROOM" />
            <el-option label="公卫科" value="PUBLIC_HEALTH" />
          </el-select>
        </el-form-item>
        <el-form-item label="检验项目" prop="projectCode">
          <el-select v-model="grantForm.projectCode" placeholder="选择项目" style="width:100%" @change="onProjectChange">
            <el-option label="生化检验 (BIOCHEM)" value="BIOCHEM" />
            <el-option label="血常规 (CBC)" value="CBC" />
            <el-option label="糖化血红蛋白 (HBA1C)" value="HBA1C" />
            <el-option label="尿常规 (URINE)" value="URINE" />
            <el-option label="DR放射 (DR)" value="DR" />
            <el-option label="血压 (BP)" value="BP" />
            <el-option label="体重身高 (BODY)" value="BODY" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作权限" prop="operateType">
          <el-checkbox-group v-model="grantForm.operateTypes">
            <el-checkbox label="QUERY">查询</el-checkbox>
            <el-checkbox label="INPUT">录入</el-checkbox>
            <el-checkbox label="AUDIT">审核</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="权限范围">
          <el-select v-model="grantForm.scope" style="width:100%">
            <el-option label="全院" value="ALL" />
            <el-option label="本院" value="OWN" />
            <el-option label="指定片区" value="ZONE" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grantVisible = false">取消</el-button>
        <el-button type="primary" :loading="grantLoading" @click="submitGrant">确认授权</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDoctorPermissions, grantPermission, revokePermission, syncFromCounty } from '@/api/auth'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const syncing = ref(false)
const grantVisible = ref(false)
const grantLoading = ref(false)
const grantFormRef = ref(null)
const tableData = ref([])
const total = ref(0)

const query = reactive({ current: 1, size: 20, docId: '', dept: '' })
const grantForm = reactive({
  docId: '', docName: '', dept: '', deptName: '',
  projectCode: '', projectName: '', operateTypes: [], scope: 'ALL'
})
const grantRules = {
  docId: [{ required: true, message: '请输入医生ID' }],
  docName: [{ required: true, message: '请输入医生姓名' }],
  projectCode: [{ required: true, message: '请选择项目' }]
}

onMounted(loadList)

async function loadList() {
  loading.value = true
  // 简化：查询指定医生权限或所有权限
  try {
    if (query.docId) {
      const res = await getDoctorPermissions(query.docId)
      if (res.code === 200) {
        tableData.value = res.data
        total.value = res.data.length
      }
    } else {
      tableData.value = []
      total.value = 0
    }
  } finally {
    loading.value = false
  }
}

function showGrantDialog() {
  Object.assign(grantForm, { docId: '', docName: '', dept: '', projectCode: '', operateTypes: [], scope: 'ALL' })
  grantVisible.value = true
}

async function submitGrant() {
  const valid = await grantFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (grantForm.operateTypes.length === 0) {
    ElMessage.warning('请至少选择一种操作权限')
    return
  }
  grantLoading.value = true
  try {
    // 为每种操作类型单独授权
    for (const operateType of grantForm.operateTypes) {
      await grantPermission({
        docId: grantForm.docId,
        docName: grantForm.docName,
        dept: grantForm.dept,
        projectCode: grantForm.projectCode,
        projectName: grantForm.projectName,
        operateType,
        scope: grantForm.scope,
        status: 1
      })
    }
    ElMessage.success('授权成功')
    grantVisible.value = false
    if (query.docId === grantForm.docId) loadList()
  } finally {
    grantLoading.value = false
  }
}

async function handleRevoke(row) {
  await ElMessageBox.confirm(`确认撤销【${row.docName}】的【${row.projectName}-${operateTypeLabel(row.operateType)}】权限？`, '撤权确认', { type: 'warning' })
  const res = await revokePermission(row.id)
  if (res.code === 200) {
    ElMessage.success('已撤销权限')
    loadList()
  }
}

async function handleSyncCounty() {
  syncing.value = true
  try {
    const res = await syncFromCounty()
    if (res.code === 200) ElMessage.success('县域同步已触发，请稍候')
  } finally {
    syncing.value = false
  }
}

const projectMap = { BIOCHEM: '生化检验', CBC: '血常规', HBA1C: '糖化血红蛋白', URINE: '尿常规', DR: 'DR放射', BP: '血压', BODY: '体重身高' }
function onProjectChange(val) { grantForm.projectName = projectMap[val] || val }

const operateTypeLabel = k => ({ QUERY: '查询', INPUT: '录入', AUDIT: '审核' }[k] || k)
const operateTypeColor = k => ({ QUERY: 'info', INPUT: '', AUDIT: 'warning' }[k] || '')
const scopeLabel = k => ({ ALL: '全院', OWN: '本院', ZONE: '指定片区' }[k] || k)
</script>

<style scoped lang="less">
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  .el-button { margin-left: auto; }
}
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>

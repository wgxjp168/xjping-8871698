<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <b>角色权限管理</b>
          <el-button type="success" :icon="Plus" @click="openCreate">新增角色</el-button>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="roleCode" label="角色编码" width="180" />
        <el-table-column prop="roleName" label="角色名称" width="160" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="handleStatusChange(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openEdit(row)">编辑</el-button>
            <el-button type="warning" size="small" link @click="openPermission(row)">分配权限</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑角色 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑角色' : '新增角色'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="角色编码"><el-input v-model="form.roleCode" :disabled="!!form.id" /></el-form-item>
        <el-form-item label="角色名称"><el-input v-model="form.roleName" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分配权限 -->
    <el-dialog v-model="permDialogVisible" :title="`分配权限 - ${currentRole?.roleName}`" width="600px">
      <div style="max-height:420px;overflow-y:auto">
        <el-checkbox-group v-model="selectedPerms">
          <div v-for="group in permGroups" :key="group.parentCode" style="margin-bottom:16px">
            <div style="font-weight:bold;margin-bottom:6px;color:#333">{{ group.parentName }}</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;padding-left:12px">
              <el-checkbox
                v-for="perm in group.perms"
                :key="perm.permCode"
                :label="perm.permCode"
              >{{ perm.permName }}</el-checkbox>
            </div>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="selectAllPerms">全选</el-button>
        <el-button @click="selectedPerms = []">清空</el-button>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePerms">保存权限</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getRoles, createRole, updateRole, deleteRole,
  updateRoleStatus, getRolePermissions, assignRolePermissions,
  getPermissions
} from '@/api/admin'

const loading = ref(false)
const list = ref([])
const allPerms = ref([])
const dialogVisible = ref(false)
const permDialogVisible = ref(false)
const currentRole = ref(null)
const selectedPerms = ref([])

const form = reactive({ id: null, roleCode: '', roleName: '', description: '', status: 1 })

const permGroups = computed(() => {
  const groups = {}
  const noParent = []
  allPerms.value.forEach(p => {
    if (!p.parentCode) {
      noParent.push(p)
    } else {
      if (!groups[p.parentCode]) groups[p.parentCode] = []
      groups[p.parentCode].push(p)
    }
  })
  const result = []
  noParent.forEach(parent => {
    result.push({
      parentCode: parent.permCode,
      parentName: parent.permName,
      perms: groups[parent.permCode] || []
    })
  })
  // 没有父级的权限也显示
  allPerms.value.filter(p => !p.parentCode).forEach(p => {
    if (!result.find(g => g.parentCode === p.permCode) && (!groups[p.permCode] || groups[p.permCode].length === 0)) {
      result.push({ parentCode: p.permCode, parentName: p.permName, perms: [p] })
    }
  })
  // 收集其他没有父级记录的权限
  const allParentCodes = new Set(noParent.map(p => p.permCode))
  allPerms.value.forEach(p => {
    if (p.parentCode && !allParentCodes.has(p.parentCode)) {
      const existing = result.find(g => g.parentCode === p.parentCode)
      if (existing) {
        existing.perms.push(p)
      } else {
        result.push({ parentCode: p.parentCode, parentName: p.parentCode, perms: [p] })
      }
    }
  })
  return result.filter(g => g.perms.length > 0)
})

const loadData = async () => {
  loading.value = true
  try {
    const [rolesRes, permsRes] = await Promise.all([getRoles(), getPermissions()])
    list.value = rolesRes.data || rolesRes || []
    allPerms.value = permsRes.data || permsRes || []
  } finally { loading.value = false }
}

const openCreate = () => {
  Object.assign(form, { id: null, roleCode: '', roleName: '', description: '', status: 1 })
  dialogVisible.value = true
}
const openEdit = (row) => { Object.assign(form, row); dialogVisible.value = true }

const handleSave = async () => {
  if (form.id) { await updateRole(form.id, form) } else { await createRole(form) }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除角色？删除后关联用户将失去该角色权限。', '提示', { type: 'warning' })
  await deleteRole(id); ElMessage.success('删除成功'); loadData()
}

const handleStatusChange = async (row) => {
  await updateRoleStatus(row.id, row.status)
  ElMessage.success(row.status === 1 ? '已启用' : '已禁用')
}

const openPermission = async (row) => {
  currentRole.value = row
  const res = await getRolePermissions(row.id)
  selectedPerms.value = res.data || res || []
  permDialogVisible.value = true
}

const selectAllPerms = () => {
  selectedPerms.value = allPerms.value.map(p => p.permCode)
}

const handleSavePerms = async () => {
  await assignRolePermissions(currentRole.value.id, selectedPerms.value)
  ElMessage.success('权限分配成功')
  permDialogVisible.value = false
}

onMounted(loadData)
</script>

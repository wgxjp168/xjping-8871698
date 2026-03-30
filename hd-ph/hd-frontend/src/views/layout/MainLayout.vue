<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo" :class="{ collapsed }">
        <span v-if="!collapsed">公卫体检系统</span>
        <span v-else>公卫</span>
      </div>
      <el-menu
        :default-active="currentPath"
        :collapse="collapsed"
        router
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <template #title>首页概览</template>
        </el-menu-item>

        <!-- 居民管理：超级管理员、卫生院管理员可见 -->
        <el-sub-menu index="resident" v-if="isSuperAdmin || isHospitalAdmin">
          <template #title>
            <el-icon><UserFilled /></el-icon>
            <span>居民管理</span>
          </template>
          <el-menu-item index="/residents">居民档案</el-menu-item>
        </el-sub-menu>

        <!-- 体检管理：超级管理员、卫生院管理员、有ORDER权限的医生可见 -->
        <el-sub-menu index="check" v-if="isSuperAdmin || isHospitalAdmin || hasPerm('ORDER:VIEW')">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>体检管理</span>
          </template>
          <el-menu-item index="/check-orders">体检单管理</el-menu-item>
        </el-sub-menu>

        <!-- DR影像：超级管理员、卫生院管理员、DR医生可见 -->
        <el-sub-menu index="dr" v-if="isSuperAdmin || isHospitalAdmin || hasPerm('DR:VIEW')">
          <template #title>
            <el-icon><Camera /></el-icon>
            <span>DR影像</span>
          </template>
          <el-menu-item index="/dr-orders">DR申请单</el-menu-item>
          <el-menu-item index="/dr-scan">DR扫码签到</el-menu-item>
        </el-sub-menu>

        <!-- 设备管理：超级管理员、卫生院管理员可见 -->
        <el-sub-menu index="device" v-if="isSuperAdmin || isHospitalAdmin">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>设备管理</span>
          </template>
          <el-menu-item index="/devices">设备列表</el-menu-item>
        </el-sub-menu>

        <!-- 系统管理：超级管理员全部可见 -->
        <el-sub-menu index="admin" v-if="isSuperAdmin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/users">用户管理</el-menu-item>
          <el-menu-item index="/depts">医疗机构管理</el-menu-item>
          <el-menu-item index="/roles">角色权限管理</el-menu-item>
          <el-menu-item index="/areas">区域地址管理</el-menu-item>
          <el-menu-item index="/doctors">责任医生查询</el-menu-item>
          <el-menu-item index="/doctor-filters">医生筛选条件配置</el-menu-item>
        </el-sub-menu>

        <!-- 卫生院管理：卫生院管理员可见（用户管理+医生管理） -->
        <el-sub-menu index="hospital-admin" v-if="isHospitalAdmin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>卫生院管理</span>
          </template>
          <el-menu-item index="/users">用户管理</el-menu-item>
          <el-menu-item index="/doctors">责任医生管理</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Fold v-if="!collapsed" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="roleLabel" :type="roleTagType" size="small" class="role-tag">{{ roleLabel }}</el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><Avatar /></el-icon>
              {{ userInfo.realName || userInfo.username }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { logout } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const userInfo = computed(() => {
  try { return JSON.parse(localStorage.getItem('userInfo') || '{}') } catch { return {} }
})

// userType: 3=超级管理员, 4=卫生院管理员, 2=责任医生, 1=普通操作员
const isSuperAdmin = computed(() => userInfo.value.userType === 3)
const isHospitalAdmin = computed(() => userInfo.value.userType === 4)
const isDoctor = computed(() => userInfo.value.userType === 2)

const hasPerm = (code) => {
  const perms = userInfo.value.permissions || []
  return perms.includes(code)
}

const roleLabel = computed(() => {
  const ut = userInfo.value.userType
  if (ut === 3) return '超级管理员'
  if (ut === 4) return '卫生院管理员'
  if (ut === 2) return '责任医生'
  return '操作员'
})

const roleTagType = computed(() => {
  const ut = userInfo.value.userType
  if (ut === 3) return 'danger'
  if (ut === 4) return 'warning'
  if (ut === 2) return ''
  return 'info'
})

const currentPath = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title || '')

const handleCommand = async (cmd) => {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
    await logout().catch(() => {})
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    router.push('/login')
    ElMessage.success('已退出登录')
  }
}
</script>

<style scoped>
.main-layout { height: 100vh; }
.sidebar {
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  font-weight: bold;
  background: #002140;
  white-space: nowrap;
  overflow: hidden;
}
.logo.collapsed { font-size: 12px; }
.header {
  background: white;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.header-left { display: flex; align-items: center; gap: 16px; }
.collapse-btn { font-size: 18px; cursor: pointer; color: #666; }
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-right .user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #333;
}
.role-tag { margin-right: 4px; }
.main-content { background: #f0f2f5; padding: 20px; overflow-y: auto; }
</style>

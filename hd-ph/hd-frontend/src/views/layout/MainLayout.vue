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

        <el-sub-menu index="resident">
          <template #title>
            <el-icon><UserFilled /></el-icon>
            <span>居民管理</span>
          </template>
          <el-menu-item index="/residents">居民档案</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="check">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>体检管理</span>
          </template>
          <el-menu-item index="/check-orders">体检单管理</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="dr">
          <template #title>
            <el-icon><Camera /></el-icon>
            <span>DR影像</span>
          </template>
          <el-menu-item index="/dr-orders">DR申请单</el-menu-item>
          <el-menu-item index="/dr-scan">DR扫码签到</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="device">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>设备管理</span>
          </template>
          <el-menu-item index="/devices">设备列表</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="admin" v-if="isAdmin">
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

const isAdmin = computed(() => userInfo.value.userType === 3)
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
.header-right .user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #333;
}
.main-content { background: #f0f2f5; padding: 20px; overflow-y: auto; }
</style>

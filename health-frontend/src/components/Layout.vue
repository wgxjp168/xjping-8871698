<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon size="28" color="#fff"><FirstAidKit /></el-icon>
        <span v-show="!isCollapse" class="logo-text">健康检查系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#fff"
        router
        unique-opened
      >
        <template v-for="route in menuRoutes" :key="route.path">
          <!-- 有子菜单 -->
          <el-sub-menu v-if="route.children?.length" :index="route.path">
            <template #title>
              <el-icon><component :is="route.meta?.icon" /></el-icon>
              <span>{{ route.meta?.title }}</span>
            </template>
            <el-menu-item
              v-for="child in route.children.filter(c => !c.meta?.hidden)"
              :key="child.path"
              :index="route.path + '/' + child.path"
            >
              {{ child.meta?.title }}
            </el-menu-item>
          </el-sub-menu>
          <!-- 无子菜单 -->
          <el-menu-item v-else :index="route.path">
            <el-icon><component :is="route.meta?.icon" /></el-icon>
            <template #title>{{ route.meta?.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse" size="20">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ userStore.userInfo?.realName || userStore.userInfo?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapse = ref(false)

const activeMenu = computed(() => route.path)

const breadcrumbs = computed(() => {
  return route.matched
    .filter(r => r.meta?.title && r.path !== '/')
    .map(r => ({ path: r.path, title: r.meta.title }))
})

const menuRoutes = [
  {
    path: '/dashboard',
    meta: { title: '工作台', icon: 'Odometer' }
  },
  {
    path: '/check',
    meta: { title: '体检管理', icon: 'Document' },
    children: [
      { path: 'list', meta: { title: '体检单列表' } },
      { path: 'items', meta: { title: '检查项目' } },
      { path: 'packages', meta: { title: '检查套餐' } }
    ]
  },
  {
    path: '/diagnosis',
    meta: { title: '诊断管理', icon: 'Reading' },
    children: [
      { path: 'list', meta: { title: '诊断报告' } }
    ]
  },
  {
    path: '/device',
    meta: { title: '设备管理', icon: 'Monitor' },
    children: [
      { path: 'list', meta: { title: '设备列表' } },
      { path: 'monitor', meta: { title: '实时监控' } }
    ]
  },
  {
    path: '/admin',
    meta: { title: '系统管理', icon: 'Setting' },
    children: [
      { path: 'user', meta: { title: '用户管理' } },
      { path: 'dept', meta: { title: '科室管理' } },
      { path: 'log', meta: { title: '操作日志' } }
    ]
  }
]

const handleCommand = async (cmd) => {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background-color: #001529;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background-color: #002140;
  overflow: hidden;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.el-menu {
  border-right: none;
}

.header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  color: #666;
}

.collapse-btn:hover {
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #333;
}

.username {
  font-size: 14px;
}

.main {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>

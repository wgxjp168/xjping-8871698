<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon size="24" color="#fff"><FirstAidKit /></el-icon>
        <span>公卫体检系统</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#fff"
        router
        class="side-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <span>工作台</span>
        </el-menu-item>

        <el-menu-item-group title="DR放射检查">
          <el-menu-item index="/dr/scan" v-if="hasPermission('DR:INPUT')">
            <el-icon><Camera /></el-icon>
            <span>DR扫码检查</span>
          </el-menu-item>
          <el-menu-item index="/dr/list" v-if="hasPermission('DR:QUERY')">
            <el-icon><List /></el-icon>
            <span>DR记录查询</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="化验室检验">
          <el-menu-item index="/lab/scan">
            <el-icon><Barcode /></el-icon>
            <span>标本扫码</span>
          </el-menu-item>
          <el-menu-item index="/lab/results">
            <el-icon><EditPen /></el-icon>
            <span>检验结果</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="数据管理">
          <el-menu-item index="/residents">
            <el-icon><User /></el-icon>
            <span>居民信息</span>
          </el-menu-item>
          <el-menu-item index="/records">
            <el-icon><Document /></el-icon>
            <span>体检记录</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="系统管理">
          <el-menu-item index="/auth/permissions">
            <el-icon><Key /></el-icon>
            <span>权限管理</span>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <el-tag type="success" size="small">{{ deptName }}</el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ doctorName }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const doctorName = computed(() => userStore.doctorName)
const deptName = computed(() => userStore.deptName)
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '公卫体检系统')

function hasPermission(perm) {
  return userStore.hasPermission(perm)
}

async function handleCommand(command) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确定退出登录？', '提示', { type: 'warning' })
    await userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped lang="less">
.layout-container {
  height: 100vh;
}

.aside {
  background: #001529;
  overflow: hidden;

  .logo {
    height: 64px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 20px;
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .side-menu {
    border-right: none;
    height: calc(100vh - 64px);
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);
      border-radius: 2px;
    }
  }
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);

  .page-title {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a2e;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .user-info {
      display: flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
      color: #333;
      font-size: 14px;

      &:hover {
        color: #409EFF;
      }
    }
  }
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>

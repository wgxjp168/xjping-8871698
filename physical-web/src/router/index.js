import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requireAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requireAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台', icon: 'House' }
      },
      // DR模块（新增核心）
      {
        path: 'dr/scan',
        name: 'DrScan',
        component: () => import('@/views/dr/DrScan.vue'),
        meta: { title: 'DR扫码检查', icon: 'Scan', perm: 'DR:INPUT' }
      },
      {
        path: 'dr/list',
        name: 'DrList',
        component: () => import('@/views/dr/DrList.vue'),
        meta: { title: 'DR记录查询', icon: 'List', perm: 'DR:QUERY' }
      },
      // 化验室检验
      {
        path: 'lab/scan',
        name: 'LabScan',
        component: () => import('@/views/lab/LabScan.vue'),
        meta: { title: '标本扫码', icon: 'Scan' }
      },
      {
        path: 'lab/results',
        name: 'LabResults',
        component: () => import('@/views/lab/LabResults.vue'),
        meta: { title: '检验结果录入', icon: 'EditPen' }
      },
      // 居民管理
      {
        path: 'residents',
        name: 'Residents',
        component: () => import('@/views/Residents.vue'),
        meta: { title: '居民信息', icon: 'User' }
      },
      // 体检记录
      {
        path: 'records',
        name: 'Records',
        component: () => import('@/views/Records.vue'),
        meta: { title: '体检记录', icon: 'Document' }
      },
      // 权限管理（新增）
      {
        path: 'auth/permissions',
        name: 'Permissions',
        component: () => import('@/views/auth/Permissions.vue'),
        meta: { title: '权限管理', icon: 'Key' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '公卫体检系统'} - 惠东县区域公卫体检集中系统`

  const requireAuth = to.meta.requireAuth !== false
  const token = localStorage.getItem('token')

  if (requireAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  if (to.path === '/login' && token) {
    next('/')
    return
  }
  next()
})

export default router

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/layout/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '首页概览' }
      },
      // 居民管理
      {
        path: 'residents',
        name: 'ResidentList',
        component: () => import('@/views/resident/ResidentList.vue'),
        meta: { title: '居民档案' }
      },
      // 体检管理
      {
        path: 'check-orders',
        name: 'CheckOrderList',
        component: () => import('@/views/check/CheckOrderList.vue'),
        meta: { title: '体检单管理' }
      },
      {
        path: 'check-orders/:id',
        name: 'CheckOrderDetail',
        component: () => import('@/views/check/CheckOrderDetail.vue'),
        meta: { title: '体检详情' }
      },
      // DR管理
      {
        path: 'dr-orders',
        name: 'DrOrderList',
        component: () => import('@/views/dr/DrOrderList.vue'),
        meta: { title: 'DR申请单' }
      },
      {
        path: 'dr-scan',
        name: 'DrScan',
        component: () => import('@/views/dr/DrScan.vue'),
        meta: { title: 'DR扫码签到' }
      },
      {
        path: 'dr-report/:orderId',
        name: 'DrReport',
        component: () => import('@/views/dr/DrReport.vue'),
        meta: { title: 'DR报告' }
      },
      // 设备管理
      {
        path: 'devices',
        name: 'DeviceList',
        component: () => import('@/views/device/DeviceList.vue'),
        meta: { title: '设备管理' }
      },
      // 系统管理
      {
        path: 'users',
        name: 'UserList',
        component: () => import('@/views/admin/UserList.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'depts',
        name: 'DeptList',
        component: () => import('@/views/admin/DeptList.vue'),
        meta: { title: '机构管理' }
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
  document.title = (to.meta.title ? to.meta.title + ' - ' : '') + '惠东县公卫体检系统'
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router

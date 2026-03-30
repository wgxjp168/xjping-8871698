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
      // 居民管理 - 超级管理员、卫生院管理员
      {
        path: 'residents',
        name: 'ResidentList',
        component: () => import('@/views/resident/ResidentList.vue'),
        meta: { title: '居民档案', allowedTypes: [3, 4] }
      },
      // 体检管理 - 所有登录用户
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
      // DR管理 - 超级管理员、卫生院管理员、DR医生
      {
        path: 'dr-orders',
        name: 'DrOrderList',
        component: () => import('@/views/dr/DrOrderList.vue'),
        meta: { title: 'DR申请单', allowedTypes: [3, 4], allowedPerms: ['DR:VIEW'] }
      },
      {
        path: 'dr-scan',
        name: 'DrScan',
        component: () => import('@/views/dr/DrScan.vue'),
        meta: { title: 'DR扫码签到', allowedTypes: [3, 4], allowedPerms: ['DR:VIEW'] }
      },
      {
        path: 'dr-report/:orderId',
        name: 'DrReport',
        component: () => import('@/views/dr/DrReport.vue'),
        meta: { title: 'DR报告', allowedTypes: [3, 4], allowedPerms: ['DR:VIEW'] }
      },
      // 设备管理 - 超级管理员、卫生院管理员
      {
        path: 'devices',
        name: 'DeviceList',
        component: () => import('@/views/device/DeviceList.vue'),
        meta: { title: '设备管理', allowedTypes: [3, 4] }
      },
      // 系统管理 - 超级管理员专属
      {
        path: 'users',
        name: 'UserList',
        component: () => import('@/views/admin/UserList.vue'),
        meta: { title: '用户管理', allowedTypes: [3, 4] }
      },
      {
        path: 'depts',
        name: 'DeptList',
        component: () => import('@/views/admin/DeptList.vue'),
        meta: { title: '医疗机构管理', allowedTypes: [3] }
      },
      {
        path: 'roles',
        name: 'RoleList',
        component: () => import('@/views/admin/RoleList.vue'),
        meta: { title: '角色权限管理', allowedTypes: [3] }
      },
      {
        path: 'areas',
        name: 'AreaList',
        component: () => import('@/views/admin/AreaList.vue'),
        meta: { title: '区域地址管理', allowedTypes: [3] }
      },
      {
        path: 'doctors',
        name: 'DoctorList',
        component: () => import('@/views/admin/DoctorList.vue'),
        meta: { title: '责任医生查询', allowedTypes: [3, 4] }
      },
      {
        path: 'doctor-filters',
        name: 'DoctorFilterConfig',
        component: () => import('@/views/admin/DoctorFilterConfig.vue'),
        meta: { title: '医生筛选条件配置', allowedTypes: [3] }
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
    return
  }
  if (to.path === '/login' && token) {
    next('/')
    return
  }

  // 权限校验
  const allowedTypes = to.meta.allowedTypes
  const allowedPerms = to.meta.allowedPerms
  if (allowedTypes || allowedPerms) {
    let userInfo = {}
    try { userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}') } catch {}
    const userType = userInfo.userType
    const perms = userInfo.permissions || []

    let allowed = false
    if (allowedTypes && allowedTypes.includes(userType)) allowed = true
    if (allowedPerms && allowedPerms.some(p => perms.includes(p))) allowed = true

    if (!allowed) {
      next('/dashboard')
      return
    }
  }

  next()
})

export default router

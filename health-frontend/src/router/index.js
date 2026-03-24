import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', noAuth: true }
  },
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台', icon: 'Odometer' }
      },
      // 体检管理
      {
        path: 'check',
        name: 'CheckManage',
        redirect: '/check/list',
        meta: { title: '体检管理', icon: 'Document' },
        children: [
          {
            path: 'list',
            name: 'CheckList',
            component: () => import('@/views/check/CheckList.vue'),
            meta: { title: '体检单列表' }
          },
          {
            path: 'detail/:id',
            name: 'CheckDetail',
            component: () => import('@/views/check/CheckDetail.vue'),
            meta: { title: '体检详情', hidden: true }
          },
          {
            path: 'items',
            name: 'CheckItems',
            component: () => import('@/views/check/CheckItems.vue'),
            meta: { title: '检查项目' }
          },
          {
            path: 'packages',
            name: 'CheckPackages',
            component: () => import('@/views/check/CheckPackages.vue'),
            meta: { title: '检查套餐' }
          }
        ]
      },
      // 诊断管理
      {
        path: 'diagnosis',
        name: 'DiagnosisManage',
        redirect: '/diagnosis/list',
        meta: { title: '诊断管理', icon: 'Stethoscope' },
        children: [
          {
            path: 'list',
            name: 'DiagnosisList',
            component: () => import('@/views/diagnosis/DiagnosisList.vue'),
            meta: { title: '诊断报告列表' }
          },
          {
            path: 'detail/:id',
            name: 'DiagnosisDetail',
            component: () => import('@/views/diagnosis/DiagnosisDetail.vue'),
            meta: { title: '诊断详情', hidden: true }
          },
          {
            path: 'edit/:id?',
            name: 'DiagnosisEdit',
            component: () => import('@/views/diagnosis/DiagnosisEdit.vue'),
            meta: { title: '编辑诊断', hidden: true }
          }
        ]
      },
      // 设备管理
      {
        path: 'device',
        name: 'DeviceManage',
        redirect: '/device/list',
        meta: { title: '设备管理', icon: 'Monitor' },
        children: [
          {
            path: 'list',
            name: 'DeviceList',
            component: () => import('@/views/device/DeviceList.vue'),
            meta: { title: '设备列表' }
          },
          {
            path: 'detail/:id',
            name: 'DeviceDetail',
            component: () => import('@/views/device/DeviceDetail.vue'),
            meta: { title: '设备详情', hidden: true }
          },
          {
            path: 'monitor',
            name: 'DeviceMonitor',
            component: () => import('@/views/device/DeviceMonitor.vue'),
            meta: { title: '实时监控' }
          }
        ]
      },
      // 系统管理
      {
        path: 'admin',
        name: 'SystemManage',
        redirect: '/admin/user',
        meta: { title: '系统管理', icon: 'Setting', roles: ['ADMIN'] },
        children: [
          {
            path: 'user',
            name: 'UserManage',
            component: () => import('@/views/admin/UserManage.vue'),
            meta: { title: '用户管理', roles: ['ADMIN'] }
          },
          {
            path: 'dept',
            name: 'DeptManage',
            component: () => import('@/views/admin/DeptManage.vue'),
            meta: { title: '科室管理', roles: ['ADMIN'] }
          },
          {
            path: 'log',
            name: 'LogManage',
            component: () => import('@/views/admin/LogManage.vue'),
            meta: { title: '操作日志', roles: ['ADMIN'] }
          }
        ]
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 健康检查系统` : '健康检查系统'
  if (to.meta.noAuth) {
    next()
    return
  }
  const userStore = useUserStore()
  if (!userStore.token) {
    next('/login')
    return
  }
  next()
})

export default router

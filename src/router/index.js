// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/supplier/list'
  },
  {
    path: '/supplier/list',
    name: 'SupplierScoreList',
    component: () => import('@/views/supplier/SupplierScoreList.vue'),
    meta: { title: '供应商评分管理' }
  },
  {
    path: '/supplier/score/:supplierId',
    name: 'SupplierScore',
    component: () => import('@/views/supplier/SupplierScore.vue'),
    meta: { title: '供应商评分' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 动态设置页面标题
router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} - 我来购ILbuy`
  }
})

export default router

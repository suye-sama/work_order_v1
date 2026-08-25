/**
 * 路由配置 — 含 token 守卫
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '工作台' },
      },
      {
        path: 'tickets',
        name: 'TicketList',
        component: () => import('../views/TicketList.vue'),
        meta: { title: '工单列表' },
      },
      {
        path: 'tickets/:id',
        name: 'TicketDetail',
        component: () => import('../views/TicketDetail.vue'),
        meta: { title: '工单详情' },
      },
      {
        path: 'customers',
        name: 'CustomerList',
        component: () => import('../views/CustomerList.vue'),
        meta: { title: '客户管理' },
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('../views/Reports.vue'),
        meta: { title: '报表中心' },
      },
      {
        path: 'knowledge',
        name: 'KnowledgeList',
        component: () => import('../views/KnowledgeList.vue'),
        meta: { title: '知识库' },
      },
      {
        path: 'knowledge/:id',
        name: 'KnowledgeDetail',
        component: () => import('../views/KnowledgeDetail.vue'),
        meta: { title: '知识详情' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/dashboard'
  }
})

export default router

// 生产环境使用 hash history，适配 GitHub Pages 没有服务端 SPA fallback；
// 本地开发保留 web history，便于调试普通路径。
import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

import { isAuthenticated } from '../auth/session.js'

const routes = [
  // requiresAuth 由全局守卫检查 Supabase session；业务资源仍由 FastAPI 再授权。
  {
    path: '/',
    name: 'today',
    component: () => import('../views/TodayView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { showNavigation: false },
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: () => import('../views/AuthCallbackView.vue'),
    meta: { showNavigation: false },
  },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('../views/OnboardingView.vue'),
    meta: { showNavigation: false, requiresAuth: true },
  },
  {
    path: '/preferences',
    name: 'preferences',
    component: () => import('../views/PreferencesView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/HistoryView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: import.meta.env.PROD
    ? createWebHashHistory(import.meta.env.BASE_URL)
    : createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  // 路由守卫只判断“是否有会话”，资料是否存在由页面调用 /api/me 判断。
  const authenticated = await isAuthenticated()
  if (to.meta.requiresAuth && !authenticated) {
    return {
      name: 'login',
      query: { next: to.fullPath },
    }
  }

  if (to.name === 'login' && authenticated) return { name: 'today' }

  return true
})

export default router

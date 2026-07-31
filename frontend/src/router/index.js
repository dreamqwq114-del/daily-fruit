import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'

import { getUserId } from '../utils/user-session.js'

const routes = [
  {
    path: '/',
    name: 'today',
    component: () => import('../views/TodayView.vue'),
    meta: { requiresUser: true },
  },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('../views/OnboardingView.vue'),
    meta: { showNavigation: false },
  },
  {
    path: '/preferences',
    name: 'preferences',
    component: () => import('../views/PreferencesView.vue'),
    meta: { requiresUser: true },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/HistoryView.vue'),
    meta: { requiresUser: true },
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

router.beforeEach((to) => {
  if (to.meta.requiresUser && !getUserId()) {
    return {
      name: 'onboarding',
      query: { next: to.fullPath },
    }
  }

  return true
})

export default router

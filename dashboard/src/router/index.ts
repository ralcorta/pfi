import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { isAuthenticated } from '../services/auth'
import AuthLayout from '../layouts/AuthLayout.vue'
import AppLayout from '../layouts/AppLayout.vue'
const routes: Array<RouteRecordRaw> = [
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'login' },
  },
  {
    path: '/',
    redirect: { name: 'login' },
  },
  {
    name: 'app',
    path: '/home',
    component: AppLayout,
    redirect: { name: 'home' },
    children: [
      {
        name: 'home',
        path: '',
        component: () => import('../pages/Home.vue'),
      },
      {
        name: 'user-vni',
        path: 'vni',
        component: () => import('../pages/UserVni.vue'),
      },
    ],
  },
  {
    path: '/auth',
    component: AuthLayout,
    children: [
      {
        name: 'login',
        path: 'login',
        component: () => import('../pages/auth/Login.vue'),
      },
      {
        name: 'signup',
        path: 'signup',
        component: () => import('../pages/auth/Signup.vue'),
      },
      {
        name: 'setup-password',
        path: 'setup-password',
        component: () => import('../pages/auth/SetupPassword.vue'),
      },
      {
        path: '',
        redirect: { name: 'login' },
      },
    ],
  },
]
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    } else {
      window.scrollTo(0, 0)
    }
  },
  routes,
})
router.beforeEach((to, from, next) => {
  const publicRoutes = ['login', 'setup-password']
  const isPublicRoute = publicRoutes.includes(to.name as string)
  if (isPublicRoute) {
    next()
    return
  }
  if (!isAuthenticated()) {
    next({ name: 'login' })
    return
  }
  next()
})
export default router
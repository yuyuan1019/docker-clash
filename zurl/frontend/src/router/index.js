import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import InitView from '../views/InitView.vue'
import LoginView from '../views/LoginView.vue'
import AdminView from '../views/AdminView.vue'

const router = createRouter({
  // 改成#号那种路由
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path:"/init",
      name:"init",
      component: InitView
    },
    {
      path:"/login",
      name:"login",
      component: LoginView
    },
    {
      path:"/admin/:name",
      name:"admin",
      component: AdminView
    },
    {
      path: '/admin',
      redirect: '/admin/list'
    },
    {
      path: '/admin/',
      redirect: '/admin/list'
    },
  ],
})

export default router

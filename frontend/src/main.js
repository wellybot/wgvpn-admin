import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import TrafficDashboard from './components/TrafficDashboard.vue'
import TrafficHistory from './components/TrafficHistory.vue'
import BandwidthDashboard from './components/BandwidthDashboard.vue'
import AlertPanel from './components/AlertPanel.vue'
import LogSearch from './components/LogSearch.vue'
import LogStream from './components/LogStream.vue'
import LoginPage from './components/LoginPage.vue'
import UserList from './components/UserList.vue'

// Auth guard
const requireAuth = (to, from, next) => {
  const token = localStorage.getItem('token')
  if (!token && to.path !== '/login') {
    next('/login')
  } else {
    next()
  }
}

const routes = [
  { path: '/', redirect: '/traffic' },
  { path: '/login', component: LoginPage },
  { path: '/traffic', component: TrafficDashboard, beforeEnter: requireAuth },
  { path: '/history', component: TrafficHistory, beforeEnter: requireAuth },
  { path: '/bandwidth', component: BandwidthDashboard, beforeEnter: requireAuth },
  { path: '/alerts', component: AlertPanel, beforeEnter: requireAuth },
  { path: '/logs', component: LogSearch, beforeEnter: requireAuth },
  { path: '/logs/stream', component: LogStream, beforeEnter: requireAuth },
  { path: '/users', component: UserList, beforeEnter: requireAuth }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.mount('#app')

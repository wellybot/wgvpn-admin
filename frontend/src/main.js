import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import TrafficDashboard from './components/TrafficDashboard.vue'
import TrafficHistory from './components/TrafficHistory.vue'
import BandwidthDashboard from './components/BandwidthDashboard.vue'
import AlertPanel from './components/AlertPanel.vue'

const routes = [
  { path: '/', redirect: '/traffic' },
  { path: '/traffic', component: TrafficDashboard },
  { path: '/history', component: TrafficHistory },
  { path: '/bandwidth', component: BandwidthDashboard },
  { path: '/alerts', component: AlertPanel }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.mount('#app')

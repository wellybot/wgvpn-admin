import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import TrafficDashboard from './components/TrafficDashboard.vue'

const routes = [
  { path: '/', redirect: '/traffic' },
  { path: '/traffic', component: TrafficDashboard }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.mount('#app')

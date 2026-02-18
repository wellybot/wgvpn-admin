<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">
        <span class="logo">🔒</span>        <span class="title">WireGuard VPN Admin</span>
      </div>
      <div class="nav-links">
        <router-link to="/traffic" class="nav-link">
          📊 流量監控
        </router-link>
        <router-link to="/history" class="nav-link">
          📈 流量歷史
        </router-link>
        <router-link to="/bandwidth" class="nav-link">
          🚀 頻寬監控
        </router-link>
        <router-link to="/alerts" class="nav-link">
          🔔 異常警示
        </router-link>
        <router-link to="/logs" class="nav-link">
          📝 日誌搜尋
        </router-link>
        <router-link to="/logs/stream" class="nav-link">
          📡 即時串流
        </router-link>
        <router-link to="/users" class="nav-link">
          👥 用戶管理
        </router-link>
        <span class="nav-link disabled">📈 報表</span>
        <button v-if="isLoggedIn" @click="logout" class="logout-btn">
          🚪 登出
        </button>
      </div>
    </nav>
    <main class="main-content">
      <router-view></router-view>
    </main>
  </div>
</template>

<script>
export default {
  name: 'App',
  computed: {
    isLoggedIn() {
      return !!localStorage.getItem('token')
    }
  },
  methods: {
    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      this.$router.push('/login')
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: #f5f6fa;
  color: #2c3e50;
}

#app {
  min-height: 100vh;
}

.navbar {
  background: white;
  padding: 0 24px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-size: 24px;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: #666;
  font-size: 14px;
  transition: all 0.2s;
  cursor: pointer;
}

.nav-link:hover:not(.disabled) {
  background: #f0f0f0;
  color: #2c3e50;
}

.nav-link.router-link-active {
  background: #e8f4fd;
  color: #3498db;
}

.nav-link.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.logout-btn {
  padding: 8px 16px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 8px;
}

.logout-btn:hover {
  background: #e74c3c;
  color: white;
}

.main-content {
  padding: 24px;
}
</style>

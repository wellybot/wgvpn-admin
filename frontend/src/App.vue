<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">
        <span class="logo">🔒</span>
        <span class="title">WireGuard VPN Admin</span>
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
        <div class="nav-dropdown">
          <span class="nav-link dropdown-toggle">📋 稽查記錄</span>
          <div class="dropdown-menu">
            <router-link to="/audit/operations" class="dropdown-item">
              管理員操作日誌
            </router-link>
            <router-link to="/audit/login-history" class="dropdown-item">
              登入紀錄
            </router-link>
            <router-link to="/audit/system-events" class="dropdown-item">
              系統事件稽核
            </router-link>
            <router-link to="/audit/reports" class="dropdown-item">
              合規報告產生
            </router-link>
          </div>
        </div>
        <div class="nav-dropdown">
          <span class="nav-link dropdown-toggle">📊 自動化報表</span>
          <div class="dropdown-menu">
            <router-link to="/reports/traffic" class="dropdown-item">
              流量報告
            </router-link>
            <router-link to="/reports/user-stats" class="dropdown-item">
              用戶統計
            </router-link>
            <router-link to="/reports/health" class="dropdown-item">
              系統健康
            </router-link>
            <router-link to="/reports/templates" class="dropdown-item">
              報告範本
            </router-link>
          </div>
        </div>
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

.nav-dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-toggle {
  cursor: pointer;
}

.dropdown-menu {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background: white;
  min-width: 180px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 8px;
  overflow: hidden;
  z-index: 1000;
}

.nav-dropdown:hover .dropdown-menu {
  display: block;
}

.dropdown-item {
  display: block;
  padding: 10px 16px;
  color: #666;
  text-decoration: none;
  font-size: 14px;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: #f0f0f0;
  color: #2c3e50;
}

.dropdown-item.router-link-active {
  background: #e8f4fd;
  color: #3498db;
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

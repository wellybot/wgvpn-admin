<template>
  <div class="login-history">
    <div class="page-header">
      <h1>🔐 登入紀錄</h1>
    </div>
    
    <!-- Filters -->
    <div class="filters">
      <div class="filter-group">
        <label>使用者:</label>
        <select v-model="filters.user_id">
          <option :value="null">全部</option>
          <option v-for="user in users" :key="user.id" :value="user.id">
            {{ user.username }}
          </option>
        </select>
      </div>
      
      <div class="filter-group">
        <label>結果:</label>
        <select v-model="filters.success">
          <option :value="null">全部</option>
          <option :value="true">成功</option>
          <option :value="false">失敗</option>
        </select>
      </div>
      
      <div class="filter-group">
        <label>開始日期:</label>
        <input type="date" v-model="filters.start_date" />
      </div>
      
      <div class="filter-group">
        <label>結束日期:</label>
        <input type="date" v-model="filters.end_date" />
      </div>
      
      <button @click="fetchLogs" class="btn-primary">篩選</button>
      <button @click="exportLogs('csv')" class="btn-secondary">匯出 CSV</button>
      <button @click="exportLogs('json')" class="btn-secondary">匯出 JSON</button>
    </div>
    
    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">總記錄數</div>
      </div>
      <div class="stat-card success">
        <div class="stat-value">{{ stats.successful }}</div>
        <div class="stat-label">成功登入</div>
      </div>
      <div class="stat-card danger">
        <div class="stat-value">{{ stats.failed }}</div>
        <div class="stat-label">失敗登入</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.successRate }}%</div>
        <div class="stat-label">成功率</div>
      </div>
    </div>
    
    <!-- Logs Table -->
    <div class="logs-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>時間</th>
            <th>使用者名稱</th>
            <th>結果</th>
            <th>失敗原因</th>
            <th>IP 位址</th>
            <th>使用者代理</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" :class="log.success ? 'success-row' : 'failed-row'">
            <td>{{ log.id }}</td>
            <td>{{ formatDateTime(log.created_at) }}</td>
            <td>{{ log.username || '-' }}</td>
            <td>
              <span :class="['status-badge', log.success ? 'status-success' : 'status-failed']">
                {{ log.success ? '成功' : '失敗' }}
              </span>
            </td>
            <td>{{ log.failure_reason || '-' }}</td>
            <td>
              <span class="ip-address">{{ log.ip_address || '-' }}</span>
            </td>
            <td class="user-agent" :title="log.user_agent">{{ truncateUA(log.user_agent) }}</td>
          </tr>
        </tbody>
      </table>
      
      <div v-if="logs.length === 0" class="no-data">
        暂无登入记录
      </div>
    </div>
    
    <!-- Pagination -->
    <div class="pagination">
      <button @click="prevPage" :disabled="offset === 0">上一頁</button>
      <span>第 {{ Math.floor(offset / limit) + 1 }} 頁 / 共 {{ Math.ceil(total / limit) }} 頁</span>
      <button @click="nextPage" :disabled="offset + limit >= total">下一頁</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginHistory',
  data() {
    return {
      logs: [],
      users: [],
      filters: {
        user_id: null,
        success: null,
        start_date: '',
        end_date: ''
      },
      limit: 50,
      offset: 0,
      total: 0,
      stats: {
        total: 0,
        successful: 0,
        failed: 0,
        successRate: 0
      }
    }
  },
  mounted() {
    this.fetchLogs()
    this.fetchUsers()
  },
  methods: {
    async fetchLogs() {
      try {
        const params = new URLSearchParams()
        if (this.filters.user_id) params.append('user_id', this.filters.user_id)
        if (this.filters.success !== null) params.append('success', this.filters.success)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        params.append('limit', this.limit)
        params.append('offset', this.offset)
        
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/audit/login-history?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.logs = data.logs
        this.total = data.total
        
        // Calculate stats
        this.calculateStats()
      } catch (error) {
        console.error('Error fetching login history:', error)
      }
    },
    async fetchUsers() {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/users?per_page=100', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.users = data.users
      } catch (error) {
        console.error('Error fetching users:', error)
      }
    },
    calculateStats() {
      this.stats.total = this.total
      const successful = this.logs.filter(l => l.success).length
      const failed = this.logs.filter(l => !l.success).length
      this.stats.successful = this.logs.length > 0 ? successful : 0
      this.stats.failed = this.logs.length > 0 ? failed : 0
      this.stats.successRate = this.logs.length > 0 
        ? Math.round((successful / this.logs.length) * 100) 
        : 0
    },
    async exportLogs(format) {
      try {
        const params = new URLSearchParams()
        if (this.filters.user_id) params.append('user_id', this.filters.user_id)
        if (this.filters.success !== null) params.append('success', this.filters.success)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        
        const token = localStorage.getItem('token')
        
        // Use login-history endpoint for export
        params.append('limit', 10000)
        const response = await fetch(`/api/audit/login-history?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        
        // Download file
        let content
        let mimeType
        if (format === 'json') {
          content = JSON.stringify(data.logs, null, 2)
          mimeType = 'application/json'
        } else {
          // CSV
          if (data.logs.length === 0) {
            content = ''
          } else {
            const headers = Object.keys(data.logs[0])
            content = headers.join(',') + '\n'
            content += data.logs.map(row => 
              headers.map(h => {
                const val = row[h]
                return typeof val === 'string' && val.includes(',') ? `"${val}"` : val
              }).join(',')
            ).join('\n')
          }
          mimeType = 'text/csv'
        }
        
        const blob = new Blob([content], { type: mimeType })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `login_history_${new Date().toISOString().split('T')[0]}.${format}`
        a.click()
        URL.revokeObjectURL(url)
      } catch (error) {
        console.error('Error exporting logs:', error)
      }
    },
    prevPage() {
      this.offset = Math.max(0, this.offset - this.limit)
      this.fetchLogs()
    },
    nextPage() {
      this.offset += this.limit
      this.fetchLogs()
    },
    formatDateTime(dateStr) {
      if (!dateStr) return '-'
      return new Date(dateStr).toLocaleString('zh-TW')
    },
    truncateUA(ua) {
      if (!ua) return '-'
      return ua.length > 50 ? ua.substring(0, 50) + '...' : ua
    }
  }
}
</script>

<style scoped>
.login-history {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  color: #2c3e50;
}

.filters {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-group label {
  font-size: 12px;
  color: #666;
}

.filter-group select,
.filter-group input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.btn-primary {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  align-self: flex-end;
}

.btn-secondary {
  padding: 8px 16px;
  background: #95a5a6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  align-self: flex-end;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.stat-card.success {
  border-left: 4px solid #27ae60;
}

.stat-card.danger {
  border-left: 4px solid #e74c3c;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #2c3e50;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.logs-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.data-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #2c3e50;
}

.success-row {
  background: rgba(39, 174, 96, 0.05);
}

.failed-row {
  background: rgba(231, 76, 60, 0.05);
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-success {
  background: #d4edda;
  color: #155724;
}

.status-failed {
  background: #f8d7da;
  color: #721c24;
}

.ip-address {
  font-family: monospace;
  color: #3498db;
}

.user-agent {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #666;
}

.no-data {
  padding: 48px;
  text-align: center;
  color: #999;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.pagination button {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.pagination button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>

<template>
  <div class="audit-logs">
    <div class="page-header">
      <h1>📋 管理員操作日誌</h1>
    </div>
    
    <!-- Filters -->
    <div class="filters">
      <div class="filter-group">
        <label>管理員:</label>
        <select v-model="filters.user_id">
          <option :value="null">全部</option>
          <option v-for="user in users" :key="user.id" :value="user.id">
            {{ user.username }}
          </option>
        </select>
      </div>
      
      <div class="filter-group">
        <label>操作類型:</label>
        <select v-model="filters.action">
          <option :value="null">全部</option>
          <option v-for="action in actions" :key="action" :value="action">
            {{ action }}
          </option>
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
    
    <!-- Logs Table -->
    <div class="logs-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>時間</th>
            <th>管理員</th>
            <th>操作類型</th>
            <th>詳情</th>
            <th>IP 位址</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="log in logs" :key="log.id">
            <tr @click="toggleExpand(log.id)" class="log-row">
              <td>{{ log.id }}</td>
              <td>{{ formatDateTime(log.created_at) }}</td>
              <td>{{ log.username || '系統' }}</td>
              <td>
                <span :class="['action-badge', getActionClass(log.action)]">
                  {{ log.action }}
                </span>
              </td>
              <td>{{ log.details || '-' }}</td>
              <td>{{ log.ip_address || '-' }}</td>
            </tr>
          </template>
        </tbody>
      </table>
      
      <div v-if="logs.length === 0" class="no-data">
        暂无操作日志
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
  name: 'AuditLogs',
  data() {
    return {
      logs: [],
      users: [],
      actions: [],
      filters: {
        user_id: null,
        action: null,
        start_date: '',
        end_date: ''
      },
      limit: 50,
      offset: 0,
      total: 0
    }
  },
  mounted() {
    this.fetchLogs()
    this.fetchUsers()
    this.fetchActions()
  },
  methods: {
    async fetchLogs() {
      try {
        const params = new URLSearchParams()
        if (this.filters.user_id) params.append('user_id', this.filters.user_id)
        if (this.filters.action) params.append('action', this.filters.action)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        params.append('limit', this.limit)
        params.append('offset', this.offset)
        
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/audit/operations?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.logs = data.logs
        this.total = data.total
      } catch (error) {
        console.error('Error fetching audit logs:', error)
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
    async fetchActions() {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/audit/operations/actions', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.actions = data.actions
      } catch (error) {
        console.error('Error fetching actions:', error)
      }
    },
    async exportLogs(format) {
      try {
        const params = new URLSearchParams()
        if (this.filters.user_id) params.append('user_id', this.filters.user_id)
        if (this.filters.action) params.append('action', this.filters.action)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/logs/export?log_type=audit&${params}&format=${format}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        
        // Download file
        const blob = new Blob([format === 'json' ? JSON.stringify(data.logs, null, 2) : data.data], {
          type: format === 'json' ? 'application/json' : 'text/csv'
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`
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
    getActionClass(action) {
      const actionMap = {
        'CREATE_USER': 'action-create',
        'UPDATE_USER': 'action-update',
        'DELETE_USER': 'action-delete',
        'user_toggle_active': 'action-toggle',
        'GENERATE_CONFIG': 'action-config',
        'password_changed': 'action-password',
        'LOGIN': 'action-login',
        'LOGOUT': 'action-logout'
      }
      return actionMap[action] || 'action-default'
    },
    toggleExpand(id) {
      // Could add expansion panel functionality
    }
  }
}
</script>

<style scoped>
.audit-logs {
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

.log-row {
  cursor: pointer;
  transition: background 0.2s;
}

.log-row:hover {
  background: #f8f9fa;
}

.action-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.action-create { background: #d4edda; color: #155724; }
.action-update { background: #cce5ff; color: #004085; }
.action-delete { background: #f8d7da; color: #721c24; }
.action-toggle { background: #fff3cd; color: #856404; }
.action-config { background: #d1ecf1; color: #0c5460; }
.action-password { background: #e2e3e5; color: #383d41; }
.action-login { background: #c3e6cb; color: #155724; }
.action-logout { background: #f5c6cb; color: #721c24; }
.action-default { background: #e2e3e5; color: #383d41; }

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

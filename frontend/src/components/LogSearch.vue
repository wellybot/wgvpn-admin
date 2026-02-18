<template>
  <div class="log-search">
    <div class="search-header">
      <h2>📝 日誌搜尋</h2>
    </div>

    <!-- Search Filters -->
    <div class="search-filters">
      <div class="filter-row">
        <div class="filter-group">
          <label>關鍵字</label>
          <input 
            v-model="filters.keyword" 
            type="text" 
            placeholder="搜尋關鍵字..."
            @keyup.enter="searchLogs"
          />
        </div>
        
        <div class="filter-group">
          <label>日誌類型</label>
          <select v-model="filters.log_type">
            <option value="">全部類型</option>
            <option value="connection">連線日誌</option>
            <option value="traffic">流量日誌</option>
            <option value="alert">警示日誌</option>
            <option value="audit">審計日誌</option>
          </select>
        </div>
        
        <div class="filter-group">
          <label>用戶</label>
          <select v-model="filters.user_id">
            <option :value="null">全部用戶</option>
            <option v-for="user in users" :key="user.id" :value="user.id">
              {{ user.username }}
            </option>
          </select>
        </div>
      </div>
      
      <div class="filter-row">
        <div class="filter-group">
          <label>開始日期</label>
          <input v-model="filters.start_date" type="date" />
        </div>
        
        <div class="filter-group">
          <label>結束日期</label>
          <input v-model="filters.end_date" type="date" />
        </div>
        
        <div class="filter-group">
          <label>每頁數量</label>
          <select v-model="filters.limit">
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="200">200</option>
          </select>
        </div>
      </div>
      
      <div class="filter-actions">
        <button class="btn btn-primary" @click="searchLogs">
          🔍 搜尋
        </button>
        <button class="btn btn-secondary" @click="resetFilters">
          重置
        </button>
        
        <div class="export-buttons">
          <button class="btn btn-success" @click="exportLogs('csv')">
            📥 匯出 CSV
          </button>
          <button class="btn btn-success" @click="exportLogs('json')">
            📥 匯出 JSON
          </button>
        </div>
      </div>
    </div>

    <!-- Results Table -->
    <div class="results-section">
      <div class="results-header">
        <span>搜尋結果: {{ totalCount }} 筆</span>
        <div class="pagination">
          <button 
            class="btn btn-small" 
            :disabled="offset === 0"
            @click="prevPage"
          >
            上一頁
          </button>
          <span>第 {{ Math.floor(offset / limit) + 1 }} 頁</span>
          <button 
            class="btn btn-small" 
            :disabled="logs.length < limit"
            @click="nextPage"
          >
            下一頁
          </button>
        </div>
      </div>
      
      <div class="results-table-wrapper">
        <table class="results-table">
          <thead>
            <tr>
              <th>時間</th>
              <th>類型</th>
              <th>用戶</th>
              <th>訊息</th>
              <th>詳情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(log, index) in logs" :key="index" :class="getLogLevelClass(log)">
              <td class="timestamp">{{ formatDate(log) }}</td>
              <td>
                <span class="log-type-badge" :class="getLogTypeClass(log.log_type)">
                  {{ getLogTypeLabel(log.log_type) }}
                </span>
              </td>
              <td>{{ log.username || 'System' }}</td>
              <td class="message">{{ log.message || getDefaultMessage(log) }}</td>
              <td class="details">{{ getDetails(log) }}</td>
            </tr>
            <tr v-if="logs.length === 0">
              <td colspan="5" class="no-results">沒有找到日誌記錄</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Export Progress Modal -->
    <div v-if="exporting" class="modal-overlay">
      <div class="modal">
        <h3>匯出日誌中...</h3>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: exportProgress + '%' }"></div>
        </div>
        <p>{{ exportProgress }}% 完成</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogSearch',
  data() {
    return {
      logs: [],
      users: [],
      totalCount: 0,
      offset: 0,
      limit: 100,
      filters: {
        keyword: '',
        log_type: '',
        user_id: null,
        start_date: '',
        end_date: '',
        limit: 100
      },
      exporting: false,
      exportProgress: 0
    }
  },
  async mounted() {
    await this.fetchUsers()
    await this.searchLogs()
  },
  methods: {
    async fetchUsers() {
      try {
        const response = await fetch('http://localhost:8000/api/users')
        const data = await response.json()
        this.users = data.users || []
      } catch (error) {
        console.error('Failed to fetch users:', error)
      }
    },
    
    async searchLogs() {
      try {
        const params = new URLSearchParams()
        
        if (this.filters.keyword) params.append('keyword', this.filters.keyword)
        if (this.filters.log_type) params.append('log_type', this.filters.log_type)
        if (this.filters.user_id) params.append('user_id', this.filters.user_id)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        params.append('limit', this.filters.limit)
        params.append('offset', this.offset)
        
        const response = await fetch(`http://localhost:8000/api/logs/search?${params}`)
        const data = await response.json()
        
        this.logs = data.logs || []
        this.totalCount = data.total || 0
        this.limit = data.limit || 100
        this.offset = data.offset || 0
      } catch (error) {
        console.error('Failed to search logs:', error)
        this.logs = []
      }
    },
    
    resetFilters() {
      this.filters = {
        keyword: '',
        log_type: '',
        user_id: null,
        start_date: '',
        end_date: '',
        limit: 100
      }
      this.offset = 0
      this.searchLogs()
    },
    
    prevPage() {
      if (this.offset > 0) {
        this.offset = Math.max(0, this.offset - this.limit)
        this.searchLogs()
      }
    },
    
    nextPage() {
      if (this.logs.length >= this.limit) {
        this.offset += this.limit
        this.searchLogs()
      }
    },
    
    async exportLogs(format) {
      this.exporting = true
      this.exportProgress = 0
      
      try {
        const params = new URLSearchParams()
        
        if (this.filters.keyword) params.append('keyword', this.filters.keyword)
        if (this.filters.log_type) params.append('log_type', this.filters.log_type)
        if (this.filters.user_id) params.append('user_id', this.filters.user_id)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        params.append('format', format)
        
        // Simulate progress
        const progressInterval = setInterval(() => {
          this.exportProgress = Math.min(90, this.exportProgress + 10)
        }, 200)
        
        const response = await fetch(`http://localhost:8000/api/logs/export?${params}`)
        
        clearInterval(progressInterval)
        this.exportProgress = 100
        
        let blob
        let filename
        
        if (format === 'json') {
          const data = await response.json()
          blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
          filename = `logs_${new Date().toISOString().slice(0, 10)}.json`
        } else {
          const data = await response.json()
          blob = new Blob([data.data], { type: 'text/csv' })
          filename = `logs_${new Date().toISOString().slice(0, 10)}.csv`
        }
        
        // Download file
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        a.click()
        URL.revokeObjectURL(url)
        
        setTimeout(() => {
          this.exporting = false
          this.exportProgress = 0
        }, 500)
        
      } catch (error) {
        console.error('Export failed:', error)
        this.exporting = false
        this.exportProgress = 0
      }
    },
    
    formatDate(log) {
      const date = log.connected_at || log.snapshot_time || log.created_at
      if (!date) return '-'
      return new Date(date).toLocaleString('zh-TW')
    },
    
    getLogTypeLabel(type) {
      const labels = {
        connection: '連線',
        traffic: '流量',
        alert: '警示',
        audit: '審計'
      }
      return labels[type] || type
    },
    
    getLogTypeClass(type) {
      return `type-${type}`
    },
    
    getLogLevelClass(log) {
      return `level-${log.level || 'info'}`
    },
    
    getDefaultMessage(log) {
      if (log.log_type === 'connection') {
        return `連線 IP: ${log.peer_ip || '-'}`
      } else if (log.log_type === 'traffic') {
        return `接收: ${this.formatBytes(log.bytes_received || 0)}, 傳送: ${this.formatBytes(log.bytes_sent || 0)}`
      } else if (log.log_type === 'alert') {
        return log.message || `${log.alert_type} - ${log.severity}`
      } else if (log.log_type === 'audit') {
        return log.action || log.details || '-'
      }
      return '-'
    },
    
    getDetails(log) {
      if (log.log_type === 'connection') {
        return log.duration_seconds ? `${Math.round(log.duration_seconds)} 秒` : '進行中'
      } else if (log.log_type === 'alert') {
        return log.severity || '-'
      }
      return '-'
    },
    
    formatBytes(bytes) {
      for (let unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
        if (bytes < 1024) return `${bytes.toFixed(2)} ${unit}`
        bytes /= 1024
      }
      return `${bytes.toFixed(2)} PB`
    }
  }
}
</script>

<style scoped>
.log-search {
  max-width: 1400px;
  margin: 0 auto;
}

.search-header {
  margin-bottom: 24px;
}

.search-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.search-filters {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.filter-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.filter-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  font-size: 13px;
  font-weight: 500;
  color: #666;
}

.filter-group input,
.filter-group select {
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: #3498db;
}

.filter-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover {
  background: #2980b9;
}

.btn-secondary {
  background: #ecf0f1;
  color: #666;
}

.btn-secondary:hover {
  background: #dfe6e9;
}

.btn-success {
  background: #27ae60;
  color: white;
}

.btn-success:hover {
  background: #219a52;
}

.btn-small {
  padding: 6px 12px;
  font-size: 13px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.export-buttons {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.results-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 14px;
  color: #666;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
}

.results-table-wrapper {
  overflow-x: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.results-table th,
.results-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.results-table th {
  font-weight: 600;
  color: #666;
  background: #f8f9fa;
}

.results-table tr:hover {
  background: #f8f9fa;
}

.timestamp {
  white-space: nowrap;
  color: #888;
  font-size: 13px;
}

.message {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.details {
  color: #888;
  font-size: 13px;
}

.log-type-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.type-connection {
  background: #e8f5e9;
  color: #2e7d32;
}

.type-traffic {
  background: #e3f2fd;
  color: #1565c0;
}

.type-alert {
  background: #fff3e0;
  color: #ef6c00;
}

.type-audit {
  background: #f3e5f5;
  color: #7b1fa2;
}

.level-error {
  background: #ffebee;
}

.level-warning {
  background: #fff8e1;
}

.level-info {
  background: #e8f5e9;
}

.no-results {
  text-align: center;
  color: #888;
  padding: 40px !important;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  padding: 24px;
  min-width: 300px;
  text-align: center;
}

.modal h3 {
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: #ecf0f1;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: #27ae60;
  transition: width 0.3s ease;
}
</style>

<template>
  <div class="system-events">
    <div class="page-header">
      <h1>⚙️ 系統事件稽核</h1>
    </div>
    
    <!-- Filters -->
    <div class="filters">
      <div class="filter-group">
        <label>事件類型:</label>
        <select v-model="filters.event_type">
          <option :value="null">全部</option>
          <option v-for="type in eventTypes" :key="type" :value="type">
            {{ type }}
          </option>
        </select>
      </div>
      
      <div class="filter-group">
        <label>嚴重程度:</label>
        <select v-model="filters.severity">
          <option :value="null">全部</option>
          <option value="info">資訊</option>
          <option value="warning">警告</option>
          <option value="error">錯誤</option>
          <option value="critical">嚴重</option>
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
      
      <button @click="fetchEvents" class="btn-primary">篩選</button>
      <button @click="exportEvents('csv')" class="btn-secondary">匯出 CSV</button>
      <button @click="exportEvents('json')" class="btn-secondary">匯出 JSON</button>
    </div>
    
    <!-- Stats by Severity -->
    <div class="stats-row">
      <div class="stat-card info">
        <div class="stat-value">{{ stats.info }}</div>
        <div class="stat-label">資訊</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-value">{{ stats.warning }}</div>
        <div class="stat-label">警告</div>
      </div>
      <div class="stat-card error">
        <div class="stat-value">{{ stats.error }}</div>
        <div class="stat-label">錯誤</div>
      </div>
      <div class="stat-card critical">
        <div class="stat-value">{{ stats.critical }}</div>
        <div class="stat-label">嚴重</div>
      </div>
    </div>
    
    <!-- Timeline View -->
    <div class="timeline-container">
      <h2>時間線檢視</h2>
      <div class="timeline">
        <div 
          v-for="event in events" 
          :key="event.id" 
          :class="['timeline-item', `severity-${event.severity}`]"
        >
          <div class="timeline-marker"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <span :class="['severity-badge', `severity-${event.severity}`]">
                {{ getSeverityText(event.severity) }}
              </span>
              <span class="event-type">{{ event.event_type }}</span>
              <span class="event-time">{{ formatDateTime(event.created_at) }}</span>
            </div>
            <div class="event-message">{{ event.message }}</div>
            <div v-if="event.details" class="event-details">
              <strong>詳情:</strong> {{ event.details }}
            </div>
            <div v-if="event.source" class="event-source">
              <strong>來源:</strong> {{ event.source }}
            </div>
          </div>
        </div>
        
        <div v-if="events.length === 0" class="no-data">
          暂无系统事件
        </div>
      </div>
    </div>
    
    <!-- Table View -->
    <div class="table-container">
      <h2>列表檢視</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>時間</th>
            <th>嚴重程度</th>
            <th>事件類型</th>
            <th>訊息</th>
            <th>來源</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in events" :key="event.id">
            <td>{{ event.id }}</td>
            <td>{{ formatDateTime(event.created_at) }}</td>
            <td>
              <span :class="['severity-badge', `severity-${event.severity}`]">
                {{ getSeverityText(event.severity) }}
              </span>
            </td>
            <td>{{ event.event_type }}</td>
            <td>{{ event.message }}</td>
            <td>{{ event.source || '-' }}</td>
          </tr>
        </tbody>
      </table>
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
  name: 'SystemEvents',
  data() {
    return {
      events: [],
      eventTypes: [],
      filters: {
        event_type: null,
        severity: null,
        start_date: '',
        end_date: ''
      },
      limit: 50,
      offset: 0,
      total: 0,
      stats: {
        info: 0,
        warning: 0,
        error: 0,
        critical: 0
      }
    }
  },
  mounted() {
    this.fetchEvents()
    this.fetchEventTypes()
  },
  methods: {
    async fetchEvents() {
      try {
        const params = new URLSearchParams()
        if (this.filters.event_type) params.append('event_type', this.filters.event_type)
        if (this.filters.severity) params.append('severity', this.filters.severity)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        params.append('limit', this.limit)
        params.append('offset', this.offset)
        
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/audit/system-events?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.events = data.events
        this.total = data.total
        
        // Calculate stats
        this.calculateStats()
      } catch (error) {
        console.error('Error fetching system events:', error)
      }
    },
    async fetchEventTypes() {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/audit/system-events/types', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.eventTypes = data.event_types || []
      } catch (error) {
        console.error('Error fetching event types:', error)
      }
    },
    calculateStats() {
      this.stats = {
        info: 0,
        warning: 0,
        error: 0,
        critical: 0
      }
      this.events.forEach(event => {
        if (this.stats[event.severity] !== undefined) {
          this.stats[event.severity]++
        }
      })
    },
    async exportEvents(format) {
      try {
        const params = new URLSearchParams()
        if (this.filters.event_type) params.append('event_type', this.filters.event_type)
        if (this.filters.severity) params.append('severity', this.filters.severity)
        if (this.filters.start_date) params.append('start_date', this.filters.start_date)
        if (this.filters.end_date) params.append('end_date', this.filters.end_date)
        params.append('limit', 10000)
        
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/audit/system-events?${params}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        
        // Download file
        let content
        let mimeType
        if (format === 'json') {
          content = JSON.stringify(data.events, null, 2)
          mimeType = 'application/json'
        } else {
          // CSV
          if (data.events.length === 0) {
            content = ''
          } else {
            const headers = Object.keys(data.events[0])
            content = headers.join(',') + '\n'
            content += data.events.map(row => 
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
        a.download = `system_events_${new Date().toISOString().split('T')[0]}.${format}`
        a.click()
        URL.revokeObjectURL(url)
      } catch (error) {
        console.error('Error exporting events:', error)
      }
    },
    prevPage() {
      this.offset = Math.max(0, this.offset - this.limit)
      this.fetchEvents()
    },
    nextPage() {
      this.offset += this.limit
      this.fetchEvents()
    },
    formatDateTime(dateStr) {
      if (!dateStr) return '-'
      return new Date(dateStr).toLocaleString('zh-TW')
    },
    getSeverityText(severity) {
      const severityMap = {
        'info': '資訊',
        'warning': '警告',
        'error': '錯誤',
        'critical': '嚴重'
      }
      return severityMap[severity] || severity
    }
  }
}
</script>

<style scoped>
.system-events {
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

.stat-card.info {
  border-left: 4px solid #3498db;
}

.stat-card.warning {
  border-left: 4px solid #f39c12;
}

.stat-card.error {
  border-left: 4px solid #e74c3c;
}

.stat-card.critical {
  border-left: 4px solid #8e44ad;
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

.timeline-container,
.table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 20px;
  margin-bottom: 24px;
}

.timeline-container h2,
.table-container h2 {
  font-size: 18px;
  color: #2c3e50;
  margin-bottom: 16px;
}

.timeline {
  position: relative;
  padding-left: 30px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e0e0e0;
}

.timeline-item {
  position: relative;
  padding-bottom: 24px;
}

.timeline-marker {
  position: absolute;
  left: -26px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ccc;
}

.severity-info .timeline-marker { background: #3498db; }
.severity-warning .timeline-marker { background: #f39c12; }
.severity-error .timeline-marker { background: #e74c3c; }
.severity-critical .timeline-marker { background: #8e44ad; }

.timeline-content {
  background: #f8f9fa;
  padding: 12px 16px;
  border-radius: 8px;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.event-type {
  font-weight: 600;
  color: #2c3e50;
}

.event-time {
  font-size: 12px;
  color: #999;
  margin-left: auto;
}

.event-message {
  color: #2c3e50;
  margin-bottom: 8px;
}

.event-details,
.event-source {
  font-size: 12px;
  color: #666;
}

.severity-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.severity-info {
  background: #d1ecf1;
  color: #0c5460;
}

.severity-warning {
  background: #fff3cd;
  color: #856404;
}

.severity-error {
  background: #f8d7da;
  color: #721c24;
}

.severity-critical {
  background: #e2d5f1;
  color: #6c3483;
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

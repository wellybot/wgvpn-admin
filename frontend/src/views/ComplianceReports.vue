<template>
  <div class="compliance-reports">
    <div class="page-header">
      <h1>📊 合規報告產生</h1>
    </div>
    
    <!-- Generate Report Form -->
    <div class="generate-section">
      <h2>產生新報告</h2>
      <div class="form-card">
        <div class="form-row">
          <div class="form-group">
            <label>報告類型:</label>
            <select v-model="reportConfig.report_type">
              <option value="daily">每日報告</option>
              <option value="weekly">每週報告</option>
              <option value="monthly">每月報告</option>
              <option value="custom">自訂範圍</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>開始日期:</label>
            <input type="date" v-model="reportConfig.start_date" />
          </div>
          
          <div class="form-group">
            <label>結束日期:</label>
            <input type="date" v-model="reportConfig.end_date" />
          </div>
        </div>
        
        <div class="form-actions">
          <button @click="generateReport" class="btn-primary" :disabled="generating">
            {{ generating ? '產生中...' : '產生報告' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Recent Reports -->
    <div class="reports-section">
      <h2>報告歷史</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>標題</th>
            <th>類型</th>
            <th>期間</th>
            <th>狀態</th>
            <th>建立者</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="report in reports" :key="report.id">
            <td>{{ report.id }}</td>
            <td>{{ report.title }}</td>
            <td>
              <span class="type-badge">{{ getTypeText(report.report_type) }}</span>
            </td>
            <td>{{ report.start_date }} ~ {{ report.end_date }}</td>
            <td>
              <span :class="['status-badge', `status-${report.status}`]">
                {{ getStatusText(report.status) }}
              </span>
            </td>
            <td>{{ report.created_by_username || '-' }}</td>
            <td>{{ formatDateTime(report.created_at) }}</td>
            <td>
              <button 
                v-if="report.status === 'completed'" 
                @click="downloadReport(report.id, 'json')"
                class="btn-small"
              >
                JSON
              </button>
              <button 
                v-if="report.status === 'completed'" 
                @click="downloadReport(report.id, 'csv')"
                class="btn-small"
              >
                CSV
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <div v-if="reports.length === 0" class="no-data">
        暂无生成的报告
      </div>
    </div>
    
    <!-- Report Preview Modal -->
    <div v-if="previewData" class="modal-overlay" @click.self="previewData = null">
      <div class="modal">
        <div class="modal-header">
          <h3>報告預覽</h3>
          <button @click="previewData = null" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="preview-section">
            <h4>摘要統計</h4>
            <div class="summary-grid" v-if="previewData.sections?.summary">
              <div class="summary-item">
                <span class="label">新增用戶:</span>
                <span class="value">{{ previewData.sections.summary.new_users }}</span>
              </div>
              <div class="summary-item">
                <span class="label">總連線數:</span>
                <span class="value">{{ previewData.sections.summary.total_connections }}</span>
              </div>
              <div class="summary-item">
                <span class="label">成功登入:</span>
                <span class="value">{{ previewData.sections.summary.successful_logins }}</span>
              </div>
              <div class="summary-item">
                <span class="label">失敗登入:</span>
                <span class="value">{{ previewData.sections.summary.failed_logins }}</span>
              </div>
              <div class="summary-item">
                <span class="label">總警示:</span>
                <span class="value">{{ previewData.sections.summary.total_alerts }}</span>
              </div>
            </div>
          </div>
          
          <div class="preview-section">
            <h4>用戶活動 ({{ previewData.sections?.user_activities?.length || 0 }} 條記錄)</h4>
            <div class="preview-table-container">
              <table class="preview-table">
                <thead>
                  <tr>
                    <th>用戶名</th>
                    <th>連線數</th>
                    <th>下載</th>
                    <th>上傳</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="user in previewData.sections?.user_activities?.slice(0, 10)" :key="user.id">
                    <td>{{ user.username }}</td>
                    <td>{{ user.connection_count || 0 }}</td>
                    <td>{{ formatBytes(user.total_received || 0) }}</td>
                    <td>{{ formatBytes(user.total_sent || 0) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <div class="preview-section">
            <h4>管理員操作 ({{ previewData.sections?.admin_operations?.length || 0 }} 條記錄)</h4>
            <div class="preview-table-container">
              <table class="preview-table">
                <thead>
                  <tr>
                    <th>時間</th>
                    <th>管理員</th>
                    <th>操作</th>
                    <th>詳情</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(op, idx) in previewData.sections?.admin_operations?.slice(0, 10)" :key="idx">
                    <td>{{ formatDateTime(op.created_at) }}</td>
                    <td>{{ op.admin_username || '-' }}</td>
                    <td>{{ op.action }}</td>
                    <td>{{ op.details || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="downloadReport(previewReportId, 'json')" class="btn-primary">
            下載 JSON
          </button>
          <button @click="downloadReport(previewReportId, 'csv')" class="btn-secondary">
            下載 CSV
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ComplianceReports',
  data() {
    const today = new Date().toISOString().split('T')[0]
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    
    return {
      reportConfig: {
        report_type: 'weekly',
        start_date: weekAgo,
        end_date: today
      },
      reports: [],
      generating: false,
      previewData: null,
      previewReportId: null
    }
  },
  watch: {
    'reportConfig.report_type'(type) {
      const today = new Date().toISOString().split('T')[0]
      if (type === 'daily') {
        this.reportConfig.start_date = today
        this.reportConfig.end_date = today
      } else if (type === 'weekly') {
        this.reportConfig.start_date = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        this.reportConfig.end_date = today
      } else if (type === 'monthly') {
        this.reportConfig.start_date = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
        this.reportConfig.end_date = today
      }
    }
  },
  mounted() {
    this.fetchReports()
  },
  methods: {
    async generateReport() {
      if (!this.reportConfig.start_date || !this.reportConfig.end_date) {
        alert('請選擇日期範圍')
        return
      }
      
      this.generating = true
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/audit/reports/generate', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.reportConfig)
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to generate report')
        }
        
        const data = await response.json()
        
        // Show preview
        this.previewData = data.data
        this.previewReportId = data.report_id
        
        // Refresh reports list
        this.fetchReports()
      } catch (error) {
        console.error('Error generating report:', error)
        alert('產生報告失敗: ' + error.message)
      } finally {
        this.generating = false
      }
    },
    async fetchReports() {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/audit/reports', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await response.json()
        this.reports = data.reports
      } catch (error) {
        console.error('Error fetching reports:', error)
      }
    },
    async downloadReport(reportId, format) {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/audit/reports/${reportId}/download?format=${format}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (!response.ok) {
          throw new Error('Download failed')
        }
        
        const data = await response.json()
        
        // Download file
        const blob = new Blob([format === 'json' ? JSON.stringify(data.report, null, 2) : data.data], {
          type: format === 'json' ? 'application/json' : 'text/csv'
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = data.filename
        a.click()
        URL.revokeObjectURL(url)
      } catch (error) {
        console.error('Error downloading report:', error)
        alert('下載報告失敗')
      }
    },
    formatDateTime(dateStr) {
      if (!dateStr) return '-'
      return new Date(dateStr).toLocaleString('zh-TW')
    },
    getTypeText(type) {
      const typeMap = {
        'daily': '每日',
        'weekly': '每週',
        'monthly': '每月',
        'custom': '自訂'
      }
      return typeMap[type] || type
    },
    getStatusText(status) {
      const statusMap = {
        'pending': '處理中',
        'completed': '已完成',
        'failed': '失敗'
      }
      return statusMap[status] || status
    },
    formatBytes(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
  }
}
</script>

<style scoped>
.compliance-reports {
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

.generate-section,
.reports-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 20px;
  margin-bottom: 24px;
}

.generate-section h2,
.reports-section h2 {
  font-size: 18px;
  color: #2c3e50;
  margin-bottom: 16px;
}

.form-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 12px;
  color: #666;
}

.form-group select,
.form-group input {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  padding: 10px 20px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 10px 20px;
  background: #95a5a6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-small {
  padding: 4px 8px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 4px;
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

.type-badge {
  padding: 4px 8px;
  background: #e8f4fd;
  color: #3498db;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-completed {
  background: #d4edda;
  color: #155724;
}

.status-failed {
  background: #f8d7da;
  color: #721c24;
}

.no-data {
  padding: 48px;
  text-align: center;
  color: #999;
}

/* Modal Styles */
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
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  font-size: 18px;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #eee;
}

.preview-section {
  margin-bottom: 24px;
}

.preview-section h4 {
  font-size: 16px;
  color: #2c3e50;
  margin-bottom: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.summary-item {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.summary-item .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.summary-item .value {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
}

.preview-table-container {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 4px;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.preview-table th,
.preview-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.preview-table th {
  background: #f8f9fa;
  position: sticky;
  top: 0;
}
</style>

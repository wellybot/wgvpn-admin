<template>
  <div class="templates-container">
    <h1>📋 自訂報告範本</h1>
    
    <div class="controls">
      <button @click="showCreateModal = true" class="btn-primary">+ 新建範本</button>
      <button @click="loadTemplates" class="btn-secondary">🔄 刷新</button>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">載入中...</div>
    
    <!-- Templates List -->
    <div v-else-if="templates.length" class="templates-grid">
      <div v-for="template in templates" :key="template.id" class="template-card">
        <div class="template-header">
          <h3>{{ template.name }}</h3>
          <span class="template-date">{{ formatDate(template.created_at) }}</span>
        </div>
        <p class="template-description">{{ template.description || '無描述' }}</p>
        
        <div class="template-details">
          <div class="detail-item">
            <span class="label">數據來源:</span>
            <span class="value">{{ formatDataSources(template.data_sources) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">日期範圍:</span>
            <span class="value">{{ template.date_range }}</span>
          </div>
          <div class="detail-item">
            <span class="label">格式:</span>
            <span class="value">{{ template.format.toUpperCase() }}</span>
          </div>
          <div class="detail-item" v-if="template.created_by_username">
            <span class="label">創建者:</span>
            <span class="value">{{ template.created_by_username }}</span>
          </div>
        </div>
        
        <div class="template-actions">
          <button @click="generateReport(template)" class="btn-primary">📊 生成報告</button>
          <button @click="editTemplate(template)" class="btn-secondary">✏️ 編輯</button>
          <button @click="duplicateTemplate(template)" class="btn-secondary">📋 複製</button>
          <button @click="deleteTemplate(template.id)" class="btn-danger">🗑️ 刪除</button>
        </div>
      </div>
    </div>
    
    <div v-else class="no-data">暫無報告範本，點擊上方按鈕創建</div>
    
    <!-- Generated Reports History -->
    <div class="section history-section">
      <h2>📜 生成的報告歷史</h2>
      <div v-if="generatedReports.length" class="reports-table">
        <table>
          <thead>
            <tr>
              <th>名稱</th>
              <th>類型</th>
              <th>日期範圍</th>
              <th>生成時間</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in generatedReports" :key="report.id">
              <td>{{ report.name }}</td>
              <td>{{ report.report_type }}</td>
              <td>{{ report.start_date }} ~ {{ report.end_date }}</td>
              <td>{{ formatDate(report.generated_at) }}</td>
              <td>
                <button @click="viewReport(report)" class="btn-small">查看</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="no-data">暫無生成的報告</div>
    </div>
    
    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click.self="closeModals">
      <div class="modal">
        <h3>{{ showEditModal ? '編輯範本' : '新建範本' }}</h3>
        <form @submit.prevent="saveTemplate">
          <div class="form-group">
            <label>名稱:</label>
            <input type="text" v-model="templateForm.name" required />
          </div>
          <div class="form-group">
            <label>描述:</label>
            <textarea v-model="templateForm.description" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label>數據來源 (多選):</label>
            <div class="checkbox-group">
              <label>
                <input type="checkbox" value="traffic" v-model="templateForm.dataSources" />
                流量數據
              </label>
              <label>
                <input type="checkbox" value="users" v-model="templateForm.dataSources" />
                用戶統計
              </label>
              <label>
                <input type="checkbox" value="system" v-model="templateForm.dataSources" />
                系統健康
              </label>
              <label>
                <input type="checkbox" value="audit" v-model="templateForm.dataSources" />
                稽查記錄
              </label>
            </div>
          </div>
          <div class="form-group">
            <label>日期範圍:</label>
            <select v-model="templateForm.dateRange" required>
              <option value="today">今天</option>
              <option value="yesterday">昨天</option>
              <option value="last7days">過去7天</option>
              <option value="last30days">過去30天</option>
              <option value="custom">自訂</option>
            </select>
          </div>
          <div v-if="templateForm.dateRange === 'custom'" class="form-group">
            <label>自訂日期:</label>
            <div class="date-range">
              <input type="date" v-model="templateForm.customStartDate" />
              <span>~</span>
              <input type="date" v-model="templateForm.customEndDate" />
            </div>
          </div>
          <div class="form-group">
            <label>輸出格式:</label>
            <select v-model="templateForm.format">
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModals" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">{{ showEditModal ? '保存' : '創建' }}</button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- Generate Report Modal -->
    <div v-if="showGenerateModal" class="modal-overlay" @click.self="showGenerateModal = false">
      <div class="modal">
        <h3>生成報告</h3>
        <form @submit.prevent="executeGenerate">
          <div class="form-group">
            <label>選擇的範本:</label>
            <div class="template-info">{{ selectedTemplate?.name }}</div>
          </div>
          <div class="form-group">
            <label>開始日期:</label>
            <input type="date" v-model="generateForm.startDate" required />
          </div>
          <div class="form-group">
            <label>結束日期:</label>
            <input type="date" v-model="generateForm.endDate" required />
          </div>
          <div class="form-actions">
            <button type="button" @click="showGenerateModal = false" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">生成</button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- Report Preview Modal -->
    <div v-if="showPreviewModal" class="modal-overlay large" @click.self="showPreviewModal = false">
      <div class="modal large">
        <h3>報告預覽: {{ previewReport?.name }}</h3>
        <div class="report-preview">
          <pre>{{ JSON.stringify(previewData, null, 2) }}</pre>
        </div>
        <div class="form-actions">
          <button @click="downloadReport" class="btn-primary">📥 下載</button>
          <button @click="showPreviewModal = false" class="btn-secondary">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReportTemplates',
  data() {
    return {
      loading: false,
      templates: [],
      generatedReports: [],
      showCreateModal: false,
      showEditModal: false,
      showGenerateModal: false,
      showPreviewModal: false,
      selectedTemplate: null,
      previewReport: null,
      previewData: null,
      editingTemplateId: null,
      templateForm: {
        name: '',
        description: '',
        dataSources: [],
        dateRange: 'last7days',
        customStartDate: '',
        customEndDate: '',
        format: 'json'
      },
      generateForm: {
        startDate: '',
        endDate: ''
      }
    };
  },
  mounted() {
    this.loadTemplates();
    this.loadGeneratedReports();
    
    // Set default dates
    const end = new Date();
    const start = new Date(Date.now() - 7 * 86400000);
    this.generateForm.endDate = end.toISOString().split('T')[0];
    this.generateForm.startDate = start.toISOString().split('T')[0];
  },
  methods: {
    async loadTemplates() {
      this.loading = true;
      try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/reports/templates', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        this.templates = await response.json();
      } catch (error) {
        console.error('Failed to load templates:', error);
      } finally {
        this.loading = false;
      }
    },
    async loadGeneratedReports() {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/reports/generated', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        this.generatedReports = await response.json();
      } catch (error) {
        console.error('Failed to load generated reports:', error);
      }
    },
    async saveTemplate() {
      try {
        const token = localStorage.getItem('token');
        const data = {
          name: this.templateForm.name,
          description: this.templateForm.description,
          data_sources: JSON.stringify(this.templateForm.dataSources),
          date_range: this.templateForm.dateRange,
          custom_start_date: this.templateForm.dateRange === 'custom' ? this.templateForm.customStartDate : null,
          custom_end_date: this.templateForm.dateRange === 'custom' ? this.templateForm.customEndDate : null,
          format: this.templateForm.format
        };
        
        if (this.showEditModal) {
          await fetch(`/api/reports/templates/${this.editingTemplateId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
          });
        } else {
          await fetch('/api/reports/templates', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
          });
        }
        
        this.closeModals();
        this.loadTemplates();
      } catch (error) {
        console.error('Failed to save template:', error);
      }
    },
    async deleteTemplate(id) {
      if (!confirm('確定要刪除此範本嗎？')) return;
      try {
        const token = localStorage.getItem('token');
        await fetch(`/api/reports/templates/${id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        this.loadTemplates();
      } catch (error) {
        console.error('Failed to delete template:', error);
      }
    },
    editTemplate(template) {
      this.editingTemplateId = template.id;
      this.templateForm = {
        name: template.name,
        description: template.description || '',
        dataSources: JSON.parse(template.data_sources || '[]'),
        dateRange: template.date_range,
        customStartDate: template.custom_start_date || '',
        customEndDate: template.custom_end_date || '',
        format: template.format || 'json'
      };
      this.showEditModal = true;
    },
    duplicateTemplate(template) {
      this.templateForm = {
        name: `${template.name} (複製)`,
        description: template.description || '',
        dataSources: JSON.parse(template.data_sources || '[]'),
        dateRange: template.date_range,
        customStartDate: template.custom_start_date || '',
        customEndDate: template.custom_end_date || '',
        format: template.format || 'json'
      };
      this.showCreateModal = true;
    },
    generateReport(template) {
      this.selectedTemplate = template;
      this.showGenerateModal = true;
    },
    async executeGenerate() {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `/api/reports/generate-from-template/${this.selectedTemplate.id}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              start_date: this.generateForm.startDate,
              end_date: this.generateForm.endDate
            })
          }
        );
        const result = await response.json();
        this.previewReport = result.report;
        this.previewData = result.data;
        this.showGenerateModal = false;
        this.showPreviewModal = true;
        this.loadGeneratedReports();
      } catch (error) {
        console.error('Failed to generate report:', error);
      }
    },
    async viewReport(report) {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`/api/reports/generated/${report.id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await response.json();
        this.previewReport = result;
        this.previewData = result.data ? JSON.parse(result.data) : null;
        this.showPreviewModal = true;
      } catch (error) {
        console.error('Failed to load report:', error);
      }
    },
    downloadReport() {
      if (!this.previewData) return;
      
      const dataStr = this.previewReport.format === 'json' 
        ? JSON.stringify(this.previewData, null, 2)
        : this.previewData;
      
      const blob = new Blob([dataStr], { 
        type: this.previewReport.format === 'json' ? 'application/json' : 'text/csv' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.previewReport.name}.${this.previewReport.format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    },
    closeModals() {
      this.showCreateModal = false;
      this.showEditModal = false;
      this.editingTemplateId = null;
      this.templateForm = {
        name: '',
        description: '',
        dataSources: [],
        dateRange: 'last7days',
        customStartDate: '',
        customEndDate: '',
        format: 'json'
      };
    },
    formatDataSources(sources) {
      try {
        const arr = JSON.parse(sources);
        const map = { traffic: '流量', users: '用戶', system: '系統', audit: '稽查' };
        return arr.map(s => map[s] || s).join(', ');
      } catch {
        return sources;
      }
    },
    formatDate(dateStr) {
      if (!dateStr) return '-';
      return new Date(dateStr).toLocaleString('zh-TW');
    }
  }
};
</script>

<style scoped>
.templates-container {
  max-width: 1200px;
  margin: 0 auto;
}

.controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.loading, .no-data {
  text-align: center;
  padding: 40px;
  color: #666;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.template-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.template-header h3 {
  margin: 0;
  font-size: 18px;
}

.template-date {
  font-size: 12px;
  color: #999;
}

.template-description {
  color: #666;
  margin-bottom: 16px;
  font-size: 14px;
}

.template-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.detail-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.detail-item .label {
  color: #666;
  min-width: 60px;
}

.detail-item .value {
  font-weight: 500;
}

.template-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.section {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.section h2 {
  margin-bottom: 16px;
  font-size: 18px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 600;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 24px;
  border-radius: 12px;
  width: 450px;
  max-width: 90%;
}

.modal.large {
  width: 800px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal h3 {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: normal;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-range input {
  flex: 1;
}

.template-info {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  font-weight: 500;
}

.report-preview {
  max-height: 400px;
  overflow: auto;
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.report-preview pre {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn-primary {
  padding: 10px 20px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-secondary {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-danger {
  padding: 10px 20px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-small {
  padding: 6px 12px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
</style>

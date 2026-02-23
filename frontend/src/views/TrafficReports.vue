<template>
  <div class="reports-container">
    <h1>📊 流量報告</h1>
    
    <!-- Date Range Selection -->
    <div class="filters">
      <div class="filter-group">
        <label>開始日期:</label>
        <input type="date" v-model="startDate" @change="loadTrafficReport" />
      </div>
      <div class="filter-group">
        <label>結束日期:</label>
        <input type="date" v-model="endDate" @change="loadTrafficReport" />
      </div>
      <button @click="loadTrafficReport" class="btn-primary">🔄 刷新報告</button>
    </div>
    
    <!-- Quick Date Filters -->
    <div class="quick-filters">
      <button @click="setDateRange('today')" :class="{active: isToday}">今天</button>
      <button @click="setDateRange('yesterday')" :class="{active: isYesterday}">昨天</button>
      <button @click="setDateRange('last7days')" :class="{active: isLast7Days}">過去7天</button>
      <button @click="setDateRange('last30days')" :class="{active: isLast30Days}">過去30天</button>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">載入中...</div>
    
    <!-- Report Data -->
    <div v-else-if="reportData" class="report-content">
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="card">
          <div class="card-title">總下載</div>
          <div class="card-value">{{ formatBytes(reportData.traffic.total_received) }}</div>
        </div>
        <div class="card">
          <div class="card-title">總上傳</div>
          <div class="card-value">{{ formatBytes(reportData.traffic.total_sent) }}</div>
        </div>
        <div class="card">
          <div class="card-title">總傳輸量</div>
          <div class="card-value">{{ formatBytes(reportData.traffic.total_transfer) }}</div>
        </div>
        <div class="card">
          <div class="card-title">活躍用戶</div>
          <div class="card-value">{{ reportData.traffic.active_users }}</div>
        </div>
      </div>
      
      <!-- Top Users -->
      <div class="section">
        <h2>🏆 Top 用戶</h2>
        <div v-if="reportData.traffic.top_users && reportData.traffic.top_users.length" class="top-users">
          <table>
            <thead>
              <tr>
                <th>排名</th>
                <th>用戶名</th>
                <th>下載</th>
                <th>上傳</th>
                <th>總計</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(user, index) in reportData.traffic.top_users" :key="user.id">
                <td>{{ index + 1 }}</td>
                <td>{{ user.username }}</td>
                <td>{{ formatBytes(user.total_received) }}</td>
                <td>{{ formatBytes(user.total_sent) }}</td>
                <td>{{ formatBytes(user.total_transfer) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="no-data">暫無數據</div>
      </div>
      
      <!-- Daily Trends Chart -->
      <div class="section">
        <h2>📈 每日趨勢</h2>
        <canvas ref="trendChart" class="chart-canvas"></canvas>
      </div>
      
      <!-- Hourly Distribution -->
      <div class="section">
        <h2>⏰ 時段分佈</h2>
        <canvas ref="hourlyChart" class="chart-canvas"></canvas>
      </div>
    </div>
    
    <div v-else class="no-data">請選擇日期範圍以查看報告</div>
    
    <!-- Schedule Section -->
    <div class="schedule-section">
      <h2>📅 定期報告排程</h2>
      <button @click="showScheduleModal = true" class="btn-primary">+ 新建排程</button>
      
      <div v-if="scheduledReports.length" class="scheduled-list">
        <table>
          <thead>
            <tr>
              <th>名稱</th>
              <th>排程類型</th>
              <th>時間</th>
              <th>狀態</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in scheduledReports" :key="report.id">
              <td>{{ report.name }}</td>
              <td>{{ report.schedule_type }}</td>
              <td>{{ report.schedule_time || '-' }}</td>
              <td>
                <span :class="['status', report.is_active ? 'active' : 'inactive']">
                  {{ report.is_active ? '啟用' : '停用' }}
                </span>
              </td>
              <td>
                <button @click="deleteSchedule(report.id)" class="btn-danger">刪除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="no-data">暫無排程報告</div>
    </div>
    
    <!-- Schedule Modal -->
    <div v-if="showScheduleModal" class="modal-overlay" @click.self="showScheduleModal = false">
      <div class="modal">
        <h3>新建定期報告排程</h3>
        <form @submit.prevent="createSchedule">
          <div class="form-group">
            <label>名稱:</label>
            <input type="text" v-model="newSchedule.name" required />
          </div>
          <div class="form-group">
            <label>排程類型:</label>
            <select v-model="newSchedule.schedule_type" required>
              <option value="daily">每日</option>
              <option value="weekly">每週</option>
              <option value="monthly">每月</option>
            </select>
          </div>
          <div class="form-group" v-if="newSchedule.schedule_type !== 'daily'">
            <label v-if="newSchedule.schedule_type === 'weekly'">星期 (0-6):</label>
            <label v-else>日期 (1-31):</label>
            <input type="number" v-if="newSchedule.schedule_type === 'weekly'" 
                   v-model="newSchedule.schedule_dayOfWeek" min="0" max="6" />
            <input type="number" v-else 
                   v-model="newSchedule.schedule_dayOfMonth" min="1" max="31" />
          </div>
          <div class="form-group">
            <label>時間:</label>
            <input type="time" v-model="newSchedule.schedule_time" />
          </div>
          <div class="form-group">
            <label>Top 用戶數:</label>
            <input type="number" v-model.number="newSchedule.top_users_count" min="1" max="50" />
          </div>
          <div class="form-actions">
            <button type="button" @click="showScheduleModal = false" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary">創建</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

export default {
  name: 'TrafficReports',
  data() {
    return {
      loading: false,
      startDate: '',
      endDate: '',
      reportData: null,
      scheduledReports: [],
      showScheduleModal: false,
      newSchedule: {
        name: '',
        schedule_type: 'daily',
        schedule_time: '09:00',
        schedule_dayOfWeek: null,
        schedule_dayOfMonth: null,
        top_users_count: 10
      },
      trendChart: null,
      hourlyChart: null
    };
  },
  computed: {
    isToday() {
      const today = new Date().toISOString().split('T')[0];
      return this.startDate === today && this.endDate === today;
    },
    isYesterday() {
      const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
      return this.startDate === yesterday && this.endDate === yesterday;
    },
    isLast7Days() {
      const end = new Date();
      const start = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];
      return this.startDate === start && this.endDate === end.toISOString().split('T')[0];
    },
    isLast30Days() {
      const end = new Date();
      const start = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
      return this.startDate === start && this.endDate === end.toISOString().split('T')[0];
    }
  },
  mounted() {
    this.setDateRange('last7days');
    this.loadScheduledReports();
  },
  methods: {
    setDateRange(range) {
      const today = new Date();
      const end = today.toISOString().split('T')[0];
      
      if (range === 'today') {
        this.startDate = end;
      } else if (range === 'yesterday') {
        const yesterday = new Date(Date.now() - 86400000);
        this.startDate = yesterday.toISOString().split('T')[0];
      } else if (range === 'last7days') {
        const start = new Date(Date.now() - 7 * 86400000);
        this.startDate = start.toISOString().split('T')[0];
      } else if (range === 'last30days') {
        const start = new Date(Date.now() - 30 * 86400000);
        this.startDate = start.toISOString().split('T')[0];
      }
      this.endDate = end;
      this.loadTrafficReport();
    },
    async loadTrafficReport() {
      this.loading = true;
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `/api/reports/traffic?start_date=${this.startDate}&end_date=${this.endDate}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        this.reportData = await response.json();
        this.$nextTick(() => this.renderCharts());
      } catch (error) {
        console.error('Failed to load traffic report:', error);
      } finally {
        this.loading = false;
      }
    },
    async loadScheduledReports() {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/reports/traffic/scheduled', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        this.scheduledReports = await response.json();
      } catch (error) {
        console.error('Failed to load scheduled reports:', error);
      }
    },
    async createSchedule() {
      try {
        const token = localStorage.getItem('token');
        await fetch('/api/reports/traffic/schedule', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(this.newSchedule)
        });
        this.showScheduleModal = false;
        this.newSchedule = {
          name: '',
          schedule_type: 'daily',
          schedule_time: '09:00',
          schedule_dayOfWeek: null,
          schedule_dayOfMonth: null,
          top_users_count: 10
        };
        this.loadScheduledReports();
      } catch (error) {
        console.error('Failed to create schedule:', error);
      }
    },
    async deleteSchedule(id) {
      if (!confirm('確定要刪除此排程嗎？')) return;
      try {
        const token = localStorage.getItem('token');
        await fetch(`/api/reports/traffic/schedule/${id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        this.loadScheduledReports();
      } catch (error) {
        console.error('Failed to delete schedule:', error);
      }
    },
    renderCharts() {
      if (!this.reportData) return;
      
      // Destroy existing charts
      if (this.trendChart) this.trendChart.destroy();
      if (this.hourlyChart) this.hourlyChart.destroy();
      
      // Daily trends chart
      if (this.reportData.traffic.daily_trends && this.$refs.trendChart) {
        const ctx1 = this.$refs.trendChart.getContext('2d');
        this.trendChart = new Chart(ctx1, {
          type: 'line',
          data: {
            labels: this.reportData.traffic.daily_trends.map(d => d.date),
            datasets: [
              {
                label: '下載',
                data: this.reportData.traffic.daily_trends.map(d => d.total_received),
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true
              },
              {
                label: '上傳',
                data: this.reportData.traffic.daily_trends.map(d => d.total_sent),
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                fill: true
              }
            ]
          },
          options: {
            responsive: true,
            plugins: { legend: { position: 'top' } },
            scales: {
              y: { 
                ticks: { callback: v => this.formatBytes(v) }
              }
            }
          }
        });
      }
      
      // Hourly distribution chart
      if (this.reportData.traffic.hourly_distribution && this.$refs.hourlyChart) {
        const ctx2 = this.$refs.hourlyChart.getContext('2d');
        this.hourlyChart = new Chart(ctx2, {
          type: 'bar',
          data: {
            labels: this.reportData.traffic.hourly_distribution.map(h => `${h.hour}:00`),
            datasets: [{
              label: '傳輸量',
              data: this.reportData.traffic.hourly_distribution.map(h => h.total_received + h.total_sent),
              backgroundColor: 'rgba(155, 89, 182, 0.6)'
            }]
          },
          options: {
            responsive: true,
            plugins: { legend: { position: 'top' } },
            scales: {
              y: { 
                ticks: { callback: v => this.formatBytes(v) }
              }
            }
          }
        });
      }
    },
    formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  }
};
</script>

<style scoped>
.reports-container {
  max-width: 1200px;
  margin: 0 auto;
}

.filters {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-weight: 500;
}

.filter-group input {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.quick-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.quick-filters button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-filters button.active {
  background: #3498db;
  color: white;
  border-color: #3498db;
}

.loading, .no-data {
  text-align: center;
  padding: 40px;
  color: #666;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.card-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 24px;
}

.section h2 {
  margin-bottom: 16px;
  font-size: 18px;
}

.chart-canvas {
  max-height: 300px;
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

.status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status.active {
  background: #d4edda;
  color: #155724;
}

.status.inactive {
  background: #f8d7da;
  color: #721c24;
}

.btn-primary {
  padding: 10px 20px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-danger {
  padding: 6px 12px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.schedule-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-top: 24px;
}

.schedule-section h2 {
  margin-bottom: 16px;
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
  border-radius: 8px;
  width: 400px;
  max-width: 90%;
}

.modal h3 {
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>

<template>
  <div class="user-stats-container">
    <h1>👥 用戶使用統計</h1>
    
    <!-- Date Range Selection -->
    <div class="filters">
      <div class="filter-group">
        <label>開始日期:</label>
        <input type="date" v-model="startDate" @change="loadUserStats" />
      </div>
      <div class="filter-group">
        <label>結束日期:</label>
        <input type="date" v-model="endDate" @change="loadUserStats" />
      </div>
      <button @click="loadUserStats" class="btn-primary">🔄 刷新</button>
      <button @click="exportStats" class="btn-secondary">📥 匯出CSV</button>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">載入中...</div>
    
    <!-- Stats Data -->
    <div v-else-if="statsData" class="stats-content">
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="card">
          <div class="card-title">總用戶數</div>
          <div class="card-value">{{ statsData.summary.total_users }}</div>
        </div>
        <div class="card">
          <div class="card-title">總下載</div>
          <div class="card-value">{{ formatBytes(statsData.summary.total_received) }}</div>
        </div>
        <div class="card">
          <div class="card-title">總上傳</div>
          <div class="card-value">{{ formatBytes(statsData.summary.total_sent) }}</div>
        </div>
        <div class="card">
          <div class="card-title">平均傳輸量</div>
          <div class="card-value">{{ formatBytes(statsData.summary.avg_transfer || 0) }}</div>
        </div>
      </div>
      
      <!-- Charts Row -->
      <div class="charts-row">
        <!-- Traffic Distribution Pie Chart -->
        <div class="chart-container">
          <h2>📊 流量分佈</h2>
          <canvas ref="pieChart" class="chart-canvas"></canvas>
        </div>
        
        <!-- Top Users Bar Chart -->
        <div class="chart-container">
          <h2>🏆 Top 10 用戶</h2>
          <canvas ref="barChart" class="chart-canvas"></canvas>
        </div>
      </div>
      
      <!-- User Table -->
      <div class="section">
        <h2>📋 用戶詳細統計</h2>
        <div class="table-controls">
          <input type="text" v-model="searchQuery" placeholder="搜尋用戶..." class="search-input" />
        </div>
        <table>
          <thead>
            <tr>
              <th @click="sortBy('id')" class="sortable">ID ↕</th>
              <th @click="sortBy('username')" class="sortable">用戶名 ↕</th>
              <th @click="sortBy('total_received')" class="sortable">下載 ↕</th>
              <th @click="sortBy('total_sent')" class="sortable">上傳 ↕</th>
              <th @click="sortBy('total_transfer')" class="sortable">總計 ↕</th>
              <th @click="sortBy('connection_count')" class="sortable">連線次數 ↕</th>
              <th @click="sortBy('active_days')" class="sortable">活躍天數 ↕</th>
              <th @click="sortBy('avg_daily_transfer')" class="sortable">日均 ↕</th>
              <th>最後連線</th>
              <th>狀態</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id">
              <td>{{ user.id }}</td>
              <td>
                <span class="username">{{ user.username }}</span>
              </td>
              <td>{{ formatBytes(user.total_received) }}</td>
              <td>{{ formatBytes(user.total_sent) }}</td>
              <td>{{ formatBytes(user.total_transfer) }}</td>
              <td>{{ user.connection_count || 0 }}</td>
              <td>{{ user.active_days || 0 }}</td>
              <td>{{ formatBytes(user.avg_daily_transfer || 0) }}</td>
              <td>{{ formatDate(user.last_connection) }}</td>
              <td>
                <span :class="['status', user.is_active ? 'active' : 'inactive']">
                  {{ user.is_active ? '啟用' : '停用' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filteredUsers.length" class="no-data">無符合條件的用戶</div>
      </div>
    </div>
    
    <div v-else class="no-data">請選擇日期範圍以查看統計</div>
  </div>
</template>

<script>
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

export default {
  name: 'UserStats',
  data() {
    return {
      loading: false,
      startDate: '',
      endDate: '',
      statsData: null,
      searchQuery: '',
      sortField: 'total_transfer',
      sortOrder: 'desc',
      pieChart: null,
      barChart: null
    };
  },
  computed: {
    filteredUsers() {
      if (!this.statsData || !this.statsData.users) return [];
      
      let users = this.statsData.users.filter(u => 
        !this.searchQuery || 
        u.username.toLowerCase().includes(this.searchQuery.toLowerCase())
      );
      
      users.sort((a, b) => {
        const aVal = a[this.sortField] || 0;
        const bVal = b[this.sortField] || 0;
        return this.sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
      });
      
      return users;
    }
  },
  mounted() {
    const end = new Date();
    const start = new Date(Date.now() - 30 * 86400000);
    this.startDate = start.toISOString().split('T')[0];
    this.endDate = end.toISOString().split('T')[0];
    this.loadUserStats();
  },
  methods: {
    async loadUserStats() {
      this.loading = true;
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `/api/reports/user-stats?start_date=${this.startDate}&end_date=${this.endDate}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        this.statsData = await response.json();
        this.$nextTick(() => this.renderCharts());
      } catch (error) {
        console.error('Failed to load user stats:', error);
      } finally {
        this.loading = false;
      }
    },
    async exportStats() {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `/api/reports/user-stats/export?start_date=${this.startDate}&end_date=${this.endDate}&format=csv`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        const result = await response.json();
        
        // Download CSV
        const blob = new Blob([result.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename;
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error('Failed to export stats:', error);
      }
    },
    sortBy(field) {
      if (this.sortField === field) {
        this.sortOrder = this.sortOrder === 'desc' ? 'asc' : 'desc';
      } else {
        this.sortField = field;
        this.sortOrder = 'desc';
      }
    },
    renderCharts() {
      if (!this.statsData || !this.statsData.users) return;
      
      // Destroy existing charts
      if (this.pieChart) this.pieChart.destroy();
      if (this.barChart) this.barChart.destroy();
      
      // Pie chart - traffic distribution
      const topUsers = this.statsData.users.slice(0, 5);
      const totalTransfer = topUsers.reduce((sum, u) => sum + (u.total_transfer || 0), 0);
      const otherTransfer = (this.statsData.summary.total_received || 0) + 
                           (this.statsData.summary.total_sent || 0) - totalTransfer;
      
      if (!this.$refs.pieChart) return;
      
      const ctx1 = this.$refs.pieChart.getContext('2d');
      this.pieChart = new Chart(ctx1, {
        type: 'doughnut',
        data: {
          labels: [...topUsers.map(u => u.username), '其他'],
          datasets: [{
            data: [...topUsers.map(u => u.total_transfer || 0), otherTransfer],
            backgroundColor: [
              '#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#95a5a6'
            ]
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'right' },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.label}: ${this.formatBytes(ctx.raw)}`
              }
            }
          }
        }
      });
      
      // Bar chart - top users
      if (!this.$refs.barChart) return;
      
      const top10 = this.statsData.users.slice(0, 10);
      const ctx2 = this.$refs.barChart.getContext('2d');
      this.barChart = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: top10.map(u => u.username),
          datasets: [{
            label: '總傳輸量',
            data: top10.map(u => u.total_transfer || 0),
            backgroundColor: '#3498db'
          }]
        },
        options: {
          responsive: true,
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: {
            x: { 
              ticks: { callback: v => this.formatBytes(v) }
            }
          }
        }
      });
    },
    formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    formatDate(dateStr) {
      if (!dateStr) return '-';
      return new Date(dateStr).toLocaleString('zh-TW');
    }
  }
};
</script>

<style scoped>
.user-stats-container {
  max-width: 1400px;
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

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.chart-container h2 {
  margin-bottom: 16px;
  font-size: 18px;
}

.chart-canvas {
  max-height: 300px;
}

.section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.section h2 {
  margin-bottom: 16px;
  font-size: 18px;
}

.table-controls {
  margin-bottom: 16px;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 300px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px 8px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 600;
}

th.sortable {
  cursor: pointer;
}

th.sortable:hover {
  background: #e9ecef;
}

.username {
  font-weight: 500;
  color: #3498db;
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
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>

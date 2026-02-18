<template>
  <div class="traffic-history">
    <div class="header">
      <h2>📈 流量使用歷史</h2>
      <div class="controls">
        <div class="date-range">
          <label>開始日期:</label>
          <input type="date" v-model="startDate" @change="fetchHistory">
        </div>
        <div class="date-range">
          <label>結束日期:</label>
          <input type="date" v-model="endDate" @change="fetchHistory">
        </div>
        <select v-model="chartType" @change="updateChart">
          <option value="line">折線圖</option>
          <option value="bar">柱狀圖</option>
        </select>
        <button @click="fetchHistory" class="refresh-btn">🔄 重新整理</button>
      </div>
    </div>

    <div class="chart-container">
      <Line v-if="chartType === 'line'" :data="chartData" :options="chartOptions" />
      <Bar v-else :data="chartData" :options="chartOptions" />
    </div>

    <div class="summary-cards">
      <div class="card">
        <div class="card-label">總下載</div>
        <div class="card-value download">{{ formatBytes(totalDownload) }}</div>
      </div>
      <div class="card">
        <div class="card-label">總上傳</div>
        <div class="card-value upload">{{ formatBytes(totalUpload) }}</div>
      </div>
      <div class="card">
        <div class="card-label">資料點數</div>
        <div class="card-value">{{ historyData.length }}</div>
      </div>
    </div>

    <div class="history-table-container">
      <h3>詳細記錄</h3>
      <table class="history-table">
        <thead>
          <tr>
            <th>時間</th>
            <th>用戶</th>
            <th>下載</th>
            <th>上傳</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in historyData" :key="log.id">
            <td>{{ formatDateTime(log.snapshot_time) }}</td>
            <td>{{ log.username || '未知' }}</td>
            <td class="download">{{ formatBytes(log.bytes_received) }}</td>
            <td class="upload">{{ formatBytes(log.bytes_sent) }}</td>
          </tr>
          <tr v-if="historyData.length === 0">
            <td colspan="4" class="no-data">沒有歷史資料</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { Line, Bar } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default {
  name: 'TrafficHistory',
  components: {
    Line,
    Bar
  },
  data() {
    return {
      historyData: [],
      startDate: '',
      endDate: '',
      chartType: 'line',
      chartData: {
        labels: [],
        datasets: []
      },
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
          },
          title: {
            display: true,
            text: '流量使用趨勢'
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => this.formatBytes(value)
            }
          }
        }
      }
    };
  },
  computed: {
    totalDownload() {
      return this.historyData.reduce((sum, log) => sum + (log.bytes_received || 0), 0);
    },
    totalUpload() {
      return this.historyData.reduce((sum, log) => sum + (log.bytes_sent || 0), 0);
    }
  },
  mounted() {
    // Set default date range (last 7 days)
    const today = new Date();
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    
    this.endDate = today.toISOString().split('T')[0];
    this.startDate = weekAgo.toISOString().split('T')[0];
    
    this.fetchHistory();
    this.fetchDailySummary();
  },
  methods: {
    async fetchHistory() {
      try {
        const params = new URLSearchParams();
        if (this.startDate) params.append('start_date', this.startDate);
        if (this.endDate) params.append('end_date', this.endDate);
        params.append('limit', 100);
        
        const response = await axios.get(`/api/traffic/history?${params}`);
        this.historyData = response.data.logs || [];
        this.updateChart();
      } catch (error) {
        console.error('Failed to fetch traffic history:', error);
      }
    },
    async fetchDailySummary() {
      try {
        const response = await axios.get('/api/traffic/daily?days=30');
        const dailyData = response.data.daily || [];
        
        // Process daily data for chart
        const labels = dailyData.map(d => d.date).reverse();
        const downloadData = dailyData.map(d => d.total_received).reverse();
        const uploadData = dailyData.map(d => d.total_sent).reverse();
        
        this.chartData = {
          labels,
          datasets: [
            {
              label: '下載 (Bytes)',
              data: downloadData,
              borderColor: '#3498db',
              backgroundColor: 'rgba(52, 152, 219, 0.2)',
              fill: this.chartType === 'line',
              tension: 0.3
            },
            {
              label: '上傳 (Bytes)',
              data: uploadData,
              borderColor: '#e67e22',
              backgroundColor: 'rgba(230, 126, 34, 0.2)',
              fill: this.chartType === 'line',
              tension: 0.3
            }
          ]
        };
      } catch (error) {
        console.error('Failed to fetch daily summary:', error);
      }
    },
    updateChart() {
      if (this.historyData.length === 0) {
        this.fetchDailySummary();
        return;
      }
      
      // Use history data if available
      const labels = this.historyData.map(d => this.formatDateTime(d.snapshot_time)).reverse();
      const downloadData = this.historyData.map(d => d.bytes_received || 0).reverse();
      const uploadData = this.historyData.map(d => d.bytes_sent || 0).reverse();
      
      this.chartData = {
        labels,
        datasets: [
          {
            label: '下載 (Bytes)',
            data: downloadData,
            borderColor: '#3498db',
            backgroundColor: 'rgba(52, 152, 219, 0.2)',
            fill: this.chartType === 'line',
            tension: 0.3
          },
          {
            label: '上傳 (Bytes)',
            data: uploadData,
            borderColor: '#e67e22',
            backgroundColor: 'rgba(230, 126, 34, 0.2)',
            fill: this.chartType === 'line',
            tension: 0.3
          }
        ]
      };
    },
    formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let i = 0;
      while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
      }
      return `${bytes.toFixed(2)} ${units[i]}`;
    },
    formatDateTime(dateStr) {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      return date.toLocaleString('zh-TW', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }
};
</script>

<style scoped>
.traffic-history {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header h2 {
  margin: 0;
  color: #2c3e50;
}

.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-range label {
  font-size: 14px;
  color: #666;
}

.date-range input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  background: white;
}

.refresh-btn {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.refresh-btn:hover {
  background: #2980b9;
}

.chart-container {
  background: white;
  border-radius: 12px;
  padding: 20px;
  height: 400px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.card-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.card-value.download {
  color: #3498db;
}

.card-value.upload {
  color: #e67e22;
}

.history-table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.history-table-container h3 {
  padding: 16px 20px;
  margin: 0;
  color: #2c3e50;
  border-bottom: 1px solid #eee;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #eee;
}

.history-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
}

.history-table tr:last-child td {
  border-bottom: none;
}

.history-table tr:hover {
  background: #f8f9fa;
}

.download {
  color: #3498db;
}

.upload {
  color: #e67e22;
}

.no-data {
  text-align: center;
  color: #999;
  padding: 40px !important;
}
</style>

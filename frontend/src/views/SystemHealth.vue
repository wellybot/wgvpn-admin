<template>
  <div class="system-health-container">
    <h1>💻 系統健康報告</h1>
    
    <div class="controls">
      <button @click="loadHealthData" class="btn-primary">🔄 刷新</button>
      <span class="last-updated">最後更新: {{ lastUpdated }}</span>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">載入中...</div>
    
    <!-- Health Data -->
    <div v-else-if="healthData" class="health-content">
      <!-- System Metrics -->
      <div class="metrics-grid">
        <!-- CPU -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">🖥️</span>
            <span class="metric-title">CPU 使用率</span>
          </div>
          <div class="gauge-container">
            <svg viewBox="0 0 100 50" class="gauge">
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#eee" stroke-width="10"/>
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" 
                    :stroke="getGaugeColor(healthData.cpu.usage_percent)" 
                    stroke-width="10"
                    :stroke-dasharray="getGaugeDashArray(healthData.cpu.usage_percent)"/>
            </svg>
            <div class="gauge-value">{{ healthData.cpu.usage_percent.toFixed(1) }}%</div>
          </div>
          <div class="metric-detail">核心數: {{ healthData.cpu.count }}</div>
        </div>
        
        <!-- Memory -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">💾</span>
            <span class="metric-title">記憶體</span>
          </div>
          <div class="gauge-container">
            <svg viewBox="0 0 100 50" class="gauge">
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#eee" stroke-width="10"/>
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" 
                    :stroke="getGaugeColor(healthData.memory.percent)" 
                    stroke-width="10"
                    :stroke-dasharray="getGaugeDashArray(healthData.memory.percent)"/>
            </svg>
            <div class="gauge-value">{{ healthData.memory.percent.toFixed(1) }}%</div>
          </div>
          <div class="metric-detail">
            {{ formatBytes(healthData.memory.used) }} / {{ formatBytes(healthData.memory.total) }}
          </div>
        </div>
        
        <!-- Disk -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">💿</span>
            <span class="metric-title">磁碟空間</span>
          </div>
          <div class="gauge-container">
            <svg viewBox="0 0 100 50" class="gauge">
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#eee" stroke-width="10"/>
              <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" 
                    :stroke="getGaugeColor(healthData.disk.percent)" 
                    stroke-width="10"
                    :stroke-dasharray="getGaugeDashArray(healthData.disk.percent)"/>
            </svg>
            <div class="gauge-value">{{ healthData.disk.percent.toFixed(1) }}%</div>
          </div>
          <div class="metric-detail">
            {{ formatBytes(healthData.disk.used) }} / {{ formatBytes(healthData.disk.total) }}
          </div>
        </div>
        
        <!-- Active Connections -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">🔗</span>
            <span class="metric-title">活躍連線</span>
          </div>
          <div class="big-number">
            {{ healthData.network.active_connections }}
          </div>
          <div class="metric-detail">目前 VPN 活躍連線數</div>
        </div>
      </div>
      
      <!-- WireGuard Status -->
      <div class="section wireguard-status">
        <h2>🔐 WireGuard 狀態</h2>
        <div class="status-row">
          <div class="status-item">
            <span class="status-label">狀態:</span>
            <span :class="['status-value', healthData.wireguard.status]">
              {{ getWireGuardStatusText(healthData.wireguard.status) }}
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">介面數:</span>
            <span class="status-value">{{ healthData.wireguard.interface_count }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">節點數:</span>
            <span class="status-value">{{ healthData.wireguard.peer_count }}</span>
          </div>
        </div>
      </div>
      
      <!-- Alerts -->
      <div class="section alerts-section">
        <h2>⚠️ 系統警示</h2>
        <div v-if="alerts.length" class="alerts-list">
          <div v-for="(alert, index) in alerts" :key="index" :class="['alert', alert.severity]">
            <span class="alert-icon">{{ alert.severity === 'critical' ? '🔴' : '🟡' }}</span>
            <span class="alert-message">{{ alert.message }}</span>
          </div>
        </div>
        <div v-else class="no-alerts">
          ✅ 系統運行正常，無警示
        </div>
      </div>
      
      <!-- Historical Trends -->
      <div class="section trends-section">
        <h2>📈 歷史趨勢</h2>
        <canvas ref="trendsChart" class="chart-canvas"></canvas>
      </div>
    </div>
    
    <div v-else class="no-data">無法載入系統健康數據</div>
  </div>
</template>

<script>
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

export default {
  name: 'SystemHealth',
  data() {
    return {
      loading: false,
      healthData: null,
      alerts: [],
      lastUpdated: '',
      trendsChart: null,
      historicalData: []
    };
  },
  mounted() {
    this.loadHealthData();
    // Auto-refresh every 30 seconds
    this.refreshInterval = setInterval(() => this.loadHealthData(), 30000);
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  },
  methods: {
    async loadHealthData() {
      this.loading = true;
      try {
        const token = localStorage.getItem('token');
        
        const [healthRes, alertsRes] = await Promise.all([
          fetch('/api/reports/health', { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch('/api/reports/health/alerts', { headers: { 'Authorization': `Bearer ${token}` } })
        ]);
        
        this.healthData = await healthRes.json();
        this.alerts = await alertsRes.json();
        
        this.lastUpdated = new Date().toLocaleString('zh-TW');
        
        // Store historical data for chart
        this.historicalData.push({
          timestamp: new Date().toISOString(),
          cpu: this.healthData.cpu.usage_percent,
          memory: this.healthData.memory.percent,
          disk: this.healthData.disk.percent
        });
        
        // Keep only last 20 data points
        if (this.historicalData.length > 20) {
          this.historicalData = this.historicalData.slice(-20);
        }
        
        this.$nextTick(() => this.renderTrendsChart());
      } catch (error) {
        console.error('Failed to load health data:', error);
      } finally {
        this.loading = false;
      }
    },
    renderTrendsChart() {
      if (this.trendsChart) this.trendsChart.destroy();
      if (!this.historicalData.length) return;
      
      const ctx = this.$refs.trendsChart.getContext('2d');
      this.trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: this.historicalData.map(d => new Date(d.timestamp).toLocaleTimeString('zh-TW')),
          datasets: [
            {
              label: 'CPU %',
              data: this.historicalData.map(d => d.cpu),
              borderColor: '#e74c3c',
              tension: 0.3
            },
            {
              label: 'Memory %',
              data: this.historicalData.map(d => d.memory),
              borderColor: '#3498db',
              tension: 0.3
            },
            {
              label: 'Disk %',
              data: this.historicalData.map(d => d.disk),
              borderColor: '#f39c12',
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          plugins: { legend: { position: 'top' } },
          scales: {
            y: { 
              beginAtZero: true,
              max: 100,
              ticks: { callback: v => v + '%' }
            }
          }
        }
      });
    },
    getGaugeColor(value) {
      if (value >= 90) return '#e74c3c';
      if (value >= 70) return '#f39c12';
      return '#2ecc71';
    },
    getGaugeDashArray(value) {
      const circumference = Math.PI * 40; // Half circle
      return `${(value / 100) * circumference} ${circumference}`;
    },
    getWireGuardStatusText(status) {
      const statusMap = {
        'active': '運行中',
        'inactive': '未運行',
        'not_installed': '未安裝'
      };
      return statusMap[status] || status;
    },
    formatBytes(bytes) {
      if (!bytes) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  }
};
</script>

<style scoped>
.system-health-container {
  max-width: 1200px;
  margin: 0 auto;
}

.controls {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.last-updated {
  color: #666;
  font-size: 14px;
}

.loading, .no-data {
  text-align: center;
  padding: 40px;
  color: #666;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.metric-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.metric-icon {
  font-size: 24px;
}

.metric-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.gauge-container {
  position: relative;
  text-align: center;
}

.gauge {
  width: 100%;
  max-width: 200px;
}

.gauge-value {
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  margin-top: -20px;
}

.metric-detail {
  text-align: center;
  color: #666;
  font-size: 14px;
  margin-top: 8px;
}

.big-number {
  font-size: 48px;
  font-weight: 700;
  color: #3498db;
  text-align: center;
}

.section {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  margin-bottom: 24px;
}

.section h2 {
  margin-bottom: 16px;
  font-size: 18px;
}

.wireguard-status .status-row {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  color: #666;
}

.status-value {
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 4px;
}

.status-value.active {
  background: #d4edda;
  color: #155724;
}

.status-value.inactive {
  background: #f8d7da;
  color: #721c24;
}

.status-value.not_installed {
  background: #fff3cd;
  color: #856404;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
}

.alert.warning {
  background: #fff3cd;
  border-left: 4px solid #ffc107;
}

.alert.critical {
  background: #f8d7da;
  border-left: 4px solid #dc3545;
}

.alert-icon {
  font-size: 20px;
}

.alert-message {
  font-weight: 500;
}

.no-alerts {
  text-align: center;
  padding: 24px;
  color: #28a745;
  font-size: 16px;
}

.chart-canvas {
  max-height: 300px;
}

.btn-primary {
  padding: 10px 20px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary:hover {
  background: #2980b9;
}
</style>

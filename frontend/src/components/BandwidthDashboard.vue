<template>
  <div class="bandwidth-dashboard">
    <div class="header">
      <h2>🚀 頻寬監控儀表板</h2>
      <div class="status">
        <span class="status-dot" :class="{ active: isConnected }"></span>
        <span>{{ isConnected ? '即時監控中' : '重新連線中...' }}</span>
        <span class="last-update">最後更新: {{ lastUpdate }}</span>
      </div>
    </div>

    <div class="gauges-container">
      <div class="gauge-card">
        <div class="gauge-header">
          <span class="gauge-icon">⬇️</span>
          <span class="gauge-label">下載頻寬</span>
        </div>
        <div class="gauge-value download">{{ formatBandwidth(currentDownload) }}</div>
        <div class="gauge-bar">
          <div 
            class="gauge-fill download" 
            :style="{ width: getGaugePercent(currentDownload, maxBandwidth) + '%' }"
          ></div>
        </div>
        <div class="gauge-max">最大: {{ formatBandwidth(maxBandwidth) }}</div>
      </div>

      <div class="gauge-card">
        <div class="gauge-header">
          <span class="gauge-icon">⬆️</span>
          <span class="gauge-label">上傳頻寬</span>
        </div>
        <div class="gauge-value upload">{{ formatBandwidth(currentUpload) }}</div>
        <div class="gauge-bar">
          <div 
            class="gauge-fill upload" 
            :style="{ width: getGaugePercent(currentUpload, maxBandwidth) + '%' }"
          ></div>
        </div>
        <div class="gauge-max">最大: {{ formatBandwidth(maxBandwidth) }}</div>
      </div>
    </div>

    <div class="speed-indicators">
      <div class="speed-card">
        <div class="speed-icon">⚡</div>
        <div class="speed-content">
          <div class="speed-label">當前速度</div>
          <div class="speed-value">{{ formatBandwidth(currentBandwidth) }}/s</div>
        </div>
      </div>
      <div class="speed-card peak">
        <div class="speed-icon">🏔️</div>
        <div class="speed-content">
          <div class="speed-label">峰值下載</div>
          <div class="speed-value">{{ formatBandwidth(peakDownload) }}/s</div>
        </div>
      </div>
      <div class="speed-card peak">
        <div class="speed-icon">🎯</div>
        <div class="speed-content">
          <div class="speed-label">峰值上傳</div>
          <div class="speed-value">{{ formatBandwidth(peakUpload) }}/s</div>
        </div>
      </div>
      <div class="speed-card">
        <div class="speed-icon">📊</div>
        <div class="speed-content">
          <div class="speed-label">平均速度</div>
          <div class="speed-value">{{ formatBandwidth(avgBandwidth) }}/s</div>
        </div>
      </div>
    </div>

    <div class="chart-section">
      <h3>頻寬趨勢 (近 5 分鐘)</h3>
      <div class="chart-container">
        <Line :data="chartData" :options="chartOptions" />
      </div>
    </div>

    <div class="auto-refresh-info">
      <span>🔄 自動刷新: {{ refreshInterval / 1000 }} 秒</span>
      <button @click="clearPeaks" class="clear-btn">清除峰值</button>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
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
  Title,
  Tooltip,
  Legend,
  Filler
);

export default {
  name: 'BandwidthDashboard',
  components: {
    Line
  },
  data() {
    return {
      isConnected: true,
      lastUpdate: '',
      refreshInterval: 2000,
      timer: null,
      
      // Current bandwidth (bytes per second)
      currentDownload: 0,
      currentUpload: 0,
      currentBandwidth: 0,
      
      // Previous values for calculating bandwidth
      prevTotalReceived: 0,
      prevTotalSent: 0,
      prevTimestamp: null,
      
      // Peak values
      peakDownload: 0,
      peakUpload: 0,
      
      // Calculated average
      avgBandwidth: 0,
      bandwidthSamples: [],
      
      // For chart
      chartLabels: [],
      downloadData: [],
      uploadData: [],
      maxDataPoints: 30,
      
      maxBandwidth: 10 * 1024 * 1024, // 10 MB/s default max for gauge
      
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
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => this.formatBandwidth(value) + '/s'
            }
          }
        },
        animation: {
          duration: 300
        }
      }
    };
  },
  mounted() {
    this.fetchTraffic();
    this.startAutoRefresh();
  },
  beforeUnmount() {
    this.stopAutoRefresh();
  },
  methods: {
    async fetchTraffic() {
      try {
        const response = await axios.get('/api/traffic');
        const data = response.data;
        
        const now = new Date();
        const totalReceived = data.total_received || 0;
        const totalSent = data.total_sent || 0;
        
        // Calculate bandwidth if we have previous data
        if (this.prevTimestamp) {
          const timeDiff = (now - this.prevTimestamp) / 1000; // seconds
          
          if (timeDiff > 0) {
            // Calculate bytes per second
            const downloadRate = (totalReceived - this.prevTotalReceived) / timeDiff;
            const uploadRate = (totalSent - this.prevTotalSent) / timeDiff;
            
            // Update current bandwidth (use absolute values)
            this.currentDownload = Math.max(0, downloadRate);
            this.currentUpload = Math.max(0, uploadRate);
            this.currentBandwidth = this.currentDownload + this.currentUpload;
            
            // Update peaks
            if (this.currentDownload > this.peakDownload) {
              this.peakDownload = this.currentDownload;
            }
            if (this.currentUpload > this.peakUpload) {
              this.peakUpload = this.currentUpload;
            }
            
            // Add to samples for average calculation
            this.bandwidthSamples.push(this.currentBandwidth);
            if (this.bandwidthSamples.length > 30) {
              this.bandwidthSamples.shift();
            }
            this.avgBandwidth = this.bandwidthSamples.reduce((a, b) => a + b, 0) / this.bandwidthSamples.length;
            
            // Update chart data
            this.updateChart();
            
            // Update max bandwidth for gauge scaling
            const maxCurrent = Math.max(this.currentDownload, this.currentUpload, this.peakDownload, this.peakUpload);
            if (maxCurrent > this.maxBandwidth * 0.8) {
              this.maxBandwidth = maxCurrent * 1.2;
            }
          }
        }
        
        // Store current values for next calculation
        this.prevTotalReceived = totalReceived;
        this.prevTotalSent = totalSent;
        this.prevTimestamp = now;
        
        this.lastUpdate = now.toLocaleTimeString('zh-TW');
        this.isConnected = true;
        
      } catch (error) {
        console.error('Failed to fetch traffic data:', error);
        this.isConnected = false;
      }
    },
    updateChart() {
      const timeLabel = new Date().toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
      
      // Add new data point
      this.chartLabels.push(timeLabel);
      this.downloadData.push(this.currentDownload);
      this.uploadData.push(this.currentUpload);
      
      // Remove old data points
      if (this.chartLabels.length > this.maxDataPoints) {
        this.chartLabels.shift();
        this.downloadData.shift();
        this.uploadData.shift();
      }
      
      this.chartData = {
        labels: [...this.chartLabels],
        datasets: [
          {
            label: '下載速度',
            data: [...this.downloadData],
            borderColor: '#3498db',
            backgroundColor: 'rgba(52, 152, 219, 0.2)',
            fill: true,
            tension: 0.3
          },
          {
            label: '上傳速度',
            data: [...this.uploadData],
            borderColor: '#e67e22',
            backgroundColor: 'rgba(230, 126, 34, 0.2)',
            fill: true,
            tension: 0.3
          }
        ]
      };
    },
    startAutoRefresh() {
      this.timer = setInterval(() => {
        this.fetchTraffic();
      }, this.refreshInterval);
    },
    stopAutoRefresh() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },
    clearPeaks() {
      this.peakDownload = 0;
      this.peakUpload = 0;
      this.bandwidthSamples = [];
      this.avgBandwidth = 0;
    },
    formatBandwidth(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB'];
      let i = 0;
      while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
      }
      return `${bytes.toFixed(2)} ${units[i]}`;
    },
    getGaugePercent(value, max) {
      if (!value || !max) return 0;
      return Math.min((value / max) * 100, 100);
    }
  }
};
</script>

<style scoped>
.bandwidth-dashboard {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h2 {
  margin: 0;
  color: #2c3e50;
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #e74c3c;
}

.status-dot.active {
  background-color: #27ae60;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.last-update {
  margin-left: 16px;
  color: #999;
}

.gauges-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.gauge-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.gauge-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.gauge-icon {
  font-size: 24px;
}

.gauge-label {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.gauge-value {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
}

.gauge-value.download {
  color: #3498db;
}

.gauge-value.upload {
  color: #e67e22;
}

.gauge-bar {
  height: 12px;
  background: #eee;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 8px;
}

.gauge-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.3s ease;
}

.gauge-fill.download {
  background: linear-gradient(90deg, #3498db, #2980b9);
}

.gauge-fill.upload {
  background: linear-gradient(90deg, #e67e22, #d35400);
}

.gauge-max {
  font-size: 12px;
  color: #999;
}

.speed-indicators {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.speed-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.speed-card.peak {
  border-left: 4px solid #9b59b6;
}

.speed-icon {
  font-size: 28px;
}

.speed-content {
  flex: 1;
}

.speed-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.speed-value {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.chart-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.chart-section h3 {
  margin: 0 0 16px 0;
  color: #2c3e50;
  font-size: 16px;
}

.chart-container {
  height: 250px;
}

.auto-refresh-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.clear-btn {
  padding: 6px 12px;
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #666;
  transition: background 0.2s;
}

.clear-btn:hover {
  background: #e0e0e0;
}
</style>

<template>
  <div class="traffic-dashboard">
    <div class="header">
      <h2>📊 即時流量監控</h2>
      <div class="status">
        <span class="status-dot" :class="{ active: isConnected }"></span>
        <span>{{ isConnected ? '連線中' : '重新連線中...' }}</span>
        <span class="last-update">最後更新: {{ lastUpdate }}</span>
      </div>
    </div>

    <div class="summary-cards">
      <div class="card total-received">
        <div class="card-icon">⬇️</div>
        <div class="card-content">
          <div class="card-label">總下載</div>
          <div class="card-value">{{ formatBytes(totalReceived) }}</div>
        </div>
      </div>
      <div class="card total-sent">
        <div class="card-icon">⬆️</div>
        <div class="card-content">
          <div class="card-label">總上傳</div>
          <div class="card-value">{{ formatBytes(totalSent) }}</div>
        </div>
      </div>
      <div class="card peer-count">
        <div class="card-icon">👥</div>
        <div class="card-content">
          <div class="card-label">在線用戶</div>
          <div class="card-value">{{ peers.length }}</div>
        </div>
      </div>
    </div>

    <div class="peers-table-container">
      <table class="peers-table">
        <thead>
          <tr>
            <th>用戶</th>
            <th>下載</th>
            <th>上傳</th>
            <th>Public Key</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="peer in peers" :key="peer.public_key">
            <td class="username">{{ peer.username || '未知' }}</td>
            <td class="download">
              <span class="bytes">{{ formatBytes(peer.bytes_received) }}</span>
              <div class="progress-bar">
                <div 
                  class="progress-fill received" 
                  :style="{ width: getProgressWidth(peer.bytes_received) + '%' }"
                ></div>
              </div>
            </td>
            <td class="upload">
              <span class="bytes">{{ formatBytes(peer.bytes_sent) }}</span>
              <div class="progress-bar">
                <div 
                  class="progress-fill sent" 
                  :style="{ width: getProgressWidth(peer.bytes_sent) + '%' }"
                ></div>
              </div>
            </td>
            <td class="public-key">{{ peer.public_key.substring(0, 16) }}...</td>
          </tr>
          <tr v-if="peers.length === 0">
            <td colspan="4" class="no-data">目前沒有在線的用戶</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="auto-refresh-info">
      <span>🔄 自動刷新: {{ refreshInterval / 1000 }} 秒</span>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'TrafficDashboard',
  data() {
    return {
      peers: [],
      totalReceived: 0,
      totalSent: 0,
      lastUpdate: '',
      isConnected: true,
      refreshInterval: 5000,
      maxBytes: 100 * 1024 * 1024, // 100MB for progress bar scale
      timer: null
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
        
        this.peers = data.peers || [];
        this.totalReceived = data.total_received || 0;
        this.totalSent = data.total_sent || 0;
        this.lastUpdate = new Date(data.timestamp).toLocaleTimeString('zh-TW');
        this.isConnected = true;
        
        // Update maxBytes for better progress bar scaling
        const maxPeerBytes = Math.max(
          ...this.peers.map(p => Math.max(p.bytes_received || 0, p.bytes_sent || 0)),
          this.maxBytes
        );
        this.maxBytes = maxPeerBytes;
        
      } catch (error) {
        console.error('Failed to fetch traffic data:', error);
        this.isConnected = false;
      }
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
    getProgressWidth(bytes) {
      if (!bytes) return 0;
      return Math.min((bytes / this.maxBytes) * 100, 100);
    }
  }
};
</script>

<style scoped>
.traffic-dashboard {
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
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s;
}

.card:hover {
  transform: translateY(-2px);
}

.card-icon {
  font-size: 32px;
}

.card-content {
  flex: 1;
}

.card-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.total-received {
  border-left: 4px solid #3498db;
}

.total-sent {
  border-left: 4px solid #e67e22;
}

.peer-count {
  border-left: 4px solid #9b59b6;
}

.peers-table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.peers-table {
  width: 100%;
  border-collapse: collapse;
}

.peers-table th {
  background: #f8f9fa;
  padding: 16px;
  text-align: left;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #eee;
}

.peers-table td {
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.peers-table tr:last-child td {
  border-bottom: none;
}

.peers-table tr:hover {
  background: #f8f9fa;
}

.username {
  font-weight: 500;
  color: #2c3e50;
}

.bytes {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 14px;
}

.download .bytes {
  color: #3498db;
}

.upload .bytes {
  color: #e67e22;
}

.progress-bar {
  width: 100px;
  height: 6px;
  background: #eee;
  border-radius: 3px;
  margin-top: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-fill.received {
  background: linear-gradient(90deg, #3498db, #2980b9);
}

.progress-fill.sent {
  background: linear-gradient(90deg, #e67e22, #d35400);
}

.public-key {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #999;
}

.no-data {
  text-align: center;
  color: #999;
  padding: 40px !important;
}

.auto-refresh-info {
  text-align: center;
  margin-top: 16px;
  color: #999;
  font-size: 14px;
}
</style>

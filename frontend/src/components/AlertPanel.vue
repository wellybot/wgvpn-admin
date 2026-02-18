<template>
  <div class="alert-panel">
    <div class="header">
      <h2>🔔 流量異常警示</h2>
      <div class="controls">
        <button @click="fetchAlerts" class="refresh-btn">🔄 重新整理</button>
        <button @click="checkAnomalies" class="check-btn">🔍 檢測異常</button>
      </div>
    </div>

    <div class="alert-filters">
      <label>
        <input type="checkbox" v-model="showResolved" @change="fetchAlerts">
        顯示已解決
      </label>
      <select v-model="severityFilter" @change="fetchAlerts">
        <option value="">全部嚴重程度</option>
        <option value="critical">嚴重</option>
        <option value="warning">警告</option>
        <option value="info">資訊</option>
      </select>
    </div>

    <div v-if="unresolvedAlerts.length > 0" class="unresolved-banner">
      <span class="banner-icon">⚠️</span>
      <span>有 {{ unresolvedAlerts.length }} 個未解決的警示</span>
    </div>

    <div class="alerts-container">
      <div 
        v-for="alert in filteredAlerts" 
        :key="alert.id" 
        class="alert-card"
        :class="[alert.severity, { resolved: alert.is_resolved }]"
      >
        <div class="alert-header">
          <span class="alert-icon">{{ getAlertIcon(alert.alert_type) }}</span>
          <span class="alert-type">{{ getAlertTypeName(alert.alert_type) }}</span>
          <span class="alert-severity" :class="alert.severity">
            {{ getSeverityName(alert.severity) }}
          </span>
        </div>
        
        <div class="alert-message">{{ alert.message }}</div>
        
        <div class="alert-details" v-if="alert.threshold_value || alert.actual_value">
          <span v-if="alert.threshold_value">
            閾值: {{ formatBytes(alert.threshold_value) }}
          </span>
          <span v-if="alert.actual_value">
            實際: {{ formatBytes(alert.actual_value) }}
          </span>
        </div>
        
        <div class="alert-footer">
          <span class="alert-time">
            {{ formatDateTime(alert.created_at) }}
          </span>
          <span v-if="alert.username" class="alert-user">
            用戶: {{ alert.username }}
          </span>
          <button 
            v-if="!alert.is_resolved" 
            @click="resolveAlert(alert.id)"
            class="resolve-btn"
          >
            標記為已解決
          </button>
          <span v-else class="resolved-badge">✓ 已解決</span>
        </div>
      </div>

      <div v-if="filteredAlerts.length === 0" class="no-alerts">
        <span class="no-alerts-icon">✅</span>
        <p>目前沒有警示記錄</p>
        <p class="hint">點擊「檢測異常」來手動檢查流量異常</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AlertPanel',
  data() {
    return {
      alerts: [],
      unresolvedAlerts: [],
      showResolved: false,
      severityFilter: '',
      refreshInterval: 10000,
      timer: null
    };
  },
  computed: {
    filteredAlerts() {
      let filtered = this.alerts;
      
      if (!this.showResolved) {
        filtered = filtered.filter(a => !a.is_resolved);
      }
      
      if (this.severityFilter) {
        filtered = filtered.filter(a => a.severity === this.severityFilter);
      }
      
      return filtered;
    }
  },
  mounted() {
    this.fetchAlerts();
    this.fetchUnresolved();
    this.startAutoRefresh();
  },
  beforeUnmount() {
    this.stopAutoRefresh();
  },
  methods: {
    async fetchAlerts() {
      try {
        const params = new URLSearchParams();
        if (this.showResolved) {
          // Fetch all including resolved
        }
        
        const response = await axios.get('/api/alerts');
        this.alerts = response.data.alerts || [];
      } catch (error) {
        console.error('Failed to fetch alerts:', error);
      }
    },
    async fetchUnresolved() {
      try {
        const response = await axios.get('/api/alerts/unresolved');
        this.unresolvedAlerts = response.data.alerts || [];
      } catch (error) {
        console.error('Failed to fetch unresolved alerts:', error);
      }
    },
    async resolveAlert(alertId) {
      try {
        await axios.post(`/api/alerts/${alertId}/resolve`);
        // Update local state
        const alert = this.alerts.find(a => a.id === alertId);
        if (alert) {
          alert.is_resolved = 1;
          alert.resolved_at = new Date().toISOString();
        }
        this.fetchUnresolved();
      } catch (error) {
        console.error('Failed to resolve alert:', error);
      }
    },
    async checkAnomalies() {
      try {
        const response = await axios.post('/api/alerts/check');
        if (response.data.new_alerts > 0) {
          this.fetchAlerts();
          this.fetchUnresolved();
        }
        alert(`異常檢測完成！新增 ${response.data.new_alerts} 個警示`);
      } catch (error) {
        console.error('Failed to check anomalies:', error);
      }
    },
    startAutoRefresh() {
      this.timer = setInterval(() => {
        this.fetchAlerts();
        this.fetchUnresolved();
      }, this.refreshInterval);
    },
    stopAutoRefresh() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },
    getAlertIcon(alertType) {
      const icons = {
        'traffic_spike': '📈',
        'high_bandwidth': '⚡',
        'unusual_pattern': '🔄',
        'connection_drop': '🔌',
        'security': '🔒'
      };
      return icons[alertType] || '⚠️';
    },
    getAlertTypeName(alertType) {
      const names = {
        'traffic_spike': '流量突增',
        'high_bandwidth': '高頻寬使用',
        'unusual_pattern': '異常模式',
        'connection_drop': '連線中斷',
        'security': '安全警示'
      };
      return names[alertType] || alertType;
    },
    getSeverityName(severity) {
      const names = {
        'critical': '嚴重',
        'warning': '警告',
        'info': '資訊'
      };
      return names[severity] || severity;
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
        year: 'numeric',
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
.alert-panel {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  color: #2c3e50;
}

.controls {
  display: flex;
  gap: 8px;
}

.refresh-btn, .check-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.refresh-btn {
  background: #f0f0f0;
  color: #666;
}

.refresh-btn:hover {
  background: #e0e0e0;
}

.check-btn {
  background: #3498db;
  color: white;
}

.check-btn:hover {
  background: #2980b9;
}

.alert-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.alert-filters label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
}

.alert-filters select {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.unresolved-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  margin-bottom: 20px;
  color: #856404;
}

.banner-icon {
  font-size: 20px;
}

.alerts-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-left: 4px solid #ddd;
  transition: transform 0.2s;
}

.alert-card:hover {
  transform: translateX(4px);
}

.alert-card.critical {
  border-left-color: #e74c3c;
}

.alert-card.warning {
  border-left-color: #f39c12;
}

.alert-card.info {
  border-left-color: #3498db;
}

.alert-card.resolved {
  opacity: 0.6;
  background: #f8f9fa;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.alert-icon {
  font-size: 18px;
}

.alert-type {
  font-weight: 600;
  color: #2c3e50;
  flex: 1;
}

.alert-severity {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.alert-severity.critical {
  background: #fadbd8;
  color: #c0392b;
}

.alert-severity.warning {
  background: #fdebd0;
  color: #d68910;
}

.alert-severity.info {
  background: #d4e6f1;
  color: #2980b9;
}

.alert-message {
  color: #555;
  font-size: 14px;
  margin-bottom: 8px;
}

.alert-details {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 6px;
}

.alert-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.alert-user {
  color: #666;
}

.resolve-btn {
  margin-left: auto;
  padding: 4px 12px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.resolve-btn:hover {
  background: #219a52;
}

.resolved-badge {
  margin-left: auto;
  color: #27ae60;
  font-weight: 500;
}

.no-alerts {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.no-alerts-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.no-alerts p {
  color: #666;
  margin: 8px 0;
}

.no-alerts .hint {
  font-size: 14px;
  color: #999;
}
</style>

<template>
  <div class="log-stream">
    <div class="stream-header">
      <h2>📡 即時日誌串流</h2>
      <div class="stream-controls">
        <button 
          class="btn" 
          :class="isPaused ? 'btn-success' : 'btn-warning'"
          @click="togglePause"
        >
          {{ isPaused ? '▶ 繼續' : '⏸ 暫停' }}
        </button>
        <button class="btn btn-secondary" @click="clearLogs">
          🗑 清除
        </button>
        <button class="btn btn-primary" @click="reconnect">
          🔄 重新連線
        </button>
      </div>
    </div>

    <!-- Connection Status -->
    <div class="connection-status" :class="connectionStatus">
      <span class="status-indicator"></span>
      <span>{{ connectionStatusText }}</span>
    </div>

    <!-- Log Display -->
    <div class="log-display" ref="logContainer">
      <div 
        v-for="(log, index) in logs" 
        :key="index" 
        class="log-entry"
        :class="getLogClass(log)"
      >
        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        <span class="log-type" :class="getTypeClass(log.log_type)">
          {{ getTypeLabel(log.log_type) }}
        </span>
        <span class="log-level" :class="getLevelClass(log.level)">
          {{ log.level?.toUpperCase() || 'INFO' }}
        </span>
        <span class="log-user">{{ log.username || 'System' }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      
      <div v-if="logs.length === 0" class="no-logs">
        <p v-if="connected">等待日誌資料...</p>
        <p v-else>正在連線至日誌串流...</p>
      </div>
    </div>

    <!-- Stats -->
    <div class="stream-stats">
      <div class="stat">
        <span class="stat-label">總日誌數</span>
        <span class="stat-value">{{ logs.length }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">資訊</span>
        <span class="stat-value info">{{ infoCount }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">警告</span>
        <span class="stat-value warning">{{ warningCount }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">錯誤</span>
        <span class="stat-value error">{{ errorCount }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogStream',
  data() {
    return {
      logs: [],
      connected: false,
      isPaused: false,
      ws: null,
      reconnectTimer: null
    }
  },
  computed: {
    connectionStatus() {
      if (this.connected) return 'connected'
      return 'disconnected'
    },
    connectionStatusText() {
      if (this.connected) return '已連線 - 接收即時日誌'
      return '未連線'
    },
    infoCount() {
      return this.logs.filter(l => (l.level || 'info') === 'info').length
    },
    warningCount() {
      return this.logs.filter(l => l.level === 'warning').length
    },
    errorCount() {
      return this.logs.filter(l => l.level === 'error').length
    }
  },
  mounted() {
    this.connect()
  },
  beforeUnmount() {
    this.disconnect()
  },
  methods: {
    connect() {
      if (this.ws) {
        this.ws.close()
      }
      
      const wsUrl = 'ws://localhost:8000/api/logs/stream'
      
      try {
        this.ws = new WebSocket(wsUrl)
        
        this.ws.onopen = () => {
          this.connected = true
          console.log('WebSocket connected')
        }
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            
            if (data.type === 'connected') {
              console.log('Log stream started:', data.message)
            } else if (data.type === 'log') {
              if (!this.isPaused) {
                this.addLog(data)
              }
            }
          } catch (e) {
            console.error('Failed to parse log:', e)
          }
        }
        
        this.ws.onclose = () => {
          this.connected = false
          console.log('WebSocket disconnected')
          // Auto reconnect after 5 seconds
          this.reconnectTimer = setTimeout(() => {
            this.connect()
          }, 5000)
        }
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
        }
        
      } catch (error) {
        console.error('Failed to connect:', error)
        this.connected = false
      }
    },
    
    disconnect() {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
      }
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
    },
    
    reconnect() {
      this.disconnect()
      setTimeout(() => {
        this.connect()
      }, 1000)
    },
    
    addLog(log) {
      this.logs.unshift(log)
      
      // Keep only last 500 logs in memory
      if (this.logs.length > 500) {
        this.logs.pop()
      }
      
      // Auto-scroll to top if not paused
      if (!this.isPaused) {
        this.$nextTick(() => {
          const container = this.$refs.logContainer
          if (container) {
            container.scrollTop = 0
          }
        })
      }
    },
    
    togglePause() {
      this.isPaused = !this.isPaused
    },
    
    clearLogs() {
      this.logs = []
    },
    
    formatTime(timestamp) {
      if (!timestamp) return '--:--:--'
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-TW', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    },
    
    getTypeLabel(type) {
      const labels = {
        connection: '連線',
        traffic: '流量',
        alert: '警示',
        audit: '審計'
      }
      return labels[type] || type || '日誌'
    },
    
    getTypeClass(type) {
      return `type-${type || 'default'}`
    },
    
    getLevelClass(level) {
      return `level-${level || 'info'}`
    },
    
    getLogClass(log) {
      return {
        'log-info': (log.level || 'info') === 'info',
        'log-warning': log.level === 'warning',
        'log-error': log.level === 'error'
      }
    }
  }
}
</script>

<style scoped>
.log-stream {
  max-width: 1400px;
  margin: 0 auto;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stream-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.stream-controls {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover {
  background: #2980b9;
}

.btn-secondary {
  background: #ecf0f1;
  color: #666;
}

.btn-secondary:hover {
  background: #dfe6e9;
}

.btn-success {
  background: #27ae60;
  color: white;
}

.btn-success:hover {
  background: #219a52;
}

.btn-warning {
  background: #f39c12;
  color: white;
}

.btn-warning:hover {
  background: #e67e22;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 500;
}

.connection-status.connected {
  background: #e8f5e9;
  color: #2e7d32;
}

.connection-status.disconnected {
  background: #ffebee;
  color: #c62828;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.connected .status-indicator {
  background: #27ae60;
}

.disconnected .status-indicator {
  background: #c62828;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.log-display {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 16px;
  height: 500px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  color: #d4d4d4;
}

.log-entry:hover {
  background: #2d2d2d;
}

.log-time {
  color: #6a9955;
  white-space: nowrap;
}

.log-type {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.type-connection {
  background: #264f78;
  color: #9cdcfe;
}

.type-traffic {
  background: #3a3d41;
  color: #ce9178;
}

.type-alert {
  background: #5c3a1e;
  color: #dcdcaa;
}

.type-audit {
  background: #3a3a6e;
  color: #c586c0;
}

.type-default {
  background: #3a3a3a;
  color: #cccccc;
}

.log-level {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  min-width: 50px;
  text-align: center;
}

.level-info {
  background: #1e3a1e;
  color: #6a9955;
}

.level-warning {
  background: #3a3a1e;
  color: #dcdcaa;
}

.level-error {
  background: #3a1e1e;
  color: #f48771;
}

.log-user {
  color: #569cd6;
  white-space: nowrap;
  min-width: 100px;
}

.log-message {
  color: #d4d4d4;
  word-break: break-word;
}

.log-info {
  border-left: 3px solid #6a9955;
}

.log-warning {
  border-left: 3px solid #dcdcaa;
}

.log-error {
  border-left: 3px solid #f48771;
}

.no-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.stream-stats {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #888;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.stat-value.info {
  color: #3498db;
}

.stat-value.warning {
  color: #f39c12;
}

.stat-value.error {
  color: #e74c3c;
}
</style>

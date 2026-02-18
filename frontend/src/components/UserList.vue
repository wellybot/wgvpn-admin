<template>
  <div class="user-list">
    <div class="page-header">
      <h1>👥 用戶管理</h1>
      <button class="btn-primary" @click="showCreateModal = true">
        + 新增用戶
      </button>
    </div>
    
    <!-- Search and Filters -->
    <div class="filters">
      <input
        v-model="search"
        type="text"
        placeholder="搜尋用戶名或Email..."
        class="search-input"
        @input="debouncedSearch"
      />
      <select v-model="filterActive" @change="loadUsers" class="filter-select">
        <option :value="null">全部狀態</option>
        <option :value="true">已啟用</option>
        <option :value="false">已停用</option>
      </select>
    </div>
    
    <!-- User Table -->
    <div class="table-container">
      <table class="user-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用戶名</th>
            <th>Email</th>
            <th>Public Key</th>
            <th>狀態</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td class="key-cell" :title="user.public_key">
              {{ user.public_key ? user.public_key.substring(0, 16) + '...' : '-' }}
            </td>
            <td>
              <span :class="['status-badge', user.is_active ? 'active' : 'inactive']">
                {{ user.is_active ? '啟用' : '停用' }}
              </span>
            </td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td class="actions">
              <button class="btn-icon" @click="viewUser(user)" title="查看">
                👁️
              </button>
              <button class="btn-icon" @click="editUser(user)" title="編輯">
                ✏️
              </button>
              <button 
                class="btn-icon" 
                @click="toggleActive(user)" 
                :title="user.is_active ? '停用' : '啟用'"
                :disabled="user.id === currentUserId"
              >
                {{ user.is_active ? '⏸️' : '▶️' }}
              </button>
              <button class="btn-icon" @click="showPasswordModal(user)" title="更改密碼">
                🔑
              </button>
              <button 
                class="btn-icon btn-danger" 
                @click="confirmDelete(user)"
                title="刪除"
                :disabled="user.id === currentUserId"
              >
                🗑️
              </button>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="7" class="empty-row">沒有找到用戶</td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1">
      <button 
        @click="changePage(page - 1)" 
        :disabled="page === 1"
        class="page-btn"
      >
        上一頁
      </button>
      <span class="page-info">第 {{ page }} / {{ totalPages }} 頁</span>
      <button 
        @click="changePage(page + 1)" 
        :disabled="page === totalPages"
        class="page-btn"
      >
        下一頁
      </button>
    </div>
    
    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ showCreateModal ? '新增用戶' : '編輯用戶' }}</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        
        <form @submit.prevent="submitForm" class="modal-form">
          <div class="form-group">
            <label>用戶名</label>
            <input v-model="formData.username" type="text" required />
          </div>
          
          <div class="form-group">
            <label>Email</label>
            <input v-model="formData.email" type="email" required />
          </div>
          
          <div class="form-group" v-if="showCreateModal">
            <label>密碼</label>
            <input v-model="formData.password" type="password" required />
          </div>
          
          <div class="form-group">
            <label>允許的 IP (Allowed IPs)</label>
            <input v-model="formData.allowed_ips" type="text" placeholder="10.0.0.2/32" />
          </div>
          
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? '儲存中...' : '儲存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- User Detail Modal -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal modal-large">
        <div class="modal-header">
          <h2>用戶詳情 - {{ selectedUser.username }}</h2>
          <button class="close-btn" @click="showDetailModal = false">×</button>
        </div>
        
        <div class="user-detail">
          <div class="detail-row">
            <span class="detail-label">ID:</span>
            <span>{{ selectedUser.id }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">用戶名:</span>
            <span>{{ selectedUser.username }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Email:</span>
            <span>{{ selectedUser.email }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">狀態:</span>
            <span :class="['status-badge', selectedUser.is_active ? 'active' : 'inactive']">
              {{ selectedUser.is_active ? '啟用' : '停用' }}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Public Key:</span>
            <code>{{ selectedUser.public_key || '-' }}</code>
          </div>
          <div class="detail-row">
            <span class="detail-label">Allowed IPs:</span>
            <span>{{ selectedUser.allowed_ips || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">建立時間:</span>
            <span>{{ formatDate(selectedUser.created_at) }}</span>
          </div>
          
          <div class="detail-actions">
            <button class="btn-primary" @click="generateConfig(selectedUser)">
              🔄 產生新設定
            </button>
            <button 
              v-if="selectedUser.public_key" 
              class="btn-secondary"
              @click="downloadConfig(selectedUser)"
            >
              📥 下載設定
            </button>
            <button 
              v-if="selectedUser.public_key" 
              class="btn-secondary"
              @click="showQRCode(selectedUser)"
            >
              📱 QR Code
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h2>確認刪除</h2>
          <button class="close-btn" @click="showDeleteModal = false">×</button>
        </div>
        
        <div class="modal-body">
          <p>確定要刪除用戶 <strong>{{ userToDelete?.username }}</strong> 嗎？</p>
          <p class="warning">此操作無法復原！</p>
        </div>
        
        <div class="modal-actions">
          <button class="btn-secondary" @click="showDeleteModal = false">取消</button>
          <button class="btn-danger" @click="deleteUser" :disabled="deleting">
            {{ deleting ? '刪除中...' : '確認刪除' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Change Password Modal -->
    <div v-if="showPasswordModalFlag" class="modal-overlay" @click.self="showPasswordModalFlag = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h2>更改密碼 - {{ passwordUser?.username }}</h2>
          <button class="close-btn" @click="showPasswordModalFlag = false">×</button>
        </div>
        
        <form @submit.prevent="changePassword" class="modal-form">
          <div class="form-group">
            <label>當前密碼</label>
            <input v-model="passwordData.old_password" type="password" required />
          </div>
          
          <div class="form-group">
            <label>新密碼</label>
            <input v-model="passwordData.new_password" type="password" required minlength="6" />
          </div>
          
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showPasswordModalFlag = false">取消</button>
            <button type="submit" class="btn-primary" :disabled="changingPassword">
              {{ changingPassword ? '更改中...' : '更改密碼' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    
    <!-- QR Code Modal -->
    <div v-if="showQRModal" class="modal-overlay" @click.self="showQRModal = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h2>QR Code - {{ qrUser?.username }}</h2>
          <button class="close-btn" @click="showQRModal = false">×</button>
        </div>
        
        <div class="qr-display">
          <img :src="qrCode" alt="QR Code" />
          <p>使用 WireGuard App 掃描此 QR Code</p>
        </div>
        
        <div class="modal-actions">
          <button class="btn-secondary" @click="showQRModal = false">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserList',
  data() {
    return {
      users: [],
      page: 1,
      perPage: 20,
      total: 0,
      search: '',
      filterActive: null,
      
      // Modals
      showCreateModal: false,
      showEditModal: false,
      showDetailModal: false,
      showDeleteModal: false,
      showPasswordModalFlag: false,
      showQRModal: false,
      
      // Form data
      formData: {
        username: '',
        email: '',
        password: '',
        allowed_ips: '10.0.0.2/32'
      },
      selectedUser: null,
      userToDelete: null,
      
      // Password modal
      passwordUser: null,
      passwordData: {
        old_password: '',
        new_password: ''
      },
      
      // QR Code
      qrUser: null,
      qrCode: '',
      
      // States
      submitting: false,
      deleting: false,
      changingPassword: false,
      
      // Debounce timer
      searchTimer: null
    }
  },
  computed: {
    totalPages() {
      return Math.ceil(this.total / this.perPage)
    },
    currentUserId() {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      return user.id
    }
  },
  methods: {
    async loadUsers() {
      const token = localStorage.getItem('token')
      if (!token) {
        this.$router.push('/login')
        return
      }
      
      const params = new URLSearchParams({
        page: this.page,
        per_page: this.perPage
      })
      
      if (this.search) params.append('search', this.search)
      if (this.filterActive !== null) params.append('is_active', this.filterActive)
      
      try {
        const response = await fetch(`http://localhost:8000/api/users?${params}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.status === 401) {
          this.logout()
          return
        }
        
        const data = await response.json()
        this.users = data.users
        this.total = data.total
      } catch (err) {
        console.error('Failed to load users:', err)
      }
    },
    
    debouncedSearch() {
      clearTimeout(this.searchTimer)
      this.searchTimer = setTimeout(() => {
        this.page = 1
        this.loadUsers()
      }, 300)
    },
    
    changePage(newPage) {
      this.page = newPage
      this.loadUsers()
    },
    
    viewUser(user) {
      this.selectedUser = user
      this.showDetailModal = true
    },
    
    editUser(user) {
      this.selectedUser = user
      this.formData = {
        username: user.username,
        email: user.email,
        password: '',
        allowed_ips: user.allowed_ips || '10.0.0.2/32'
      }
      this.showEditModal = true
    },
    
    confirmDelete(user) {
      this.userToDelete = user
      this.showDeleteModal = true
    },
    
    async submitForm() {
      this.submitting = true
      
      const token = localStorage.getItem('token')
      
      try {
        if (this.showCreateModal) {
          const response = await fetch('http://localhost:8000/api/users', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(this.formData)
          })
          
          if (!response.ok) {
            const err = await response.json()
            throw new Error(err.detail)
          }
        } else {
          const response = await fetch(`http://localhost:8000/api/users/${this.selectedUser.id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              username: this.formData.username,
              email: this.formData.email,
              allowed_ips: this.formData.allowed_ips
            })
          })
          
          if (!response.ok) {
            const err = await response.json()
            throw new Error(err.detail)
          }
        }
        
        this.closeModal()
        this.loadUsers()
      } catch (err) {
        alert(err.message)
      } finally {
        this.submitting = false
      }
    },
    
    async deleteUser() {
      this.deleting = true
      
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch(`http://localhost:8000/api/users/${this.userToDelete.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail)
        }
        
        this.showDeleteModal = false
        this.loadUsers()
      } catch (err) {
        alert(err.message)
      } finally {
        this.deleting = false
      }
    },
    
    async toggleActive(user) {
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch(`http://localhost:8000/api/users/${user.id}/toggle-active`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail)
        }
        
        this.loadUsers()
      } catch (err) {
        alert(err.message)
      }
    },
    
    showPasswordModal(user) {
      this.passwordUser = user
      this.passwordData = { old_password: '', new_password: '' }
      this.showPasswordModalFlag = true
    },
    
    async changePassword() {
      this.changingPassword = true
      
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch(`http://localhost:8000/api/users/${this.passwordUser.id}/change-password`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(this.passwordData)
        })
        
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail)
        }
        
        alert('密碼已更改')
        this.showPasswordModalFlag = false
      } catch (err) {
        alert(err.message)
      } finally {
        this.changingPassword = false
      }
    },
    
    async generateConfig(user) {
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch(`http://localhost:8000/api/users/${user.id}/generate-config`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail)
        }
        
        const data = await response.json()
        alert(`設定已產生！\n\nPublic Key: ${data.public_key}\n\n請妥善保管私鑰，這是唯一一次顯示。`)
        
        // Refresh user data
        this.loadUsers()
      } catch (err) {
        alert(err.message)
      }
    },
    
    async downloadConfig(user) {
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch(`http://localhost:8000/api/users/${user.id}/config`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail)
        }
        
        const data = await response.json()
        
        // Download as file
        const blob = new Blob([data.config], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = data.filename
        a.click()
        URL.revokeObjectURL(url)
      } catch (err) {
        alert(err.message)
      }
    },
    
    async showQRCode(user) {
      const token = localStorage.getItem('token')
      
      try {
        const response = await fetch(`http://localhost:8000/api/users/${user.id}/qr`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail)
        }
        
        const data = await response.json()
        this.qrUser = user
        this.qrCode = data.qr_code
        this.showQRModal = true
      } catch (err) {
        alert(err.message)
      }
    },
    
    closeModal() {
      this.showCreateModal = false
      this.showEditModal = false
      this.formData = {
        username: '',
        email: '',
        password: '',
        allowed_ips: '10.0.0.2/32'
      }
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleString('zh-TW')
    },
    
    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      this.$router.push('/login')
    }
  },
  mounted() {
    this.loadUsers()
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  color: #2c3e50;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.filter-select {
  padding: 10px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  background: white;
}

.table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.user-table {
  width: 100%;
  border-collapse: collapse;
}

.user-table th,
.user-table td {
  padding: 14px 16px;
  text-align: left;
}

.user-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #555;
  font-size: 13px;
}

.user-table tr:not(:last-child) td {
  border-bottom: 1px solid #eee;
}

.key-cell {
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-badge.inactive {
  background: #ffebee;
  color: #c62828;
}

.actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  padding: 6px 8px;
  border: none;
  background: #f5f5f5;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-icon:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  background: #ffebee;
}

.btn-danger:hover:not(:disabled) {
  background: #ffcdd2;
}

.empty-row {
  text-align: center;
  color: #999;
  padding: 40px !important;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 6px;
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: #666;
  font-size: 14px;
}

.btn-primary {
  padding: 10px 20px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
}

.btn-secondary {
  padding: 10px 20px;
  background: #95a5a6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
}

.btn-danger-action {
  padding: 10px 20px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
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
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 600px;
}

.modal-small {
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  font-size: 18px;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.modal-form {
  padding: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #555;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.modal-body {
  padding: 24px;
}

.warning {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 8px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #eee;
}

/* User Detail */
.user-detail {
  padding: 24px;
}

.detail-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

.detail-label {
  width: 120px;
  color: #666;
  font-weight: 500;
}

.detail-row code {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

/* QR Code */
.qr-display {
  padding: 24px;
  text-align: center;
}

.qr-display img {
  max-width: 250px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.qr-display p {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}
</style>

# WireGuard VPN Admin

WireGuard VPN 管理系統 - 完整的前後端解決方案

![WireGuard](https://img.shields.io/badge/WireGuard-VPN-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Vue.js](https://img.shields.io/badge/Vue.js-3-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal)

## ✨ 功能特色

### 📊 流量監控 (Traffic Monitoring)
- 即時流量統計
- 流量使用歷史圖表
- 頻寬監控儀表板
- 流量異常警示

### 📝 用戶日誌 (User Logs)
- 連線記錄查詢
- 日誌搜尋與篩選
- 日誌匯出 (CSV/JSON)
- 即時日誌串流 (WebSocket)

### 👤 帳號管理 (Account Management)
- 用戶帳號 CRUD
- VPN 設定自動產生
- QR Code 下載
- 帳號啟用/停用
- JWT 認證

### 📋 稽查記錄 (Audit Records)
- 管理員操作日誌
- 登入紀錄追蹤
- 系統事件稽核
- 合規報告產生

### 📈 自動化報表 (Automated Reports)
- 定期流量報告
- 用戶使用統計
- 系統健康報告
- 自訂報告範本

## 🛠️ 技術棧

### Backend
- **FastAPI** - Python Web Framework
- **SQLite** - Database
- **PyJWT** - Authentication
- **WireGuard Tools** - VPN Management

### Frontend
- **Vue.js 3** - Frontend Framework
- **Vite** - Build Tool
- **Chart.js** - Charts
- **WebSocket** - Real-time Updates

## 📦 安裝

### 方式 1: 本地安裝

```bash
# Clone the repository
git clone https://github.com/wellybot/wgvpn-admin.git
cd wgvpn-admin

# Setup Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
sqlite3 wgvpn.db < ../schema.sql

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Setup Frontend (new terminal)
cd ../frontend
npm install
npm run dev
```

### 方式 2: Docker

```bash
# Build and run with Docker
cd docker
docker-compose up -d
```

## 🔐 預設帳號

首次啟動後，系統會建立預設管理員帳號：

- **帳號**: `admin`
- **密碼**: `admin123`

⚠️ **重要**: 請在首次登入後立即變更密碼！

## 🌐 存取位址

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📁 專案結構

```
wgvpn-admin/
├── backend/
│   ├── main.py          # FastAPI 主程式
│   ├── database.py      # 資料庫操作
│   ├── requirements.txt # Python 依賴
│   └── wgvpn.db         # SQLite 資料庫
├── frontend/
│   ├── src/             # Vue.js 原始碼
│   ├── package.json     # npm 依賴
│   └── vite.config.js   # Vite 設定
├── docker/
│   ├── Dockerfile       # Docker 映像
│   ├── docker-compose.yml
│   └── test-docker.sh   # 測試腳本
├── schema.sql           # 資料庫 schema
├── init.sh              # 啟動腳本
├── claude-progress.txt  # 開發進度記錄
└── feature_list.json    # 功能清單
```

## 🔧 WireGuard 設定

確保伺服器已安裝並設定 WireGuard：

```bash
# Install WireGuard
sudo apt install wireguard

# Generate keys
wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey

# Create config
sudo nano /etc/wireguard/wg0.conf

# Start WireGuard
sudo wg-quick up wg0
```

## 📖 API 文件

啟動 Backend 後，可存取：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要 API Endpoints

| Endpoint | 說明 |
|----------|------|
| `POST /api/auth/login` | 登入取得 JWT |
| `GET /api/traffic` | 即時流量統計 |
| `GET /api/users` | 用戶列表 |
| `GET /api/logs/connections` | 連線記錄 |
| `GET /api/audit/operations` | 操作日誌 |
| `GET /api/reports/health` | 系統健康 |

## 🧪 測試

```bash
# Docker 完整測試
cd docker
./test-docker.sh
```

## 📝 開發說明

本專案使用 **Anthropic Long-Running Agent Harness** 模式開發：

1. **Initializer Agent** - 建立專案結構和功能清單
2. **Coding Agents** - 逐功能實作、測試、提交

每個功能模組獨立開發，確保品質和可維護性。

## 📄 License

MIT License

## 🤝 貢獻

歡迎提交 Pull Request 或開 Issue！

---

Built with ❤️ using OpenClaw + Claude Code Agent Harness

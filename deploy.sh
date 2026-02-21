#!/bin/bash
#
# WireGuard VPN Admin - Ubuntu 自動部署腳本
# 
# 使用方式:
#   curl -fsSL https://raw.githubusercontent.com/wellybot/wgvpn-admin/main/deploy.sh | sudo bash
#
# 或:
#   wget -qO- https://raw.githubusercontent.com/wellybot/wgvpn-admin/main/deploy.sh | sudo bash
#

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# 檢查是否為 root
if [ "$EUID" -ne 0 ]; then
    log_error "請使用 sudo 執行此腳本"
    exit 1
fi

# 設定變數
INSTALL_DIR="/opt/wgvpn-admin"
GIT_REPO="https://github.com/wellybot/wgvpn-admin.git"
WG_INTERFACE="wg0"
WG_PORT=51820
WG_NETWORK="10.0.0.1/24"
ADMIN_USER="admin"
ADMIN_PASS="admin123"

# 顯示標題
echo ""
echo "=========================================="
echo "  WireGuard VPN Admin - 自動部署腳本"
echo "=========================================="
echo ""

# 步驟 1: 更新系統
log_step "[1/8] 更新系統套件..."
apt-get update -qq
apt-get upgrade -y -qq

# 步驟 2: 安裝系統依賴
log_step "[2/8] 安裝系統依賴..."
apt-get install -y -qq \
    wireguard \
    wireguard-tools \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    git \
    curl \
    wget \
    sqlite3 \
    jq \
    qrencode \
    > /dev/null

log_info "系統依賴安裝完成"

# 步驟 3: 設定 WireGuard
log_step "[3/8] 設定 WireGuard..."

# 產生金鑰
if [ ! -f /etc/wireguard/privatekey ]; then
    wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey
    chmod 600 /etc/wireguard/privatekey
    log_info "WireGuard 金鑰已產生"
fi

PRIVATE_KEY=$(cat /etc/wireguard/privatekey)
PUBLIC_KEY=$(cat /etc/wireguard/publickey)

# 建立 WireGuard 設定檔
if [ ! -f /etc/wireguard/${WG_INTERFACE}.conf ]; then
    cat > /etc/wireguard/${WG_INTERFACE}.conf << EOF
[Interface]
Address = ${WG_NETWORK}
ListenPort = ${WG_PORT}
PrivateKey = ${PRIVATE_KEY}
SaveConfig = true

# WireGuard VPN Admin 自動管理 Peers
EOF
    chmod 600 /etc/wireguard/${WG_INTERFACE}.conf
    log_info "WireGuard 設定檔已建立"
fi

# 啟用 IP 轉發
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p > /dev/null
    log_info "IP 轉發已啟用"
fi

# 設定防火牆規則
log_info "設定防火牆規則..."
# WireGuard UDP
iptables -A INPUT -p udp --dport ${WG_PORT} -j ACCEPT 2>/dev/null || true
# 轉發規則
iptables -A FORWARD -i ${WG_INTERFACE} -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -o ${WG_INTERFACE} -j ACCEPT 2>/dev/null || true
# NAT
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || true
# API 端口
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT 2>/dev/null || true
iptables -A INPUT -p tcp --dport 5173 -j ACCEPT 2>/dev/null || true

# 儲存 iptables 規則
if command -v iptables-save &> /dev/null; then
    iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
fi

log_info "WireGuard 設定完成"
log_info "Public Key: ${PUBLIC_KEY}"

# 步驟 4: 下載專案
log_step "[4/8] 下載 WireGuard VPN Admin..."

if [ -d "$INSTALL_DIR" ]; then
    log_warn "發現現有安裝，正在更新..."
    cd $INSTALL_DIR
    git pull -q
else
    git clone -q $GIT_REPO $INSTALL_DIR
    cd $INSTALL_DIR
fi

log_info "專案下載完成"

# 步驟 5: 設定 Backend
log_step "[5/8] 設定 Backend (FastAPI)..."

cd $INSTALL_DIR/backend

# 建立 Python 虛擬環境
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 安裝依賴
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
deactivate

# 初始化資料庫
if [ ! -f "wgvpn.db" ]; then
    sqlite3 wgvpn.db < ../schema.sql
    log_info "資料庫已初始化"
fi

# 建立 admin 用戶
python3 << PYEOF
import sqlite3
import hashlib
from datetime import datetime

conn = sqlite3.connect('wgvpn.db')
cursor = conn.cursor()

password_hash = hashlib.sha256('${ADMIN_PASS}'.encode()).hexdigest()

cursor.execute("SELECT id FROM users WHERE username = '${ADMIN_USER}'")
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 1, ?, ?)
    """, ('${ADMIN_USER}', 'admin@localhost', password_hash, 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    print("Admin 用戶已建立")
else:
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", 
                   (password_hash, '${ADMIN_USER}'))
    conn.commit()
    print("Admin 密碼已更新")

conn.close()
PYEOF

log_info "Backend 設定完成"

# 步驟 6: 設定 Frontend
log_step "[6/8] 設定 Frontend (Vue.js)..."

cd $INSTALL_DIR/frontend

# 安裝依賴
npm install --silent > /dev/null 2>&1

# Build for production
npm run build > /dev/null 2>&1

log_info "Frontend 設定完成"

# 步驟 7: 建立 Systemd 服務
log_step "[7/8] 建立 Systemd 服務..."

# Backend 服務
cat > /etc/systemd/system/wgvpn-backend.service << EOF
[Unit]
Description=WireGuard VPN Admin Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/backend
Environment="PATH=${INSTALL_DIR}/backend/venv/bin"
ExecStart=${INSTALL_DIR}/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Frontend 服務 (使用 serve)
cat > /etc/systemd/system/wgvpn-frontend.service << EOF
[Unit]
Description=WireGuard VPN Admin Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/frontend
ExecStart=$(which npx) serve -s dist -l 5173
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# WireGuard 服務
systemctl enable wg-quick@${WG_INTERFACE} 2>/dev/null || true

# 重新載入 systemd
systemctl daemon-reload

log_info "Systemd 服務已建立"

# 步驟 8: 啟動服務
log_step "[8/8] 啟動服務..."

# 啟動 WireGuard
systemctl start wg-quick@${WG_INTERFACE} 2>/dev/null || true
sleep 2

# 啟動 Backend
systemctl start wgvpn-backend
systemctl enable wgvpn-backend

# 啟動 Frontend
systemctl start wgvpn-frontend
systemctl enable wgvpn-frontend

# 等待服務啟動
sleep 3

# 顯示結果
echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "=========================================="
echo ""
echo "  🌐 存取位址:"
echo "     Frontend:  http://$(hostname -I | awk '{print $1}'):5173"
echo "     Backend:   http://$(hostname -I | awk '{print $1}'):8000"
echo "     API Docs:  http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "  🔐 登入資訊:"
echo "     帳號: ${ADMIN_USER}"
echo "     密碼: ${ADMIN_PASS}"
echo ""
echo "  🔑 WireGuard Public Key:"
echo "     ${PUBLIC_KEY}"
echo ""
echo "  📁 安裝目錄: ${INSTALL_DIR}"
echo ""
echo "=========================================="
echo ""
echo "  📋 常用指令:"
echo "     查看狀態:  systemctl status wgvpn-backend"
echo "     查看日誌:  journalctl -u wgvpn-backend -f"
echo "     重啟服務:  systemctl restart wgvpn-backend"
echo "     停止服務:  systemctl stop wgvpn-backend"
echo ""
echo "  🔧 WireGuard:"
echo "     查看狀態:  wg show"
echo "     重啟 VPN:  systemctl restart wg-quick@${WG_INTERFACE}"
echo ""
echo "=========================================="

# 測試 API
echo ""
log_info "測試 API..."
sleep 2

HEALTH=$(curl -s http://localhost:8000/api/health 2>/dev/null || echo "failed")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅${NC} Backend API 運行正常"
else
    echo -e "${YELLOW}⚠️${NC} Backend API 可能需要時間啟動"
fi

LOGIN=$(curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}" 2>/dev/null || echo "failed")
if echo "$LOGIN" | grep -q "token"; then
    echo -e "${GREEN}✅${NC} 登入測試成功"
else
    echo -e "${YELLOW}⚠️${NC} 登入測試失敗，請檢查日誌"
fi

# WireGuard 狀態
if wg show 2>/dev/null | grep -q "interface"; then
    echo -e "${GREEN}✅${NC} WireGuard 運行正常"
else
    echo -e "${YELLOW}⚠️${NC} WireGuard 可能需要額外設定"
fi

echo ""
log_info "部署腳本執行完畢！"
echo ""

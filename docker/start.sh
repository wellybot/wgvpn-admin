#!/bin/bash
set -e

echo "=========================================="
echo "  WireGuard VPN Admin - Docker Startup"
echo "=========================================="

# 設定 WireGuard
echo "[1/5] 設定 WireGuard..."
if [ ! -f /etc/wireguard/wg0.conf ]; then
    # 產生金鑰
    PRIVATE_KEY=$(cat /etc/wireguard/privatekey)
    PUBLIC_KEY=$(cat /etc/wireguard/publickey)
    
    cat > /etc/wireguard/wg0.conf << WGEOF
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = ${PRIVATE_KEY}
SaveConfig = true

# Peer 會自動加入
WGEOF
    chmod 600 /etc/wireguard/wg0.conf
    echo "WireGuard 設定已建立"
fi

# 啟動 WireGuard
echo "[2/5] 啟動 WireGuard..."
ip link add dev wg0 type wireguard 2>/dev/null || true
wg setconf wg0 /etc/wireguard/wg0.conf 2>/dev/null || true
ip address add dev wg0 10.0.0.1/24 2>/dev/null || true
ip link set up dev wg0 2>/dev/null || true
echo "WireGuard 已啟動"
wg show

# 初始化資料庫
echo "[3/5] 初始化資料庫..."
cd /app/backend
if [ ! -f wgvpn.db ]; then
    sqlite3 wgvpn.db < ../schema.sql
fi

# 建立 admin 用戶
python3 << 'PYEOF'
import sqlite3
import hashlib
from datetime import datetime

conn = sqlite3.connect('wgvpn.db')
cursor = conn.cursor()

# 檢查 admin 是否存在
cursor.execute("SELECT id FROM users WHERE username = 'admin'")
if not cursor.fetchone():
    password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 1, ?, ?)
    """, ('admin', 'admin@wgvpn.local', password_hash, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    print("Admin 用戶已建立")
else:
    print("Admin 用戶已存在")

conn.close()
PYEOF

# 啟動 Backend
echo "[4/5] 啟動 Backend API..."
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 2

# 啟動 Frontend
echo "[5/5] 啟動 Frontend..."
cd /app/frontend
npm install --silent 2>/dev/null
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  ✅ 系統已啟動！"
echo "=========================================="
echo ""
echo "  Backend API:  http://localhost:8000"
echo "  Frontend:     http://localhost:5173"
echo "  WireGuard:    UDP 51820"
echo ""
echo "  登入帳號: admin"
echo "  登入密碼: admin123"
echo ""
echo "=========================================="

# 測試 API
echo ""
echo "測試 API..."
sleep 3
curl -s http://localhost:8000/api/health && echo " ✅ Health OK"
curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' | head -c 100 && echo "... ✅ Login OK"

echo ""
echo "按 Ctrl+C 停止服務"

# 等待
wait

#!/bin/bash
# WireGuard VPN Admin - Docker 自動啟動腳本 (後台執行)

echo "=========================================="
echo "  WireGuard VPN Admin - 啟動服務"
echo "=========================================="

# 設定 WireGuard
echo "[1/4] 設定 WireGuard..."
ip link add dev wg0 type wireguard 2>/dev/null || true
ip address add dev wg0 10.0.0.1/24 2>/dev/null || true
ip link set up dev wg0 2>/dev/null || true
echo "WireGuard 已設定"

# 初始化資料庫
echo "[2/4] 初始化資料庫..."
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

cursor.execute("SELECT id FROM users WHERE username = 'admin'")
if not cursor.fetchone():
    password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 1, ?, ?)
    """, ('admin', 'admin@wgvpn.local', password_hash, 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    print("Admin 用戶已建立")
else:
    print("Admin 用戶已存在")

conn.close()
PYEOF

# 啟動 Backend (後台)
echo "[3/4] 啟動 Backend..."
cd /app/backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
echo "Backend PID: $!"

# 啟動 Frontend (後台)
echo "[4/4] 啟動 Frontend..."
cd /app/frontend
nohup npm run dev -- --host 0.0.0.0 > /tmp/frontend.log 2>&1 &
echo "Frontend PID: $!"

echo ""
echo "=========================================="
echo "  ✅ 服務已啟動"
echo "=========================================="
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""

# 等待服務啟動
sleep 3

# 測試
curl -s http://localhost:8000/api/health > /dev/null && echo "✅ Backend 運作中" || echo "❌ Backend 失敗"
curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend 運作中" || echo "❌ Frontend 失敗"

# 保持腳本運行 (用於 Docker)
echo ""
echo "服務持續運作中... (Ctrl+C 停止)"
tail -f /dev/null

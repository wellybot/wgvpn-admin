#!/bin/bash
# WireGuard VPN Admin - Docker 自動啟動腳本

echo "=========================================="
echo "  WireGuard VPN Admin - 啟動服務"
echo "=========================================="

# 檢查是否已有 WireGuard 介面
echo "[1/5] 檢查 WireGuard 狀態..."
if ip link show wg0 > /dev/null 2>&1; then
    echo "✅ WireGuard wg0 已存在"
    ip link show wg0
else
    # 如果使用 host 網路模式，可能需要手動設定
    echo "⚠️ WireGuard wg0 不存在，請確保主機上 WireGuard 正常運行"
fi

# 初始化資料庫
echo "[2/5] 初始化資料庫..."
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

# 從現有 WireGuard 設定匯入用戶（可選）
echo "[3/5] 檢查現有用戶..."
if [ -f /etc/wireguard/wg0.conf ]; then
    echo "找到 /etc/wireguard/wg0.conf，可以匯入現有用戶"
    # 這裡可以新增邏輯來匯入現有的 peers
fi

# 啟動 Backend
echo "[4/5] 啟動 Backend..."
cd /app/backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
echo "Backend PID: $!"

# 啟動 Frontend
echo "[5/5] 啟動 Frontend..."
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

# 保持腳本運行
echo ""
echo "服務持續運作中..."
tail -f /dev/null

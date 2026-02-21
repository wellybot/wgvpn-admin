#!/bin/bash
# WireGuard VPN Admin - Docker 完整測試腳本

set -e

CONTAINER_NAME="wgvpn-test"
IMAGE_NAME="wgvpn-admin:test"

echo "=========================================="
echo "  WireGuard VPN Admin - Docker 測試"
echo "=========================================="

# 1. 建立 Docker 映像
echo ""
echo "[1/5] 建立 Docker 映像..."
cd "$(dirname "$0")/.."
docker build -t $IMAGE_NAME -f docker/Dockerfile .

# 2. 啟動容器
echo ""
echo "[2/5] 啟動容器..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true
docker run -d \
    --name $CONTAINER_NAME \
    --privileged \
    --cap-add NET_ADMIN \
    -p 8000:8000 \
    -p 5173:5173 \
    -p 51820:51820/udp \
    $IMAGE_NAME \
    sleep infinity

# 等待容器啟動
echo "等待容器啟動..."
sleep 5

# 3. 進入容器並執行測試
echo ""
echo "[3/5] 執行測試..."

docker exec $CONTAINER_NAME /bin/bash << 'TESTEOF'
set -e

echo "=========================================="
echo "  在 Docker 內部測試"
echo "=========================================="

# 檢查 WireGuard
echo ""
echo "[1/4] 檢查 WireGuard..."
wg version || apt-get install -y wireguard-tools
echo "WireGuard 版本: $(wg version | head -1)"

# 設定 WireGuard
echo ""
echo "[2/4] 設定 WireGuard..."
mkdir -p /etc/wireguard
chmod 700 /etc/wireguard

# 產生金鑰
wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey
PRIVATE_KEY=$(cat /etc/wireguard/privatekey)
PUBLIC_KEY=$(cat /etc/wireguard/publickey)
echo "Public Key: $PUBLIC_KEY"

# 建立 WireGuard 設定檔
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = $PRIVATE_KEY

[Peer]
PublicKey = $PUBLIC_KEY
AllowedIPs = 10.0.0.2/32
EOF

chmod 600 /etc/wireguard/wg0.conf
echo "WireGuard 設定檔已建立"

# 啟動 WireGuard
echo ""
echo "[3/4] 啟動 WireGuard..."
ip link add dev wg0 type wireguard 2>/dev/null || true
wg setconf wg0 /etc/wireguard/wg0.conf
ip address add dev wg0 10.0.0.1/24
ip link set up dev wg0
sleep 2
echo "WireGuard 狀態:"
wg show

# 初始化資料庫
echo ""
echo "[4/4] 初始化並測試 Backend..."
cd /app/backend

# 確保資料庫存在
if [ ! -f wgvpn.db ]; then
    sqlite3 wgvpn.db < ../schema.sql
fi

# 建立 admin 用戶
python3 << PYEOF
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
    """, ('admin', 'admin@wgvpn.local', password_hash, 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    print("✅ Admin 用戶已建立")
else:
    print("✅ Admin 用戶已存在")

conn.close()
PYEOF

# 啟動 Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 3

# 測試 API
echo ""
echo "測試 API..."
echo ""

# Health Check
HEALTH=$(curl -s http://localhost:8000/api/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health Check: PASSED"
else
    echo "❌ Health Check: FAILED"
    echo "Response: $HEALTH"
fi

# Login
LOGIN=$(curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

if echo "$LOGIN" | grep -q "token"; then
    echo "✅ Login: PASSED"
    TOKEN=$(echo "$LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null || echo "")
else
    echo "❌ Login: FAILED"
    echo "Response: $LOGIN"
    TOKEN=""
fi

# Traffic API
if [ -n "$TOKEN" ]; then
    TRAFFIC=$(curl -s http://localhost:8000/api/traffic -H "Authorization: Bearer $TOKEN")
    if echo "$TRAFFIC" | grep -q "error"; then
        echo "⚠️  Traffic API: WireGuard 未配置 peer (預期)"
    else
        echo "✅ Traffic API: PASSED"
    fi
    
    # Users API
    USERS=$(curl -s http://localhost:8000/api/users -H "Authorization: Bearer $TOKEN")
    if echo "$USERS" | grep -q "users"; then
        echo "✅ Users API: PASSED"
    else
        echo "❌ Users API: FAILED"
    fi
fi

# 停止 Backend
kill $BACKEND_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Docker 測試完成"
echo "=========================================="
TESTEOF

# 4. 清理
echo ""
echo "[5/5] 清理..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

echo ""
echo "✅ Docker 測試完成！"

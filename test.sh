#!/bin/bash
# wgvpn-admin 自動測試腳本

echo "=========================================="
echo "  WireGuard VPN Admin - 自動測試"
echo "=========================================="
echo ""

# 測試 1: Backend Health
echo "[測試 1] Backend Health Check..."
HEALTH=$(curl -s http://localhost:8000/api/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "  ✅ Backend 健康檢查通過"
else
    echo "  ❌ Backend 健康檢查失敗"
    exit 1
fi

# 測試 2: Login
echo "[測試 2] 登入測試..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
if [ -n "$TOKEN" ]; then
    echo "  ✅ 登入成功"
else
    echo "  ❌ 登入失敗"
    exit 1
fi

# 測試 3: 取得用戶列表 (需要認證)
echo "[測試 3] 認證 API 測試..."
USERS=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/users)
if echo "$USERS" | grep -q "admin"; then
    echo "  ✅ 認證 API 正常"
else
    echo "  ❌ 認證 API 失敗"
    exit 1
fi

# 測試 4: Frontend
echo "[測試 4] Frontend 測試..."
FRONTEND=$(curl -s http://localhost:5173)
if echo "$FRONTEND" | grep -q "WireGuard"; then
    echo "  ✅ Frontend 正常運作"
else
    echo "  ❌ Frontend 無回應"
    exit 1
fi

echo ""
echo "=========================================="
echo "  ✅ 所有測試通過！"
echo "=========================================="
echo ""
echo "系統狀態:"
echo "  - Backend: http://localhost:8000 ✅"
echo "  - Frontend: http://localhost:5173 ✅"
echo "  - 登入帳號: admin / admin123"

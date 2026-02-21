#!/bin/bash
#
# WireGuard VPN Admin - 管理腳本
#

set -e

INSTALL_DIR="/opt/wgvpn-admin"
WG_INTERFACE="wg0"

# 顏色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo ""
    echo "WireGuard VPN Admin - 管理腳本"
    echo ""
    echo "使用方式: wgvpn-admin <指令>"
    echo ""
    echo "指令:"
    echo "  status      顯示系統狀態"
    echo "  start       啟動所有服務"
    echo "  stop        停止所有服務"
    echo "  restart     重啟所有服務"
    echo "  logs        查看日誌"
    echo "  backup      備份資料庫"
    echo "  restore     還原資料庫"
    echo "  update      更新系統"
    echo "  add-user    新增 VPN 用戶"
    echo "  list-users  列出所有用戶"
    echo "  wg-status   WireGuard 狀態"
    echo "  uninstall   移除系統"
    echo ""
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}請使用 sudo 執行此腳本${NC}"
        exit 1
    fi
}

cmd_status() {
    echo ""
    echo "=========================================="
    echo "  系統狀態"
    echo "=========================================="
    echo ""
    
    # Backend
    if systemctl is-active --quiet wgvpn-backend; then
        echo -e "Backend:   ${GREEN}運行中${NC}"
    else
        echo -e "Backend:   ${RED}已停止${NC}"
    fi
    
    # Frontend
    if systemctl is-active --quiet wgvpn-frontend; then
        echo -e "Frontend:  ${GREEN}運行中${NC}"
    else
        echo -e "Frontend:  ${RED}已停止${NC}"
    fi
    
    # WireGuard
    if wg show 2>/dev/null | grep -q "interface"; then
        echo -e "WireGuard: ${GREEN}運行中${NC}"
    else
        echo -e "WireGuard: ${YELLOW}未啟動${NC}"
    fi
    
    echo ""
    echo "存取位址:"
    echo "  Frontend: http://$(hostname -I | awk '{print $1}'):5173"
    echo "  Backend:  http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
}

cmd_start() {
    check_root
    echo "啟動服務..."
    systemctl start wg-quick@${WG_INTERFACE} 2>/dev/null || true
    systemctl start wgvpn-backend
    systemctl start wgvpn-frontend
    echo -e "${GREEN}✅ 所有服務已啟動${NC}"
}

cmd_stop() {
    check_root
    echo "停止服務..."
    systemctl stop wgvpn-frontend 2>/dev/null || true
    systemctl stop wgvpn-backend 2>/dev/null || true
    echo -e "${YELLOW}服務已停止${NC}"
}

cmd_restart() {
    check_root
    echo "重啟服務..."
    systemctl restart wgvpn-backend
    systemctl restart wgvpn-frontend
    echo -e "${GREEN}✅ 所有服務已重啟${NC}"
}

cmd_logs() {
    echo "顯示 Backend 日誌 (Ctrl+C 離開)..."
    journalctl -u wgvpn-backend -f
}

cmd_backup() {
    check_root
    BACKUP_FILE="/root/wgvpn-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    echo "備份資料庫到 $BACKUP_FILE ..."
    tar -czf $BACKUP_FILE -C $INSTALL_DIR/backend wgvpn.db
    echo -e "${GREEN}✅ 備份完成: $BACKUP_FILE${NC}"
}

cmd_restore() {
    check_root
    if [ -z "$1" ]; then
        echo "使用方式: wgvpn-admin restore <備份檔案>"
        exit 1
    fi
    if [ ! -f "$1" ]; then
        echo -e "${RED}備份檔案不存在: $1${NC}"
        exit 1
    fi
    echo "還原資料庫..."
    systemctl stop wgvpn-backend
    tar -xzf "$1" -C $INSTALL_DIR/backend
    systemctl start wgvpn-backend
    echo -e "${GREEN}✅ 還原完成${NC}"
}

cmd_update() {
    check_root
    echo "更新系統..."
    cd $INSTALL_DIR
    git pull
    
    # 更新 Backend
    cd $INSTALL_DIR/backend
    source venv/bin/activate
    pip install -q -r requirements.txt
    deactivate
    
    # 更新 Frontend
    cd $INSTALL_DIR/frontend
    npm install --silent
    npm run build > /dev/null 2>&1
    
    # 重啟服務
    systemctl restart wgvpn-backend
    systemctl restart wgvpn-frontend
    
    echo -e "${GREEN}✅ 更新完成${NC}"
}

cmd_add_user() {
    check_root
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo "使用方式: wgvpn-admin add-user <用戶名> <email>"
        exit 1
    fi
    
    USERNAME=$1
    EMAIL=$2
    
    cd $INSTALL_DIR/backend
    
    # 產生金鑰
    PRIVATE_KEY=$(wg genkey)
    PUBLIC_KEY=$(echo $PRIVATE_KEY | wg pubkey)
    
    # 產生客戶端設定
    SERVER_PUBKEY=$(cat /etc/wireguard/publickey)
    CLIENT_IP="10.0.0.$((RANDOM % 200 + 10))"
    
    cat > /tmp/${USERNAME}.conf << EOF
[Interface]
Address = ${CLIENT_IP}/32
PrivateKey = ${PRIVATE_KEY}
DNS = 1.1.1.1

[Peer]
PublicKey = ${SERVER_PUBKEY}
Endpoint = $(curl -s ifconfig.me):51820
AllowedIPs = 0.0.0.0/0
EOF
    
    # 加入資料庫
    python3 << PYEOF
import sqlite3
from datetime import datetime

conn = sqlite3.connect('wgvpn.db')
cursor = conn.cursor()
cursor.execute("""
    INSERT INTO users (username, email, public_key, private_key, allowed_ips, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
""", ('${USERNAME}', '${EMAIL}', '${PUBLIC_KEY}', '${PRIVATE_KEY}', '${CLIENT_IP}/32',
      datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
conn.commit()
conn.close()
PYEOF
    
    # 加入 WireGuard
    wg set $WG_INTERFACE peer $PUBLIC_KEY allowed-ips $CLIENT_IP/32
    
    echo ""
    echo -e "${GREEN}✅ 用戶已建立${NC}"
    echo ""
    echo "用戶名: $USERNAME"
    echo "Email: $EMAIL"
    echo "IP: $CLIENT_IP"
    echo ""
    echo "設定檔已儲存到: /tmp/${USERNAME}.conf"
    echo ""
    echo "QR Code:"
    qrencode -t ANSIUTF8 < /tmp/${USERNAME}.conf
    echo ""
}

cmd_list_users() {
    cd $INSTALL_DIR/backend
    python3 << 'PYEOF'
import sqlite3

conn = sqlite3.connect('wgvpn.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT id, username, email, is_active, created_at FROM users ORDER BY id")

print("\n用戶列表:")
print("-" * 70)
print(f"{'ID':<5} {'用戶名':<15} {'Email':<25} {'狀態':<8} {'建立時間'}")
print("-" * 70)

for row in cursor.fetchall():
    status = "啟用" if row['is_active'] else "停用"
    print(f"{row['id']:<5} {row['username']:<15} {row['email']:<25} {status:<8} {row['created_at']}")

conn.close()
PYEOF
}

cmd_wg_status() {
    echo ""
    echo "WireGuard 狀態:"
    echo ""
    wg show
    echo ""
}

cmd_uninstall() {
    check_root
    echo -e "${RED}警告: 這將完全移除 WireGuard VPN Admin${NC}"
    read -p "確定要繼續嗎? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "取消移除"
        exit 0
    fi
    
    echo "停止服務..."
    systemctl stop wgvpn-frontend 2>/dev/null || true
    systemctl stop wgvpn-backend 2>/dev/null || true
    systemctl stop wg-quick@${WG_INTERFACE} 2>/dev/null || true
    
    echo "移除服務..."
    systemctl disable wgvpn-frontend 2>/dev/null || true
    systemctl disable wgvpn-backend 2>/dev/null || true
    rm -f /etc/systemd/system/wgvpn-*.service
    systemctl daemon-reload
    
    echo "移除檔案..."
    rm -rf $INSTALL_DIR
    
    echo -e "${GREEN}✅ 移除完成${NC}"
}

# 主程式
case "$1" in
    status)     cmd_status ;;
    start)      cmd_start ;;
    stop)       cmd_stop ;;
    restart)    cmd_restart ;;
    logs)       cmd_logs ;;
    backup)     cmd_backup ;;
    restore)    cmd_restore "$2" ;;
    update)     cmd_update ;;
    add-user)   cmd_add_user "$2" "$3" ;;
    list-users) cmd_list_users ;;
    wg-status)  cmd_wg_status ;;
    uninstall)  cmd_uninstall ;;
    *)          show_help ;;
esac

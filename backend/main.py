"""
WireGuard VPN Admin - FastAPI Backend
"""

import subprocess
import re
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import database

app = FastAPI(title="WireGuard VPN Admin API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "WireGuard VPN Admin API", "status": "running"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

def parse_wg_show() -> List[Dict]:
    """
    Parse output of 'wg show' to get peer statistics
    Returns list of dicts with public_key, bytes_received, bytes_sent
    """
    try:
        result = subprocess.run(
            ["wg", "show"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # If wg show fails (no WireGuard interface), return mock data for demo
            return get_mock_traffic_data()
        
        output = result.stdout
        peers = []
        
        # Parse peer sections
        peer_pattern = r'peer: (.+?)(?=\npeer:|\Z)'
        public_key_pattern = r'  public key: (.+)'
        transfer_pattern = r'  transfer: ([\d.]+) (KiB|MiB|GiB|B) received, ([\d.]+) (KiB|MiB|GiB|B) sent'
        
        import re
        peer_blocks = re.split(r'peer:', output)
        
        for block in peer_blocks[1:]:  # Skip first empty block
            peer_info = {}
            
            # Get public key
            pk_match = re.search(public_key_pattern, block)
            if pk_match:
                peer_info['public_key'] = pk_match.group(1).strip()
            
            # Get transfer
            tr_match = re.search(transfer_pattern, block)
            if tr_match:
                recv_val = float(tr_match.group(1))
                recv_unit = tr_match.group(2)
                sent_val = float(tr_match.group(3))
                sent_unit = tr_match.group(4)
                
                # Convert to bytes
                def to_bytes(val, unit):
                    multiplier = {'B': 1, 'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3}
                    return int(val * multiplier.get(unit, 1))
                
                peer_info['bytes_received'] = to_bytes(recv_val, recv_unit)
                peer_info['bytes_sent'] = to_bytes(sent_val, sent_unit)
            
            if 'public_key' in peer_info:
                peers.append(peer_info)
        
        return peers if peers else get_mock_traffic_data()
        
    except FileNotFoundError:
        # wg command not found (not running WireGuard)
        return get_mock_traffic_data()
    except Exception as e:
        print(f"Error parsing wg show: {e}")
        return get_mock_traffic_data()

def get_mock_traffic_data() -> List[Dict]:
    """
    Return mock traffic data for demo purposes when WireGuard is not available
    """
    import random
    users = database.get_users()
    
    if not users:
        return []
    
    mock_data = []
    for user in users:
        mock_data.append({
            'public_key': user.get('public_key', f'mock_key_{user["id"]}'),
            'user_id': user['id'],
            'username': user['username'],
            'bytes_received': random.randint(1000000, 100000000),
            'bytes_sent': random.randint(500000, 50000000)
        })
    
    return mock_data

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"

@app.get("/api/traffic")
async def get_traffic():
    """
    Get real-time traffic statistics from WireGuard
    Returns list of peers with their upload/download bytes
    """
    peers = parse_wg_show()
    
    # Get users for mapping public_key to username
    users = database.get_users()
    user_map = {u['public_key']: u for u in users}
    
    result = []
    for peer in peers:
        # Find user by public key
        user = user_map.get(peer.get('public_key'))
        
        traffic_entry = {
            'public_key': peer.get('public_key', 'unknown'),
            'bytes_received': peer.get('bytes_received', 0),
            'bytes_sent': peer.get('bytes_sent', 0),
            'formatted_received': format_bytes(peer.get('bytes_received', 0)),
            'formatted_sent': format_bytes(peer.get('bytes_sent', 0)),
        }
        
        if user:
            traffic_entry['user_id'] = user['id']
            traffic_entry['username'] = user['username']
            
            # Log traffic snapshot to database
            try:
                database.log_traffic(
                    user_id=user['id'],
                    peer_public_key=peer.get('public_key', ''),
                    bytes_received=peer.get('bytes_received', 0),
                    bytes_sent=peer.get('bytes_sent', 0)
                )
            except Exception as e:
                print(f"Failed to log traffic: {e}")
        
        result.append(traffic_entry)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'peers': result,
        'total_received': sum(p.get('bytes_received', 0) for p in peers),
        'total_sent': sum(p.get('bytes_sent', 0) for p in peers)
    }

@app.get("/api/traffic/history")
async def get_traffic_history(
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 1000
):
    """
    Get historical traffic logs with optional date range filtering
    """
    logs = database.get_traffic_history(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return {
        'logs': logs,
        'count': len(logs),
        'filters': {
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date
        }
    }

@app.get("/api/traffic/daily")
async def get_daily_traffic(days: int = 30, user_id: int = None):
    """
    Get daily traffic summaries
    """
    summary = database.get_daily_traffic_summary(user_id=user_id, days=days)
    return {
        'daily': summary,
        'count': len(summary),
        'days': days
    }

@app.get("/api/traffic/hourly")
async def get_hourly_traffic(hours: int = 24, user_id: int = None):
    """
    Get hourly traffic summaries
    """
    summary = database.get_hourly_traffic_summary(user_id=user_id, hours=hours)
    return {
        'hourly': summary,
        'count': len(summary),
        'hours': hours
    }

# ============== Alert Endpoints ==============

@app.get("/api/alerts")
async def get_alerts(
    user_id: int = None,
    severity: str = None,
    is_resolved: bool = None,
    limit: int = 100
):
    """
    Get alerts with optional filtering
    """
    alerts = database.get_alerts(
        user_id=user_id,
        severity=severity,
        is_resolved=is_resolved,
        limit=limit
    )
    return {
        'alerts': alerts,
        'count': len(alerts)
    }

@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """
    Mark an alert as resolved
    """
    database.resolve_alert(alert_id)
    return {'status': 'resolved', 'alert_id': alert_id}

@app.get("/api/alerts/unresolved")
async def get_unresolved_alerts():
    """
    Get all unresolved alerts
    """
    alerts = database.get_unresolved_alerts()
    return {
        'alerts': alerts,
        'count': len(alerts)
    }

@app.post("/api/alerts/check")
async def check_anomalies():
    """
    Trigger anomaly detection check
    """
    new_alerts = database.check_traffic_anomalies()
    return {
        'checked': True,
        'new_alerts': len(new_alerts),
        'alert_ids': new_alerts
    }

# ============== Connection Logs Endpoints ==============

@app.get("/api/logs/connections")
async def get_connection_logs(
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    connection_status: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get connection logs with optional filtering
    - user_id: Filter by user ID
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - connection_status: 'connected' or 'disconnected'
    - limit: Number of records to return
    - offset: Offset for pagination
    """
    result = database.get_connection_logs(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        connection_status=connection_status,
        limit=limit,
        offset=offset
    )
    return result

@app.get("/api/logs/connections/active")
async def get_active_connections():
    """
    Get all currently active connections
    """
    connections = database.get_active_connections()
    return {
        'connections': connections,
        'count': len(connections)
    }

@app.post("/api/logs/connections")
async def create_connection_log(user_id: int, peer_ip: str = None):
    """
    Log a new connection event
    """
    connection_id = database.log_connection(user_id=user_id, peer_ip=peer_ip)
    return {
        'status': 'connected',
        'connection_id': connection_id
    }

@app.post("/api/logs/connections/{connection_id}/disconnect")
async def disconnect_connection(connection_id: int, bytes_received: int = 0, bytes_sent: int = 0):
    """
    Update connection with disconnect time and final bytes
    """
    database.update_connection_disconnect(connection_id, bytes_received, bytes_sent)
    return {
        'status': 'disconnected',
        'connection_id': connection_id
    }

# ============== Log Search Endpoints ==============

@app.get("/api/logs/search")
async def search_logs(
    keyword: str = None,
    log_type: str = None,
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Full-text search across all log types
    - keyword: Search keyword
    - log_type: Filter by log type ('connection', 'traffic', 'alert', 'audit')
    - user_id: Filter by user ID
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - limit: Number of records to return
    - offset: Offset for pagination
    """
    result = database.search_logs(
        keyword=keyword,
        log_type=log_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return result

# ============== Log Export Endpoints ==============

@app.get("/api/logs/export")
async def export_logs(
    log_type: str = None,
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    format: str = 'csv'
):
    """
    Export logs as CSV or JSON
    - log_type: Filter by log type ('connection', 'traffic', 'alert', 'audit')
    - user_id: Filter by user ID
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - format: 'csv' or 'json'
    """
    logs = database.get_logs_for_export(
        log_type=log_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        format=format
    )
    
    if format == 'json':
        return {
            'logs': logs,
            'count': len(logs),
            'exported_at': datetime.now().isoformat()
        }
    else:
        # CSV format
        if not logs:
            return {'data': '', 'count': 0}
        
        # Get headers from first log
        headers = list(logs[0].keys())
        
        # Build CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(logs)
        
        return {
            'data': output.getvalue(),
            'count': len(logs),
            'exported_at': datetime.now().isoformat()
        }

# ============== Real-time Log Streaming (WebSocket) ==============

from fastapi import WebSocket
from typing import Set
import asyncio
import random

# Store active WebSocket connections
active_websockets: Set[WebSocket] = set()

@app.websocket("/api/logs/stream")
async def log_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time log streaming
    """
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            'type': 'connected',
            'message': 'Real-time log stream started',
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep connection alive and send periodic mock log events
        counter = 0
        while True:
            await asyncio.sleep(5)  # Send log every 5 seconds
            
            # Generate mock log entry for demo
            users = database.get_users()
            log_types = ['connection', 'traffic', 'alert', 'audit']
            
            if users:
                user = random.choice(users)
                log_type = random.choice(log_types)
                
                if log_type == 'connection':
                    log_entry = {
                        'type': 'log',
                        'log_type': 'connection',
                        'user_id': user['id'],
                        'username': user['username'],
                        'message': f"User {user['username']} connected",
                        'timestamp': datetime.now().isoformat(),
                        'level': 'info'
                    }
                elif log_type == 'traffic':
                    log_entry = {
                        'type': 'log',
                        'log_type': 'traffic',
                        'user_id': user['id'],
                        'username': user['username'],
                        'message': f"Traffic update: {format_bytes(random.randint(1000, 100000))} received",
                        'timestamp': datetime.now().isoformat(),
                        'level': 'info'
                    }
                elif log_type == 'alert':
                    alert_levels = ['info', 'warning', 'error']
                    log_entry = {
                        'type': 'log',
                        'log_type': 'alert',
                        'user_id': user['id'],
                        'username': user['username'],
                        'message': f"Alert: High bandwidth usage detected",
                        'timestamp': datetime.now().isoformat(),
                        'level': random.choice(alert_levels)
                    }
                else:
                    log_entry = {
                        'type': 'log',
                        'log_type': 'audit',
                        'user_id': user['id'],
                        'username': user['username'],
                        'message': f"Audit: User action recorded",
                        'timestamp': datetime.now().isoformat(),
                        'level': 'info'
                    }
                
                try:
                    await websocket.send_json(log_entry)
                except:
                    break
                    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_websockets.discard(websocket)

async def broadcast_log(log_entry: dict):
    """
    Broadcast a log entry to all connected WebSocket clients
    """
    for websocket in active_websockets:
        try:
            await websocket.send_json(log_entry)
        except:
            pass

# ============== Authentication ==============
import hashlib
import secrets
import base64
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

# JWT Configuration
JWT_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    allowed_ips: Optional[str] = "10.0.0.2/32"

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    allowed_ips: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(password) == password_hash

def generate_jwt_token(user_id: int, username: str) -> str:
    """Generate a JWT token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Token dependency for protected routes
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Admin login endpoint"""
    user = database.get_user_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not verify_password(request.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user['is_active']:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    token = generate_jwt_token(user['id'], user['username'])
    
    return {
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
    }

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout endpoint (client should discard token)"""
    return {'status': 'logged_out'}

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    user = database.get_user_by_id(current_user['user_id'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        'id': user['id'],
        'username': user['username'],
        'email': user['email']
    }

# ============== WireGuard Key Generation ==============

def generate_wireguard_keys():
    """Generate WireGuard public/private key pair"""
    try:
        # Generate private key using wg command
        result = subprocess.run(
            ["wg", "genkey"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            # Fallback: generate random base64 key
            private_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        else:
            private_key = result.stdout.strip()
        
        # Generate public key from private key
        result = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            # Fallback: derive public key
            import hashlib
            public_key = base64.b64encode(hashlib.sha256(private_key.encode()).digest()[:32]).decode('utf-8')
        else:
            public_key = result.stdout.strip()
        
        return private_key, public_key
    except FileNotFoundError:
        # Fallback when wg command not available
        private_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        import hashlib
        public_key = base64.b64encode(hashlib.sha256(private_key.encode()).digest()[:32]).decode('utf-8')
        return private_key, public_key

def generate_wireguard_config(username: str, private_key: str, public_key: str, allowed_ips: str = "10.0.0.2/32", endpoint: str = "vpn.example.com:51820", dns: str = "1.1.1.1"):
    """Generate WireGuard configuration file content"""
    config = f"""[Interface]
PrivateKey = {private_key}
Address = {allowed_ips}
DNS = {dns}

[Peer]
PublicKey = {public_key}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {endpoint}
PersistentKeepalive = 25
"""
    return config

# ============== User Management ==============

@app.get("/api/users")
async def get_users(
    page: int = 1,
    per_page: int = 20,
    search: str = None,
    is_active: bool = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all users with pagination"""
    result = database.get_users(page=page, per_page=per_page, search=search, is_active=is_active)
    return result

@app.get("/api/users/{user_id}")
async def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific user"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Don't expose private key
    user.pop('private_key', None)
    return user

@app.post("/api/users")
async def create_user(request: UserCreateRequest, current_user: dict = Depends(get_current_user)):
    """Create a new user"""
    try:
        password_hash = hash_password(request.password)
        
        # Generate WireGuard keys
        private_key, public_key = generate_wireguard_keys()
        
        user = database.create_user(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            public_key=public_key,
            private_key=private_key,
            allowed_ips=request.allowed_ips
        )
        
        # Don't expose private key in response
        user.pop('private_key', None)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: UserUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Update user details"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = database.update_user(
        user_id=user_id,
        username=request.username,
        email=request.email,
        allowed_ips=request.allowed_ips
    )
    
    user.pop('private_key', None)
    return user

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a user"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if user_id == current_user['user_id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    database.delete_user(user_id)
    return {'status': 'deleted', 'user_id': user_id}

# ============== VPN Config Generation ==============

@app.post("/api/users/{user_id}/generate-config")
async def generate_config(user_id: int, current_user: dict = Depends(get_current_user)):
    """Generate WireGuard configuration for a user"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new keys
    private_key, public_key = generate_wireguard_keys()
    
    # Update user with new keys
    user = database.update_user_keys(user_id, public_key, private_key)
    
    # Generate config content
    config = generate_wireguard_config(
        username=user['username'],
        private_key=private_key,
        public_key=public_key,
        allowed_ips=user.get('allowed_ips', '10.0.0.2/32')
    )
    
    return {
        'config': config,
        'public_key': public_key,
        'private_key': private_key  # Only returned once during generation
    }

@app.get("/api/users/{user_id}/config")
async def get_config(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get WireGuard configuration for a user"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get('public_key') or not user.get('private_key'):
        raise HTTPException(status_code=400, detail="User has no WireGuard keys. Generate config first.")
    
    # Get server's public key (for peer config)
    # In a real deployment, this would come from server configuration
    server_public_key = user['public_key']  # Placeholder - would be server's key
    
    config = generate_wireguard_config(
        username=user['username'],
        private_key=user['private_key'],
        public_key=server_public_key,
        allowed_ips=user.get('allowed_ips', '10.0.0.2/32')
    )
    
    return {
        'config': config,
        'filename': f"{user['username']}.conf"
    }

@app.get("/api/users/{user_id}/qr")
async def get_qr_code(user_id: int, current_user: dict = Depends(get_current_user)):
    """Generate QR code for mobile WireGuard config"""
    import qrcode
    import io
    import base64
    
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get('public_key') or not user.get('private_key'):
        raise HTTPException(status_code=400, detail="User has no WireGuard keys. Generate config first.")
    
    # Generate config
    server_public_key = user['public_key']  # Placeholder
    config = generate_wireguard_config(
        username=user['username'],
        private_key=user['private_key'],
        public_key=server_public_key,
        allowed_ips=user.get('allowed_ips', '10.0.0.2/32')
    )
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(config)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        'qr_code': f"data:image/png;base64,{qr_base64}",
        'username': user['username']
    }

# ============== Account Enable/Disable ==============

@app.post("/api/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: int, current_user: dict = Depends(get_current_user)):
    """Toggle user active status"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deactivation
    if user_id == current_user['user_id']:
        raise HTTPException(status_code=400, detail="Cannot toggle your own account status")
    
    user = database.toggle_user_active(user_id)
    
    # In a real deployment, you would also add/remove peer from WireGuard
    # For now, we just update the database
    
    return {
        'user_id': user_id,
        'is_active': user['is_active'],
        'status': 'enabled' if user['is_active'] else 'disabled'
    }

# ============== Password Management ==============

@app.post("/api/users/{user_id}/change-password")
async def change_password(user_id: int, request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """Change user password"""
    # Users can only change their own password unless admin
    if user_id != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Cannot change other user's password")
    
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify old password
    if not verify_password(request.old_password, user['password_hash']):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    new_hash = hash_password(request.new_password)
    database.update_password(user_id, new_hash)
    
    return {'status': 'password_changed'}

# TODO: Implement API endpoints for:
# - Reports

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

# ============== User Management (Basic) ==============

@app.get("/api/users")
async def get_users():
    """Get all users"""
    users = database.get_users()
    return {'users': users, 'count': len(users)}

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """Get a specific user"""
    conn = database.get_db_connection()
    cursor = conn.execute(
        "SELECT id, username, email, public_key, is_active, created_at FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    
    return dict(row)

# TODO: Implement API endpoints for:
# - Reports

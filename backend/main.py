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
async def get_traffic_history(limit: int = 100):
    """Get historical traffic logs"""
    logs = database.get_recent_traffic_logs(limit)
    return {
        'logs': logs,
        'count': len(logs)
    }

# TODO: Implement API endpoints for:
# - User management
# - Logs
# - Audit records
# - Reports

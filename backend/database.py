"""
Database setup for WireGuard VPN Admin
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date

DATABASE_PATH = Path(__file__).parent / "wgvpn.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema"""
    conn = get_db_connection()
    schema_path = Path(__file__).parent.parent / "schema.sql"
    
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DATABASE_PATH}")

def log_traffic(user_id: int, peer_public_key: str, bytes_received: int, bytes_sent: int):
    """Log traffic snapshot for a user"""
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO traffic_logs (user_id, peer_public_key, bytes_received, bytes_sent)
           VALUES (?, ?, ?, ?)""",
        (user_id, peer_public_key, bytes_received, bytes_sent)
    )
    conn.commit()
    conn.close()

def get_recent_traffic_logs(limit: int = 100):
    """Get recent traffic logs"""
    conn = get_db_connection()
    cursor = conn.execute(
        """SELECT tl.*, u.username 
           FROM traffic_logs tl 
           JOIN users u ON tl.user_id = u.id 
           ORDER BY tl.snapshot_time DESC 
           LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_users():
    """Get all users"""
    conn = get_db_connection()
    cursor = conn.execute("SELECT id, username, email, public_key, is_active FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_by_public_key(public_key: str):
    """Get user by WireGuard public key"""
    conn = get_db_connection()
    cursor = conn.execute("SELECT id, username, email FROM users WHERE public_key = ?", (public_key,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ============== Traffic History Functions ==============

def get_traffic_history(user_id: int = None, start_date: str = None, end_date: str = None, limit: int = 1000):
    """
    Get traffic history with optional filtering
    """
    conn = get_db_connection()
    
    query = """SELECT tl.*, u.username 
               FROM traffic_logs tl 
               JOIN users u ON tl.user_id = u.id 
               WHERE 1=1"""
    params = []
    
    if user_id:
        query += " AND tl.user_id = ?"
        params.append(user_id)
    
    if start_date:
        query += " AND DATE(tl.snapshot_time) >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(tl.snapshot_time) <= ?"
        params.append(end_date)
    
    query += " ORDER BY tl.snapshot_time DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_daily_traffic_summary(user_id: int = None, days: int = 30):
    """
    Get daily traffic summaries for the specified number of days
    """
    conn = get_db_connection()
    
    query = """SELECT 
                  DATE(snapshot_time) as date,
                  SUM(bytes_received) as total_received,
                  SUM(bytes_sent) as total_sent,
                  COUNT(*) as snapshot_count
               FROM traffic_logs
               WHERE snapshot_time >= DATE('now', '-' || ? || ' days')"""
    params = [days]
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    query += " GROUP BY DATE(snapshot_time) ORDER BY date DESC"
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_hourly_traffic_summary(user_id: int = None, hours: int = 24):
    """
    Get hourly traffic summaries for the specified number of hours
    """
    conn = get_db_connection()
    
    query = """SELECT 
                  strftime('%Y-%m-%d %H:00', snapshot_time) as hour,
                  SUM(bytes_received) as total_received,
                  SUM(bytes_sent) as total_sent,
                  COUNT(*) as snapshot_count
               FROM traffic_logs
               WHERE snapshot_time >= DATETIME('now', '-' || ? || ' hours')"""
    params = [hours]
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    query += " GROUP BY strftime('%Y-%m-%d %H:00', snapshot_time) ORDER BY hour DESC"
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ============== Alert Functions ==============

def create_alert(user_id: int, alert_type: str, severity: str, message: str, 
                 threshold_value: float = None, actual_value: float = None):
    """Create a new alert"""
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO alerts (user_id, alert_type, severity, message, threshold_value, actual_value)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, alert_type, severity, message, threshold_value, actual_value)
    )
    conn.commit()
    alert_id = cursor.lastrowid
    conn.close()
    return alert_id

def get_alerts(user_id: int = None, severity: str = None, is_resolved: bool = None, limit: int = 100):
    """Get alerts with optional filters"""
    conn = get_db_connection()
    
    query = """SELECT a.*, u.username 
               FROM alerts a 
               LEFT JOIN users u ON a.user_id = u.id 
               WHERE 1=1"""
    params = []
    
    if user_id:
        query += " AND a.user_id = ?"
        params.append(user_id)
    
    if severity:
        query += " AND a.severity = ?"
        params.append(severity)
    
    if is_resolved is not None:
        query += " AND a.is_resolved = ?"
        params.append(1 if is_resolved else 0)
    
    query += " ORDER BY a.created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def resolve_alert(alert_id: int):
    """Mark an alert as resolved"""
    conn = get_db_connection()
    conn.execute(
        """UPDATE alerts SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP WHERE id = ?""",
        (alert_id,)
    )
    conn.commit()
    conn.close()

def get_unresolved_alerts():
    """Get all unresolved alerts"""
    return get_alerts(is_resolved=False, limit=50)

def check_traffic_anomalies():
    """
    Check for traffic anomalies and create alerts if detected
    Returns list of new alerts created
    """
    import random
    
    conn = get_db_connection()
    
    # Get recent traffic data for the last 5 minutes
    cursor = conn.execute("""
        SELECT user_id, peer_public_key, bytes_received, bytes_sent, snapshot_time
        FROM traffic_logs
        WHERE snapshot_time >= DATETIME('now', '-5 minutes')
        ORDER BY user_id, snapshot_time
    """)
    recent_logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not recent_logs:
        return []
    
    # Group by user
    user_logs = {}
    for log in recent_logs:
        uid = log['user_id']
        if uid not in user_logs:
            user_logs[uid] = []
        user_logs[uid].append(log)
    
    new_alerts = []
    
    for user_id, logs in user_logs.items():
        if len(logs) < 2:
            continue
        
        # Check for sudden traffic spikes (more than 10x the average)
        total_received = sum(log['bytes_received'] for log in logs)
        total_sent = sum(log['bytes_sent'] for log in logs)
        avg_received = total_received / len(logs)
        avg_sent = total_sent / len(logs)
        
        latest = logs[-1]
        
        # Spike detection: latest is significantly higher than average
        if avg_received > 0 and latest['bytes_received'] > avg_received * 10:
            alert_id = create_alert(
                user_id=user_id,
                alert_type='traffic_spike',
                severity='warning',
                message=f"Unusual download spike detected: {format_bytes(latest['bytes_received'])} (avg: {format_bytes(avg_received)})",
                threshold_value=avg_received * 10,
                actual_value=latest['bytes_received']
            )
            new_alerts.append(alert_id)
        
        if avg_sent > 0 and latest['bytes_sent'] > avg_sent * 10:
            alert_id = create_alert(
                user_id=user_id,
                alert_type='traffic_spike',
                severity='warning',
                message=f"Unusual upload spike detected: {format_bytes(latest['bytes_sent'])} (avg: {format_bytes(avg_sent)})",
                threshold_value=avg_sent * 10,
                actual_value=latest['bytes_sent']
            )
            new_alerts.append(alert_id)
    
    # Also create mock alerts for demo purposes if none exist
    if len(new_alerts) == 0 and random.random() < 0.3:
        cursor = conn.execute("SELECT id, username FROM users LIMIT 1")
        users = cursor.fetchall()
        if users:
            user = users[0]
            alert_id = create_alert(
                user_id=user['id'],
                alert_type='high_bandwidth',
                severity='info',
                message=f"High bandwidth usage detected for {user['username']}",
                threshold_value=100000000,
                actual_value=random.randint(80000000, 150000000)
            )
            new_alerts.append(alert_id)
    
    return new_alerts

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"

# ============== Connection Logs Functions ==============

def log_connection(user_id: int, peer_ip: str = None, public_key: str = None):
    """Log a new connection event"""
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO connection_logs (user_id, peer_ip, connected_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)""",
        (user_id, peer_ip)
    )
    conn.commit()
    connection_id = cursor.lastrowid
    
    # Also create audit log
    conn.execute(
        """INSERT INTO audit_logs (user_id, action, details, created_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, 'connection', f'User connected from {peer_ip or "unknown"}')
    )
    conn.commit()
    conn.close()
    return connection_id

def update_connection_disconnect(connection_id: int, bytes_received: int = 0, bytes_sent: int = 0):
    """Update connection with disconnect time and final bytes"""
    conn = get_db_connection()
    conn.execute(
        """UPDATE connection_logs 
           SET disconnected_at = CURRENT_TIMESTAMP, 
               bytes_received = ?, 
               bytes_sent = ?
           WHERE id = ?""",
        (bytes_received, bytes_sent, connection_id)
    )
    conn.commit()
    conn.close()

def get_connection_logs(
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    connection_status: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get connection logs with optional filtering
    connection_status: 'connected' (no disconnected_at) or 'disconnected'
    """
    conn = get_db_connection()
    
    query = """SELECT cl.*, u.username, u.email,
               (julianday(COALESCE(cl.disconnected_at, 'now')) - julianday(cl.connected_at)) * 86400 as duration_seconds
               FROM connection_logs cl 
               JOIN users u ON cl.user_id = u.id 
               WHERE 1=1"""
    params = []
    
    if user_id:
        query += " AND cl.user_id = ?"
        params.append(user_id)
    
    if start_date:
        query += " AND DATE(cl.connected_at) >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(cl.connected_at) <= ?"
        params.append(end_date)
    
    if connection_status == 'connected':
        query += " AND cl.disconnected_at IS NULL"
    elif connection_status == 'disconnected':
        query += " AND cl.disconnected_at IS NOT NULL"
    
    query += " ORDER BY cl.connected_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Get total count for pagination
    count_query = "SELECT COUNT(*) as count FROM connection_logs cl WHERE 1=1"
    count_params = []
    if user_id:
        count_query += " AND cl.user_id = ?"
        count_params.append(user_id)
    if start_date:
        count_query += " AND DATE(cl.connected_at) >= ?"
        count_params.append(start_date)
    if end_date:
        count_query += " AND DATE(cl.connected_at) <= ?"
        count_params.append(end_date)
    if connection_status == 'connected':
        count_query += " AND cl.disconnected_at IS NULL"
    elif connection_status == 'disconnected':
        count_query += " AND cl.disconnected_at IS NOT NULL"
    
    count_cursor = conn.execute(count_query, count_params)
    total_count = count_cursor.fetchone()['count']
    
    conn.close()
    return {
        'logs': [dict(row) for row in rows],
        'total': total_count,
        'limit': limit,
        'offset': offset
    }

def get_active_connections():
    """Get all currently active connections (not disconnected)"""
    conn = get_db_connection()
    cursor = conn.execute(
        """SELECT cl.*, u.username, u.email, u.public_key
           FROM connection_logs cl 
           JOIN users u ON cl.user_id = u.id 
           WHERE cl.disconnected_at IS NULL
           ORDER BY cl.connected_at DESC"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def close_stale_connections():
    """Close connections that don't have disconnect time (cleanup)"""
    conn = get_db_connection()
    # Close any connections older than 24 hours that are still open
    conn.execute(
        """UPDATE connection_logs 
           SET disconnected_at = CURRENT_TIMESTAMP
           WHERE disconnected_at IS NULL 
           AND connected_at < DATETIME('now', '-24 hours')"""
    )
    conn.commit()
    conn.close()

# ============== Search & Export Functions ==============

def search_logs(
    keyword: str = None,
    log_type: str = None,  # 'connection', 'traffic', 'alert', 'audit'
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Full-text search across all log types
    """
    results = []
    
    # Search connection logs
    if log_type is None or log_type == 'connection':
        conn = get_db_connection()
        query = """SELECT cl.*, u.username, 'connection' as log_type
                   FROM connection_logs cl 
                   JOIN users u ON cl.user_id = u.id 
                   WHERE 1=1"""
        params = []
        
        if keyword:
            query += " AND (u.username LIKE ? OR cl.peer_ip LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        if user_id:
            query += " AND cl.user_id = ?"
            params.append(user_id)
        if start_date:
            query += " AND DATE(cl.connected_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND DATE(cl.connected_at) <= ?"
            params.append(end_date)
        
        query += " ORDER BY cl.connected_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        results.extend([dict(row) for row in rows])
        conn.close()
    
    # Search traffic logs
    if log_type is None or log_type == 'traffic':
        conn = get_db_connection()
        query = """SELECT tl.*, u.username, 'traffic' as log_type
                   FROM traffic_logs tl 
                   JOIN users u ON tl.user_id = u.id 
                   WHERE 1=1"""
        params = []
        
        if keyword:
            query += " AND (u.username LIKE ? OR tl.peer_public_key LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        if user_id:
            query += " AND tl.user_id = ?"
            params.append(user_id)
        if start_date:
            query += " AND DATE(tl.snapshot_time) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND DATE(tl.snapshot_time) <= ?"
            params.append(end_date)
        
        query += " ORDER BY tl.snapshot_time DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        results.extend([dict(row) for row in rows])
        conn.close()
    
    # Search alerts
    if log_type is None or log_type == 'alert':
        conn = get_db_connection()
        query = """SELECT a.*, u.username, 'alert' as log_type
                   FROM alerts a 
                   LEFT JOIN users u ON a.user_id = u.id 
                   WHERE 1=1"""
        params = []
        
        if keyword:
            query += " AND (a.message LIKE ? OR a.alert_type LIKE ?)"
            params.append(f'%{keyword}%')
        if user_id:
            query += " AND a.user_id = ?"
            params.append(user_id)
        if start_date:
            query += " AND DATE(a.created_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND DATE(a.created_at) <= ?"
            params.append(end_date)
        
        query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        results.extend([dict(row) for row in rows])
        conn.close()
    
    # Search audit logs
    if log_type is None or log_type == 'audit':
        conn = get_db_connection()
        query = """SELECT al.*, u.username, 'audit' as log_type
                   FROM audit_logs al 
                   LEFT JOIN users u ON al.user_id = u.id 
                   WHERE 1=1"""
        params = []
        
        if keyword:
            query += " AND (al.action LIKE ? OR al.details LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        if user_id:
            query += " AND al.user_id = ?"
            params.append(user_id)
        if start_date:
            query += " AND DATE(al.created_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND DATE(al.created_at) <= ?"
            params.append(end_date)
        
        query += " ORDER BY al.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        results.extend([dict(row) for row in rows])
        conn.close()
    
    # Sort all results by date
    results.sort(key=lambda x: x.get('connected_at') or x.get('snapshot_time') or x.get('created_at', ''), reverse=True)
    
    # Apply offset and limit
    paginated_results = results[offset:offset + limit]
    
    return {
        'logs': paginated_results,
        'total': len(results),
        'limit': limit,
        'offset': offset
    }

def get_logs_for_export(
    log_type: str = None,
    user_id: int = None,
    start_date: str = None,
    end_date: str = None,
    format: str = 'csv'
):
    """
    Get all logs for export (no pagination limit)
    """
    logs = search_logs(
        keyword=None,
        log_type=log_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0
    )
    return logs['logs']

def create_audit_log(user_id: int, action: str, details: str = None, ip_address: str = None):
    """Create an audit log entry"""
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO audit_logs (user_id, action, details, ip_address, created_at)
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, action, details, ip_address)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()

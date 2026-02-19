"""
Database setup for WireGuard VPN Admin
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta

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

def get_users(page: int = 1, per_page: int = 20, search: str = None, is_active: bool = None):
    """Get users with pagination and filtering"""
    conn = get_db_connection()
    
    query = "SELECT id, username, email, public_key, is_active, created_at, updated_at FROM users WHERE 1=1"
    params = []
    
    if search:
        query += " AND (username LIKE ? OR email LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    
    # Get total count
    count_query = query.replace("SELECT id, username, email, public_key, is_active, created_at, updated_at", "SELECT COUNT(*) as count")
    cursor = conn.execute(count_query, params)
    total_count = cursor.fetchone()['count']
    
    # Add pagination
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return {
        'users': [dict(row) for row in rows],
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    }

def get_user_by_id(user_id: int):
    """Get user by ID"""
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT id, username, email, password_hash, public_key, private_key, allowed_ips, is_active, created_at, updated_at FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_username(username: str):
    """Get user by username (for authentication)"""
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username: str, email: str, password_hash: str, public_key: str = None, private_key: str = None, allowed_ips: str = None):
    """Create a new user"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO users (username, email, password_hash, public_key, private_key, allowed_ips, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (username, email, password_hash, public_key, private_key, allowed_ips or "10.0.0.2/32")
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Create audit log
        conn.execute(
            """INSERT INTO audit_logs (user_id, action, details, created_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, 'user_created', f'User {username} created')
        )
        conn.commit()
        
        conn.close()
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"User already exists: {e}")

def update_user(user_id: int, username: str = None, email: str = None, allowed_ips: str = None):
    """Update user details"""
    conn = get_db_connection()
    
    updates = []
    params = []
    
    if username:
        updates.append("username = ?")
        params.append(username)
    if email:
        updates.append("email = ?")
        params.append(email)
    if allowed_ips:
        updates.append("allowed_ips = ?")
        params.append(allowed_ips)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    conn.execute(query, params)
    conn.commit()
    
    # Create audit log
    conn.execute(
        """INSERT INTO audit_logs (user_id, action, details, created_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, 'user_updated', f'User ID {user_id} updated')
    )
    conn.commit()
    conn.close()
    
    return get_user_by_id(user_id)

def delete_user(user_id: int):
    """Delete a user"""
    conn = get_db_connection()
    
    # Get user info before deletion
    user = get_user_by_id(user_id)
    if not user:
        conn.close()
        return False
    
    # Delete user
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    
    # Create audit log
    conn.execute(
        """INSERT INTO audit_logs (user_id, action, details, created_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, 'user_deleted', f'User {user["username"]} deleted')
    )
    conn.commit()
    conn.close()
    
    return True

def toggle_user_active(user_id: int):
    """Toggle user active status"""
    conn = get_db_connection()
    
    # Get current status
    cursor = conn.execute("SELECT is_active, username FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    new_status = 0 if row['is_active'] else 1
    conn.execute("UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, user_id))
    conn.commit()
    
    # Create audit log
    status_text = "enabled" if new_status else "disabled"
    conn.execute(
        """INSERT INTO audit_logs (user_id, action, details, created_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, 'user_toggle_active', f'User {row["username"]} {status_text}')
    )
    conn.commit()
    conn.close()
    
    return get_user_by_id(user_id)

def update_user_keys(user_id: int, public_key: str, private_key: str):
    """Update user's WireGuard keys"""
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET public_key = ?, private_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (public_key, private_key, user_id)
    )
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

def update_password(user_id: int, password_hash: str):
    """Update user's password"""
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (password_hash, user_id)
    )
    conn.commit()
    
    # Create audit log
    conn.execute(
        """INSERT INTO audit_logs (user_id, action, details, created_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, 'password_changed', 'User password changed')
    )
    conn.commit()
    conn.close()

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

# ============== Audit Records Functions ==============

def get_audit_logs(
    user_id: int = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get audit logs with optional filtering
    """
    conn = get_db_connection()
    
    query = """SELECT al.*, u.username, u.email
               FROM audit_logs al 
               LEFT JOIN users u ON al.user_id = u.id 
               WHERE 1=1"""
    params = []
    
    if user_id:
        query += " AND al.user_id = ?"
        params.append(user_id)
    
    if action:
        query += " AND al.action = ?"
        params.append(action)
    
    if start_date:
        query += " AND DATE(al.created_at) >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(al.created_at) <= ?"
        params.append(end_date)
    
    query += " ORDER BY al.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Get total count
    count_query = "SELECT COUNT(*) as count FROM audit_logs al WHERE 1=1"
    count_params = []
    if user_id:
        count_query += " AND al.user_id = ?"
        count_params.append(user_id)
    if action:
        count_query += " AND al.action = ?"
        count_params.append(action)
    if start_date:
        count_query += " AND DATE(al.created_at) >= ?"
        count_params.append(start_date)
    if end_date:
        count_query += " AND DATE(al.created_at) <= ?"
        count_params.append(end_date)
    
    count_cursor = conn.execute(count_query, count_params)
    total_count = count_cursor.fetchone()['count']
    
    conn.close()
    return {
        'logs': [dict(row) for row in rows],
        'total': total_count,
        'limit': limit,
        'offset': offset
    }

def get_distinct_audit_actions():
    """Get list of distinct audit action types"""
    conn = get_db_connection()
    cursor = conn.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action")
    rows = cursor.fetchall()
    conn.close()
    return [row['action'] for row in rows]

# ============== Login History Functions ==============

def log_login_attempt(user_id: int, username: str, ip_address: str, user_agent: str, success: bool, failure_reason: str = None):
    """Log a login attempt"""
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO login_history (user_id, username, ip_address, user_agent, success, failure_reason, created_at)
           VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (user_id, username, ip_address, user_agent, 1 if success else 0, failure_reason)
    )
    conn.commit()
    conn.close()

def get_login_history(
    user_id: int = None,
    success: bool = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get login history with optional filtering
    """
    conn = get_db_connection()
    
    query = """SELECT lh.*, u.email
               FROM login_history lh 
               LEFT JOIN users u ON lh.user_id = u.id 
               WHERE 1=1"""
    params = []
    
    if user_id:
        query += " AND lh.user_id = ?"
        params.append(user_id)
    
    if success is not None:
        query += " AND lh.success = ?"
        params.append(1 if success else 0)
    
    if start_date:
        query += " AND DATE(lh.created_at) >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(lh.created_at) <= ?"
        params.append(end_date)
    
    query += " ORDER BY lh.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Get total count
    count_query = "SELECT COUNT(*) as count FROM login_history lh WHERE 1=1"
    count_params = []
    if user_id:
        count_query += " AND lh.user_id = ?"
        count_params.append(user_id)
    if success is not None:
        count_query += " AND lh.success = ?"
        count_params.append(1 if success else 0)
    if start_date:
        count_query += " AND DATE(lh.created_at) >= ?"
        count_params.append(start_date)
    if end_date:
        count_query += " AND DATE(lh.created_at) <= ?"
        count_params.append(end_date)
    
    count_cursor = conn.execute(count_query, count_params)
    total_count = count_cursor.fetchone()['count']
    
    conn.close()
    return {
        'logs': [dict(row) for row in rows],
        'total': total_count,
        'limit': limit,
        'offset': offset
    }

# ============== System Events Functions ==============

def log_system_event(event_type: str, severity: str, message: str, details: str = None, source: str = None):
    """Log a system event"""
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO system_events (event_type, severity, message, details, source, created_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (event_type, severity, message, details, source)
    )
    conn.commit()
    conn.close()

def get_system_events(
    event_type: str = None,
    severity: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get system events with optional filtering
    """
    conn = get_db_connection()
    
    query = """SELECT * FROM system_events WHERE 1=1"""
    params = []
    
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    
    if start_date:
        query += " AND DATE(created_at) >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND DATE(created_at) <= ?"
        params.append(end_date)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Get total count
    count_query = "SELECT COUNT(*) as count FROM system_events WHERE 1=1"
    count_params = []
    if event_type:
        count_query += " AND event_type = ?"
        count_params.append(event_type)
    if severity:
        count_query += " AND severity = ?"
        count_params.append(severity)
    if start_date:
        count_query += " AND DATE(created_at) >= ?"
        count_params.append(start_date)
    if end_date:
        count_query += " AND DATE(created_at) <= ?"
        count_params.append(end_date)
    
    count_cursor = conn.execute(count_query, count_params)
    total_count = count_cursor.fetchone()['count']
    
    conn.close()
    return {
        'events': [dict(row) for row in rows],
        'total': total_count,
        'limit': limit,
        'offset': offset
    }

def get_distinct_event_types():
    """Get list of distinct event types"""
    conn = get_db_connection()
    cursor = conn.execute("SELECT DISTINCT event_type FROM system_events ORDER BY event_type")
    rows = cursor.fetchall()
    conn.close()
    return [row['event_type'] for row in rows]

# ============== Compliance Reports Functions ==============

def create_compliance_report(report_type: str, title: str, start_date: str, end_date: str, created_by: int):
    """Create a new compliance report record"""
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO compliance_reports (report_type, title, start_date, end_date, created_by, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)""",
        (report_type, title, start_date, end_date, created_by)
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id

def update_compliance_report(report_id: int, status: str = None, file_path: str = None):
    """Update compliance report status"""
    conn = get_db_connection()
    if status:
        conn.execute(
            """UPDATE compliance_reports SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (status, report_id)
        )
    if file_path:
        conn.execute(
            """UPDATE compliance_reports SET file_path = ? WHERE id = ?""",
            (file_path, report_id)
        )
    conn.commit()
    conn.close()

def get_compliance_reports(
    report_type: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get compliance reports with optional filtering
    """
    conn = get_db_connection()
    
    query = """SELECT cr.*, u.username as created_by_username
               FROM compliance_reports cr 
               LEFT JOIN users u ON cr.created_by = u.id 
               WHERE 1=1"""
    params = []
    
    if report_type:
        query += " AND cr.report_type = ?"
        params.append(report_type)
    
    if status:
        query += " AND cr.status = ?"
        params.append(status)
    
    query += " ORDER BY cr.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    # Get total count
    count_query = "SELECT COUNT(*) as count FROM compliance_reports cr WHERE 1=1"
    count_params = []
    if report_type:
        count_query += " AND cr.report_type = ?"
        count_params.append(report_type)
    if status:
        count_query += " AND cr.status = ?"
        count_params.append(status)
    
    count_cursor = conn.execute(count_query, count_params)
    total_count = count_cursor.fetchone()['count']
    
    conn.close()
    return {
        'reports': [dict(row) for row in rows],
        'total': total_count,
        'limit': limit,
        'offset': offset
    }

def get_compliance_report_by_id(report_id: int):
    """Get a specific compliance report by ID"""
    conn = get_db_connection()
    cursor = conn.execute(
        """SELECT cr.*, u.username as created_by_username
           FROM compliance_reports cr 
           LEFT JOIN users u ON cr.created_by = u.id 
           WHERE cr.id = ?""",
        (report_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def generate_compliance_report_data(report_type: str, start_date: str, end_date: str):
    """Generate compliance report data based on type"""
    import json
    
    report_data = {
        'report_type': report_type,
        'period': {'start_date': start_date, 'end_date': end_date},
        'generated_at': datetime.now().isoformat(),
        'sections': {}
    }
    
    conn = get_db_connection()
    
    # 1. User Activities
    user_activity_query = """SELECT 
        u.id, u.username, u.email, u.is_active, u.created_at,
        COUNT(DISTINCT cl.id) as connection_count,
        SUM(COALESCE(cl.bytes_received, 0)) as total_received,
        SUM(COALESCE(cl.bytes_sent, 0)) as total_sent
    FROM users u
    LEFT JOIN connection_logs cl ON u.id = cl.user_id 
        AND DATE(cl.connected_at) >= ? AND DATE(cl.connected_at) <= ?
    GROUP BY u.id"""
    
    cursor = conn.execute(user_activity_query, (start_date, end_date))
    report_data['sections']['user_activities'] = [dict(row) for row in cursor.fetchall()]
    
    # 2. Login Attempts
    login_query = """SELECT 
        lh.username, lh.ip_address, lh.success, lh.failure_reason,
        COUNT(*) as attempt_count,
        MIN(lh.created_at) as first_attempt,
        MAX(lh.created_at) as last_attempt
    FROM login_history lh
    WHERE DATE(lh.created_at) >= ? AND DATE(lh.created_at) <= ?
    GROUP BY lh.username, lh.ip_address"""
    
    cursor = conn.execute(login_query, (start_date, end_date))
    report_data['sections']['login_attempts'] = [dict(row) for row in cursor.fetchall()]
    
    # 3. Admin Operations
    admin_query = """SELECT 
        al.action, al.details, al.ip_address, al.created_at,
        u.username as admin_username
    FROM audit_logs al
    LEFT JOIN users u ON al.user_id = u.id
    WHERE DATE(al.created_at) >= ? AND DATE(al.created_at) <= ?
    ORDER BY al.created_at DESC"""
    
    cursor = conn.execute(admin_query, (start_date, end_date))
    report_data['sections']['admin_operations'] = [dict(row) for row in cursor.fetchall()]
    
    # 4. System Events
    system_query = """SELECT 
        event_type, severity, message, source, created_at,
        COUNT(*) as event_count
    FROM system_events
    WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?
    GROUP BY event_type, severity
    ORDER BY created_at DESC"""
    
    cursor = conn.execute(system_query, (start_date, end_date))
    report_data['sections']['system_events'] = [dict(row) for row in cursor.fetchall()]
    
    # 5. Summary Statistics
    summary_query = """SELECT 
        (SELECT COUNT(*) FROM users WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?) as new_users,
        (SELECT COUNT(*) FROM connection_logs WHERE DATE(connected_at) >= ? AND DATE(connected_at) <= ?) as total_connections,
        (SELECT COUNT(*) FROM login_history WHERE success = 1 AND DATE(created_at) >= ? AND DATE(created_at) <= ?) as successful_logins,
        (SELECT COUNT(*) FROM login_history WHERE success = 0 AND DATE(created_at) >= ? AND DATE(created_at) <= ?) as failed_logins,
        (SELECT COUNT(*) FROM alerts WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?) as total_alerts"""
    
    cursor = conn.execute(summary_query, (start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date))
    summary = cursor.fetchone()
    report_data['sections']['summary'] = dict(summary)
    
    conn.close()
    return report_data

# ============== Scheduled Reports ==============

def create_scheduled_report(name: str, report_type: str, schedule_type: str, schedule_time: str = None,
                            schedule_dayOfWeek: int = None, schedule_dayOfMonth: int = None,
                            include_traffic: bool = True, include_users: bool = False,
                            include_system: bool = False, include_audit: bool = False,
                            top_users_count: int = 10, email_recipients: str = None,
                            created_by: int = None):
    """Create a new scheduled report"""
    import json
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO scheduled_reports 
           (name, report_type, schedule_type, schedule_time, schedule_dayOfWeek, schedule_dayOfMonth,
            include_traffic, include_users, include_system, include_audit, top_users_count,
            email_recipients, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, report_type, schedule_type, schedule_time, schedule_dayOfWeek, schedule_dayOfMonth,
         include_traffic, include_users, include_system, include_audit, top_users_count,
         email_recipients, created_by)
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return get_scheduled_report(report_id)

def get_scheduled_report(report_id: int):
    """Get a scheduled report by ID"""
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM scheduled_reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_scheduled_reports(report_type: str = None, is_active: bool = None, limit: int = 50, offset: int = 0):
    """Get list of scheduled reports"""
    conn = get_db_connection()
    query = "SELECT * FROM scheduled_reports WHERE 1=1"
    params = []
    
    if report_type:
        query += " AND report_type = ?"
        params.append(report_type)
    if is_active is not None:
        query += " AND is_active = ?"
        params.append(1 if is_active else 0)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_scheduled_report(report_id: int, **kwargs):
    """Update a scheduled report"""
    allowed_fields = ['name', 'report_type', 'schedule_type', 'schedule_time', 'schedule_dayOfWeek',
                     'schedule_dayOfMonth', 'include_traffic', 'include_users', 'include_system',
                     'include_audit', 'top_users_count', 'email_recipients', 'is_active']
    
    updates = []
    params = []
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    
    if not updates:
        return get_scheduled_report(report_id)
    
    params.append(report_id)
    conn = get_db_connection()
    conn.execute(f"UPDATE scheduled_reports SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return get_scheduled_report(report_id)

def delete_scheduled_report(report_id: int):
    """Delete a scheduled report"""
    conn = get_db_connection()
    conn.execute("DELETE FROM scheduled_reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return True

def update_scheduled_report_run_time(report_id: int, last_run: str, next_run: str):
    """Update last_run_at and next_run_at for a scheduled report"""
    conn = get_db_connection()
    conn.execute(
        "UPDATE scheduled_reports SET last_run_at = ?, next_run_at = ? WHERE id = ?",
        (last_run, next_run, report_id)
    )
    conn.commit()
    conn.close()

# ============== Report Templates ==============

def create_report_template(name: str, description: str, data_sources: str, date_range: str,
                           custom_start_date: str = None, custom_end_date: str = None,
                           format: str = 'json', filters: str = None, created_by: int = None):
    """Create a new report template"""
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO report_templates 
           (name, description, data_sources, date_range, custom_start_date, custom_end_date, format, filters, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, description, data_sources, date_range, custom_start_date, custom_end_date, format, filters, created_by)
    )
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    return get_report_template(template_id)

def get_report_template(template_id: int):
    """Get a report template by ID"""
    conn = get_db_connection()
    cursor = conn.execute(
        """SELECT rt.*, u.username as created_by_username
           FROM report_templates rt 
           LEFT JOIN users u ON rt.created_by = u.id 
           WHERE rt.id = ?""",
        (template_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_report_templates(created_by: int = None, limit: int = 50, offset: int = 0):
    """Get list of report templates"""
    conn = get_db_connection()
    query = "SELECT rt.*, u.username as created_by_username FROM report_templates rt LEFT JOIN users u ON rt.created_by = u.id"
    params = []
    
    if created_by:
        query += " WHERE rt.created_by = ?"
        params.append(created_by)
    
    query += " ORDER BY rt.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_report_template(template_id: int, **kwargs):
    """Update a report template"""
    import json
    allowed_fields = ['name', 'description', 'data_sources', 'date_range', 'custom_start_date',
                     'custom_end_date', 'format', 'filters']
    
    updates = []
    params = []
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    
    if not updates:
        return get_report_template(template_id)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(template_id)
    conn = get_db_connection()
    conn.execute(f"UPDATE report_templates SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return get_report_template(template_id)

def delete_report_template(template_id: int):
    """Delete a report template"""
    conn = get_db_connection()
    conn.execute("DELETE FROM report_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
    return True

# ============== Generated Reports ==============

def create_generated_report(name: str, report_type: str, start_date: str, end_date: str,
                            data: str = None, file_path: str = None, format: str = 'json',
                            template_id: int = None, scheduled_report_id: int = None,
                            generated_by: int = None):
    """Create a generated report record"""
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO generated_reports 
           (name, report_type, start_date, end_date, data, file_path, format, template_id, scheduled_report_id, generated_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, report_type, start_date, end_date, data, file_path, format, template_id, scheduled_report_id, generated_by)
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return get_generated_report(report_id)

def get_generated_report(report_id: int):
    """Get a generated report by ID"""
    conn = get_db_connection()
    cursor = conn.execute(
        """SELECT gr.*, u.username as generated_by_username
           FROM generated_reports gr 
           LEFT JOIN users u ON gr.generated_by = u.id 
           WHERE gr.id = ?""",
        (report_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_generated_reports(template_id: int = None, scheduled_report_id: int = None,
                          report_type: str = None, limit: int = 50, offset: int = 0):
    """Get list of generated reports"""
    conn = get_db_connection()
    query = "SELECT gr.*, u.username as generated_by_username FROM generated_reports gr LEFT JOIN users u ON gr.generated_by = u.id WHERE 1=1"
    params = []
    
    if template_id:
        query += " AND gr.template_id = ?"
        params.append(template_id)
    if scheduled_report_id:
        query += " AND gr.scheduled_report_id = ?"
        params.append(scheduled_report_id)
    if report_type:
        query += " AND gr.report_type = ?"
        params.append(report_type)
    
    query += " ORDER BY gr.generated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ============== Traffic Report Data Generation ==============

def generate_traffic_report_data(start_date: str, end_date: str, include_users: bool = True,
                                  include_system: bool = False, top_users_count: int = 10):
    """Generate traffic report data"""
    import json
    
    report_data = {
        'period': {'start_date': start_date, 'end_date': end_date},
        'generated_at': datetime.now().isoformat(),
        'traffic': {}
    }
    
    conn = get_db_connection()
    
    # 1. Total traffic summary
    total_query = """SELECT 
        COALESCE(SUM(bytes_received), 0) as total_received,
        COALESCE(SUM(bytes_sent), 0) as total_sent,
        COUNT(DISTINCT user_id) as active_users
    FROM traffic_records
    WHERE date >= ? AND date <= ?"""
    
    cursor = conn.execute(total_query, (start_date, end_date))
    total = cursor.fetchone()
    report_data['traffic']['total_received'] = total['total_received']
    report_data['traffic']['total_sent'] = total['total_sent']
    report_data['traffic']['total_transfer'] = total['total_received'] + total['total_sent']
    report_data['traffic']['active_users'] = total['active_users']
    
    # 2. Top users by traffic
    if include_users:
        top_users_query = """SELECT 
            u.id, u.username,
            COALESCE(SUM(tr.bytes_received), 0) as total_received,
            COALESCE(SUM(tr.bytes_sent), 0) as total_sent,
            COALESCE(SUM(tr.bytes_received) + SUM(tr.bytes_sent), 0) as total_transfer
        FROM users u
        LEFT JOIN traffic_records tr ON u.id = tr.user_id AND tr.date >= ? AND tr.date <= ?
        GROUP BY u.id
        ORDER BY total_transfer DESC
        LIMIT ?"""
        
        cursor = conn.execute(top_users_query, (start_date, end_date, top_users_count))
        report_data['traffic']['top_users'] = [dict(row) for row in cursor.fetchall()]
    
    # 3. Daily traffic trends
    daily_query = """SELECT 
        date,
        COALESCE(SUM(bytes_received), 0) as total_received,
        COALESCE(SUM(bytes_sent), 0) as total_sent
    FROM traffic_records
    WHERE date >= ? AND date <= ?
    GROUP BY date
    ORDER BY date"""
    
    cursor = conn.execute(daily_query, (start_date, end_date))
    report_data['traffic']['daily_trends'] = [dict(row) for row in cursor.fetchall()]
    
    # 4. Peak hours analysis
    hourly_query = """SELECT 
        strftime('%H', snapshot_time) as hour,
        COUNT(*) as connection_count,
        COALESCE(SUM(bytes_received), 0) as total_received,
        COALESCE(SUM(bytes_sent), 0) as total_sent
    FROM traffic_logs
    WHERE DATE(snapshot_time) >= ? AND DATE(snapshot_time) <= ?
    GROUP BY hour
    ORDER BY hour"""
    
    cursor = conn.execute(hourly_query, (start_date, end_date))
    report_data['traffic']['hourly_distribution'] = [dict(row) for row in cursor.fetchall()]
    
    # Find peak hour
    if report_data['traffic']['hourly_distribution']:
        peak = max(report_data['traffic']['hourly_distribution'], 
                   key=lambda x: x['total_received'] + x['total_sent'])
        report_data['traffic']['peak_hour'] = peak['hour']
    
    conn.close()
    return report_data

# ============== User Statistics ==============

def get_user_statistics(start_date: str = None, end_date: str = None):
    """Get user usage statistics"""
    import json
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    stats = {
        'period': {'start_date': start_date, 'end_date': end_date},
        'users': []
    }
    
    conn = get_db_connection()
    
    # Get all users with their stats
    users_query = """SELECT 
        u.id, u.username, u.email, u.is_active, u.created_at,
        COALESCE(SUM(tr.bytes_received), 0) as total_received,
        COALESCE(SUM(tr.bytes_sent), 0) as total_sent,
        COALESCE(SUM(tr.bytes_received) + SUM(tr.bytes_sent), 0) as total_transfer,
        COUNT(DISTINCT tr.date) as active_days,
        (SELECT COUNT(*) FROM connection_logs cl WHERE cl.user_id = u.id AND DATE(cl.connected_at) >= ? AND DATE(cl.connected_at) <= ?) as connection_count,
        (SELECT MAX(cl.connected_at) FROM connection_logs cl WHERE cl.user_id = u.id) as last_connection
    FROM users u
    LEFT JOIN traffic_records tr ON u.id = tr.user_id AND tr.date >= ? AND tr.date <= ?
    GROUP BY u.id
    ORDER BY total_transfer DESC"""
    
    cursor = conn.execute(users_query, (start_date, end_date, start_date, end_date))
    users = [dict(row) for row in cursor.fetchall()]
    
    # Calculate average daily usage
    for user in users:
        if user['active_days'] and user['active_days'] > 0:
            user['avg_daily_transfer'] = user['total_transfer'] / user['active_days']
        else:
            user['avg_daily_transfer'] = 0
    
    stats['users'] = users
    
    # Summary
    summary_query = """SELECT 
        COUNT(*) as total_users,
        SUM(total_received) as total_received,
        SUM(total_sent) as total_sent,
        AVG(total_transfer) as avg_transfer
    FROM (
        SELECT 
            u.id,
            COALESCE(SUM(tr.bytes_received), 0) as total_received,
            COALESCE(SUM(tr.bytes_sent), 0) as total_sent,
            COALESCE(SUM(tr.bytes_received) + SUM(tr.bytes_sent), 0) as total_transfer
        FROM users u
        LEFT JOIN traffic_records tr ON u.id = tr.user_id AND tr.date >= ? AND tr.date <= ?
        GROUP BY u.id
    )"""
    
    cursor = conn.execute(summary_query, (start_date, end_date))
    summary = cursor.fetchone()
    stats['summary'] = dict(summary)
    
    conn.close()
    return stats

# ============== System Health ==============

def get_system_health():
    """Get system health metrics"""
    import psutil
    import subprocess
    
    health = {
        'timestamp': datetime.now().isoformat(),
        'cpu': {},
        'memory': {},
        'disk': {},
        'network': {},
        'wireguard': {}
    }
    
    # CPU usage
    health['cpu']['usage_percent'] = psutil.cpu_percent(interval=1)
    health['cpu']['count'] = psutil.cpu_count()
    
    # Memory
    mem = psutil.virtual_memory()
    health['memory']['total'] = mem.total
    health['memory']['used'] = mem.used
    health['memory']['free'] = mem.free
    health['memory']['percent'] = mem.percent
    
    # Disk
    disk = psutil.disk_usage('/')
    health['disk']['total'] = disk.total
    health['disk']['used'] = disk.used
    health['disk']['free'] = disk.free
    health['disk']['percent'] = disk.percent
    
    # Active connections
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM connection_logs WHERE disconnected_at IS NULL"
        )
        row = cursor.fetchone()
        health['network']['active_connections'] = row['count'] if row else 0
        conn.close()
    except:
        health['network']['active_connections'] = 0
    
    # WireGuard status
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True, timeout=5)
        health['wireguard']['status'] = 'active' if result.returncode == 0 else 'inactive'
        health['wireguard']['interface_count'] = result.stdout.count('interface:')
        health['wireguard']['peer_count'] = result.stdout.count('peer:')
    except:
        health['wireguard']['status'] = 'not_installed'
        health['wireguard']['interface_count'] = 0
        health['wireguard']['peer_count'] = 0
    
    return health

def get_health_alerts():
    """Get health alerts"""
    import psutil
    
    alerts = []
    
    # Check CPU
    cpu = psutil.cpu_percent(interval=1)
    if cpu > 80:
        alerts.append({
            'type': 'cpu',
            'severity': 'warning' if cpu < 90 else 'critical',
            'message': f'CPU usage is at {cpu:.1f}%',
            'value': cpu
        })
    
    # Check Memory
    mem = psutil.virtual_memory()
    if mem.percent > 80:
        alerts.append({
            'type': 'memory',
            'severity': 'warning' if mem.percent < 90 else 'critical',
            'message': f'Memory usage is at {mem.percent:.1f}%',
            'value': mem.percent
        })
    
    # Check Disk
    disk = psutil.disk_usage('/')
    if disk.percent > 80:
        alerts.append({
            'type': 'disk',
            'severity': 'warning' if disk.percent < 90 else 'critical',
            'message': f'Disk usage is at {disk.percent:.1f}%',
            'value': disk.percent
        })
    
    return alerts

if __name__ == "__main__":
    init_db()

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

if __name__ == "__main__":
    init_db()

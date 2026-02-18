"""
Database setup for WireGuard VPN Admin
"""

import sqlite3
from pathlib import Path

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

if __name__ == "__main__":
    init_db()

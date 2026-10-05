import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "server_room.db")


def _query(sql: str, params: tuple = ()):
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_all_servers():
    return _query("SELECT id, name, type, status FROM servers ORDER BY name")


def get_server_by_name(name: str):
    rows = _query("SELECT id, name, type, status FROM servers WHERE name = ?", (name,))
    return rows[0] if rows else None


def get_incidents():
    return _query("""
        SELECT servers.name AS server, incidents.description AS description
        FROM incidents
        JOIN servers ON incidents.server_id = servers.id
        ORDER BY servers.name
    """)


def get_stats():
    return _query("""
        SELECT status, COUNT(*) AS total
        FROM servers
        GROUP BY status
        ORDER BY total DESC
    """)
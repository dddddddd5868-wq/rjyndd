DB_NAME = "tg_bot.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn  = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'жив'
        )
    """)

    conn.commit()
    conn.close()

def add_server(name:str, server_type:str, status:str="жив"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO servers (name, server_type, status) VALUES (?, ?, ?)",
        (name, server_type, status)
                 )
    conn.commit()
    conn.close()

def get_all_servers():
    conn = get_connection()

    rows = conn.execute("SELECT id, name, type, status FROM servers").fetchall()

    conn.close()

    return rows

def get_server_by_name(name:str):
    conn = get_connection()

    row = conn.execute(
        "SELECT id, name, type, status FROM servers WHERE name = ?", (name,)).fetchone()

    conn.close()

    return row

def update_server_status(name:str, new_status:str) -> bool:

    conn = get_connection()

    cursor = conn.execute(
        "UPDATE servers SET status = ? WHERE name = ?", (new_status, name)
    )
    
    conn.commit()
    
    updated = cursor.rowcount > 0
    conn.close()

    return updated

def delete_server(name:str) -> bool:
    conn = get_connection()

    cursor = conn.execute(
        "DELETE FROM servers WHERE name = ?", (name,)
    )
    
    conn.commit()
    
    deleted = cursor.rowcount > 0
    conn.close()

    return deleted
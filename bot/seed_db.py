import sqlite3

conn = sqlite3.connect("server_room.db")
conn.executescript("""
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS servers;

CREATE TABLE servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'жив'
);
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    server_id INTEGER,
    FOREIGN KEY (server_id) REFERENCES servers (id)
);

INSERT INTO servers (name, type, status) VALUES
    ('web_server', 'web', 'жив'),
    ('db_server', 'db', 'грустит'),
    ('backup_server', 'backup', 'мёртв'),
    ('mail_server', 'mail', 'работает');

INSERT INTO incidents (description, server_id) VALUES
    ('диск заполнен на 67%, админ делает вид, что не видит', 2),
    ('бэкап не отвечает 3-й день, классика', 3),
    ('кто-то запустил rm-rf в проде, это был стажёр (его последний день)', 1),
    ('база ушла в отпуск без предупреждения', 2);
""")
conn.commit()
conn.close()
print("server_room.db готов")
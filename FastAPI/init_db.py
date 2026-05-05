import sqlite3

print("Đang khởi tạo / cập nhật database...")

conn = sqlite3.connect("bots.db", timeout=10)
cur = conn.cursor()

# Tạo bảng users
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Tạo bảng bots với cấu trúc đầy đủ
cur.execute("""
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT UNIQUE NOT NULL,
    page_token TEXT NOT NULL,
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Thêm cột created_at nếu bảng cũ chưa có
try:
    cur.execute("ALTER TABLE bots ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("✅ Đã thêm cột 'created_at' vào bảng bots")
except sqlite3.OperationalError:
    print("Cột 'created_at' đã tồn tại")

# Insert admin mặc định
cur.execute("""
INSERT OR IGNORE INTO users (username, password)
VALUES ('admin', '123456')
""")

conn.commit()
conn.close()

print("✅ Database đã được cập nhật thành công!")
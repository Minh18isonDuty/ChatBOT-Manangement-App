# =====================================================
# init_db.py - Script khởi tạo / reset database
# Chạy: python init_db.py
#
# ⚠️  Script này an toàn để chạy nhiều lần (idempotent).
#     Dùng IF NOT EXISTS và try/except để không bị lỗi
#     khi bảng/cột đã tồn tại.
# =====================================================

import sqlite3
import hashlib

DB_NAME = "bots.db"


def hash_password(password: str) -> str:
    """Hash password SHA-256 — khớp với db.py."""
    return hashlib.sha256(password.encode()).hexdigest()


def init():
    print(f"🚀 Khởi tạo database: {DB_NAME}")
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cur = conn.cursor()

    # ── Bảng users ────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Bảng users OK")

    # ── Bảng bots ─────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id       TEXT UNIQUE NOT NULL,
            page_token    TEXT NOT NULL,
            name          TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            is_active     INTEGER DEFAULT 1,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Bảng bots OK")

    # ── Bảng messages ─────────────────────────────────
    # FIX: Đây là bảng bị thiếu gây lỗi 500
    # "sqlite3.OperationalError: no such table: messages"
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id      TEXT NOT NULL,
            sender_id    TEXT NOT NULL,
            message      TEXT NOT NULL,
            is_from_user INTEGER NOT NULL CHECK (is_from_user IN (0, 1)),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES bots(page_id) ON DELETE CASCADE
        )
    """)
    print("✅ Bảng messages OK")

    # ── Index ─────────────────────────────────────────
    # Tăng tốc query lịch sử chat theo page_id + thời gian
    try:
        cur.execute("""
            CREATE INDEX idx_messages_page_created
            ON messages (page_id, created_at ASC)
        """)
        print("✅ Index idx_messages_page_created OK")
    except sqlite3.OperationalError:
        print("   Index đã tồn tại — bỏ qua")

    # ── Migrations: thêm column nếu bảng cũ thiếu ────
    _migrate_add_column(cur, "bots", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    # ── Seed admin mặc định ───────────────────────────
    # FIX: password được hash — khớp với verify_user() trong db.py
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
        ("admin", hash_password("123456"))
    )
    print("✅ Admin user OK")

    conn.commit()
    conn.close()

    # ── Verify kết quả ────────────────────────────────
    _verify(DB_NAME)


def _migrate_add_column(cur: sqlite3.Cursor, table: str, column: str, definition: str):
    """Thêm column vào bảng đã tồn tại nếu chưa có."""
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"✅ Migration: thêm cột '{column}' vào bảng {table}")
    except sqlite3.OperationalError:
        pass  # Column đã tồn tại


def _verify(db_name: str):
    """Kiểm tra lại các bảng đã được tạo đúng."""
    print("\n📋 Xác minh schema:")
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    print(f"   Tables: {tables}")

    required = {"users", "bots", "messages"}
    missing = required - set(tables)
    if missing:
        print(f"❌ THIẾU BẢNG: {missing}")
    else:
        print("✅ Tất cả bảng đã sẵn sàng")

    # In schema của messages để confirm
    cur.execute("PRAGMA table_info(messages)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"   messages columns: {cols}")

    conn.close()
    print("\n🎉 Database khởi tạo thành công!")


if __name__ == "__main__":
    init()
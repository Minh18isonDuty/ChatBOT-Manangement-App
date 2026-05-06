# =====================================================
# db.py - Database connection và helper functions
# Version: 2.0 - Optimized
# =====================================================

import sqlite3
import hashlib
import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_NAME = "bots.db"


# =====================================================
# UTILS
# =====================================================
def hash_password(password: str) -> str:
    """Hash password bằng SHA-256. Production nên dùng bcrypt."""
    return hashlib.sha256(password.encode()).hexdigest()


# =====================================================
# CONTEXT MANAGER
# =====================================================
@contextmanager
def get_db_connection():
    """
    Context manager quản lý connection SQLite.
    - WAL mode: cho phép đọc đồng thời khi đang ghi
    - foreign_keys=ON: enforce FK constraints
    - row_factory: trả về dict-like rows
    """
    conn = None
    try:
        conn = sqlite3.connect(
            DB_NAME,
            timeout=15,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        # Auto-commit nếu không có lỗi
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


# =====================================================
# INIT DATABASE
# =====================================================
def init_database():
    """
    Khởi tạo toàn bộ schema database.
    Dùng CREATE TABLE IF NOT EXISTS để idempotent —
    có thể gọi nhiều lần mà không bị lỗi.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()

        # --- Bảng users ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                password TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- Bảng bots ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id       TEXT    UNIQUE NOT NULL,
                page_token    TEXT    NOT NULL,
                name          TEXT    NOT NULL,
                system_prompt TEXT    NOT NULL,
                is_active     INTEGER DEFAULT 1,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- Bảng messages ---
        # is_from_user: 1 = khách hàng gửi, 0 = bot trả lời
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id      TEXT    NOT NULL,
                sender_id    TEXT    NOT NULL,
                message      TEXT    NOT NULL,
                is_from_user INTEGER NOT NULL CHECK (is_from_user IN (0, 1)),
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (page_id) REFERENCES bots(page_id) ON DELETE CASCADE
            )
        """)

        # --- Index để tăng tốc query lịch sử chat ---
        # Không dùng IF NOT EXISTS vì SQLite < 3.36 không hỗ trợ
        # Dùng try/except để bỏ qua nếu index đã tồn tại
        try:
            cur.execute("""
                CREATE INDEX idx_messages_page_id_created
                ON messages (page_id, created_at ASC)
            """)
        except sqlite3.OperationalError:
            pass  # Index đã tồn tại — bỏ qua

        # --- Seed admin mặc định (password đã hash) ---
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
            ("admin", hash_password("123456"))
        )

        print("✅ Database initialized successfully")
        _verify_tables(cur)


def _verify_tables(cur: sqlite3.Cursor):
    """Debug helper: in ra danh sách bảng đã tạo."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    print(f"📋 Tables: {tables}")


# =====================================================
# MIGRATION HELPER
# Dùng khi cần thêm column vào bảng đã tồn tại
# =====================================================
def run_migrations():
    """
    Chạy các migration cần thiết.
    Thêm vào đây khi schema thay đổi thay vì xóa DB.
    """
    migrations = [
        # Ví dụ: thêm cột nếu chưa có
        # ("ALTER TABLE bots ADD COLUMN description TEXT DEFAULT ''",),
    ]
    with get_db_connection() as conn:
        for migration in migrations:
            try:
                conn.execute(migration[0])
                print(f"✅ Migration applied: {migration[0][:50]}...")
            except sqlite3.OperationalError:
                pass  # Đã tồn tại


# =====================================================
# USER FUNCTIONS
# =====================================================
def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Xác thực user. Trả về user dict nếu đúng, None nếu sai."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password))
        )
        row = cur.fetchone()
        return dict(row) if row else None


# =====================================================
# BOT FUNCTIONS
# =====================================================
def get_all_bots() -> List[Dict[str, Any]]:
    """Lấy toàn bộ danh sách bot, sắp xếp mới nhất lên đầu."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, page_id, name, is_active 
            FROM bots 
            ORDER BY id DESC
        """)
        return [dict(row) for row in cur.fetchall()]


def get_bot_by_id(bot_id: int) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết bot theo ID."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, page_id, name, system_prompt, is_active,
                   COALESCE(created_at, '') AS created_at
            FROM bots 
            WHERE id = ?
        """, (bot_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_bot_by_page(page_id: str) -> Optional[Dict[str, Any]]:
    """
    Lấy bot đang active theo page_id.
    Dùng trong webhook handler để check bot có bật không.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, page_token, system_prompt, is_active
            FROM bots 
            WHERE page_id = ? AND is_active = 1
        """, (page_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_bot(
    page_id: str,
    page_token: str,
    name: str,
    system_prompt: str
) -> Optional[int]:
    """
    Tạo bot mới.
    Trả về bot_id nếu thành công, None nếu page_id đã tồn tại.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Kiểm tra duplicate page_id
            cur.execute("SELECT id FROM bots WHERE page_id = ?", (page_id,))
            if cur.fetchone():
                print(f"⚠️  [DB] Page ID '{page_id}' đã tồn tại")
                return None

            cur.execute("""
                INSERT INTO bots (page_id, page_token, name, system_prompt, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (page_id, page_token or "default_token", name, system_prompt))

            bot_id = cur.lastrowid
            print(f"✅ [DB] Tạo bot ID={bot_id} | page_id={page_id} | name={name}")
            return bot_id

    except Exception as e:
        print(f"❌ [DB ERROR] create_bot: {e}")
        return None


def update_bot(bot_id: int, is_active: Optional[int] = None) -> bool:
    """
    Cập nhật trạng thái bot.
    Hiện tại chỉ hỗ trợ is_active, có thể mở rộng thêm fields.
    """
    if is_active is None:
        return False
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE bots SET is_active = ? WHERE id = ?",
                (is_active, bot_id)
            )
            success = cur.rowcount > 0
            if success:
                print(f"✅ [DB] Bot {bot_id} → is_active={is_active}")
            return success
    except Exception as e:
        print(f"❌ [DB ERROR] update_bot: {e}")
        return False


def delete_bot(bot_id: int) -> bool:
    """
    Xóa bot theo ID.
    Messages liên quan sẽ bị xóa theo nhờ ON DELETE CASCADE.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
            success = cur.rowcount > 0
            if success:
                print(f"✅ [DB] Đã xóa bot ID={bot_id}")
            return success
    except Exception as e:
        print(f"❌ [DB ERROR] delete_bot: {e}")
        return False


# =====================================================
# MESSAGE FUNCTIONS
# =====================================================
def save_message(
    page_id: str,
    sender_id: str,
    message: str,
    is_from_user: int  # 1 = khách, 0 = bot
) -> bool:
    """
    Lưu tin nhắn vào database.
    Trả về True nếu thành công.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO messages (page_id, sender_id, message, is_from_user)
                VALUES (?, ?, ?, ?)
            """, (page_id, sender_id, message, is_from_user))
            return True
    except Exception as e:
        print(f"❌ [DB ERROR] save_message: {e}")
        return False


def get_chat_history(
    page_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Lấy lịch sử chat của một page.

    FIX: ORDER BY created_at ASC (tăng dần) để Android hiển thị
    đúng thứ tự thời gian — tin cũ trên, tin mới dưới.

    Dùng subquery để lấy N tin nhắn MỚI NHẤT nhưng vẫn sắp xếp ASC.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sender_id, message, is_from_user, created_at
            FROM (
                SELECT id, sender_id, message, is_from_user, created_at
                FROM messages
                WHERE page_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) recent
            ORDER BY created_at ASC
        """, (page_id, limit))

        rows = cur.fetchall()
        return [dict(row) for row in rows]


def get_recent_context(
    page_id: str,
    sender_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Lấy N tin nhắn gần nhất của một sender cụ thể.
    Dùng để build conversation context khi gọi AI.
    Trả về theo thứ tự ASC (cũ → mới) để đưa vào messages array của Ollama.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT message, is_from_user
            FROM (
                SELECT message, is_from_user, created_at
                FROM messages
                WHERE page_id = ? AND sender_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) recent
            ORDER BY created_at ASC
        """, (page_id, sender_id, limit))

        return [dict(row) for row in cur.fetchall()]


# =====================================================
# ENTRY POINT (chạy trực tiếp để init DB)
# =====================================================
if __name__ == "__main__":
    print("🚀 Initializing database...")
    init_database()
    run_migrations()
    print("✅ Done!")
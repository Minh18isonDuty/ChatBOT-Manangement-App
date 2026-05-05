# =====================================================
# db.py - Database connection và helper functions
# =====================================================

import sqlite3
import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_NAME = "bots.db"

# =====================================================
# CONTEXT MANAGER
# =====================================================
@contextmanager
def get_db_connection():
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
    finally:
        if conn:
            conn.close()


# =====================================================
# HELPER FUNCTIONS
# =====================================================
def init_database():
    with get_db_connection() as conn:
        cur = conn.cursor()

        # Bảng users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # Bảng bots
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

        # Bảng messages - Lưu lịch sử chat
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                message TEXT NOT NULL,
                is_from_user INTEGER NOT NULL,   -- 1 = user, 0 = bot
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (page_id) REFERENCES bots(page_id)
            )
        """)

        cur.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('admin', '123456')")
        conn.commit()
        print("✅ Database initialized successfully with messages table")


def get_bot_by_page(page_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, page_token, system_prompt, is_active 
            FROM bots WHERE page_id = ? AND is_active = 1
        """, (page_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_bots() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, page_id, name, is_active FROM bots ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]


def create_bot_new(page_id: str, page_token: str, name: str, system_prompt: str) -> Optional[int]:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM bots WHERE page_id = ?", (page_id,))
            if cur.fetchone():
                print(f"[DB] Page ID {page_id} đã tồn tại")
                return None

            cur.execute("""
                INSERT INTO bots (page_id, page_token, name, system_prompt, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (page_id, page_token or "default_token", name, system_prompt))
            conn.commit()
            bot_id = cur.lastrowid
            print(f"✅ [DB SUCCESS] Tạo bot ID={bot_id} | PageID={page_id} | Name={name}")
            return bot_id
    except Exception as e:
        print(f"❌ [DB ERROR] create_bot_new: {e}")
        return None


def update_bot(bot_id: int, is_active: Optional[int] = None) -> bool:
    if is_active is None:
        return False
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE bots SET is_active = ? WHERE id = ?", (is_active, bot_id))
            conn.commit()
            success = cur.rowcount > 0
            if success:
                print(f"✅ [DB SUCCESS] Updated bot {bot_id} → is_active = {is_active}")
            return success
    except Exception as e:
        print(f"❌ [DB ERROR] update_bot: {e}")
        return False


def delete_bot(bot_id: int) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        conn.commit()
        return cur.rowcount > 0


def get_bot_by_id(bot_id: int) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết một bot theo ID"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, page_id, name, system_prompt, is_active, 
                   COALESCE(created_at, '') as created_at
            FROM bots WHERE id = ?
        """, (bot_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# ====================== NEW: MESSAGE HISTORY ======================
def save_message(page_id: str, sender_id: str, message: str, is_from_user: int):
    """Lưu tin nhắn vào database"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO messages (page_id, sender_id, message, is_from_user)
                VALUES (?, ?, ?, ?)
            """, (page_id, sender_id, message, is_from_user))
            conn.commit()
    except Exception as e:
        print(f"❌ [DB ERROR] save_message: {e}")


def get_chat_history(page_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Lấy lịch sử chat của một page"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sender_id, message, is_from_user, created_at 
            FROM messages 
            WHERE page_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (page_id, limit))
        rows = cur.fetchall()
        return [dict(row) for row in rows]


# =====================================================
# INIT
# =====================================================
if __name__ == "__main__":
    init_database()
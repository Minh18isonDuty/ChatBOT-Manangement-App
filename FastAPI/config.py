# =====================================================
# config.py - Quản lý cấu hình dự án
# Version: 2.0 - Optimized
#
# ⚠️  QUAN TRỌNG:
# Các giá trị mặc định dưới đây CHỈ dùng cho development.
# Production: tạo file .env và override tất cả secret fields.
# KHÔNG commit file .env lên git.
# =====================================================

import secrets
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Server ────────────────────────────────────────
    APP_NAME: str = "AI Chatbot Admin API"
    DEBUG: bool = True          # Override: DEBUG=false trong .env production
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Auth ──────────────────────────────────────────
    # ⚠️  THAY GIÁ TRỊ NÀY TRONG FILE .env
    # Tạo token ngẫu nhiên: python -c "import secrets; print(secrets.token_hex(32))"
    ADMIN_TOKEN: str = "admin-token-change-me-in-production"

    # Facebook Webhook Verify Token — tự đặt, khớp với Meta Developer Console
    VERIFY_TOKEN: str = "minh18072004"

    # ── AI Engine ─────────────────────────────────────
    # Đổi sang /api/chat để hỗ trợ multi-turn conversation chuẩn
    OLLAMA_URL: str = "http://localhost:11434/api/chat"
    OLLAMA_MODEL: str = "phi3"      # Có thể đổi: llama3, gemma3, mistral, etc.
    OLLAMA_TIMEOUT: int = 90        # Giây — model lớn cần timeout dài hơn

    # ── Conversation ──────────────────────────────────
    # Số tin nhắn gần nhất đưa vào context AI
    # Tăng = AI nhớ lâu hơn nhưng token nhiều hơn → chậm hơn
    MAX_CONVERSATION_TURNS: int = 10

    # ── Database ──────────────────────────────────────
    DB_NAME: str = "bots.db"
    DB_TIMEOUT: int = 15

    # ── Facebook ──────────────────────────────────────
    FACEBOOK_API_VERSION: str = "v18.0"
    FACEBOOK_GRAPH_URL: str = "https://graph.facebook.com"

    # ── Validators ────────────────────────────────────
    @field_validator("ADMIN_TOKEN")
    @classmethod
    def admin_token_must_not_be_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 8:
            raise ValueError(
                "ADMIN_TOKEN phải có ít nhất 8 ký tự. "
                "Tạo token: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v.strip()

    @field_validator("VERIFY_TOKEN")
    @classmethod
    def verify_token_must_not_be_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 4:
            raise ValueError("VERIFY_TOKEN không được để trống")
        return v.strip()

    @field_validator("OLLAMA_URL")
    @classmethod
    def ollama_url_must_end_with_chat(cls, v: str) -> str:
        """Đảm bảo dùng /api/chat endpoint, không phải /api/generate."""
        if v.endswith("/api/generate"):
            return v.replace("/api/generate", "/api/chat")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# ── Singleton instance ────────────────────────────────
settings = Settings()


# =====================================================
# HELPER FUNCTIONS
# Giữ interface tương thích với main.py
# =====================================================
def get_admin_token() -> str:
    return settings.ADMIN_TOKEN

def get_verify_token() -> str:
    return settings.VERIFY_TOKEN

def get_max_turns() -> int:
    return settings.MAX_CONVERSATION_TURNS

def get_ollama_url() -> str:
    return settings.OLLAMA_URL
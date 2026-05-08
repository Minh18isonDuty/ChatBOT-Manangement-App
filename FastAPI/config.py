# =====================================================
# config.py - Quản lý cấu hình dự án
# Version: 2.2
# =====================================================

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Server ────────────────────────────────────────
    APP_NAME: str  = "AI Chatbot Admin API"
    DEBUG:    bool = True
    HOST:     str  = "0.0.0.0"
    PORT:     int  = 8000

    # ── Auth ──────────────────────────────────────────
    ADMIN_TOKEN:  str = "admin-token-change-me-in-production"
    VERIFY_TOKEN: str = "minh18072004"

    # ── AI Engine ─────────────────────────────────────
    OLLAMA_URL:     str = "http://localhost:11434/api/chat"
    OLLAMA_MODEL:   str = "phi3"
    OLLAMA_TIMEOUT: int = 90

    # ── Conversation ──────────────────────────────────
    MAX_CONVERSATION_TURNS: int = 10

    # ── Database ──────────────────────────────────────
    DB_NAME:    str = "bots.db"
    DB_TIMEOUT: int = 15

    # ── Facebook ──────────────────────────────────────
    FACEBOOK_API_VERSION: str = "v18.0"
    FACEBOOK_GRAPH_URL:   str = "https://graph.facebook.com"

    # BƯỚC 3: App Secret để verify webhook signature
    # Lấy tại: Meta Developer Console → App → Settings → Basic → App Secret
    # Để trống trong dev → server sẽ bỏ qua verify (warning mode)
    # BẮT BUỘC set trong production
    FACEBOOK_APP_SECRET: str = ""

    # ── Validators ────────────────────────────────────
    @field_validator("ADMIN_TOKEN")
    @classmethod
    def admin_token_not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 8:
            raise ValueError("ADMIN_TOKEN phải có ít nhất 8 ký tự")
        return v.strip()

    @field_validator("OLLAMA_URL")
    @classmethod
    def fix_ollama_url(cls, v: str) -> str:
        if v.endswith("/api/generate"):
            return v.replace("/api/generate", "/api/chat")
        return v

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"
        case_sensitive    = True


settings = Settings()


def get_admin_token()  -> str: return settings.ADMIN_TOKEN
def get_verify_token() -> str: return settings.VERIFY_TOKEN
def get_max_turns()    -> int: return settings.MAX_CONVERSATION_TURNS
def get_ollama_url()   -> str: return settings.OLLAMA_URL
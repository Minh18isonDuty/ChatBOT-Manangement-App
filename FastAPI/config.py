# =====================================================
# config.py - Quản lý các cấu hình chung của dự án
# =====================================================

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ====================== SERVER ======================
    APP_NAME: str = "AI Chatbot Admin API"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ====================== AUTH ======================
    ADMIN_TOKEN: str = "admin-token-123"
    VERIFY_TOKEN: str = "minh18072004"          # Facebook Webhook Verify Token

    # ====================== AI ENGINE ======================
    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "phi3"                  # Có thể đổi thành llama3, gemma, etc.

    # ====================== CONVERSATION ======================
    MAX_CONVERSATION_TURNS: int = 5             # Số lượt hội thoại lưu trong memory

    # ====================== DATABASE ======================
    DB_NAME: str = "bots.db"
    DB_TIMEOUT: int = 15

    # ====================== FACEBOOK ======================
    FACEBOOK_API_VERSION: str = "v18.0"
    FACEBOOK_GRAPH_URL: str = "https://graph.facebook.com"

    class Config:
        env_file = ".env"           # Cho phép load từ file .env sau này
        env_file_encoding = 'utf-8'
        case_sensitive = True


# Tạo instance settings
settings = Settings()


# ====================== HELPER FUNCTIONS ======================
def get_ollama_url() -> str:
    """Trả về URL của Ollama"""
    return settings.OLLAMA_URL


def get_admin_token() -> str:
    """Trả về Admin Token"""
    return settings.ADMIN_TOKEN


def get_verify_token() -> str:
    """Trả về Facebook Verify Token"""
    return settings.VERIFY_TOKEN


def get_max_turns() -> int:
    """Số lượt hội thoại tối đa trong memory"""
    return settings.MAX_CONVERSATION_TURNS
# =====================================================
# schemas.py - Pydantic Models cho FastAPI
# Version: 2.0 - Optimized
# =====================================================

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


# =====================================================
# AUTH
# =====================================================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=50)

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "password": "123456"
            }
        }
    }


class TokenResponse(BaseModel):
    token: str = Field(..., description="Bearer token để xác thực các request tiếp theo")


# =====================================================
# BOT MODELS
# =====================================================
class BotCreate(BaseModel):
    page_id: str = Field(..., min_length=5, max_length=50, description="Facebook Page ID")
    # Optional vì Android app có thể gửi empty string → dùng default_token
    page_token: Optional[str] = Field(None, description="Facebook Page Access Token")
    name: str = Field(..., min_length=2, max_length=100, description="Tên bot")
    system_prompt: str = Field(
        default="Bạn là một trợ lý tư vấn bán hàng thân thiện, chuyên nghiệp và nhiệt tình.",
        min_length=10,
        description="System prompt hướng dẫn AI cách trả lời"
    )

    @field_validator("page_id")
    @classmethod
    def page_id_must_be_numeric(cls, v: str) -> str:
        """Facebook Page ID chỉ chứa chữ số."""
        v = v.strip()
        if not v.isdigit():
            raise ValueError("page_id chỉ được chứa chữ số (ví dụ: 123456789012345)")
        return v

    @field_validator("system_prompt")
    @classmethod
    def system_prompt_strip(cls, v: str) -> str:
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "page_id": "123456789012345",
                "page_token": "EAAxxxlong_token",
                "name": "Bot Tư Vấn Sản Phẩm",
                "system_prompt": "Bạn là nhân viên tư vấn bán mỹ phẩm, luôn lịch sự và khéo léo."
            }
        }
    }


class BotUpdate(BaseModel):
    """
    FIX: is_active dùng int thay vì bool.

    Lý do: Android gửi is_active = 0 hoặc 1 (int).
    Pydantic có thể convert bool → int nhưng không nhất quán
    khi nhận từ JSON của Kotlin. Dùng int để tránh mọi ambiguity.
    """
    is_active: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="Trạng thái bot: 1 = bật, 0 = tắt"
    )

    @field_validator("is_active")
    @classmethod
    def validate_is_active(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (0, 1):
            raise ValueError("is_active chỉ nhận giá trị 0 hoặc 1")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {"is_active": 1}
        }
    }


class BotResponse(BaseModel):
    """Response trả về cho Android app."""
    id: int
    page_id: str
    name: str
    is_active: int      # Giữ int để đồng nhất với Android model

    model_config = {
        "from_attributes": True,    # Cho phép map từ dict/sqlite.Row
        "json_schema_extra": {
            "example": {
                "id": 1,
                "page_id": "123456789012345",
                "name": "Bot Tư Vấn Sản Phẩm",
                "is_active": 1
            }
        }
    }


# =====================================================
# MESSAGE HISTORY MODELS
# =====================================================
class Message(BaseModel):
    """
    FIX: created_at dùng str thay vì datetime.

    Lý do: SQLite lưu TIMESTAMP dạng string "2024-01-15 10:30:00".
    Nếu dùng datetime, Pydantic sẽ cố parse → có thể fail
    với một số format SQLite. Dùng str để an toàn,
    việc format sẽ do Android client xử lý.
    """
    id: int
    sender_id: str
    message: str
    is_from_user: int       # 1 = Khách hàng gửi, 0 = Bot trả lời
    created_at: str         # ISO string: "2024-01-15 10:30:00"

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "sender_id": "1234567890",
                "message": "Shop có bán áo không?",
                "is_from_user": 1,
                "created_at": "2024-01-15 10:30:00"
            }
        }
    }


class ChatHistoryResponse(BaseModel):
    """
    Response cho endpoint GET /bots/{bot_id}/history.
    Khớp với ChatHistoryResponse trong Android app (Bot.kt).
    """
    page_id: str
    messages: List[Message]

    model_config = {
        "json_schema_extra": {
            "example": {
                "page_id": "123456789012345",
                "messages": [
                    {
                        "id": 1,
                        "sender_id": "987654321",
                        "message": "Shop có bán áo không?",
                        "is_from_user": 1,
                        "created_at": "2024-01-15 10:30:00"
                    },
                    {
                        "id": 2,
                        "sender_id": "bot",
                        "message": "Dạ shop có bán áo ạ, bạn muốn xem mẫu nào?",
                        "is_from_user": 0,
                        "created_at": "2024-01-15 10:30:05"
                    }
                ]
            }
        }
    }


# =====================================================
# COMMON RESPONSES
# =====================================================
class MessageResponse(BaseModel):
    message: str = Field(..., description="Thông báo kết quả")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "Bot updated successfully"}
        }
    }


class ErrorResponse(BaseModel):
    """Dùng để document lỗi trong Swagger UI."""
    detail: str

    model_config = {
        "json_schema_extra": {
            "example": {"detail": "Bot không tồn tại"}
        }
    }

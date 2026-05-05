# =====================================================
# schemas.py - Pydantic Models cho FastAPI
# =====================================================

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ====================== AUTH ======================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=4, max_length=50, description="Mật khẩu")


class TokenResponse(BaseModel):
    token: str = Field(..., description="JWT-like token để xác thực")


# ====================== BOT MODELS ======================
class BotCreate(BaseModel):
    page_id: str = Field(..., min_length=5, max_length=50, description="Facebook Page ID")
    page_token: str = Field(..., min_length=10, description="Facebook Page Access Token")
    name: str = Field(..., min_length=2, max_length=100, description="Tên bot")
    system_prompt: str = Field(
        default="Bạn là một trợ lý tư vấn bán hàng thân thiện, chuyên nghiệp và nhiệt tình.",
        min_length=10,
        description="System prompt hướng dẫn AI cách trả lời"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "page_id": "123456789012345",
                "page_token": "EAA...long_token_here",
                "name": "Bot Tư Vấn Sản Phẩm",
                "system_prompt": "Bạn là nhân viên tư vấn bán mỹ phẩm, luôn lịch sự và khéo léo."
            }
        }


class BotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    system_prompt: Optional[str] = Field(None, min_length=10)
    is_active: Optional[bool] = Field(None, description="True = bật bot, False = tắt bot")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Bot Tư Vấn Mới",
                "is_active": True
            }
        }


class BotResponse(BaseModel):
    id: int
    page_id: str
    name: str
    is_active: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "page_id": "123456789012345",
                "name": "Bot Tư Vấn Sản Phẩm",
                "is_active": 1
            }
        }


# ====================== MESSAGE HISTORY MODELS (MỚI) ======================
class Message(BaseModel):
    id: int
    sender_id: str
    message: str
    is_from_user: int          # 1 = Khách hàng, 0 = Bot
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    page_id: str
    messages: List[Message]


# ====================== COMMON RESPONSE ======================
class MessageResponse(BaseModel):
    message: str = Field(..., description="Thông báo kết quả")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Bot updated successfully"
            }
        }


# ====================== LIST RESPONSES ======================
class BotListResponse(BaseModel):
    bots: List[BotResponse]


# Optional: Error response model
class ErrorResponse(BaseModel):
    detail: str


# ====================== STATUS ======================
class StatusResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None


# ====================== CONFIG FOR ALL ======================
class Config:
    json_schema_extra = {
        "example": {
            "id": 1,
            "page_id": "123456789012345",
            "name": "Bot Tư Vấn Sản Phẩm",
            "is_active": 1
        }
    }
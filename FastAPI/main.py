# =====================================================
# main.py - FastAPI chính cho AI Chatbot Admin
# Version: 2.1 - Thêm Typing Indicator
# =====================================================

from fastapi import FastAPI, Request, Query, Depends, Header, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import List

from config import settings, get_admin_token, get_verify_token, get_max_turns
from schemas import (
    LoginRequest, TokenResponse,
    BotCreate, BotUpdate, BotResponse,
    MessageResponse, ChatHistoryResponse
)
from db import (
    init_database,
    get_db_connection,
    get_bot_by_page,
    get_all_bots,
    create_bot,
    update_bot,
    delete_bot,
    save_message,
    get_chat_history,
    get_bot_by_id,
    get_recent_context,
    verify_user,
)


# =====================================================
# APP INIT
# =====================================================
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="AI Chatbot Management API",
    version="2.1.0"
)


# =====================================================
# STARTUP
# =====================================================
@app.on_event("startup")
def on_startup():
    print("🚀 Starting up...")
    init_database()
    print("✅ Database ready")


# =====================================================
# CORS
# ⚠️  allow_origins=["*"] chỉ dùng cho dev/demo
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# AUTH DEPENDENCY
# =====================================================
def verify_token(authorization: str = Header(None)) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.replace("Bearer ", "").strip()
    if token != get_admin_token():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return True


# =====================================================
# FACEBOOK HELPERS
# =====================================================
def _send_facebook_message(page_token: str, recipient_id: str, text: str):
    """Gửi tin nhắn text về Facebook Messenger."""
    try:
        resp = requests.post(
            f"{settings.FACEBOOK_GRAPH_URL}/{settings.FACEBOOK_API_VERSION}/me/messages",
            params={"access_token": page_token},
            json={
                "recipient": {"id": recipient_id},
                "message":   {"text": text}
            },
            timeout=10
        )
        if resp.status_code != 200:
            print(f"⚠️  [Facebook] Send failed: {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"❌ [Facebook Send Error] {e}")


def _send_typing_action(page_token: str, recipient_id: str, action: str = "typing_on"):
    """
    Gửi typing indicator về Facebook.

    action options:
      "typing_on"  → hiện dấu "..." trong chat của user
      "typing_off" → tắt dấu "..."
      "mark_seen"  → đánh dấu đã xem tin nhắn

    Lưu ý:
      - Facebook tự tắt typing_on sau 20 giây nếu không gọi typing_off
      - Nên gọi typing_off ngay sau khi có reply để UX mượt hơn
      - Fail silently — không ảnh hưởng đến luồng chính
    """
    try:
        requests.post(
            f"{settings.FACEBOOK_GRAPH_URL}/{settings.FACEBOOK_API_VERSION}/me/messages",
            params={"access_token": page_token},
            json={
                "recipient":     {"id": recipient_id},
                "sender_action": action
            },
            timeout=5   # timeout ngắn — không block luồng chính
        )
    except Exception as e:
        # Typing indicator fail không được crash webhook handler
        print(f"⚠️  [Typing] {action} failed: {e}")


# =====================================================
# AI HELPER
# =====================================================
def build_messages(system_prompt: str, context: list, user_text: str) -> list:
    """
    Build messages array theo chuẩn Ollama /api/chat.
    Lấy context từ DB → bot nhớ lịch sử hội thoại.
    """
    messages = [{"role": "system", "content": system_prompt.strip()}]

    for item in context:
        role = "user" if item["is_from_user"] == 1 else "assistant"
        messages.append({"role": role, "content": item["message"]})

    messages.append({"role": "user", "content": user_text})
    return messages


def ask_ai(
    system_prompt: str,
    user_text: str,
    page_id: str,
    sender_id: str
) -> str:
    """
    Gọi Ollama /api/chat và lưu kết quả vào DB.

    Dùng /api/chat (không phải /api/generate) để:
    - Hỗ trợ multi-turn conversation natively
    - Model hiểu rõ role system/user/assistant
    """
    context  = get_recent_context(page_id=page_id, sender_id=sender_id, limit=get_max_turns())
    messages = build_messages(system_prompt, context, user_text)

    try:
        response = requests.post(
            settings.OLLAMA_URL,
            json={"model": settings.OLLAMA_MODEL, "messages": messages, "stream": False},
            timeout=90
        )
        response.raise_for_status()
        answer = response.json().get("message", {}).get("content", "").strip()
        if not answer:
            answer = "Xin lỗi, tôi chưa hiểu câu hỏi của bạn."

    except requests.Timeout:
        print("⚠️  [AI] Timeout")
        answer = "Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau."
    except Exception as e:
        print(f"❌ [AI Error] {e}")
        answer = "Xin lỗi, chatbot đang gặp vấn đề kỹ thuật."

    save_message(page_id, sender_id, user_text, is_from_user=1)
    save_message(page_id, "bot",       answer,   is_from_user=0)

    return answer


# =====================================================
# WEBHOOK — FACEBOOK
# =====================================================
@app.get("/webhook")
async def verify_webhook(
    hub_mode:         str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge:    str = Query(None, alias="hub.challenge")
):
    """Facebook webhook verification (GET)."""
    if hub_mode == "subscribe" and hub_verify_token == get_verify_token():
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    """
    Nhận và xử lý tin nhắn từ Facebook Messenger.

    Flow đầy đủ với typing indicator:
      1. Nhận webhook từ Facebook
      2. Validate bot còn active
      3. Gửi typing_on  → user thấy "..."
      4. Gọi AI (3-10s)
      5. Gửi typing_off → tắt "..."
      6. Gửi reply      → user nhận câu trả lời
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(content={"status": "invalid_json"}, status_code=400)

    for entry in data.get("entry", []):
        page_id = entry.get("id")
        if not page_id:
            continue

        bot = get_bot_by_page(page_id)
        if not bot or bot.get("is_active") == 0:
            continue

        for messaging in entry.get("messaging", []):
            if "message" not in messaging or "sender" not in messaging:
                continue

            sender_id = messaging["sender"]["id"]
            text      = messaging.get("message", {}).get("text", "").strip()

            if not text:
                continue

            # Bỏ qua echo message (page tự gửi)
            if messaging.get("message", {}).get("is_echo"):
                continue

            # ── Bước 1: Đánh dấu đã xem ──────────────
            _send_typing_action(bot["page_token"], sender_id, "mark_seen")

            # ── Bước 2: Hiện "đang nhập..." ───────────
            _send_typing_action(bot["page_token"], sender_id, "typing_on")

            # ── Bước 3: Gọi AI ────────────────────────
            try:
                reply = ask_ai(
                    system_prompt=bot["system_prompt"],
                    user_text=text,
                    page_id=page_id,
                    sender_id=sender_id
                )
            except Exception as e:
                print(f"❌ [Webhook] AI error: {e}")
                reply = "Xin lỗi, chatbot đang gặp vấn đề."

            # ── Bước 4: Tắt "đang nhập..." ───────────
            _send_typing_action(bot["page_token"], sender_id, "typing_off")

            # ── Bước 5: Gửi reply ─────────────────────
            _send_facebook_message(
                page_token=bot["page_token"],
                recipient_id=sender_id,
                text=reply
            )

    return JSONResponse(content={"status": "ok"})


# =====================================================
# TYPING INDICATOR ENDPOINT (trigger thủ công)
# Dùng để test hoặc trigger từ admin Android app
# =====================================================
class TypingPayload(BaseModel if False else object):
    pass

from pydantic import BaseModel as _BaseModel

class TypingPayload(_BaseModel):
    recipient_id: str
    is_typing:    bool

@app.post("/bots/{bot_id}/typing", response_model=MessageResponse)
def trigger_typing(
    bot_id:  int,
    payload: TypingPayload,
    auth:    bool = Depends(verify_token)
):
    """
    Trigger typing indicator thủ công từ admin app.
    Thường dùng để test — trong production tự động chạy trong webhook.
    """
    bot = get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại")

    action = "typing_on" if payload.is_typing else "typing_off"
    _send_typing_action(bot["page_token"], payload.recipient_id, action)

    return MessageResponse(message=f"Đã gửi {action} tới {payload.recipient_id}")


# =====================================================
# AUTH
# =====================================================
@app.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    user = verify_user(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng"
        )
    return TokenResponse(token=get_admin_token())


# =====================================================
# BOT MANAGEMENT
# =====================================================
@app.get("/bots", response_model=List[BotResponse])
def get_bots(auth: bool = Depends(verify_token)):
    return get_all_bots()


@app.post("/bots", response_model=BotResponse, status_code=201)
def create_bot_endpoint(bot: BotCreate, auth: bool = Depends(verify_token)):
    bot_id = create_bot(
        page_id=bot.page_id,
        page_token=bot.page_token or "default_token",
        name=bot.name,
        system_prompt=bot.system_prompt
    )
    if bot_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page ID đã tồn tại hoặc tạo bot thất bại"
        )
    new_bot = get_bot_by_id(bot_id)
    if not new_bot:
        raise HTTPException(status_code=500, detail="Lỗi khi lấy thông tin bot vừa tạo")
    return new_bot


@app.put("/bots/{bot_id}", response_model=MessageResponse)
def update_bot_endpoint(bot_id: int, data: BotUpdate, auth: bool = Depends(verify_token)):
    success = update_bot(bot_id=bot_id, is_active=data.is_active)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot không tồn tại hoặc không có thay đổi"
        )
    return MessageResponse(message="Cập nhật bot thành công")


@app.delete("/bots/{bot_id}", response_model=MessageResponse)
def delete_bot_endpoint(bot_id: int, auth: bool = Depends(verify_token)):
    success = delete_bot(bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot không tồn tại")
    return MessageResponse(message="Xóa bot thành công")


# =====================================================
# CHAT HISTORY
# =====================================================
@app.get("/bots/{bot_id}/history", response_model=ChatHistoryResponse)
def get_bot_history(bot_id: int, auth: bool = Depends(verify_token)):
    bot = get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại")

    messages = get_chat_history(bot["page_id"], limit=50)
    return ChatHistoryResponse(page_id=bot["page_id"], messages=messages)


# =====================================================
# ROOT — Health check
# =====================================================
@app.get("/")
def root():
    return {
        "status":  "success",
        "message": f"{settings.APP_NAME} is running",
        "version": "2.1.0"
    }
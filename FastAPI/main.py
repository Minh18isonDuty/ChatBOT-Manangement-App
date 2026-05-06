# =====================================================
# main.py - FastAPI chính cho AI Chatbot Admin
# Version: 2.0 - Optimized
# =====================================================

from fastapi import FastAPI, Request, Query, Depends, Header, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import hashlib
import hmac
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
    create_bot,          # ← đổi từ create_bot_new
    update_bot,
    delete_bot,
    save_message,
    get_chat_history,
    get_bot_by_id,
    get_recent_context,  # ← hàm mới để build AI context từ DB
    verify_user,         # ← hàm mới xác thực user có hash
)


# =====================================================
# APP INIT
# =====================================================
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="AI Chatbot Management API",
    version="2.0.0"
)


# =====================================================
# STARTUP — QUAN TRỌNG: gọi init_database() ở đây
# Đây là nguyên nhân gốc gây lỗi 500 "no such table: messages"
# =====================================================
@app.on_event("startup")
def on_startup():
    print("🚀 Starting up...")
    init_database()
    print("✅ Database ready")


# =====================================================
# CORS
# ⚠️  allow_origins=["*"] chỉ dùng cho môi trường dev/demo
# Production: thay bằng domain cụ thể
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
    """
    Xác thực Bearer token từ header Authorization.
    Dùng làm Depends() cho các endpoint cần bảo vệ.
    """
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
# AI HELPER
# =====================================================
def build_messages(system_prompt: str, context: list, user_text: str) -> list:
    """
    Build messages array theo chuẩn chat format của Ollama.
    Dùng lịch sử từ DB thay vì in-memory → không mất context khi restart.

    Args:
        system_prompt: Tính cách/hướng dẫn của bot
        context: List các tin nhắn gần nhất từ DB [{message, is_from_user}]
        user_text: Tin nhắn hiện tại của user

    Returns:
        List messages theo format Ollama chat API
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
    Gọi Ollama API để sinh câu trả lời.

    Flow:
    1. Lấy context từ DB (N tin nhắn gần nhất của sender này)
    2. Build messages array chuẩn chat format
    3. Gọi Ollama /api/chat endpoint
    4. Lưu cả user message + bot reply vào DB
    5. Trả về câu trả lời

    Lý do dùng /api/chat thay vì /api/generate:
    - Hỗ trợ multi-turn natively
    - Model hiểu rõ role (system/user/assistant) hơn
    """
    # Lấy context từ DB — không dùng in-memory nữa
    context = get_recent_context(
        page_id=page_id,
        sender_id=sender_id,
        limit=get_max_turns()
    )

    messages = build_messages(system_prompt, context, user_text)

    try:
        response = requests.post(
            # Dùng /api/chat thay vì /api/generate
            settings.OLLAMA_URL.replace("/api/generate", "/api/chat"),
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=90
        )
        response.raise_for_status()

        # Chat API trả về response.message.content
        answer = response.json().get("message", {}).get("content", "").strip()
        if not answer:
            answer = "Xin lỗi, tôi chưa hiểu câu hỏi của bạn."

    except requests.Timeout:
        print(f"⚠️  [AI] Timeout khi gọi Ollama")
        answer = "Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau."
    except Exception as e:
        print(f"❌ [AI Error] {e}")
        answer = "Xin lỗi, chatbot đang gặp vấn đề kỹ thuật."

    # Lưu vào DB sau khi có kết quả
    save_message(page_id, sender_id, user_text, is_from_user=1)
    save_message(page_id, "bot", answer, is_from_user=0)

    return answer


# =====================================================
# WEBHOOK — FACEBOOK
# =====================================================
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """Facebook webhook verification (GET)."""
    if hub_mode == "subscribe" and hub_verify_token == get_verify_token():
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    """
    Nhận tin nhắn từ Facebook Messenger.

    Flow: Facebook → POST /webhook → xử lý → gọi AI → gửi reply
    """
    # ── Đọc body ──────────────────────────────────────
    try:
        body_bytes = await request.body()
        data = await request.json()
    except Exception:
        return JSONResponse(content={"status": "invalid_json"}, status_code=400)

    # ── Xử lý từng entry ──────────────────────────────
    for entry in data.get("entry", []):
        page_id = entry.get("id")
        if not page_id:
            continue

        # Lấy bot — nếu không tìm thấy hoặc đang tắt thì bỏ qua
        bot = get_bot_by_page(page_id)
        if not bot or bot.get("is_active") == 0:
            continue

        for messaging in entry.get("messaging", []):
            # Bỏ qua nếu thiếu field cần thiết
            if "message" not in messaging or "sender" not in messaging:
                continue

            sender_id = messaging["sender"]["id"]
            text = messaging.get("message", {}).get("text", "").strip()

            # Bỏ qua tin nhắn rỗng hoặc attachment
            if not text:
                continue

            # Bỏ qua echo (tin nhắn từ chính page gửi đi)
            if messaging.get("message", {}).get("is_echo"):
                continue

            # ── Gọi AI ────────────────────────────────
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

            # ── Gửi reply về Facebook ──────────────────
            _send_facebook_message(
                page_token=bot["page_token"],
                recipient_id=sender_id,
                text=reply
            )

    return JSONResponse(content={"status": "ok"})


def _send_facebook_message(page_token: str, recipient_id: str, text: str):
    """
    Gửi tin nhắn về cho user qua Facebook Graph API.
    Tách thành function riêng để dễ test và maintain.
    """
    try:
        resp = requests.post(
            f"{settings.FACEBOOK_GRAPH_URL}/{settings.FACEBOOK_API_VERSION}/me/messages",
            params={"access_token": page_token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text}
            },
            timeout=10
        )
        if resp.status_code != 200:
            print(f"⚠️  [Facebook] Send failed: {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"❌ [Facebook Send Error] {e}")


# =====================================================
# AUTH
# =====================================================
@app.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    """
    Đăng nhập admin.
    Dùng verify_user() từ db.py — password đã được hash SHA-256.
    """
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
    """Lấy danh sách tất cả bot."""
    return get_all_bots()


@app.post("/bots", response_model=BotResponse, status_code=201)
def create_bot_endpoint(bot: BotCreate, auth: bool = Depends(verify_token)):
    """Tạo bot mới."""
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

    # Trả về bot vừa tạo
    new_bot = get_bot_by_id(bot_id)
    if not new_bot:
        raise HTTPException(status_code=500, detail="Lỗi khi lấy thông tin bot vừa tạo")

    return new_bot


@app.put("/bots/{bot_id}", response_model=MessageResponse)
def update_bot_endpoint(
    bot_id: int,
    data: BotUpdate,
    auth: bool = Depends(verify_token)
):
    """Cập nhật trạng thái bot (bật/tắt)."""
    success = update_bot(bot_id=bot_id, is_active=data.is_active)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot không tồn tại hoặc không có thay đổi"
        )

    return MessageResponse(message="Cập nhật bot thành công")


@app.delete("/bots/{bot_id}", response_model=MessageResponse)
def delete_bot_endpoint(bot_id: int, auth: bool = Depends(verify_token)):
    """Xóa bot. Messages liên quan sẽ bị xóa theo (CASCADE)."""
    success = delete_bot(bot_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot không tồn tại"
        )
    return MessageResponse(message="Xóa bot thành công")


# =====================================================
# CHAT HISTORY
# =====================================================
@app.get("/bots/{bot_id}/history", response_model=ChatHistoryResponse)
def get_bot_history(bot_id: int, auth: bool = Depends(verify_token)):
    """
    Lấy lịch sử chat của bot theo bot_id.
    Trả về 50 tin nhắn gần nhất, sắp xếp ASC (cũ → mới).
    """
    bot = get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot không tồn tại"
        )

    messages = get_chat_history(bot["page_id"], limit=50)

    return ChatHistoryResponse(
        page_id=bot["page_id"],
        messages=messages
    )


# =====================================================
# ROOT — Health check
# =====================================================
@app.get("/")
def root():
    return {
        "status": "success",
        "message": f"{settings.APP_NAME} is running",
        "version": "2.0.0"
    }
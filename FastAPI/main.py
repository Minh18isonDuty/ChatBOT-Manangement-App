# =====================================================
# main.py - FastAPI chính cho AI Chatbot Admin
# Version: 2.2
#   + Bước 2: Fallback mechanism (retry + message dự phòng)
#   + Bước 3: Webhook signature verification (X-Hub-Signature-256)
# =====================================================

from fastapi import FastAPI, Request, Query, Depends, Header, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as _BaseModel
import requests
import hashlib
import hmac
import time
from typing import List
from pydantic import BaseModel as _BM
from typing import List as _L

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
    get_stats_overview,      
    get_messages_by_day,     
    get_messages_by_hour,    
    get_peak_hour,          
)


# =====================================================
# APP INIT
# =====================================================
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="AI Chatbot Management API",
    version="2.2.0"
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
# BƯỚC 3: WEBHOOK SIGNATURE VERIFICATION
#
# Tại sao cần:
#   Không verify → bất kỳ ai cũng có thể POST vào /webhook
#   giả mạo Facebook, khiến bot trả lời tin nhắn giả.
#
# Cách hoạt động:
#   Facebook gửi header X-Hub-Signature-256 = "sha256=<hash>"
#   Hash được tính bằng HMAC-SHA256 của request body
#   với App Secret là key.
#   Server tính lại hash → so sánh → nếu khớp thì hợp lệ.
#
# Quan trọng: dùng hmac.compare_digest() thay vì ==
#   để chống timing attack.
# =====================================================
def verify_facebook_signature(request_body: bytes, signature_header: str) -> bool:
    """
    Xác thực chữ ký X-Hub-Signature-256 từ Facebook.

    Args:
        request_body:      Raw bytes của request body
        signature_header:  Giá trị header X-Hub-Signature-256

    Returns:
        True nếu hợp lệ, False nếu không
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    # Lấy hash Facebook gửi
    facebook_hash = signature_header[len("sha256="):]

    # Tính lại hash từ body với App Secret
    expected_hash = hmac.new(
        key=settings.FACEBOOK_APP_SECRET.encode("utf-8"),
        msg=request_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # So sánh constant-time để chống timing attack
    return hmac.compare_digest(expected_hash, facebook_hash)


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
    action: "typing_on" | "typing_off" | "mark_seen"
    Fail silently — không ảnh hưởng luồng chính.
    """
    try:
        requests.post(
            f"{settings.FACEBOOK_GRAPH_URL}/{settings.FACEBOOK_API_VERSION}/me/messages",
            params={"access_token": page_token},
            json={
                "recipient":     {"id": recipient_id},
                "sender_action": action
            },
            timeout=5
        )
    except Exception as e:
        print(f"⚠️  [Typing] {action} failed: {e}")


# =====================================================
# BƯỚC 2: AI HELPER VỚI FALLBACK MECHANISM
#
# Vấn đề cũ:
#   Ollama timeout hoặc lỗi → bot im lặng hoàn toàn
#   → user không biết có chuyện gì → trải nghiệm tệ
#
# Giải pháp:
#   1. Retry tối đa MAX_RETRIES lần với delay tăng dần
#   2. Nếu vẫn fail → trả về fallback message thân thiện
#   3. Vẫn lưu tin nhắn user vào DB dù AI fail
#      → lịch sử chat không bị mất
# =====================================================
MAX_RETRIES  = 2       # Số lần retry khi AI fail
RETRY_DELAY  = 1.5     # Giây chờ giữa các lần retry

FALLBACK_MESSAGES = [
    "Xin lỗi, mình đang bận xử lý nhiều yêu cầu. Bạn có thể nhắn lại sau 1-2 phút không ạ? 🙏",
    "Hệ thống đang tạm thời quá tải. Mình sẽ trả lời bạn sớm nhất có thể!",
    "Xin lỗi vì sự bất tiện này! Bạn vui lòng thử lại sau ít phút nhé. 😊"
]

_fallback_index = 0  # Xoay vòng fallback messages


def _get_fallback_message() -> str:
    """Lấy fallback message theo vòng để không lặp lại liên tục."""
    global _fallback_index
    msg = FALLBACK_MESSAGES[_fallback_index % len(FALLBACK_MESSAGES)]
    _fallback_index += 1
    return msg


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
    Gọi Ollama API với retry logic và fallback mechanism.

    Flow:
      1. Lấy context từ DB
      2. Thử gọi Ollama tối đa MAX_RETRIES lần
      3. Nếu thành công → lưu DB → trả về answer
      4. Nếu vẫn fail sau retry → lưu user message → trả về fallback
    """
    context  = get_recent_context(page_id=page_id, sender_id=sender_id, limit=get_max_turns())
    messages = build_messages(system_prompt, context, user_text)

    answer   = None
    last_err = None

    # ── Retry loop ────────────────────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🤖 [AI] Attempt {attempt}/{MAX_RETRIES}...")

            response = requests.post(
                settings.OLLAMA_URL,
                json={
                    "model":    settings.OLLAMA_MODEL,
                    "messages": messages,
                    "stream":   False
                },
                timeout=settings.OLLAMA_TIMEOUT
            )
            response.raise_for_status()

            answer = response.json().get("message", {}).get("content", "").strip()

            if answer:
                print(f"✅ [AI] Success on attempt {attempt}")
                break   # Thành công → thoát loop
            else:
                print(f"⚠️  [AI] Empty response on attempt {attempt}")

        except requests.Timeout:
            last_err = f"Timeout (attempt {attempt})"
            print(f"⚠️  [AI] {last_err}")
        except requests.ConnectionError:
            last_err = f"Ollama không chạy hoặc không kết nối được (attempt {attempt})"
            print(f"❌ [AI] {last_err}")
            break   # Connection error → không retry vì sẽ fail giống nhau
        except Exception as e:
            last_err = str(e)
            print(f"❌ [AI] Error attempt {attempt}: {e}")

        # Delay trước lần retry tiếp theo (không delay sau lần cuối)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    # ── Lưu vào DB ────────────────────────────────────
    # Luôn lưu tin nhắn user dù AI có fail hay không
    save_message(page_id, sender_id, user_text, is_from_user=1)

    if answer:
        # AI thành công → lưu reply thật
        save_message(page_id, "bot", answer, is_from_user=0)
        return answer
    else:
        # AI fail → dùng fallback, vẫn lưu vào DB
        fallback = _get_fallback_message()
        save_message(page_id, "bot", fallback, is_from_user=0)
        print(f"⚠️  [AI] All retries failed. Last error: {last_err}. Using fallback.")
        return fallback


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

    Flow đầy đủ:
      1. Đọc raw body (cần để verify signature)
      2. BƯỚC 3: Verify X-Hub-Signature-256
      3. Parse JSON
      4. Tìm bot, check active
      5. Typing on → AI (với retry) → Typing off → Reply
    """
    # ── Đọc raw body trước khi parse JSON ─────────────
    # Quan trọng: phải đọc body dưới dạng bytes để verify signature
    body_bytes = await request.body()

    # ── BƯỚC 3: Verify Facebook signature ─────────────
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Chỉ verify khi đã cấu hình FACEBOOK_APP_SECRET
    if settings.FACEBOOK_APP_SECRET:
        if not verify_facebook_signature(body_bytes, signature):
            print(f"❌ [Webhook] Invalid signature — possible spoofed request")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature"
            )
    else:
        # Chưa config App Secret → warning nhưng vẫn xử lý (dev mode)
        print("⚠️  [Webhook] FACEBOOK_APP_SECRET chưa được cấu hình — bỏ qua verify signature")

    # ── Parse JSON ────────────────────────────────────
    try:
        data = request.json() if hasattr(request, '_json') else None
        import json
        data = json.loads(body_bytes)
    except Exception:
        return JSONResponse(content={"status": "invalid_json"}, status_code=400)

    # ── Xử lý từng entry ──────────────────────────────
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

            if messaging.get("message", {}).get("is_echo"):
                continue

            # ── Typing flow ───────────────────────────
            _send_typing_action(bot["page_token"], sender_id, "mark_seen")
            _send_typing_action(bot["page_token"], sender_id, "typing_on")

            # ── Gọi AI với retry + fallback ───────────
            reply = ask_ai(
                system_prompt=bot["system_prompt"],
                user_text=text,
                page_id=page_id,
                sender_id=sender_id
            )

            _send_typing_action(bot["page_token"], sender_id, "typing_off")
            _send_facebook_message(bot["page_token"], sender_id, reply)

    return JSONResponse(content={"status": "ok"})


# =====================================================
# TYPING ENDPOINT (trigger thủ công từ admin app)
# =====================================================
class TypingPayload(_BaseModel):
    recipient_id: str
    is_typing:    bool

@app.post("/bots/{bot_id}/typing", response_model=MessageResponse)
def trigger_typing(bot_id: int, payload: TypingPayload, auth: bool = Depends(verify_token)):
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
        raise HTTPException(status_code=404, detail="Bot không tồn tại hoặc không có thay đổi")
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
        "version": "2.2.0"
    }

class StatsOverview(_BM):
    total_messages: int
    unique_users:   int
    today_messages: int
    user_messages:  int
    bot_messages:   int

class DailyCount(_BM):
    date:  str
    count: int

class HourlyCount(_BM):
    hour:  int
    count: int

class StatsResponse(_BM):
    page_id:        str
    overview:       StatsOverview
    daily_7days:    _L[DailyCount]
    hourly:         _L[HourlyCount]
    peak_hour:      int
    peak_count:     int

@app.get("/bots/{bot_id}/stats", response_model=StatsResponse)
def get_bot_stats(bot_id: int, auth: bool = Depends(verify_token)):
    """
    Thống kê toàn diện của một bot.
    
    Trả về:
      - overview:    tổng tin nhắn, user unique, hôm nay
      - daily_7days: tin nhắn mỗi ngày trong 7 ngày qua
      - hourly:      phân bố theo giờ trong ngày
      - peak_hour:   giờ cao điểm
    
    Dùng để vẽ dashboard thống kê trên Android app.
    """
    bot = get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại")

    page_id  = bot["page_id"]
    overview = get_stats_overview(page_id)
    daily    = get_messages_by_day(page_id, days=7)
    hourly   = get_messages_by_hour(page_id)
    peak     = get_peak_hour(page_id)

    return StatsResponse(
        page_id     = page_id,
        overview    = StatsOverview(**overview),
        daily_7days = [DailyCount(**d) for d in daily],
        hourly      = [HourlyCount(**h) for h in hourly],
        peak_hour   = peak["peak_hour"],
        peak_count  = peak["count"]
    )
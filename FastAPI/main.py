# =====================================================
# main.py - FastAPI chính cho AI Chatbot Admin
# =====================================================

from fastapi import FastAPI, Request, Query, Depends, Header, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import List

# Import từ các file đã tách
from config import settings, get_admin_token, get_verify_token, get_max_turns
from schemas import (
    LoginRequest, TokenResponse, 
    BotCreate, BotUpdate, BotResponse, 
    MessageResponse, ChatHistoryResponse, Message
)
from db import (
    get_db_connection, 
    get_bot_by_page, 
    get_all_bots, 
    create_bot_new,     
    update_bot, 
    delete_bot,
    save_message,           
    get_chat_history,
    get_bot_by_id           # ← Đã thêm
)

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

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
# MEMORY (Conversation History)
# =====================================================
conversation_memory = {}

# =====================================================
# AUTH DEPENDENCY
# =====================================================
def verify_token(authorization: str = Header(None)):
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
def build_prompt(system_prompt: str, memory_key: str, user_text: str) -> str:
    history = conversation_memory.get(memory_key, [])
    prompt = f"{system_prompt.strip()}\n\n"
    
    for h in history:
        prompt += f"User: {h['user']}\nAI: {h['ai']}\n"
    
    prompt += f"User: {user_text}\nAI:"
    return prompt

def ask_ai(memory_key: str, system_prompt: str, user_text: str, page_id: str, sender_id: str) -> str:
    prompt = build_prompt(system_prompt, memory_key, user_text)

    try:
        response = requests.post(
            settings.OLLAMA_URL,
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=90
        )
        response.raise_for_status()
        answer = response.json().get("response", "").strip()

        save_message(page_id, sender_id, user_text, is_from_user=1)
        save_message(page_id, "bot", answer, is_from_user=0)

        history = conversation_memory.get(memory_key, [])
        history.append({"user": user_text, "ai": answer})
        conversation_memory[memory_key] = history[-get_max_turns():]

        return answer
    except Exception as e:
        print(f"[AI Error] {e}")
        return "Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau."

# =====================================================
# WEBHOOK - FACEBOOK
# =====================================================
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == get_verify_token():
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request):
    try:
        data = await request.json()
    except:
        return JSONResponse(content={"status": "error"}, status_code=400)

    for entry in data.get("entry", []):
        page_id = entry.get("id")

        bot = get_bot_by_page(page_id)
        if not bot or bot.get("is_active") == 0:
            continue

        for messaging in entry.get("messaging", []):
            if "message" not in messaging or "sender" not in messaging:
                continue

            sender_id = messaging["sender"]["id"]
            text = messaging.get("message", {}).get("text")
            if not text:
                continue

            memory_key = f"{page_id}_{sender_id}"

            try:
                reply = ask_ai(memory_key, bot["system_prompt"], text, page_id, sender_id)
            except:
                reply = "Xin lỗi, chatbot đang gặp vấn đề."

            try:
                requests.post(
                    f"{settings.FACEBOOK_GRAPH_URL}/{settings.FACEBOOK_API_VERSION}/me/messages",
                    params={"access_token": bot["page_token"]},
                    json={
                        "recipient": {"id": sender_id},
                        "message": {"text": reply}
                    },
                    timeout=10
                )
            except Exception as e:
                print(f"[Facebook Send Error] {e}")

    return JSONResponse(content={"status": "ok"})


# =====================================================
# NEW: LẤY LỊCH SỬ CHAT
# =====================================================
@app.get("/bots/{bot_id}/history", response_model=ChatHistoryResponse)
def get_bot_history(bot_id: int, auth: bool = Depends(verify_token)):
    bot = get_bot_by_id(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    history = get_chat_history(bot["page_id"], limit=50)
    return ChatHistoryResponse(page_id=bot["page_id"], messages=history)


# =====================================================
# AUTH & BOT MANAGEMENT
# =====================================================
@app.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM users WHERE username=? AND password=?",
            (data.username, data.password)
        )
        user = cur.fetchone()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    return TokenResponse(token=get_admin_token())


@app.get("/bots", response_model=List[BotResponse])
def get_bots(auth: bool = Depends(verify_token)):
    return get_all_bots()


@app.post("/bots", response_model=BotResponse, status_code=201)
def create_bot(bot: BotCreate, auth: bool = Depends(verify_token)):
    bot_id = create_bot_new(
        page_id=bot.page_id,
        page_token=bot.page_token or "default_token",
        name=bot.name,
        system_prompt=bot.system_prompt
    )

    if bot_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot with this Page ID already exists or creation failed"
        )

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, page_id, name, is_active 
            FROM bots WHERE id = ?
        """, (bot_id,))
        new_bot = dict(cur.fetchone())

    return new_bot


@app.put("/bots/{bot_id}", response_model=MessageResponse)
def update_bot_route(bot_id: int, data: BotUpdate, auth: bool = Depends(verify_token)):
    success = update_bot(
        bot_id=bot_id,
        is_active=data.is_active
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found or no changes made"
        )

    return MessageResponse(message="Bot updated successfully")


@app.delete("/bots/{bot_id}", response_model=MessageResponse)
def delete_bot_route(bot_id: int, auth: bool = Depends(verify_token)):
    success = delete_bot(bot_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )

    return MessageResponse(message="Bot deleted successfully")


# =====================================================
# ROOT
# =====================================================
@app.get("/")
def root():
    return {
        "status": "success",
        "message": f"{settings.APP_NAME} is running",
        "version": "1.0"
    }
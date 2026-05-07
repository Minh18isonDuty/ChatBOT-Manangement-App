package com.ngocquanlychatbot.data.model

// ── Bot ───────────────────────────────────────────
data class Bot(
    val id: Int,
    val page_id: String,
    val name: String,
    val is_active: Int          // 0 = tắt, 1 = bật
)

// ── Auth ──────────────────────────────────────────
data class LoginRequest(
    val username: String,
    val password: String
)

data class LoginResponse(
    val token: String
)

// ── Bot CRUD ──────────────────────────────────────
data class CreateBotRequest(
    val page_id: String,
    val page_token: String,
    val name: String,
    val system_prompt: String
)

data class BotUpdateRequest(
    val is_active: Int? = null
)

// ── Message History ───────────────────────────────
data class Message(
    val id: Int,
    val sender_id: String,
    val message: String,
    val is_from_user: Int,      // 1 = Khách hàng, 0 = Bot
    val created_at: String      // SQLite string: "2024-01-15 10:30:00"
)

data class ChatHistoryResponse(
    val page_id: String,
    val messages: List<Message>
)

// ── Typing Indicator ──────────────────────────────
// Gửi lên backend để trigger Facebook "đang nhập..."
// Backend gọi Facebook Graph API với sender_action = "typing_on/off"
data class TypingRequest(
    val recipient_id: String,   // Facebook sender ID
    val is_typing: Boolean      // true = hiện "...", false = ẩn
)
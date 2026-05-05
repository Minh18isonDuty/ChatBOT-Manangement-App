package com.ngocquanlychatbot.data.model

import java.time.LocalDateTime

data class Bot(
    val id: Int,
    val page_id: String,
    val name: String,
    val is_active: Int          // 0 hoặc 1
)

data class LoginRequest(
    val username: String,
    val password: String
)

data class LoginResponse(
    val token: String
)

data class CreateBotRequest(
    val page_id: String,
    val page_token: String,
    val name: String,
    val system_prompt: String
)

data class BotUpdateRequest(
    val is_active: Int? = null
)

// ====================== MESSAGE HISTORY MODELS ======================
data class Message(
    val id: Int,
    val sender_id: String,
    val message: String,
    val is_from_user: Int,           // 1 = Khách hàng, 0 = Bot
    val created_at: String           // ISO format hoặc timestamp string
)

data class ChatHistoryResponse(
    val page_id: String,
    val messages: List<Message>
)
package com.ngocquanlychatbot.data.api

import com.ngocquanlychatbot.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ── Auth ──────────────────────────────────────
    @POST("/login")
    suspend fun login(
        @Body request: LoginRequest
    ): Response<LoginResponse>

    // ── Bot CRUD ──────────────────────────────────
    @GET("/bots")
    suspend fun getBots(
        @Header("Authorization") authorization: String
    ): Response<List<Bot>>

    @POST("/bots")
    suspend fun createBot(
        @Header("Authorization") authorization: String,
        @Body request: CreateBotRequest
    ): Response<Bot>

    @PUT("/bots/{bot_id}")
    suspend fun updateBot(
        @Header("Authorization") authorization: String,
        @Path("bot_id") botId: Int,
        @Body request: BotUpdateRequest
    ): Response<Any>

    @DELETE("/bots/{bot_id}")
    suspend fun deleteBot(
        @Header("Authorization") authorization: String,
        @Path("bot_id") botId: Int
    ): Response<Any>

    // ── Chat History ──────────────────────────────
    @GET("/bots/{bot_id}/history")
    suspend fun getChatHistory(
        @Header("Authorization") authorization: String,
        @Path("bot_id") botId: Int
    ): Response<ChatHistoryResponse>

    // ── Typing Indicator ──────────────────────────
    // Trigger backend gửi "typing_on/off" về Facebook.
    // Thường KHÔNG cần gọi từ Android vì backend tự xử lý
    // trong webhook flow. Endpoint này dùng để test thủ công
    // hoặc trigger từ admin dashboard nếu cần.
    @POST("/bots/{bot_id}/typing")
    suspend fun sendTypingIndicator(
        @Header("Authorization") authorization: String,
        @Path("bot_id") botId: Int,
        @Body request: TypingRequest
    ): Response<Any>
}
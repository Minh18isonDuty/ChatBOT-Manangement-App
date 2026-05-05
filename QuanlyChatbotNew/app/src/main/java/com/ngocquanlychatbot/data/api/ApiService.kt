package com.ngocquanlychatbot.data.api

import com.ngocquanlychatbot.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @POST("/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("/bots")
    suspend fun getBots(@Header("Authorization") authorization: String): Response<List<Bot>>

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

    // ====================== MỚI: LẤY LỊCH SỬ CHAT ======================
    @GET("/bots/{bot_id}/history")
    suspend fun getChatHistory(
        @Header("Authorization") authorization: String,
        @Path("bot_id") botId: Int
    ): Response<ChatHistoryResponse>
}
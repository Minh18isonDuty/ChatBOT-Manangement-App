package com.ngocquanlychatbot.data.repository

import com.ngocquanlychatbot.data.api.ApiService
import com.ngocquanlychatbot.data.api.RetrofitClient
import com.ngocquanlychatbot.data.model.*

class BotRepository {

    private val apiService: ApiService = RetrofitClient.instance

    // =====================================================
    // AUTH
    // =====================================================
    suspend fun login(username: String, password: String): Result<LoginResponse> {
        return try {
            val response = apiService.login(LoginRequest(username, password))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Đăng nhập thất bại: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // =====================================================
    // BOT MANAGEMENT
    // =====================================================
    suspend fun getBots(token: String): Result<List<Bot>> {
        return try {
            val response = apiService.getBots("Bearer $token")
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Không thể lấy danh sách bot: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun createBot(token: String, request: CreateBotRequest): Result<Bot> {
        return try {
            val response = apiService.createBot("Bearer $token", request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(
                    Exception("Tạo bot thất bại: ${response.code()} - ${response.errorBody()?.string()}")
                )
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateBot(token: String, botId: Int, isActive: Int): Result<Unit> {
        return try {
            val response = apiService.updateBot(
                authorization = "Bearer $token",
                botId         = botId,
                request       = BotUpdateRequest(is_active = isActive)
            )
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Cập nhật thất bại: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteBot(token: String, botId: Int): Result<Unit> {
        return try {
            val response = apiService.deleteBot("Bearer $token", botId)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Xóa bot thất bại: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // =====================================================
    // CHAT HISTORY
    // =====================================================
    suspend fun getChatHistory(token: String, botId: Int): Result<ChatHistoryResponse> {
        return try {
            val response = apiService.getChatHistory("Bearer $token", botId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Không thể tải lịch sử chat: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // =====================================================
    // TYPING INDICATOR
    //
    // Gọi endpoint này TRƯỚC khi AI trả lời để Facebook
    // hiển thị "..." (đang nhập) trong hộp chat của user.
    //
    // Flow chuẩn:
    //   1. Nhận tin nhắn từ user
    //   2. sendTypingOn()  ← hiện "..."
    //   3. Gọi AI (mất 3-10s)
    //   4. sendTypingOff() ← tắt "..."  (tự tắt sau 20s nếu quên)
    //   5. Gửi reply
    //
    // Lưu ý: typing indicator được điều khiển từ BACKEND
    // (FastAPI → Facebook Graph API), không phải từ Android.
    // Repository này chỉ cung cấp hàm trigger backend.
    // =====================================================
    suspend fun sendTypingIndicator(
        token: String,
        botId: Int,
        recipientId: String,
        isTyping: Boolean
    ): Result<Unit> {
        return try {
            val response = apiService.sendTypingIndicator(
                authorization = "Bearer $token",
                botId         = botId,
                request       = TypingRequest(
                    recipient_id = recipientId,
                    is_typing    = isTyping
                )
            )
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                // Typing indicator fail không nên crash app → log và bỏ qua
                Result.failure(Exception("Typing indicator thất bại: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
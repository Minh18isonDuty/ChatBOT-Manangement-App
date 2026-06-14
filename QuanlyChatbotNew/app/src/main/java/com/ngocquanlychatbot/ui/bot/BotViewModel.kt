package com.ngocquanlychatbot.ui.bot

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ngocquanlychatbot.data.model.Bot
import com.ngocquanlychatbot.data.model.BotStatsResponse
import com.ngocquanlychatbot.data.model.ChatHistoryResponse
import com.ngocquanlychatbot.data.repository.BotRepository
import kotlinx.coroutines.launch

class BotViewModel(private val repository: BotRepository) : ViewModel() {

    // Danh sách bot
    private val _bots = MutableLiveData<List<Bot>>()
    val bots: LiveData<List<Bot>> = _bots

    private val _botStats = MutableLiveData<BotStatsResponse>()
    val botStats: LiveData<BotStatsResponse> = _botStats

    // Lịch sử chat
    private val _chatHistory = MutableLiveData<ChatHistoryResponse>()
    val chatHistory: LiveData<ChatHistoryResponse> = _chatHistory

    private val _isLoading = MutableLiveData<Boolean>()
    val isLoading: LiveData<Boolean> = _isLoading

    private val _errorMessage = MutableLiveData<String?>()
    val errorMessage: LiveData<String?> = _errorMessage

    private val _successMessage = MutableLiveData<String?>()
    val successMessage: LiveData<String?> = _successMessage

    // ====================== LOAD DANH SÁCH BOT ======================
    fun loadBots(token: String) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null

            val result = repository.getBots(token)
            result.onSuccess { botList ->
                _bots.value = botList
            }.onFailure { exception ->
                _errorMessage.value = "Lỗi tải danh sách bot: ${exception.message}"
            }

            _isLoading.value = false
        }
    }

    // ====================== TOGGLE BOT ======================
    fun toggleBot(token: String, bot: Bot) {
        viewModelScope.launch {
            _isLoading.value = true

            val newIsActive = if (bot.is_active == 1) 0 else 1

            val result = repository.updateBot(token, bot.id, newIsActive)

            result.onSuccess {
                _successMessage.value = "Đã ${if (newIsActive == 1) "bật" else "tắt"} bot '${bot.name}'"
                loadBots(token)
            }.onFailure { exception ->
                _errorMessage.value = "Không thể thay đổi trạng thái bot: ${exception.message}"
                loadBots(token)
            }

            _isLoading.value = false
        }
    }

    // ====================== XÓA BOT ======================
    fun deleteBot(token: String, botId: Int, botName: String) {
        viewModelScope.launch {
            _isLoading.value = true

            val result = repository.deleteBot(token, botId)

            result.onSuccess {
                _successMessage.value = "Đã xóa bot '$botName'"
                loadBots(token)
            }.onFailure { exception ->
                _errorMessage.value = "Không thể xóa bot: ${exception.message}"
            }

            _isLoading.value = false
        }
    }

    // ====================== LẤY LỊCH SỬ CHAT ======================
    fun getChatHistory(token: String, botId: Int) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null

            val result = repository.getChatHistory(token, botId)

            result.onSuccess { history ->
                _chatHistory.value = history
            }.onFailure { exception ->
                _errorMessage.value = "Không thể tải lịch sử chat: ${exception.message}"
            }

            _isLoading.value = false
        }
    }

    fun clearMessages() {
        _errorMessage.value = null
        _successMessage.value = null
    }

    fun getBotStats(token: String, botId: Int) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null

            val result = repository.getBotStats(token, botId)

            result.onSuccess { stats ->
                _botStats.value = stats
            }.onFailure { exception ->
                _errorMessage.value = "Không thể tải thống kê: ${exception.message}"
            }

            _isLoading.value = false
        }
    }

    // ====================== FACTORY ======================
    class Factory(private val repository: BotRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return BotViewModel(repository) as T
        }
    }
}
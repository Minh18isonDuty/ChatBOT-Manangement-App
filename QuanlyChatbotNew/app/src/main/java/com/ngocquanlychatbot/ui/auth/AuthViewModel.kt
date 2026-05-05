package com.ngocquanlychatbot.ui.auth

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ngocquanlychatbot.data.model.LoginResponse
import com.ngocquanlychatbot.data.repository.BotRepository
import kotlinx.coroutines.launch

class AuthViewModel : ViewModel() {

    private val repository = BotRepository()

    private val _isLoading = MutableLiveData<Boolean>()
    val isLoading: LiveData<Boolean> = _isLoading

    private val _errorMessage = MutableLiveData<String?>()
    val errorMessage: LiveData<String?> = _errorMessage

    private val _loginSuccess = MutableLiveData<LoginResponse?>()
    val loginSuccess: LiveData<LoginResponse?> = _loginSuccess

    fun login(username: String, password: String) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null

            try {
                val result = repository.login(username, password)

                result.onSuccess { response ->
                    _loginSuccess.value = response
                }.onFailure { exception ->
                    _errorMessage.value = exception.message ?: "Đăng nhập thất bại"
                }
            } catch (e: Exception) {
                _errorMessage.value = "Lỗi kết nối: ${e.message}"
            }

            _isLoading.value = false
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }
}
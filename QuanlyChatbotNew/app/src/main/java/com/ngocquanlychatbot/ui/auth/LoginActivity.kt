package com.ngocquanlychatbot.ui.auth

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.lifecycle.ViewModelProvider
import com.ngocquanlychatbot.databinding.ActivityLoginBinding
import com.ngocquanlychatbot.ui.bot.BotListActivity
import com.ngocquanlychatbot.utils.SecurePrefs   // ← import helper mới

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var viewModel: AuthViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        viewModel = ViewModelProvider(this)[AuthViewModel::class.java]

        setupObservers()
        setupListeners()
    }

    private fun setupObservers() {

        viewModel.isLoading.observe(this) { isLoading ->
            binding.btnLogin.isEnabled   = !isLoading
            binding.progressBar.isVisible = isLoading
        }

        viewModel.errorMessage.observe(this) { error ->
            error?.let {
                Toast.makeText(this, it, Toast.LENGTH_LONG).show()
                viewModel.clearError()
            }
        }

        viewModel.loginSuccess.observe(this) { response ->
            response?.let {
                // FIX: dùng SecurePrefs thay vì SharedPreferences plain text
                // Token được mã hóa AES-256-GCM trước khi lưu xuống disk
                SecurePrefs.saveToken(this, it.token)

                Toast.makeText(this, "Đăng nhập thành công!", Toast.LENGTH_SHORT).show()
                startActivity(Intent(this, BotListActivity::class.java))
                finish()
            }
        }
    }

    private fun setupListeners() {
        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Vui lòng nhập đầy đủ thông tin", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.login(username, password)
        }
    }
}
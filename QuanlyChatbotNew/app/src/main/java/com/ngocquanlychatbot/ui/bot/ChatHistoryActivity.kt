package com.ngocquanlychatbot.ui.bot

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.ngocquanlychatbot.data.model.ChatHistoryResponse
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.ActivityChatHistoryBinding

class ChatHistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChatHistoryBinding
    private lateinit var adapter: ChatHistoryAdapter
    private lateinit var viewModel: BotViewModel

    private var botId: Int = -1
    private var botName: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        botId = intent.getIntExtra("BOT_ID", -1)
        botName = intent.getStringExtra("BOT_NAME") ?: "Lịch sử chat"

        if (botId == -1) {
            Toast.makeText(this, "Không tìm thấy thông tin bot", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        viewModel = ViewModelProvider(
            this,
            BotViewModel.Factory(BotRepository())
        )[BotViewModel::class.java]

        setupToolbar()
        setupRecyclerView()
        observeViewModel()

        loadChatHistory()
    }

    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = botName

        binding.toolbar.setNavigationOnClickListener { finish() }
    }

    private fun setupRecyclerView() {
        adapter = ChatHistoryAdapter()

        binding.recyclerViewChat.apply {
            layoutManager = LinearLayoutManager(this@ChatHistoryActivity).apply {
                stackFromEnd = true
            }
            this.adapter = this@ChatHistoryActivity.adapter
        }
    }

    private fun observeViewModel() {
        viewModel.chatHistory.observe(this) { history ->
            adapter.submitList(history.messages)
            binding.layoutEmptyChat.isVisible = history.messages.isEmpty()

            if (history.messages.isNotEmpty()) {
                binding.recyclerViewChat.scrollToPosition(history.messages.size - 1)
            }
        }

        viewModel.isLoading.observe(this) { isLoading ->
            // Nếu layout chưa có progressBar thì comment dòng dưới lại
            binding.progressBar?.isVisible = isLoading
        }

        viewModel.errorMessage.observe(this) { error ->
            error?.let {
                Toast.makeText(this, it, Toast.LENGTH_LONG).show()
                viewModel.clearMessages()
            }
        }
    }

    private fun loadChatHistory() {
        val token = getSharedPreferences("auth_prefs", MODE_PRIVATE)
            .getString("token", null)

        if (token != null) {
            viewModel.getChatHistory(token, botId)
        } else {
            Toast.makeText(this, "Token không tồn tại. Vui lòng đăng nhập lại.", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    companion object {
        fun newIntent(context: android.content.Context, botId: Int, botName: String): Intent {
            return Intent(context, ChatHistoryActivity::class.java).apply {
                putExtra("BOT_ID", botId)
                putExtra("BOT_NAME", botName)
            }
        }
    }
}
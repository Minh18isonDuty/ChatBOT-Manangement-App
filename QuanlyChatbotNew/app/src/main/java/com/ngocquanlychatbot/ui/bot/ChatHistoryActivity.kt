package com.ngocquanlychatbot.ui.bot

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.ActivityChatHistoryBinding
import com.ngocquanlychatbot.ui.auth.LoginActivity
import com.ngocquanlychatbot.utils.SecurePrefs   // ← import helper mới

class ChatHistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChatHistoryBinding
    private lateinit var adapter: ChatHistoryAdapter
    private lateinit var viewModel: BotViewModel

    private val layoutManager by lazy {
        LinearLayoutManager(this).apply { stackFromEnd = true }
    }

    private var botId: Int    = -1
    private var botName: String = ""
    private var token: String?  = null

    // Pagination state
    private var isLoadingMore = false
    private var hasMoreData   = true
    private var currentOffset = 0
    private val pageSize      = 30

    // ── Lifecycle ─────────────────────────────────────
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        botId   = intent.getIntExtra("BOT_ID", -1)
        botName = intent.getStringExtra("BOT_NAME") ?: "Lịch sử chat"

        // FIX: đọc token từ SecurePrefs thay vì SharedPreferences plain text
        token = SecurePrefs.getToken(this)

        if (botId == -1)   { showToast("Không tìm thấy thông tin bot"); finish(); return }
        if (token == null) { showToast("Phiên đăng nhập đã hết hạn"); goToLogin(); return }

        viewModel = ViewModelProvider(
            this,
            BotViewModel.Factory(BotRepository())
        )[BotViewModel::class.java]

        setupToolbar()
        setupRecyclerView()
        setupSwipeRefresh()
        setupRetryButton()
        observeViewModel()
        loadChatHistory()
    }

    // ── Toolbar ───────────────────────────────────────
    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            title = botName
        }
        binding.toolbar.setNavigationOnClickListener { finish() }
    }

    // ── RecyclerView ──────────────────────────────────
    private fun setupRecyclerView() {
        adapter = ChatHistoryAdapter()

        binding.recyclerViewChat.apply {
            this.layoutManager = this@ChatHistoryActivity.layoutManager
            adapter            = this@ChatHistoryActivity.adapter

            addOnScrollListener(object : RecyclerView.OnScrollListener() {
                override fun onScrolled(rv: RecyclerView, dx: Int, dy: Int) {
                    val firstVisible = this@ChatHistoryActivity.layoutManager
                        .findFirstVisibleItemPosition()
                    if (dy < 0 && firstVisible <= 3 && !isLoadingMore && hasMoreData) {
                        loadMoreHistory()
                    }
                }
            })
        }
    }

    // ── Swipe Refresh ─────────────────────────────────
    private fun setupSwipeRefresh() {
        binding.swipeRefreshLayout.setOnRefreshListener { resetAndReload() }
    }

    // ── Retry ─────────────────────────────────────────
    private fun setupRetryButton() {
        binding.btnRetry.setOnClickListener {
            binding.layoutErrorChat.isVisible = false
            loadChatHistory()
        }
    }

    // ── Observe ───────────────────────────────────────
    private fun observeViewModel() {

        viewModel.chatHistory.observe(this) { history ->
            val messages = history.messages

            binding.layoutEmptyChat.isVisible  = messages.isEmpty()
            binding.layoutErrorChat.isVisible  = false
            binding.recyclerViewChat.isVisible = messages.isNotEmpty()

            adapter.submitList(messages) {
                if (currentOffset == 0 && messages.isNotEmpty()) {
                    binding.recyclerViewChat.scrollToPosition(messages.size - 1)
                }
            }

            hasMoreData                      = messages.size >= pageSize
            isLoadingMore                    = false
            binding.progressBarTop.isVisible = false
        }

        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.isVisible           = isLoading && currentOffset == 0
            binding.swipeRefreshLayout.isRefreshing = false
        }

        viewModel.errorMessage.observe(this) { error ->
            error ?: return@observe

            if (error.contains("401") || error.contains("Unauthorized", ignoreCase = true)) {
                showToast("Phiên đăng nhập đã hết hạn")
                goToLogin()
                return@observe
            }

            showToast(error)

            val isEmpty = adapter.currentList.isEmpty()
            binding.layoutErrorChat.isVisible  = isEmpty
            binding.recyclerViewChat.isVisible = !isEmpty
            isLoadingMore                      = false
            binding.progressBarTop.isVisible   = false
            viewModel.clearMessages()
        }
    }

    // ── Load data ─────────────────────────────────────
    private fun loadChatHistory() {
        currentOffset = 0
        hasMoreData   = true
        viewModel.getChatHistory(token!!, botId)
    }

    private fun loadMoreHistory() {
        if (!hasMoreData || isLoadingMore) return
        isLoadingMore             = true
        currentOffset            += pageSize
        binding.progressBarTop.isVisible = true
        viewModel.getChatHistory(token!!, botId)
    }

    private fun resetAndReload() {
        currentOffset = 0
        hasMoreData   = true
        isLoadingMore = false
        loadChatHistory()
    }

    // ── Navigation ────────────────────────────────────
    private fun goToLogin() {
        // FIX: xóa secure prefs thay vì plain SharedPreferences
        SecurePrefs.clear(this)
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
        finish()
    }

    // ── Helpers ───────────────────────────────────────
    private fun showToast(msg: String) =
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()

    companion object {
        fun newIntent(context: android.content.Context, botId: Int, botName: String): Intent =
            Intent(context, ChatHistoryActivity::class.java).apply {
                putExtra("BOT_ID",   botId)
                putExtra("BOT_NAME", botName)
            }
    }
}
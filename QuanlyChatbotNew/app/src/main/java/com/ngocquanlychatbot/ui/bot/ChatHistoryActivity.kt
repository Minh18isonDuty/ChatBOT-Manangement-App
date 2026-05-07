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

class ChatHistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChatHistoryBinding
    private lateinit var adapter: ChatHistoryAdapter
    private lateinit var viewModel: BotViewModel
    private lateinit var layoutManager: LinearLayoutManager

    private var botId: Int = -1
    private var botName: String = ""
    private var token: String? = null

    // Pagination
    private var isLoadingMore = false
    private var hasMoreData = true
    private var currentOffset = 0
    private val pageSize = 30

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        botId   = intent.getIntExtra("BOT_ID", -1)
        botName = intent.getStringExtra("BOT_NAME") ?: "Lịch sử chat"
        token   = getSharedPreferences("auth_prefs", MODE_PRIVATE).getString("token", null)

        // Guard: không có bot ID
        if (botId == -1) {
            showToast("Không tìm thấy thông tin bot")
            finish()
            return
        }

        // Guard: không có token → về Login
        if (token == null) {
            showToast("Phiên đăng nhập đã hết hạn")
            goToLogin()
            return
        }

        viewModel = ViewModelProvider(
            this,
            BotViewModel.Factory(BotRepository())
        )[BotViewModel::class.java]

        setupToolbar()
        setupRecyclerView()
        setupSwipeRefresh()
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

    // ── RecyclerView + Pagination ──────────────────────
    private fun setupRecyclerView() {
        adapter = ChatHistoryAdapter()
        layoutManager = LinearLayoutManager(this).apply { stackFromEnd = true }

        binding.recyclerViewChat.apply {
            this.layoutManager = this@ChatHistoryActivity.layoutManager
            adapter = this@ChatHistoryActivity.adapter

            // Load thêm khi scroll lên đầu (pagination)
            addOnScrollListener(object : RecyclerView.OnScrollListener() {
                override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                    super.onScrolled(recyclerView, dx, dy)

                    val firstVisible = layoutManager.findFirstVisibleItemPosition()

                    // Khi scroll đến gần đầu danh sách → load thêm
                    if (firstVisible <= 3 && !isLoadingMore && hasMoreData) {
                        loadMoreHistory()
                    }
                }
            })
        }
    }

    // ── Swipe to refresh ──────────────────────────────
    private fun setupSwipeRefresh() {
        binding.swipeRefreshLayout?.setOnRefreshListener {
            resetAndReload()
        }
    }

    // ── Observe ViewModel ─────────────────────────────
    private fun observeViewModel() {

        viewModel.chatHistory.observe(this) { history ->
            val messages = history.messages

            // Empty state
            binding.layoutEmptyChat.isVisible = messages.isEmpty()
            binding.recyclerViewChat.isVisible = messages.isNotEmpty()

            adapter.submitList(messages) {
                // Scroll xuống cuối sau khi load lần đầu
                if (currentOffset == 0 && messages.isNotEmpty()) {
                    binding.recyclerViewChat.scrollToPosition(messages.size - 1)
                }
            }

            // Nếu trả về ít hơn pageSize → không còn data cũ hơn
            hasMoreData = messages.size >= pageSize
            isLoadingMore = false
            binding.progressBarTop?.isVisible = false
        }

        viewModel.isLoading.observe(this) { isLoading ->
            // ProgressBar trung tâm chỉ hiện khi load lần đầu
            binding.progressBar?.isVisible = isLoading && currentOffset == 0
            binding.swipeRefreshLayout?.isRefreshing = false
        }

        viewModel.errorMessage.observe(this) { error ->
            error ?: return@observe

            // Token hết hạn → về Login
            if (error.contains("401") || error.contains("Unauthorized", ignoreCase = true)) {
                showToast("Phiên đăng nhập đã hết hạn")
                goToLogin()
            } else {
                showToast(error)
            }

            // Hiện error state nếu chưa có data
            val isEmpty = adapter.currentList.isEmpty()
            binding.layoutErrorChat?.isVisible = isEmpty
            binding.recyclerViewChat.isVisible = !isEmpty

            isLoadingMore = false
            binding.progressBarTop?.isVisible = false
            viewModel.clearMessages()
        }
    }

    // ── Load data ─────────────────────────────────────

    /** Load lần đầu hoặc sau khi refresh */
    private fun loadChatHistory() {
        currentOffset = 0
        hasMoreData = true
        viewModel.getChatHistory(token!!, botId)
    }

    /** Load thêm tin nhắn cũ hơn khi scroll lên đầu */
    private fun loadMoreHistory() {
        if (!hasMoreData || isLoadingMore) return
        isLoadingMore = true
        currentOffset += pageSize
        binding.progressBarTop?.isVisible = true
        // Gọi cùng hàm — ViewModel sẽ append nếu offset > 0
        // (cần mở rộng ViewModel/API nếu muốn true pagination)
        viewModel.getChatHistory(token!!, botId)
    }

    /** Reset state và reload từ đầu */
    private fun resetAndReload() {
        currentOffset = 0
        hasMoreData = true
        isLoadingMore = false
        loadChatHistory()
    }

    // ── Navigation ────────────────────────────────────
    private fun goToLogin() {
        getSharedPreferences("auth_prefs", MODE_PRIVATE).edit().clear().apply()
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
        finish()
    }

    // ── Helpers ───────────────────────────────────────
    private fun showToast(msg: String) =
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()

    // ── Retry button (nếu có trong layout) ───────────
    private fun setupRetryButton() {
        binding.btnRetry?.setOnClickListener {
            binding.layoutErrorChat?.isVisible = false
            loadChatHistory()
        }
    }

    // ── Companion ─────────────────────────────────────
    companion object {
        fun newIntent(
            context: android.content.Context,
            botId: Int,
            botName: String
        ): Intent = Intent(context, ChatHistoryActivity::class.java).apply {
            putExtra("BOT_ID", botId)
            putExtra("BOT_NAME", botName)
        }
    }
}
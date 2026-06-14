package com.ngocquanlychatbot.ui.bot

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SearchView
import androidx.core.view.isVisible
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.ngocquanlychatbot.data.model.Bot
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.ActivityBotListBinding
import com.ngocquanlychatbot.ui.auth.LoginActivity
import com.ngocquanlychatbot.ui.bot.dialog.CreateBotDialog
import com.ngocquanlychatbot.ui.stats.BotStatsActivity  // ← thêm import
import com.ngocquanlychatbot.utils.SecurePrefs

class BotListActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBotListBinding
    private lateinit var adapter: BotAdapter
    private lateinit var viewModel: BotViewModel

    private var currentToken: String? = null
    private var originalBotList: List<Bot> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBotListBinding.inflate(layoutInflater)
        setContentView(binding.root)

        currentToken = getToken()

        viewModel = ViewModelProvider(
            this,
            BotViewModel.Factory(BotRepository())
        )[BotViewModel::class.java]

        setupToolbar()
        setupRecyclerView()
        setupSwipeRefresh()
        setupFab()
        observeViewModel()

        if (currentToken.isNullOrEmpty()) goToLogin() else loadBots()
    }

    // ── Toolbar ───────────────────────────────────────
    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(false)
        supportActionBar?.title = "Quản lý Chatbot"

        binding.btnLogout.setOnClickListener { showLogoutConfirmation() }

        binding.searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?) = false
            override fun onQueryTextChange(newText: String?): Boolean {
                filterBots(newText.orEmpty())
                return true
            }
        })
    }

    // ── RecyclerView ──────────────────────────────────
    private fun setupRecyclerView() {
        adapter = BotAdapter(
            onToggleClick      = { bot, isChecked ->
                currentToken?.let { token ->
                    if (isChecked) viewModel.toggleBot(token, bot)
                    else showToggleConfirmation(bot, token)
                }
            },
            onDeleteClick      = { bot -> showDeleteConfirmation(bot) },
            onViewHistoryClick = { bot -> openChatHistory(bot) },
            // FIX: thêm callback cho nút thống kê
            onViewStatsClick   = { bot -> openBotStats(bot) }
        )

        binding.recyclerViewBots.apply {
            layoutManager = LinearLayoutManager(this@BotListActivity)
            adapter       = this@BotListActivity.adapter
        }
    }

    // ── Swipe Refresh ─────────────────────────────────
    private fun setupSwipeRefresh() {
        binding.swipeRefreshLayout.setOnRefreshListener { loadBots() }
    }

    // ── FAB ───────────────────────────────────────────
    private fun setupFab() {
        binding.fabAddBot.setOnClickListener {
            CreateBotDialog.newInstance().apply {
                setOnBotCreatedListener { loadBots() }
            }.show(supportFragmentManager, "CreateBotDialog")
        }
    }

    // ── Observe ───────────────────────────────────────
    private fun observeViewModel() {
        viewModel.bots.observe(this) { bots ->
            originalBotList               = bots
            adapter.submitList(bots)
            binding.layoutEmpty.isVisible = bots.isEmpty()
        }

        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.isVisible = isLoading
            if (!isLoading) binding.swipeRefreshLayout.isRefreshing = false
        }

        viewModel.errorMessage.observe(this) { error ->
            error ?: return@observe
            if (error.contains("401") || error.contains("Unauthorized", ignoreCase = true)) {
                Toast.makeText(this, "Phiên đăng nhập đã hết hạn", Toast.LENGTH_LONG).show()
                performLogout()
            } else {
                Toast.makeText(this, error, Toast.LENGTH_LONG).show()
            }
            viewModel.clearMessages()
        }

        viewModel.successMessage.observe(this) { message ->
            message?.let {
                Toast.makeText(this, it, Toast.LENGTH_SHORT).show()
                viewModel.clearMessages()
            }
        }
    }

    // ── Search ────────────────────────────────────────
    private fun filterBots(query: String) {
        adapter.submitList(
            if (query.isEmpty()) originalBotList
            else originalBotList.filter {
                it.name.contains(query, ignoreCase = true) ||
                        it.page_id.contains(query, ignoreCase = true)
            }
        )
    }

    // ── Load ──────────────────────────────────────────
    private fun loadBots() {
        currentToken?.let { viewModel.loadBots(it) }
    }

    // ── Navigation ────────────────────────────────────
    private fun openChatHistory(bot: Bot) {
        startActivity(Intent(this, ChatHistoryActivity::class.java).apply {
            putExtra("BOT_ID",   bot.id)
            putExtra("BOT_NAME", bot.name)
            putExtra("PAGE_ID",  bot.page_id)
        })
    }

    // FIX: hàm mở màn hình thống kê
    private fun openBotStats(bot: Bot) {
        startActivity(BotStatsActivity.newIntent(this, bot.id, bot.name))
    }

    // ── Dialogs ───────────────────────────────────────
    private fun showToggleConfirmation(bot: Bot, token: String) {
        AlertDialog.Builder(this)
            .setTitle("Xác nhận tắt bot")
            .setMessage("Bạn có chắc muốn tắt bot '${bot.name}' không?\n\nBot sẽ ngừng tự động trả lời tin nhắn.")
            .setPositiveButton("Tắt bot") { _, _ -> viewModel.toggleBot(token, bot) }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun showDeleteConfirmation(bot: Bot) {
        AlertDialog.Builder(this)
            .setTitle("Xác nhận xóa")
            .setMessage("Bạn có chắc muốn xóa bot '${bot.name}' không?")
            .setPositiveButton("Xóa") { _, _ ->
                currentToken?.let { viewModel.deleteBot(it, bot.id, bot.name) }
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun showLogoutConfirmation() {
        AlertDialog.Builder(this)
            .setTitle("Đăng xuất")
            .setMessage("Bạn có chắc muốn đăng xuất không?")
            .setPositiveButton("Đăng xuất") { _, _ -> performLogout() }
            .setNegativeButton("Hủy", null)
            .show()
    }

    // ── Auth ──────────────────────────────────────────
    private fun performLogout() {
        SecurePrefs.clear(this)
        Toast.makeText(this, "Đã đăng xuất thành công", Toast.LENGTH_SHORT).show()
        goToLogin()
    }

    private fun goToLogin() {
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
        finish()
    }

    private fun getToken(): String? = SecurePrefs.getToken(this)

    // ── Lifecycle ─────────────────────────────────────
    override fun onResume() {
        super.onResume()
        if (!currentToken.isNullOrEmpty()) loadBots()
    }
}
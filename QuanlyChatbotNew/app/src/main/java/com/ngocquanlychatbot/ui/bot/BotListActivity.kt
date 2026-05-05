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
import com.ngocquanlychatbot.R
import com.ngocquanlychatbot.data.model.Bot
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.ActivityBotListBinding
import com.ngocquanlychatbot.ui.auth.LoginActivity
import com.ngocquanlychatbot.ui.bot.dialog.CreateBotDialog

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

        if (currentToken.isNullOrEmpty()) {
            goToLogin()
        } else {
            loadBots()
        }
    }

    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(false)
        supportActionBar?.title = "Quản lý Chatbot"

        binding.btnLogout.setOnClickListener {
            showLogoutConfirmation()
        }

        binding.searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean = false

            override fun onQueryTextChange(newText: String?): Boolean {
                filterBots(newText.orEmpty())
                return true
            }
        })
    }

    private fun setupRecyclerView() {
        adapter = BotAdapter(
            onToggleClick = { bot, isChecked ->
                currentToken?.let { token ->
                    if (isChecked) {
                        viewModel.toggleBot(token, bot)
                    } else {
                        showToggleConfirmation(bot, token)
                    }
                }
            },
            onDeleteClick = { bot ->
                showDeleteConfirmation(bot)
            },
            onViewHistoryClick = { bot ->
                openChatHistory(bot)
            }
        )

        binding.recyclerViewBots.apply {
            layoutManager = LinearLayoutManager(this@BotListActivity)
            adapter = this@BotListActivity.adapter
        }
    }

    private fun setupSwipeRefresh() {
        binding.swipeRefreshLayout.setOnRefreshListener {
            loadBots()
        }
    }

    private fun setupFab() {
        binding.fabAddBot.setOnClickListener {
            val dialog = CreateBotDialog.newInstance()
            dialog.setOnBotCreatedListener {
                loadBots()
            }
            dialog.show(supportFragmentManager, "CreateBotDialog")
        }
    }

    private fun observeViewModel() {
        viewModel.bots.observe(this) { bots ->
            originalBotList = bots
            adapter.submitList(bots)
            binding.layoutEmpty.isVisible = bots.isEmpty()
        }

        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.isVisible = isLoading
            if (!isLoading) {
                binding.swipeRefreshLayout.isRefreshing = false
            }
        }

        viewModel.errorMessage.observe(this) { error ->
            error?.let {
                if (it.contains("401") || it.contains("Unauthorized", ignoreCase = true)) {
                    Toast.makeText(this, "Phiên đăng nhập đã hết hạn", Toast.LENGTH_LONG).show()
                    performLogout()
                } else {
                    Toast.makeText(this, it, Toast.LENGTH_LONG).show()
                }
                viewModel.clearMessages()
            }
        }

        viewModel.successMessage.observe(this) { message ->
            message?.let {
                Toast.makeText(this, it, Toast.LENGTH_SHORT).show()
                viewModel.clearMessages()
            }
        }
    }

    // ====================== TÌM KIẾM ======================
    private fun filterBots(query: String) {
        val filtered = if (query.isEmpty()) {
            originalBotList
        } else {
            originalBotList.filter { bot ->
                bot.name.contains(query, ignoreCase = true) ||
                        bot.page_id.contains(query, ignoreCase = true)
            }
        }
        adapter.submitList(filtered)
    }

    private fun loadBots() {
        currentToken?.let { token ->
            viewModel.loadBots(token)
        }
    }

    // ====================== XEM LỊCH SỬ CHAT ======================
    private fun openChatHistory(bot: Bot) {
        val intent = Intent(this, ChatHistoryActivity::class.java).apply {
            putExtra("BOT_ID", bot.id)
            putExtra("BOT_NAME", bot.name)
            putExtra("PAGE_ID", bot.page_id)
        }
        startActivity(intent)
    }

    private fun showToggleConfirmation(bot: Bot, token: String) {
        AlertDialog.Builder(this)
            .setTitle("Xác nhận tắt bot")
            .setMessage("Bạn có chắc muốn tắt bot '${bot.name}' không?\n\nBot sẽ ngừng tự động trả lời tin nhắn.")
            .setPositiveButton("Tắt bot") { _, _ ->
                viewModel.toggleBot(token, bot)
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun showDeleteConfirmation(bot: Bot) {
        AlertDialog.Builder(this)
            .setTitle("Xác nhận xóa")
            .setMessage("Bạn có chắc muốn xóa bot '${bot.name}' không?")
            .setPositiveButton("Xóa") { _, _ ->
                currentToken?.let { token ->
                    viewModel.deleteBot(token, bot.id, bot.name)
                }
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun showLogoutConfirmation() {
        AlertDialog.Builder(this)
            .setTitle("Đăng xuất")
            .setMessage("Bạn có chắc muốn đăng xuất không?")
            .setPositiveButton("Đăng xuất") { _, _ ->
                performLogout()
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun performLogout() {
        getSharedPreferences("auth_prefs", MODE_PRIVATE).edit().clear().apply()
        Toast.makeText(this, "Đã đăng xuất thành công", Toast.LENGTH_SHORT).show()
        goToLogin()
    }

    private fun goToLogin() {
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    private fun getToken(): String? {
        return getSharedPreferences("auth_prefs", MODE_PRIVATE)
            .getString("token", null)
    }

    override fun onResume() {
        super.onResume()
        if (!currentToken.isNullOrEmpty()) {
            loadBots()
        }
    }
}
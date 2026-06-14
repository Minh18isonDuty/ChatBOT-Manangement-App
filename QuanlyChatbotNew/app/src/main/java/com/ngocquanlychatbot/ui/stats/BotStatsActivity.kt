package com.ngocquanlychatbot.ui.stats

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.lifecycle.ViewModelProvider
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.ActivityBotStatsBinding
import com.ngocquanlychatbot.ui.bot.BotViewModel
import com.ngocquanlychatbot.utils.SecurePrefs
import java.text.SimpleDateFormat
import java.util.Locale

class BotStatsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBotStatsBinding
    private lateinit var viewModel: BotViewModel

    private var botId:   Int     = -1
    private var botName: String  = ""
    private var token:   String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBotStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        botId   = intent.getIntExtra("BOT_ID", -1)
        botName = intent.getStringExtra("BOT_NAME") ?: "Thống kê"
        token   = SecurePrefs.getToken(this)

        if (botId == -1 || token == null) { finish(); return }

        viewModel = ViewModelProvider(
            this,
            BotViewModel.Factory(BotRepository())
        )[BotViewModel::class.java]

        setupToolbar()
        observeViewModel()
        viewModel.getBotStats(token!!, botId)
    }

    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            title = "Thống kê · $botName"
        }
        binding.toolbar.setNavigationOnClickListener { finish() }
    }

    private fun observeViewModel() {

        viewModel.botStats.observe(this) { stats ->
            val ov = stats.overview

            // ── 4 thẻ tổng quan ──────────────────────
            binding.tvTotalMessages.text = ov.total_messages.toString()
            binding.tvUniqueUsers.text   = ov.unique_users.toString()
            binding.tvTodayMessages.text = ov.today_messages.toString()
            binding.tvPeakHour.text      =
                if (stats.peak_count > 0) "${stats.peak_hour}:00" else "--"

            // ── Bar chart 7 ngày ──────────────────────
            if (stats.daily_7days.isNotEmpty()) {
                val labels = stats.daily_7days.map { formatDate(it.date) }
                val values = stats.daily_7days.map { it.count.toFloat() }
                binding.barChartView.setData(
                    labels = labels,
                    values = values,
                    color  = 0xFF7C4DFF.toInt()
                )
            }

            // ── Hourly chart ──────────────────────────
            if (stats.hourly.isNotEmpty()) {
                val hourMap = stats.hourly.associate { it.hour to it.count }
                // Gộp mỗi 3 giờ thành 1 cột → 8 cột (0h,3h,6h,...,21h)
                val labels = (0..23 step 3).map { "${it}h" }
                val values = (0..23 step 3).map { h ->
                    (h until minOf(h + 3, 24)).sumOf { hourMap[it] ?: 0 }.toFloat()
                }
                binding.hourlyChartView.setData(
                    labels = labels,
                    values = values,
                    color  = 0xFF00BCD4.toInt()
                )
            }
        }

        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.isVisible = isLoading
        }

        viewModel.errorMessage.observe(this) { error ->
            error?.let {
                Toast.makeText(this, it, Toast.LENGTH_LONG).show()
                viewModel.clearMessages()
            }
        }
    }

    /**
     * Format ngày từ "2024-01-15" → "T3\n15/1"
     *
     * FIX: dùng SimpleDateFormat thay vì java.time.LocalDate
     * vì LocalDate yêu cầu API 26+, minSdk của project là 24.
     * SimpleDateFormat tương thích từ API 1.
     */
    private fun formatDate(dateStr: String): String {
        return try {
            val inputFmt  = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            val date      = inputFmt.parse(dateStr) ?: return dateStr

            // Lấy tên thứ viết tắt tiếng Việt
            val dayFmt    = SimpleDateFormat("EEE", Locale("vi", "VN"))
            val dateFmt   = SimpleDateFormat("d/M", Locale.getDefault())

            "${dayFmt.format(date)}\n${dateFmt.format(date)}"
        } catch (e: Exception) {
            // Fallback: lấy phần MM-dd nếu parse thất bại
            dateStr.takeLast(5)
        }
    }

    companion object {
        fun newIntent(context: Context, botId: Int, botName: String): Intent =
            Intent(context, BotStatsActivity::class.java).apply {
                putExtra("BOT_ID",   botId)
                putExtra("BOT_NAME", botName)
            }
    }
}
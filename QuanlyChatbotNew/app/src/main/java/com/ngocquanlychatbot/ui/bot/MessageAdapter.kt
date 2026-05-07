package com.ngocquanlychatbot.ui.bot

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ngocquanlychatbot.data.model.Message
import com.ngocquanlychatbot.databinding.ItemMessageBotBinding
import com.ngocquanlychatbot.databinding.ItemMessageUserBinding
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

class ChatHistoryAdapter : ListAdapter<Message, RecyclerView.ViewHolder>(MessageDiffCallback()) {

    companion object {
        const val VIEW_TYPE_USER = 1
        const val VIEW_TYPE_BOT = 2

        /**
         * Format thời gian từ SQLite string sang dạng đọc được.
         *
         * SQLite trả về: "2024-01-15 10:30:00" hoặc "2024-01-15T10:30:00"
         * Hiển thị:      "10:30, 15/01/2024"
         *
         * Nếu parse thất bại → trả về chuỗi gốc để không crash.
         */
        fun formatTime(raw: String?): String {
            if (raw.isNullOrBlank()) return ""

            // Thử lần lượt các format SQLite có thể trả về
            val inputFormats = listOf(
                "yyyy-MM-dd HH:mm:ss",
                "yyyy-MM-dd'T'HH:mm:ss",
                "yyyy-MM-dd HH:mm:ss.SSSSSS",  // SQLite với microseconds
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
            )

            val outputFormat = SimpleDateFormat("HH:mm, dd/MM/yyyy", Locale("vi", "VN"))

            for (pattern in inputFormats) {
                try {
                    val sdf = SimpleDateFormat(pattern, Locale.getDefault())
                    sdf.timeZone = TimeZone.getTimeZone("Asia/Ho_Chi_Minh")
                    val date = sdf.parse(raw) ?: continue
                    return outputFormat.format(date)
                } catch (e: Exception) {
                    continue
                }
            }

            // Fallback: trả về raw nếu không parse được
            return raw
        }
    }

    // ── View type ─────────────────────────────────────
    override fun getItemViewType(position: Int): Int {
        return if (getItem(position).is_from_user == 1) VIEW_TYPE_USER else VIEW_TYPE_BOT
    }

    // ── Create ViewHolder ──────────────────────────────
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (viewType == VIEW_TYPE_USER) {
            UserMessageViewHolder(ItemMessageUserBinding.inflate(inflater, parent, false))
        } else {
            BotMessageViewHolder(ItemMessageBotBinding.inflate(inflater, parent, false))
        }
    }

    // ── Bind ───────────────────────────────────────────
    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = getItem(position)
        when (holder) {
            is UserMessageViewHolder -> holder.bind(message)
            is BotMessageViewHolder  -> holder.bind(message)
        }
    }

    // ── ViewHolder: User ───────────────────────────────
    inner class UserMessageViewHolder(
        private val binding: ItemMessageUserBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(message: Message) {
            binding.tvUserMessage.text = message.message
            // FIX: format thời gian thay vì hiển thị raw string
            binding.tvUserTime.text = formatTime(message.created_at)
        }
    }

    // ── ViewHolder: Bot ────────────────────────────────
    inner class BotMessageViewHolder(
        private val binding: ItemMessageBotBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(message: Message) {
            binding.tvBotMessage.text = message.message
            // FIX: format thời gian thay vì hiển thị raw string
            binding.tvBotTime.text = formatTime(message.created_at)
        }
    }

    // ── DiffCallback ───────────────────────────────────
    class MessageDiffCallback : DiffUtil.ItemCallback<Message>() {
        override fun areItemsTheSame(oldItem: Message, newItem: Message) =
            oldItem.id == newItem.id

        override fun areContentsTheSame(oldItem: Message, newItem: Message) =
            oldItem == newItem
    }
}
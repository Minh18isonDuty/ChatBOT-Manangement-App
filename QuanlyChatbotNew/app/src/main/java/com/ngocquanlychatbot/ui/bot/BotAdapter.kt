package com.ngocquanlychatbot.ui.bot

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ngocquanlychatbot.R
import com.ngocquanlychatbot.data.model.Bot
import com.ngocquanlychatbot.databinding.ItemBotBinding

class BotAdapter(
    private val onToggleClick: (Bot, Boolean) -> Unit,      // Toggle bật/tắt
    private val onDeleteClick: (Bot) -> Unit,               // Xóa bot
    private val onViewHistoryClick: (Bot) -> Unit           // Xem lịch sử chat (mới)
) : ListAdapter<Bot, BotAdapter.BotViewHolder>(BotDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): BotViewHolder {
        val binding = ItemBotBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return BotViewHolder(binding)
    }

    override fun onBindViewHolder(holder: BotViewHolder, position: Int) {
        val bot = getItem(position)
        holder.bind(bot)
    }

    inner class BotViewHolder(private val binding: ItemBotBinding) : RecyclerView.ViewHolder(binding.root) {

        fun bind(bot: Bot) {
            binding.tvBotName.text = bot.name
            binding.tvPageId.text = "Page ID: ${bot.page_id}"

            // Trạng thái
            if (bot.is_active == 1) {
                binding.tvStatus.text = "Đang hoạt động"
                binding.tvStatus.setTextColor(ContextCompat.getColor(binding.root.context, android.R.color.holo_green_dark))
                binding.switchActive.isChecked = true
            } else {
                binding.tvStatus.text = "Đã tắt"
                binding.tvStatus.setTextColor(ContextCompat.getColor(binding.root.context, android.R.color.holo_red_dark))
                binding.switchActive.isChecked = false
            }

            // Toggle Switch
            binding.switchActive.setOnCheckedChangeListener { _, isChecked ->
                if (isChecked != (bot.is_active == 1)) {
                    onToggleClick(bot, isChecked)
                }
            }

            // Nút Xem lịch sử
            binding.btnViewHistory.setOnClickListener {
                onViewHistoryClick(bot)
            }

            // Nút Xóa
            binding.btnDelete.setOnClickListener {
                onDeleteClick(bot)
            }
        }
    }

    class BotDiffCallback : DiffUtil.ItemCallback<Bot>() {
        override fun areItemsTheSame(oldItem: Bot, newItem: Bot): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: Bot, newItem: Bot): Boolean {
            return oldItem == newItem
        }
    }
}
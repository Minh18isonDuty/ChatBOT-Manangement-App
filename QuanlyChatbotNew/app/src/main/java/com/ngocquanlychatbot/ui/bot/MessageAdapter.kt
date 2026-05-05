package com.ngocquanlychatbot.ui.bot

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.ngocquanlychatbot.data.model.Message
import com.ngocquanlychatbot.databinding.ItemMessageBotBinding
import com.ngocquanlychatbot.databinding.ItemMessageUserBinding

class ChatHistoryAdapter : ListAdapter<Message, RecyclerView.ViewHolder>(MessageDiffCallback()) {

    companion object {
        const val VIEW_TYPE_USER = 1
        const val VIEW_TYPE_BOT = 2
    }

    override fun getItemViewType(position: Int): Int {
        val message = getItem(position)
        // Sửa ở đây: is_from_user là Int (0 hoặc 1)
        return if (message.is_from_user == 1) VIEW_TYPE_USER else VIEW_TYPE_BOT
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        return if (viewType == VIEW_TYPE_USER) {
            val binding = ItemMessageUserBinding.inflate(LayoutInflater.from(parent.context), parent, false)
            UserMessageViewHolder(binding)
        } else {
            val binding = ItemMessageBotBinding.inflate(LayoutInflater.from(parent.context), parent, false)
            BotMessageViewHolder(binding)
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = getItem(position)
        when (holder) {
            is UserMessageViewHolder -> holder.bind(message)
            is BotMessageViewHolder -> holder.bind(message)
        }
    }

    // ViewHolder cho tin nhắn từ User
    inner class UserMessageViewHolder(private val binding: ItemMessageUserBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(message: Message) {
            binding.tvUserMessage.text = message.message
            binding.tvUserTime.text = message.created_at ?: ""
        }
    }

    // ViewHolder cho tin nhắn từ Bot
    inner class BotMessageViewHolder(private val binding: ItemMessageBotBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(message: Message) {
            binding.tvBotMessage.text = message.message
            binding.tvBotTime.text = message.created_at ?: ""
        }
    }

    class MessageDiffCallback : DiffUtil.ItemCallback<Message>() {
        override fun areItemsTheSame(oldItem: Message, newItem: Message): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: Message, newItem: Message): Boolean {
            return oldItem == newItem
        }
    }
}
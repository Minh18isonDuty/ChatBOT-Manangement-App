package com.ngocquanlychatbot.ui.bot.dialog

import android.app.Dialog
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.DialogFragment
import com.ngocquanlychatbot.data.model.CreateBotRequest
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.DialogCreateBotBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class CreateBotDialog : DialogFragment() {

    private var onBotCreatedListener: (() -> Unit)? = null
    private val repository = BotRepository()

    fun setOnBotCreatedListener(listener: () -> Unit) {
        onBotCreatedListener = listener
    }

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val binding = DialogCreateBotBinding.inflate(layoutInflater)

        val dialog = AlertDialog.Builder(requireContext())
            .setTitle("Tạo Bot Mới")
            .setView(binding.root)
            .setPositiveButton("Tạo", null) // Sẽ xử lý sau
            .setNegativeButton("Hủy", null)
            .create()

        dialog.setOnShowListener {
            val positiveButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            positiveButton.setOnClickListener {
                val pageId = binding.etPageId.text.toString().trim()
                val pageToken = binding.etPageToken.text.toString().trim()
                val name = binding.etName.text.toString().trim()
                val systemPrompt = binding.etSystemPrompt.text.toString().trim()

                if (pageId.isEmpty() || name.isEmpty() || systemPrompt.isEmpty()) {
                    Toast.makeText(requireContext(), "Vui lòng nhập đầy đủ thông tin", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }

                val token = requireActivity().getSharedPreferences("auth_prefs", 0)
                    .getString("token", null)

                if (token == null) {
                    Toast.makeText(requireContext(), "Token không tồn tại", Toast.LENGTH_SHORT).show()
                    dismiss()
                    return@setOnClickListener
                }

                CoroutineScope(Dispatchers.IO).launch {
                    val request = CreateBotRequest(
                        page_id = pageId,
                        page_token = pageToken.ifEmpty { "default_token" },
                        name = name,
                        system_prompt = systemPrompt
                    )

                    val result = repository.createBot(token, request)

                    withContext(Dispatchers.Main) {
                        result.onSuccess {
                            Toast.makeText(requireContext(), "Tạo bot thành công!", Toast.LENGTH_SHORT).show()
                            onBotCreatedListener?.invoke()
                            dismiss()
                        }.onFailure { exception ->
                            Toast.makeText(requireContext(), "Tạo bot thất bại: ${exception.message}", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            }
        }

        return dialog
    }

    companion object {
        fun newInstance(): CreateBotDialog = CreateBotDialog()
    }
}
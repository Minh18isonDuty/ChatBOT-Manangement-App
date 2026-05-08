package com.ngocquanlychatbot.ui.bot.dialog

import android.app.Dialog
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.DialogFragment
import androidx.lifecycle.lifecycleScope
import com.ngocquanlychatbot.data.model.CreateBotRequest
import com.ngocquanlychatbot.data.repository.BotRepository
import com.ngocquanlychatbot.databinding.DialogCreateBotBinding
import com.ngocquanlychatbot.utils.SecurePrefs  // ← import SecurePrefs
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
            .setPositiveButton("Tạo", null)
            .setNegativeButton("Hủy", null)
            .create()

        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {

                val pageId      = binding.etPageId.text.toString().trim()
                val pageToken   = binding.etPageToken.text.toString().trim()
                val name        = binding.etName.text.toString().trim()
                val systemPrompt = binding.etSystemPrompt.text.toString().trim()

                // Validate input
                if (pageId.isEmpty() || name.isEmpty() || systemPrompt.isEmpty()) {
                    Toast.makeText(requireContext(), "Vui lòng nhập đầy đủ thông tin", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }

                // FIX 1: đọc token từ SecurePrefs thay vì getSharedPreferences plain text
                val token = SecurePrefs.getToken(requireContext())

                if (token == null) {
                    Toast.makeText(requireContext(), "Phiên đăng nhập đã hết hạn", Toast.LENGTH_SHORT).show()
                    dismiss()
                    return@setOnClickListener
                }

                // FIX 2: dùng lifecycleScope thay vì CoroutineScope(Dispatchers.IO)
                // lifecycleScope tự cancel khi Fragment bị destroy → không bị memory leak
                lifecycleScope.launch(Dispatchers.IO) {
                    val request = CreateBotRequest(
                        page_id      = pageId,
                        page_token   = pageToken.ifEmpty { "default_token" },
                        name         = name,
                        system_prompt = systemPrompt
                    )

                    val result = repository.createBot(token, request)

                    withContext(Dispatchers.Main) {
                        // Check fragment vẫn còn attached trước khi update UI
                        if (!isAdded) return@withContext

                        result.onSuccess {
                            Toast.makeText(requireContext(), "Tạo bot thành công!", Toast.LENGTH_SHORT).show()
                            onBotCreatedListener?.invoke()
                            dismiss()
                        }.onFailure { exception ->
                            Toast.makeText(
                                requireContext(),
                                "Tạo bot thất bại: ${exception.message}",
                                Toast.LENGTH_LONG
                            ).show()
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
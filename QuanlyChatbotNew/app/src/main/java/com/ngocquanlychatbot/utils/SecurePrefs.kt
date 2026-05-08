package com.ngocquanlychatbot.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * SecurePrefs — Wrapper cho EncryptedSharedPreferences.
 *
 * Tại sao cần:
 *   SharedPreferences thông thường lưu plain text trên disk.
 *   Thiết bị bị root → attacker đọc được token dễ dàng.
 *   EncryptedSharedPreferences mã hóa cả key lẫn value bằng AES-256-GCM
 *   thông qua Android Keystore — key không bao giờ rời khỏi hardware.
 *
 * Cách dùng:
 *   // Lưu token
 *   SecurePrefs.saveToken(context, "abc123")
 *
 *   // Lấy token
 *   val token = SecurePrefs.getToken(context)
 *
 *   // Xóa khi logout
 *   SecurePrefs.clear(context)
 */
object SecurePrefs {

    private const val FILE_NAME  = "secure_auth_prefs"
    private const val KEY_TOKEN  = "token"

    /**
     * Khởi tạo EncryptedSharedPreferences.
     * MasterKey dùng AES256_GCM — chuẩn mã hóa hiện đại,
     * được Android Keystore bảo vệ ở tầng hardware.
     */
    private fun getPrefs(context: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        return EncryptedSharedPreferences.create(
            context,
            FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    /** Lưu token sau khi đăng nhập thành công. */
    fun saveToken(context: Context, token: String) {
        getPrefs(context).edit().putString(KEY_TOKEN, token).apply()
    }

    /**
     * Lấy token đã lưu.
     * Trả về null nếu chưa đăng nhập hoặc đã logout.
     */
    fun getToken(context: Context): String? {
        return getPrefs(context).getString(KEY_TOKEN, null)
    }

    /**
     * Xóa toàn bộ dữ liệu — gọi khi logout.
     * File vẫn còn nhưng rỗng, sẵn sàng cho lần đăng nhập tiếp.
     */
    fun clear(context: Context) {
        getPrefs(context).edit().clear().apply()
    }
}
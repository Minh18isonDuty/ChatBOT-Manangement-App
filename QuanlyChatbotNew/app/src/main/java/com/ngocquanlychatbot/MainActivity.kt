package com.ngocquanlychatbot

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.ngocquanlychatbot.ui.auth.LoginActivity

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Chuyển thẳng sang màn hình Login
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
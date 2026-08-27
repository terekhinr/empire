package ru.neverretire.zadachnik

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import ru.neverretire.zadachnik.data.TokenStore
import ru.neverretire.zadachnik.databinding.ActivityTokenBinding
import ru.neverretire.zadachnik.widget.TasksWidgetProvider

class TokenActivity : AppCompatActivity() {
    private lateinit var binding: ActivityTokenBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTokenBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.tokenInput.setText(TokenStore(this).token.orEmpty())
        binding.btnSave.setOnClickListener {
            val token = binding.tokenInput.text?.toString()?.trim().orEmpty()
            if (token.length < 8) {
                Toast.makeText(this, "Введите PLANNING_API_TOKEN", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            TokenStore(this).token = token
            // Allow one-shot native_token bootstrap in Chrome again
            getSharedPreferences("zadachnik", MODE_PRIVATE).edit().putBoolean("chrome_token_ok", false).apply()
            TasksWidgetProvider.requestRefresh(this)
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }
}

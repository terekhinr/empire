package ru.neverretire.zadachnik

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Intent
import android.content.pm.ShortcutInfo
import android.content.pm.ShortcutManager
import android.graphics.drawable.Icon
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.browser.customtabs.CustomTabsIntent
import ru.neverretire.zadachnik.data.TokenStore
import ru.neverretire.zadachnik.databinding.ActivityMainBinding
import ru.neverretire.zadachnik.widget.TasksWidgetProvider

/**
 * Xiaomi WebView нестабилен — UI всегда в Chrome Custom Tabs.
 * Токен всегда передаём в URL: Chrome может сбросить localStorage.
 */
class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (TokenStore(this).token.isNullOrBlank()) {
            startActivity(Intent(this, TokenActivity::class.java))
            finish()
            return
        }
        installShortcuts()
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnOpen.setOnClickListener { openTasks(passToken = true) }
        binding.btnPinWidget.setOnClickListener { pinWidget() }
        binding.btnChangeToken.setOnClickListener {
            startActivity(Intent(this, TokenActivity::class.java))
            finish()
        }

        // Сразу в Chrome
        if (savedInstanceState == null) {
            openTasks(passToken = true)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        openTasks(passToken = true)
    }

    private fun openTasks(passToken: Boolean) {
        val token = TokenStore(this).token.orEmpty()
        val path = intent?.getStringExtra(EXTRA_PATH) ?: BuildConfig.TASKS_PATH
        val uri = Uri.parse(BuildConfig.BASE_URL.trimEnd('/') + path).buildUpon().apply {
            if (passToken && token.isNotBlank()) {
                appendQueryParameter("native_token", token)
            }
        }.build()

        val viewIntent = Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try {
            CustomTabsIntent.Builder()
                .setShowTitle(true)
                .setUrlBarHidingEnabled(false)
                .build()
                .launchUrl(this, uri)
        } catch (_: Exception) {
            try {
                startActivity(viewIntent)
            } catch (_: Exception) {
                Toast.makeText(this, "Не удалось открыть браузер: $uri", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun pinWidget() {
        val mgr = AppWidgetManager.getInstance(this)
        val provider = ComponentName(this, TasksWidgetProvider::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && mgr.isRequestPinAppWidgetSupported) {
            val success = PendingIntent.getBroadcast(
                this,
                0,
                Intent(this, TasksWidgetProvider::class.java).setAction(TasksWidgetProvider.ACTION_REFRESH),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            mgr.requestPinAppWidget(provider, null, success)
            Toast.makeText(this, "Подтверди виджет на столе", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Долгий тап по столу → Виджеты → Задачник", Toast.LENGTH_LONG).show()
        }
    }

    private fun installShortcuts() {
        if (Build.VERSION.SDK_INT < 25) return
        val sm = getSystemService(ShortcutManager::class.java) ?: return
        fun shortcut(id: String, label: String, path: String): ShortcutInfo {
            val intent = Intent(this, MainActivity::class.java).apply {
                action = Intent.ACTION_VIEW
                putExtra(EXTRA_PATH, path)
            }
            return ShortcutInfo.Builder(this, id)
                .setShortLabel(label)
                .setLongLabel(label)
                .setIcon(Icon.createWithResource(this, R.drawable.ic_launcher_foreground))
                .setIntent(intent)
                .build()
        }
        sm.dynamicShortcuts = listOf(
            shortcut("program", "Тренировка", "/gym/"),
            shortcut("measure", "Замеры", "/gym/?tab=meas"),
            shortcut("stats", "Статистика", "/gym/?tab=meas"),
            shortcut("diary", "Дневник", "/gym/?tab=diary"),
        )
    }

    override fun onResume() {
        super.onResume()
        TasksWidgetProvider.requestRefresh(this)
    }

    companion object {
        const val EXTRA_PATH = "path"
    }
}

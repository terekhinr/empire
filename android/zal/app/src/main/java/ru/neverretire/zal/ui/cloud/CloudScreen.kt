package ru.neverretire.zal.ui.cloud

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import ru.neverretire.zal.data.BackupImporter
import ru.neverretire.zal.data.GymRepository
import ru.neverretire.zal.sync.SupabaseConfig
import ru.neverretire.zal.sync.SyncScheduler

@Composable
fun CloudScreen(repo: GymRepository, onMessage: (String) -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var lastSync by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        lastSync = repo.lastSyncAt()
    }

    val pickBackup = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent(),
    ) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            busy = true
            runCatching {
                val name = uri.lastPathSegment ?: "backup.json"
                ctx.contentResolver.openInputStream(uri)?.use { ins ->
                    val r = BackupImporter.import(ctx, ins, name)
                    onMessage("Импорт: логов ${r.logs}, замеров ${r.measurements}, программ ${r.programs}")
                    SyncScheduler.enqueue(ctx)
                }
            }.onFailure { onMessage(it.message ?: "Ошибка импорта") }
            busy = false
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Облако", style = MaterialTheme.typography.titleLarge)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (SupabaseConfig.isConfigured) {
                    Text("Supabase подключён", color = MaterialTheme.colorScheme.secondary)
                    Text("Последний синк: ${lastSync ?: "ещё не было"}")
                    Button(
                        enabled = !busy,
                        onClick = {
                            scope.launch {
                                busy = true
                                SyncScheduler.enqueue(ctx)
                                // give worker a moment; refresh label after short delay via re-read
                                kotlinx.coroutines.delay(1500)
                                lastSync = repo.lastSyncAt() ?: lastSync
                                onMessage("Синхронизация запущена")
                                busy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Синхронизировать сейчас") }
                } else {
                    Text(
                        "Облако не настроено. Приложение работает офлайн.\n" +
                            "Чтобы включить постоянный синк: создайте бесплатный проект Supabase, " +
                            "выполните schema.sql, пропишите SUPABASE_URL и SUPABASE_ANON_KEY в local.properties, " +
                            "пересоберите APK. См. docs/health/ZAL_ANDROID_SUPABASE.md",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Миграция с VPS", style = MaterialTheme.typography.titleSmall)
                Text(
                    "Импортируйте JSON/ZIP бэкап health (логи, замеры, программы).\n" +
                        "История с веб-зала уже вшита в APK и подтягивается при первом запуске.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedButton(
                    enabled = !busy,
                    onClick = { pickBackup.launch("*/*") },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Импорт бэкапа") }
            }
        }
    }
}

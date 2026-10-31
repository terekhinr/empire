package ru.neverretire.zal.ui.diary

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import ru.neverretire.zal.data.GymRepository
import java.time.LocalDate

@Composable
fun DiaryScreen(repo: GymRepository, onMessage: (String) -> Unit) {
    val logs by repo.observeLogs(80).collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    var showAdd by remember { mutableStateOf(false) }
    var key by remember { mutableStateOf("") }
    var label by remember { mutableStateOf("") }
    var weight by remember { mutableStateOf("") }
    var reps by remember { mutableStateOf("8") }
    var sets by remember { mutableStateOf("1") }

    Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Дневник", style = MaterialTheme.typography.titleLarge)
            TextButton(onClick = { showAdd = !showAdd }) {
                Text(if (showAdd) "Скрыть" else "Добавить")
            }
        }
        if (showAdd) {
            OutlinedTextField(key, { key = it }, label = { Text("Ключ упражнения") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(label, { label = it }, label = { Text("Название") }, modifier = Modifier.fillMaxWidth())
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    weight,
                    { weight = it },
                    label = { Text("кг") },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                )
                OutlinedTextField(
                    reps,
                    { reps = it },
                    label = { Text("повт") },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                )
                OutlinedTextField(
                    sets,
                    { sets = it },
                    label = { Text("подх") },
                    modifier = Modifier.weight(1f),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                )
            }
            Button(
                onClick = {
                    scope.launch {
                        val k = key.trim().ifBlank { return@launch }
                        repo.addLog(
                            day = LocalDate.now().toString(),
                            exerciseKey = k,
                            label = label.ifBlank { k },
                            weight = weight.toDoubleOrNull() ?: 0.0,
                            reps = reps.toIntOrNull() ?: 0,
                            sets = sets.toIntOrNull() ?: 1,
                            note = null,
                        )
                        onMessage("Запись добавлена")
                        showAdd = false
                        key = ""
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Сохранить") }
        }
        if (logs.isEmpty()) {
            Text("Пока нет записей", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(logs, key = { it.id }) { row ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(row.exerciseLabel ?: row.exerciseKey, style = MaterialTheme.typography.titleSmall)
                            Text(
                                "${row.loggedOn} · ${row.sets}×${row.reps} · ${row.weightKg} кг" +
                                    (row.note?.let { " · $it" } ?: ""),
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            TextButton(onClick = {
                                scope.launch {
                                    repo.deleteLog(row.id)
                                    onMessage("Удалено")
                                }
                            }) { Text("Удалить") }
                        }
                    }
                }
            }
        }
    }
}

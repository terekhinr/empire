package ru.neverretire.zal.ui.meas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
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
import ru.neverretire.zal.data.db.MeasurementEntity
import ru.neverretire.zal.ui.components.SparklineCard
import java.time.LocalDate

@Composable
fun MeasScreen(repo: GymRepository, onMessage: (String) -> Unit) {
    val rows by repo.observeMeasurements(800).collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    var weight by remember { mutableStateOf("") }
    var waist by remember { mutableStateOf("") }
    var br by remember { mutableStateOf("") }
    var bl by remember { mutableStateOf("") }
    var legs by remember { mutableStateOf("") }

    val sorted = remember(rows) { rows.sortedBy { it.measuredOn } }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("Замеры", style = MaterialTheme.typography.titleLarge)
        Text(
            "Графики ниже · для линии нужно ≥2 замера. Статистика зала — вкладка «Статистика».",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Новый замер", style = MaterialTheme.typography.titleSmall)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    numField(weight, { weight = it }, "вес", Modifier.weight(1f))
                    numField(waist, { waist = it }, "талия", Modifier.weight(1f))
                }
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    numField(br, { br = it }, "биц пр", Modifier.weight(1f))
                    numField(bl, { bl = it }, "биц лев", Modifier.weight(1f))
                    numField(legs, { legs = it }, "ноги", Modifier.weight(1f))
                }
                Button(
                    onClick = {
                        scope.launch {
                            repo.addMeasurement(
                                day = LocalDate.now().toString(),
                                weightKg = weight.toDoubleOrNull(),
                                waistCm = waist.toDoubleOrNull(),
                                bicepsR = br.toDoubleOrNull(),
                                bicepsL = bl.toDoubleOrNull(),
                                legsCm = legs.toDoubleOrNull(),
                            )
                            onMessage("Замер сохранён")
                            weight = ""; waist = ""; br = ""; bl = ""; legs = ""
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Сохранить") }
            }
        }

        Text("Графики", style = MaterialTheme.typography.titleSmall)
        SparklineCard("Вес", sorted.mapNotNull { m -> m.weightKg?.let { m.measuredOn to it } }, " кг")
        SparklineCard("Талия", sorted.mapNotNull { m -> m.waistCm?.let { m.measuredOn to it } }, " см")
        SparklineCard(
            "Бицепс ср.",
            sorted.mapNotNull { m ->
                val vals = listOfNotNull(m.bicepsRCm, m.bicepsLCm)
                if (vals.isEmpty()) null else m.measuredOn to vals.average()
            },
            " см",
        )
        SparklineCard("Ноги", sorted.mapNotNull { m -> m.legsCm?.let { m.measuredOn to it } }, " см")

        Text("История", style = MaterialTheme.typography.titleSmall)
        sorted.asReversed().take(15).forEach { m ->
            MeasurementRow(m)
        }
    }
}

@Composable
private fun numField(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        modifier = modifier,
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
    )
}

@Composable
private fun MeasurementRow(m: MeasurementEntity) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(m.measuredOn, style = MaterialTheme.typography.titleSmall)
            Text(
                "вес ${m.weightKg ?: "—"} · талия ${m.waistCm ?: "—"} · биц ${m.bicepsRCm ?: "—"}/${m.bicepsLCm ?: "—"} · ноги ${m.legsCm ?: "—"}",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

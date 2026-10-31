package ru.neverretire.zal.ui.stats

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ru.neverretire.zal.data.DeltaStat
import ru.neverretire.zal.data.GymRepository
import ru.neverretire.zal.data.HealthStats
import ru.neverretire.zal.ui.components.SparklineCard

@Composable
fun StatsScreen(repo: GymRepository) {
    val logs by repo.observeLogs(500).collectAsState(initial = emptyList())
    val measurements by repo.observeMeasurements(800).collectAsState(initial = emptyList())
    var period by remember { mutableStateOf("month") }
    val days = when (period) {
        "week" -> 7
        "quarter" -> 90
        else -> 30
    }
    val stats = remember(logs, measurements, period) {
        HealthStats.compute(logs, measurements, days)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("Статистика", style = MaterialTheme.typography.titleLarge)
        Text(
            "Походы в зал, тоннаж и прогресс в весах",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            listOf("week" to "7 дней", "month" to "30 дней", "quarter" to "90 дней").forEach { (id, label) ->
                FilterChip(
                    selected = period == id,
                    onClick = { period = id },
                    label = { Text(label) },
                )
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Силовые за период", style = MaterialTheme.typography.titleSmall)
                Metric("Дней в зале", "${stats.workoutDays}")
                Metric("Подходов", "${stats.setCount}")
                Metric("В неделю (дни)", "${stats.workoutsPerWeek}")
                Metric("Тоннаж / нед", "${stats.volumePerWeekKg} кг")
                Metric("Тоннаж всего", "${stats.totalVolumeKg} кг")
                Metric("Замеров", "${stats.measurementsCount}")
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Замеры · динамика", style = MaterialTheme.typography.titleSmall)
                DeltaRow("Вес", stats.weight, " кг")
                DeltaRow("Талия", stats.waist, " см")
                DeltaRow("Бицепс", stats.biceps, " см")
                DeltaRow("Ноги", stats.legs, " см")
                Metric("ИМТ", stats.bmi?.toString() ?: "—")
                Metric("Талия/рост", stats.whtr?.toString() ?: "—")
            }
        }

        Text("Графики замеров", style = MaterialTheme.typography.titleSmall)
        val sorted = remember(measurements) { measurements.sortedBy { it.measuredOn } }
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

        Text("Прогресс в весах", style = MaterialTheme.typography.titleSmall)
        if (stats.exerciseProgress.isEmpty()) {
            Text(
                "Пока мало данных: отметьте подходы в программе или дневнике (нужно ≥2 тренировки по упражнению).",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            stats.exerciseProgress.forEach { ex ->
                SparklineCard(ex.exerciseLabel, ex.points, " кг")
            }
        }

        Text("Рекорды за период", style = MaterialTheme.typography.titleSmall)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (stats.personalRecords.isEmpty()) {
                    Text("—", color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else {
                    stats.personalRecords.forEach { pr ->
                        Text(
                            "${pr.exerciseLabel}: ${fmt(pr.maxKg)} кг · ${pr.on}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.titleSmall)
    }
}

@Composable
private fun DeltaRow(label: String, d: DeltaStat?, unit: String) {
    if (d == null) {
        Metric(label, "—")
        return
    }
    val sign = when {
        d.delta > 0 -> "+"
        else -> ""
    }
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("${fmt(d.end)}$unit  ($sign${fmt(d.delta)}$unit)")
    }
}

private fun fmt(v: Double): String =
    if (v == v.toLong().toDouble()) v.toLong().toString() else "%.1f".format(v)

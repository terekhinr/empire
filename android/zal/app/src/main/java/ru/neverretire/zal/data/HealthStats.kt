package ru.neverretire.zal.data

import ru.neverretire.zal.data.db.MeasurementEntity
import ru.neverretire.zal.data.db.StrengthLogEntity
import java.time.LocalDate
import kotlin.math.roundToInt

data class DeltaStat(val start: Double, val end: Double) {
    val delta: Double get() = end - start
}

data class PersonalRecord(
    val exerciseKey: String,
    val exerciseLabel: String,
    val maxKg: Double,
    val on: String,
)

data class ExerciseProgress(
    val exerciseKey: String,
    val exerciseLabel: String,
    /** date → max weight that day */
    val points: List<Pair<String, Double>>,
)

data class HealthStatsSnapshot(
    val periodDays: Int,
    val since: String,
    val workoutDays: Int,
    val setCount: Int,
    val workoutsPerWeek: Double,
    val volumePerWeekKg: Double,
    val totalVolumeKg: Double,
    val measurementsCount: Int,
    val weight: DeltaStat?,
    val waist: DeltaStat?,
    val biceps: DeltaStat?,
    val legs: DeltaStat?,
    val bmi: Double?,
    val whtr: Double?,
    val personalRecords: List<PersonalRecord>,
    val exerciseProgress: List<ExerciseProgress>,
)

object HealthStats {
    private const val HEIGHT_CM = 186.0

    fun compute(
        logs: List<StrengthLogEntity>,
        measurements: List<MeasurementEntity>,
        periodDays: Int,
        today: LocalDate = LocalDate.now(),
    ): HealthStatsSnapshot {
        val since = today.minusDays(periodDays.toLong() - 1)
        val sinceStr = since.toString()
        val periodLogs = logs.filter { it.loggedOn >= sinceStr && !it.deleted }
        val periodMeas = measurements
            .filter { it.measuredOn >= sinceStr && !it.deleted }
            .sortedBy { it.measuredOn }

        val days = periodLogs.map { it.loggedOn }.toSet()
        val setCount = periodLogs.size
        val totalVolume = periodLogs.sumOf { it.weightKg * it.reps * it.sets.coerceAtLeast(1) }
        val weeks = (periodDays / 7.0).coerceAtLeast(1.0)

        fun delta(selector: (MeasurementEntity) -> Double?): DeltaStat? {
            val pts = periodMeas.mapNotNull { m -> selector(m)?.let { m.measuredOn to it } }
            if (pts.size < 2) {
                val one = pts.singleOrNull() ?: return null
                return DeltaStat(one.second, one.second)
            }
            return DeltaStat(pts.first().second, pts.last().second)
        }

        val bicepsDelta = delta { m ->
            val vals = listOfNotNull(m.bicepsRCm, m.bicepsLCm)
            if (vals.isEmpty()) null else vals.average()
        }
        val weightDelta = delta { it.weightKg }
        val lastWeight = weightDelta?.end
        val lastWaist = delta { it.waistCm }?.end

        val prs = periodLogs
            .groupBy { it.exerciseKey }
            .mapNotNull { (key, rows) ->
                val best = rows.maxByOrNull { it.weightKg } ?: return@mapNotNull null
                if (best.weightKg <= 0) return@mapNotNull null
                PersonalRecord(
                    exerciseKey = key,
                    exerciseLabel = best.exerciseLabel ?: key,
                    maxKg = best.weightKg,
                    on = best.loggedOn,
                )
            }
            .sortedByDescending { it.maxKg }
            .take(12)

        val progress = periodLogs
            .groupBy { it.exerciseKey }
            .map { (key, rows) ->
                val label = rows.first().exerciseLabel ?: key
                val byDay = rows
                    .groupBy { it.loggedOn }
                    .map { (day, dayRows) -> day to dayRows.maxOf { it.weightKg } }
                    .sortedBy { it.first }
                ExerciseProgress(key, label, byDay)
            }
            .filter { it.points.size >= 2 && it.points.any { p -> p.second > 0 } }
            .sortedByDescending { it.points.last().second }
            .take(8)

        return HealthStatsSnapshot(
            periodDays = periodDays,
            since = sinceStr,
            workoutDays = days.size,
            setCount = setCount,
            workoutsPerWeek = ((days.size / weeks) * 10).roundToInt() / 10.0,
            volumePerWeekKg = ((totalVolume / weeks) * 10).roundToInt() / 10.0,
            totalVolumeKg = (totalVolume * 10).roundToInt() / 10.0,
            measurementsCount = periodMeas.size,
            weight = weightDelta,
            waist = delta { it.waistCm },
            biceps = bicepsDelta,
            legs = delta { it.legsCm },
            bmi = lastWeight?.let { w ->
                val h = HEIGHT_CM / 100.0
                ((w / (h * h)) * 10).roundToInt() / 10.0
            },
            whtr = lastWaist?.let { ((it / HEIGHT_CM) * 100).roundToInt() / 100.0 },
            personalRecords = prs,
            exerciseProgress = progress,
        )
    }
}

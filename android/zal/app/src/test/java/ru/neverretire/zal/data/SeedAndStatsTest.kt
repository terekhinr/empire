package ru.neverretire.zal.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import ru.neverretire.zal.data.db.StrengthLogEntity
import ru.neverretire.zal.ui.components.downsample
import java.io.File
import java.time.LocalDate
import org.json.JSONObject

class SeedAndStatsTest {
    @Test
    fun healthExport_hasWorkoutsAndMeasurements() {
        val roots = listOf(
            File("src/main/assets/seed/health_export.json"),
            File("app/src/main/assets/seed/health_export.json"),
        )
        val f = roots.firstOrNull { it.isFile } ?: error("seed missing")
        val root = JSONObject(f.readText())
        assertEquals("empire-health-export/v1", root.getString("schema"))
        val workouts = root.getJSONArray("workouts")
        val measurements = root.getJSONArray("measurements")
        assertTrue(workouts.length() >= 200)
        assertTrue(measurements.length() >= 60)
        val first = workouts.getJSONObject(0)
        assertTrue(first.getString("uuid").startsWith("web-log-"))
        assertTrue(first.getString("exercise_key").isNotBlank())
        assertTrue(first.has("exercise_label"))
    }

    @Test
    fun healthStats_countsDistinctGymDays() {
        val logs = listOf(
            fakeLog("2026-09-01", "жим", 100.0),
            fakeLog("2026-09-01", "тяга", 40.0),
            fakeLog("2026-09-03", "жим", 105.0),
        )
        val stats = HealthStats.compute(
            logs = logs,
            measurements = emptyList(),
            periodDays = 30,
            today = LocalDate.of(2026, 9, 11),
        )
        assertEquals(2, stats.workoutDays)
        assertEquals(3, stats.setCount)
        assertTrue(stats.personalRecords.size >= 2)
        assertEquals(105.0, stats.personalRecords.first().maxKg, 0.01)
    }

    @Test
    fun downsample_capsPoints() {
        val pts = (1..500).map { "2026-01-%02d".format((it % 28) + 1) to it.toDouble() }
        val out = downsample(pts, 80)
        assertEquals(80, out.size)
        assertEquals(pts.first(), out.first())
        assertEquals(pts.last(), out.last())
    }

    private fun fakeLog(day: String, key: String, kg: Double) = StrengthLogEntity(
        uuid = "$day-$key-$kg",
        loggedOn = day,
        exerciseKey = key,
        exerciseLabel = key,
        weightKg = kg,
        reps = 5,
        sets = 1,
        createdAt = day,
        updatedAt = day,
        dirty = false,
    )
}

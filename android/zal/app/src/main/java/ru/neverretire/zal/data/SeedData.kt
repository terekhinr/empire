package ru.neverretire.zal.data

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import ru.neverretire.zal.data.db.MeasurementEntity
import ru.neverretire.zal.data.db.SettingEntity
import ru.neverretire.zal.data.db.StrengthLogEntity
import ru.neverretire.zal.data.db.ZalDatabase
import java.time.Instant

/**
 * One-shot import of VPS web health history bundled in assets.
 */
object SeedData {
    private const val TAG = "ZalSeed"
    private const val KEY = "seed_web_health_v1"
    private const val ASSET = "seed/health_export.json"

    suspend fun ensureImported(context: Context): BackupImporter.Result? = withContext(Dispatchers.IO) {
        val dao = ZalDatabase.get(context).gymDao()
        if (dao.getSetting(KEY) == "1") return@withContext null

        runCatching {
            val text = context.assets.open(ASSET).bufferedReader().use { it.readText() }
            val root = JSONObject(text)
            val now = Instant.now().toString()
            val logs = importLogsFast(dao, root.optJSONArray("workouts") ?: JSONArray(), now)
            val meas = importMeasFast(dao, root.optJSONArray("measurements") ?: JSONArray(), now)
            dao.putSetting(SettingEntity(KEY, "1"))
            Log.i(TAG, "seed ok logs=$logs meas=$meas")
            BackupImporter.Result(logs, meas, 0)
        }.getOrElse { e ->
            Log.e(TAG, "seed failed", e)
            null
        }
    }

    private suspend fun importLogsFast(
        dao: ru.neverretire.zal.data.db.GymDao,
        arr: JSONArray,
        now: String,
    ): Int {
        if (arr.length() == 0) return 0
        val existing = dao.allLogUuids().toHashSet()
        val rows = ArrayList<StrengthLogEntity>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val uuid = o.optString("uuid")
            if (uuid.isBlank() || uuid in existing) continue
            val key = o.optString("exercise_key").ifBlank { o.optString("exerciseKey") }
            if (key.isBlank()) continue
            val day = o.optString("logged_on").ifBlank { o.optString("loggedOn") }
            if (day.isBlank()) continue
            val label = o.optString("exercise_label").ifBlank { o.optString("exerciseLabel") }
            rows += StrengthLogEntity(
                uuid = uuid,
                loggedOn = day,
                exerciseKey = key,
                exerciseLabel = label.takeIf { it.isNotBlank() },
                weightKg = o.optDouble("weight_kg", o.optDouble("weightKg", 0.0)),
                reps = o.optInt("reps", 0),
                sets = o.optInt("sets", 1).coerceAtLeast(1),
                note = o.optString("note").takeIf { it.isNotBlank() },
                createdAt = o.optString("created_at").ifBlank { now },
                updatedAt = now,
                dirty = false,
            )
        }
        rows.chunked(100).forEach { dao.upsertLogs(it) }
        return rows.size
    }

    private suspend fun importMeasFast(
        dao: ru.neverretire.zal.data.db.GymDao,
        arr: JSONArray,
        now: String,
    ): Int {
        if (arr.length() == 0) return 0
        val existing = dao.allMeasurementUuids().toHashSet()
        val rows = ArrayList<MeasurementEntity>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val uuid = o.optString("uuid")
            if (uuid.isBlank() || uuid in existing) continue
            val day = o.optString("measured_on").ifBlank { o.optString("measuredOn") }
            if (day.isBlank()) continue
            fun dbl(vararg keys: String): Double? {
                for (k in keys) {
                    if (o.has(k) && !o.isNull(k)) return o.getDouble(k)
                }
                return null
            }
            rows += MeasurementEntity(
                uuid = uuid,
                measuredOn = day,
                weightKg = dbl("weight_kg", "weightKg"),
                waistCm = dbl("waist_cm", "waistCm"),
                bicepsRCm = dbl("biceps_r_cm", "bicepsRCm"),
                bicepsLCm = dbl("biceps_l_cm", "bicepsLCm"),
                legsCm = dbl("legs_cm", "legsCm"),
                note = o.optString("note").takeIf { it.isNotBlank() },
                source = o.optString("source", "import"),
                createdAt = o.optString("created_at").ifBlank { now },
                updatedAt = now,
                dirty = false,
            )
        }
        rows.chunked(100).forEach { dao.upsertMeasurements(it) }
        return rows.size
    }
}

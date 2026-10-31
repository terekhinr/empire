package ru.neverretire.zal.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import ru.neverretire.zal.data.db.MeasurementEntity
import ru.neverretire.zal.data.db.StrengthLogEntity
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.time.Instant
import java.util.UUID
import java.util.zip.ZipInputStream

object BackupImporter {
    data class Result(val logs: Int, val measurements: Int, val programs: Int)

    suspend fun import(
        context: Context,
        input: InputStream,
        fileName: String,
        markDirty: Boolean = true,
    ): Result =
        withContext(Dispatchers.IO) {
            val repo = GymRepository(context)
            val dao = repo.dao()
            val now = Instant.now().toString()
            var logs = 0
            var meas = 0
            var programs = 0

            val bytes = input.readBytes()
            val lower = fileName.lowercase()
            if (lower.endsWith(".zip")) {
                ZipInputStream(BufferedInputStream(bytes.inputStream())).use { zip ->
                    var entry = zip.nextEntry
                    while (entry != null) {
                        if (!entry.isDirectory) {
                            val name = entry.name.substringAfterLast('/')
                            val data = zip.readBytes()
                            when {
                                name.endsWith(".json") && name.contains("strength") -> {
                                    logs += importLogs(dao, JSONArray(String(data)), now, markDirty)
                                }
                                name.endsWith(".json") && name.contains("measure") -> {
                                    meas += importMeasurements(dao, JSONArray(String(data)), now, markDirty)
                                }
                                name.endsWith(".json") && (name.contains("program") || dataLooksLikeProgram(data)) -> {
                                    runCatching {
                                        repo.importUserProgramJson(String(data))
                                        programs++
                                    }
                                }
                                name == "export.json" || name == "health.json" || name == "health_export.json" -> {
                                    val root = JSONObject(String(data))
                                    logs += importWorkoutsRoot(dao, root, now, markDirty)
                                    meas += importMeasurementsRoot(dao, root, now, markDirty)
                                }
                            }
                        }
                        zip.closeEntry()
                        entry = zip.nextEntry
                    }
                }
            } else {
                val text = String(bytes)
                val trimmed = text.trim()
                when {
                    trimmed.startsWith("[") -> {
                        val arr = JSONArray(trimmed)
                        if (arr.length() > 0 && arr.getJSONObject(0).has("measured_on")) {
                            meas += importMeasurements(dao, arr, now, markDirty)
                        } else {
                            logs += importLogs(dao, arr, now, markDirty)
                        }
                    }
                    trimmed.startsWith("{") -> {
                        val root = JSONObject(trimmed)
                        if (root.optString("schema") == "empire-workout-program/v1") {
                            repo.importUserProgramJson(trimmed)
                            programs++
                        } else {
                            logs += importWorkoutsRoot(dao, root, now, markDirty)
                            meas += importMeasurementsRoot(dao, root, now, markDirty)
                        }
                    }
                }
            }
            Result(logs, meas, programs)
        }

    private suspend fun importWorkoutsRoot(
        dao: ru.neverretire.zal.data.db.GymDao,
        root: JSONObject,
        now: String,
        markDirty: Boolean,
    ): Int {
        if (!root.has("workouts") && !root.has("strength_logs")) return 0
        val arr = root.optJSONArray("workouts") ?: root.optJSONArray("strength_logs") ?: return 0
        return importLogs(dao, arr, now, markDirty)
    }

    private suspend fun importMeasurementsRoot(
        dao: ru.neverretire.zal.data.db.GymDao,
        root: JSONObject,
        now: String,
        markDirty: Boolean,
    ): Int {
        if (!root.has("measurements")) return 0
        return importMeasurements(dao, root.getJSONArray("measurements"), now, markDirty)
    }

    private fun dataLooksLikeProgram(data: ByteArray): Boolean =
        String(data).contains("empire-workout-program/v1")

    private suspend fun importLogs(
        dao: ru.neverretire.zal.data.db.GymDao,
        arr: JSONArray,
        now: String,
        markDirty: Boolean,
    ): Int {
        val rows = mutableListOf<StrengthLogEntity>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val uuid = o.optString("uuid").ifBlank { UUID.randomUUID().toString() }
            if (dao.logByUuid(uuid) != null) continue
            val key = o.optString("exercise_key", o.optString("exerciseKey"))
            if (key.isBlank()) continue
            val label = o.optString("exercise_label", o.optString("exerciseLabel")).ifBlank { null }
            rows += StrengthLogEntity(
                uuid = uuid,
                loggedOn = o.optString("logged_on", o.optString("loggedOn")),
                exerciseKey = key,
                exerciseLabel = label,
                weightKg = o.optDouble("weight_kg", o.optDouble("weightKg", 0.0)),
                reps = o.optInt("reps", 0),
                sets = o.optInt("sets", 1),
                note = o.optString("note").ifBlank { null },
                createdAt = o.optString("created_at", now),
                updatedAt = now,
                dirty = markDirty,
            )
        }
        if (rows.isNotEmpty()) dao.upsertLogs(rows)
        return rows.size
    }

    private suspend fun importMeasurements(
        dao: ru.neverretire.zal.data.db.GymDao,
        arr: JSONArray,
        now: String,
        markDirty: Boolean,
    ): Int {
        val rows = mutableListOf<MeasurementEntity>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val uuid = o.optString("uuid").ifBlank { UUID.randomUUID().toString() }
            if (dao.measurementByUuid(uuid) != null) continue
            fun dbl(vararg keys: String): Double? {
                for (k in keys) {
                    if (o.has(k) && !o.isNull(k)) return o.getDouble(k)
                }
                return null
            }
            val day = o.optString("measured_on", o.optString("measuredOn"))
            if (day.isBlank()) continue
            rows += MeasurementEntity(
                uuid = uuid,
                measuredOn = day,
                weightKg = dbl("weight_kg", "weightKg"),
                waistCm = dbl("waist_cm", "waistCm"),
                bicepsRCm = dbl("biceps_r_cm", "bicepsRCm"),
                bicepsLCm = dbl("biceps_l_cm", "bicepsLCm"),
                legsCm = dbl("legs_cm", "legsCm"),
                note = o.optString("note").ifBlank { null },
                source = o.optString("source", "import"),
                createdAt = o.optString("created_at", now),
                updatedAt = now,
                dirty = markDirty,
            )
        }
        if (rows.isNotEmpty()) dao.upsertMeasurements(rows)
        return rows.size
    }

    private fun InputStream.readBytes(): ByteArray {
        val buf = ByteArrayOutputStream()
        copyTo(buf)
        return buf.toByteArray()
    }
}

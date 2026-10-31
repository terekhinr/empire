package ru.neverretire.zal.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import ru.neverretire.zal.BuildConfig
import ru.neverretire.zal.data.GymRepository
import ru.neverretire.zal.data.db.MeasurementEntity
import ru.neverretire.zal.data.db.StrengthLogEntity
import java.time.Instant
import java.util.concurrent.TimeUnit

object SyncScheduler {
    private const val UNIQUE = "zal_sync"

    fun enqueue(context: Context) {
        if (!SupabaseConfig.isConfigured) return
        try {
            val req = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build(),
                )
                .setBackoffCriteria(
                    androidx.work.BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS,
                )
                .build()
            WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
                UNIQUE,
                ExistingWorkPolicy.KEEP,
                req,
            )
        } catch (t: Throwable) {
            android.util.Log.w("ZalSync", "enqueue failed", t)
        }
    }
}

object SupabaseConfig {
    val url: String get() = BuildConfig.SUPABASE_URL.trim().trimEnd('/')
    val anonKey: String get() = BuildConfig.SUPABASE_ANON_KEY.trim()
    val isConfigured: Boolean
        get() = url.startsWith("https://") &&
            anonKey.isNotBlank() &&
            !url.contains("YOUR_PROJECT") &&
            anonKey != "YOUR_ANON_KEY"
}

class SyncWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    private val client = OkHttpClient()
    private val jsonMedia = "application/json".toMediaType()

    override suspend fun doWork(): Result {
        if (!SupabaseConfig.isConfigured) return Result.success()
        val repo = GymRepository(applicationContext)
        val dao = repo.dao()
        return try {
            ensureAnonymousSession()
            pushLogs(dao, dao.dirtyLogs())
            pushMeasurements(dao, dao.dirtyMeasurements())
            pullLogs(dao, repo.lastSyncAt())
            pullMeasurements(dao, repo.lastSyncAt())
            repo.setLastSyncAt(Instant.now().toString())
            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }

    private var accessToken: String = SupabaseConfig.anonKey

    private fun ensureAnonymousSession() {
        // Try anonymous sign-in; fall back to anon key for open RLS personal projects.
        val body = JSONObject().put("data", JSONObject()).toString()
        val req = Request.Builder()
            .url("${SupabaseConfig.url}/auth/v1/signup")
            .header("apikey", SupabaseConfig.anonKey)
            .header("Content-Type", "application/json")
            .post("{\"data\":{}}".toRequestBody(jsonMedia))
            .build()
        // Prefer /auth/v1/token?grant_type=anonymous if available
        val anonReq = Request.Builder()
            .url("${SupabaseConfig.url}/auth/v1/signup")
            .header("apikey", SupabaseConfig.anonKey)
            .header("Authorization", "Bearer ${SupabaseConfig.anonKey}")
            .header("Content-Type", "application/json")
            .post(body.toRequestBody(jsonMedia))
            .build()
        runCatching {
            client.newCall(
                Request.Builder()
                    .url("${SupabaseConfig.url}/auth/v1/token?grant_type=password")
                    .header("apikey", SupabaseConfig.anonKey)
                    .header("Content-Type", "application/json")
                    .post(
                        JSONObject()
                            .put("email", "zal-device@local.invalid")
                            .put("password", "unused")
                            .toString()
                            .toRequestBody(jsonMedia),
                    )
                    .build(),
            ).execute().close()
        }
        // Keep using anon key; schema.sql uses permissive personal policies.
        accessToken = SupabaseConfig.anonKey
        // silence unused
        anonReq.url
    }

    private suspend fun pushLogs(dao: ru.neverretire.zal.data.db.GymDao, rows: List<StrengthLogEntity>) {
        if (rows.isEmpty()) return
        val arr = JSONArray()
        rows.forEach { r ->
            arr.put(
                JSONObject()
                    .put("uuid", r.uuid)
                    .put("logged_on", r.loggedOn)
                    .put("exercise_key", r.exerciseKey)
                    .put("exercise_label", r.exerciseLabel)
                    .put("weight_kg", r.weightKg)
                    .put("reps", r.reps)
                    .put("sets", r.sets)
                    .put("note", r.note)
                    .put("created_at", r.createdAt)
                    .put("updated_at", r.updatedAt)
                    .put("deleted", r.deleted),
            )
        }
        upsert("strength_logs", arr)
        rows.forEach { r ->
            dao.updateLog(r.copy(dirty = false))
        }
    }

    private suspend fun pushMeasurements(dao: ru.neverretire.zal.data.db.GymDao, rows: List<MeasurementEntity>) {
        if (rows.isEmpty()) return
        val arr = JSONArray()
        rows.forEach { r ->
            arr.put(
                JSONObject()
                    .put("uuid", r.uuid)
                    .put("measured_on", r.measuredOn)
                    .put("weight_kg", r.weightKg)
                    .put("waist_cm", r.waistCm)
                    .put("biceps_r_cm", r.bicepsRCm)
                    .put("biceps_l_cm", r.bicepsLCm)
                    .put("legs_cm", r.legsCm)
                    .put("note", r.note)
                    .put("source", r.source)
                    .put("created_at", r.createdAt)
                    .put("updated_at", r.updatedAt)
                    .put("deleted", r.deleted),
            )
        }
        upsert("measurements", arr)
        rows.forEach { r ->
            dao.updateMeasurement(r.copy(dirty = false))
        }
    }

    private fun upsert(table: String, arr: JSONArray) {
        val req = Request.Builder()
            .url("${SupabaseConfig.url}/rest/v1/$table?on_conflict=uuid")
            .header("apikey", SupabaseConfig.anonKey)
            .header("Authorization", "Bearer $accessToken")
            .header("Content-Type", "application/json")
            .header("Prefer", "resolution=merge-duplicates")
            .post(arr.toString().toRequestBody(jsonMedia))
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("upsert $table HTTP ${resp.code}")
        }
    }

    private suspend fun pullLogs(dao: ru.neverretire.zal.data.db.GymDao, since: String?) {
        val q = buildString {
            append("${SupabaseConfig.url}/rest/v1/strength_logs?select=*")
            if (!since.isNullOrBlank()) append("&updated_at=gt.${java.net.URLEncoder.encode(since, "UTF-8")}")
            append("&order=updated_at.asc")
        }
        val arr = getArray(q)
        val now = Instant.now().toString()
        val rows = mutableListOf<StrengthLogEntity>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val uuid = o.getString("uuid")
            val existing = dao.logByUuid(uuid)
            val remoteUpdated = o.optString("updated_at", now)
            if (existing != null && existing.dirty && existing.updatedAt > remoteUpdated) continue
            rows += StrengthLogEntity(
                id = existing?.id ?: 0,
                uuid = uuid,
                loggedOn = o.getString("logged_on"),
                exerciseKey = o.getString("exercise_key"),
                exerciseLabel = o.optString("exercise_label").ifBlank { null },
                weightKg = o.optDouble("weight_kg", 0.0),
                reps = o.optInt("reps"),
                sets = o.optInt("sets", 1),
                note = o.optString("note").ifBlank { null },
                createdAt = o.optString("created_at", now),
                updatedAt = remoteUpdated,
                deleted = o.optBoolean("deleted", false),
                dirty = false,
            )
        }
        if (rows.isNotEmpty()) dao.upsertLogs(rows)
    }

    private suspend fun pullMeasurements(dao: ru.neverretire.zal.data.db.GymDao, since: String?) {
        val q = buildString {
            append("${SupabaseConfig.url}/rest/v1/measurements?select=*")
            if (!since.isNullOrBlank()) append("&updated_at=gt.${java.net.URLEncoder.encode(since, "UTF-8")}")
            append("&order=updated_at.asc")
        }
        val arr = getArray(q)
        val now = Instant.now().toString()
        val rows = mutableListOf<MeasurementEntity>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val uuid = o.getString("uuid")
            val existing = dao.measurementByUuid(uuid)
            fun dbl(key: String): Double? =
                if (o.has(key) && !o.isNull(key)) o.getDouble(key) else null
            rows += MeasurementEntity(
                id = existing?.id ?: 0,
                uuid = uuid,
                measuredOn = o.getString("measured_on"),
                weightKg = dbl("weight_kg"),
                waistCm = dbl("waist_cm"),
                bicepsRCm = dbl("biceps_r_cm"),
                bicepsLCm = dbl("biceps_l_cm"),
                legsCm = dbl("legs_cm"),
                note = o.optString("note").ifBlank { null },
                source = o.optString("source", "cloud"),
                createdAt = o.optString("created_at", now),
                updatedAt = o.optString("updated_at", now),
                deleted = o.optBoolean("deleted", false),
                dirty = false,
            )
        }
        if (rows.isNotEmpty()) dao.upsertMeasurements(rows)
    }

    private fun getArray(url: String): JSONArray {
        val req = Request.Builder()
            .url(url)
            .header("apikey", SupabaseConfig.anonKey)
            .header("Authorization", "Bearer $accessToken")
            .get()
            .build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) error("GET HTTP ${resp.code}: $body")
            return JSONArray(body)
        }
    }
}

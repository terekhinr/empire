package ru.neverretire.zal.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import ru.neverretire.zal.data.db.CustomExerciseEntity
import ru.neverretire.zal.data.db.GymDao
import ru.neverretire.zal.data.db.MeasurementEntity
import ru.neverretire.zal.data.db.SettingEntity
import ru.neverretire.zal.data.db.StrengthLogEntity
import ru.neverretire.zal.data.db.ZalDatabase
import ru.neverretire.zal.sync.SyncScheduler
import java.io.File
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

class GymRepository(private val context: Context) {
    private val dao: GymDao = ZalDatabase.get(context).gymDao()
    private val programsDir: File = File(context.filesDir, "programs").also { it.mkdirs() }

    fun observeLogs(limit: Int = 80): Flow<List<StrengthLogEntity>> = dao.observeLogs(limit)
    fun observeMeasurements(limit: Int = 80): Flow<List<MeasurementEntity>> = dao.observeMeasurements(limit)

    suspend fun getProgramId(): String {
        val id = dao.getSetting(KEY_PROGRAM) ?: "gym_2026"
        // Migrate away from demo program if it was selected earlier.
        if (id.contains("full_body") || id.contains("example")) {
            dao.putSetting(SettingEntity(KEY_PROGRAM, "gym_2026"))
            return "gym_2026"
        }
        return id
    }

    suspend fun setProgramId(id: String) {
        dao.putSetting(SettingEntity(KEY_PROGRAM, id))
    }

    suspend fun listPrograms(): List<ProgramMeta> = withContext(Dispatchers.IO) {
        loadAllPrograms().map { it.meta }
    }

    suspend fun loadProgram(id: String? = null): LoadedProgram = withContext(Dispatchers.IO) {
        val pid = id ?: getProgramId()
        loadAllPrograms().find { it.meta.id == pid }
            ?: loadAllPrograms().first()
    }

    suspend fun sessionFor(date: LocalDate, programId: String? = null): WorkoutSession? {
        val program = loadProgram(programId)
        return ProgramParser.sessionForDate(program, date)
            ?: ProgramParser.nextSession(program, date)
    }

    suspend fun logsForDay(day: String): List<StrengthLogEntity> = dao.logsForDay(day)

    suspend fun saveProgramSets(
        day: String,
        programId: String,
        notePrefix: String,
        entries: List<SetEntry>,
    ) = withContext(Dispatchers.IO) {
        dao.deleteProgramLogsForDay(day, "${notePrefix.trim()} %")
        val now = Instant.now().toString()
        val rows = entries.map { e ->
            dao.upsertExercise(
                CustomExerciseEntity(e.exerciseKey, e.exerciseLabel, now),
            )
            StrengthLogEntity(
                uuid = UUID.randomUUID().toString(),
                loggedOn = day,
                exerciseKey = e.exerciseKey,
                exerciseLabel = e.exerciseLabel,
                weightKg = e.weightKg,
                reps = e.reps,
                sets = 1,
                note = "${notePrefix.trim()} ${e.setIndex}/${e.setTotal}",
                createdAt = now,
                updatedAt = now,
                dirty = true,
            )
        }
        dao.upsertLogs(rows)
        SyncScheduler.enqueue(context)
    }

    suspend fun addLog(
        day: String,
        exerciseKey: String,
        label: String,
        weight: Double,
        reps: Int,
        sets: Int,
        note: String?,
    ) = withContext(Dispatchers.IO) {
        val now = Instant.now().toString()
        dao.upsertExercise(CustomExerciseEntity(exerciseKey, label, now))
        dao.upsertLog(
            StrengthLogEntity(
                uuid = UUID.randomUUID().toString(),
                loggedOn = day,
                exerciseKey = exerciseKey,
                exerciseLabel = label,
                weightKg = weight,
                reps = reps,
                sets = sets,
                note = note,
                createdAt = now,
                updatedAt = now,
                dirty = true,
            ),
        )
        SyncScheduler.enqueue(context)
    }

    suspend fun deleteLog(id: Long) = withContext(Dispatchers.IO) {
        dao.softDeleteLog(id, Instant.now().toString())
        SyncScheduler.enqueue(context)
    }

    suspend fun addMeasurement(
        day: String,
        weightKg: Double?,
        waistCm: Double?,
        bicepsR: Double?,
        bicepsL: Double?,
        legsCm: Double?,
        note: String? = null,
    ) = withContext(Dispatchers.IO) {
        val now = Instant.now().toString()
        dao.upsertMeasurement(
            MeasurementEntity(
                uuid = UUID.randomUUID().toString(),
                measuredOn = day,
                weightKg = weightKg,
                waistCm = waistCm,
                bicepsRCm = bicepsR,
                bicepsLCm = bicepsL,
                legsCm = legsCm,
                note = note,
                createdAt = now,
                updatedAt = now,
                dirty = true,
            ),
        )
        SyncScheduler.enqueue(context)
    }

    suspend fun importUserProgramJson(json: String): ProgramMeta = withContext(Dispatchers.IO) {
        val program = ProgramParser.parse(json)
        File(programsDir, "${program.meta.id}.json").writeText(json)
        program.meta
    }

    suspend fun getRestSec(): Int = dao.getSetting(KEY_REST)?.toIntOrNull() ?: 120
    suspend fun setRestSec(sec: Int) = dao.putSetting(SettingEntity(KEY_REST, sec.toString()))
    suspend fun restAutostart(): Boolean = dao.getSetting(KEY_REST_AUTO) != "0"
    suspend fun setRestAutostart(on: Boolean) =
        dao.putSetting(SettingEntity(KEY_REST_AUTO, if (on) "1" else "0"))

    suspend fun lastSyncAt(): String? = dao.getSetting(KEY_LAST_SYNC)
    suspend fun setLastSyncAt(iso: String) = dao.putSetting(SettingEntity(KEY_LAST_SYNC, iso))

    fun dao(): GymDao = dao

    private fun loadAllPrograms(): List<LoadedProgram> {
        val out = linkedMapOf<String, LoadedProgram>()
        // Built-ins first, same order as web: Зал → Вне зала
        val preferred = listOf("gym_2026.json", "outside_hall.json")
        preferred.forEach { name ->
            runCatching {
                val text = context.assets.open("programs/$name").bufferedReader().use { it.readText() }
                val p = ProgramParser.parse(text)
                out[p.meta.id] = p
            }
        }
        context.assets.list("programs")?.forEach { name ->
            if (!name.endsWith(".json") || name in preferred) return@forEach
            // Skip demo templates — they confuse the switcher (e.g. 3-exercise example).
            if (name.contains("full_body") || name.contains("example") || name.contains("пример")) return@forEach
            runCatching {
                val text = context.assets.open("programs/$name").bufferedReader().use { it.readText() }
                val p = ProgramParser.parse(text)
                out[p.meta.id] = p
            }
        }
        programsDir.listFiles()?.filter { it.extension == "json" }?.forEach { f ->
            runCatching {
                val p = ProgramParser.parse(f.readText())
                out[p.meta.id] = p
            }
        }
        return out.values.toList()
    }

    data class SetEntry(
        val exerciseKey: String,
        val exerciseLabel: String,
        val setIndex: Int,
        val setTotal: Int,
        val weightKg: Double,
        val reps: Int,
    )

    companion object {
        const val KEY_PROGRAM = "program_id"
        const val KEY_REST = "rest_sec"
        const val KEY_REST_AUTO = "rest_autostart"
        const val KEY_LAST_SYNC = "last_sync_at"
    }
}

/** Minimal JSON helpers for backup import. */
fun JSONArray.forEachObj(block: (JSONObject) -> Unit) {
    for (i in 0 until length()) block(getJSONObject(i))
}

package ru.neverretire.zal.data

import org.json.JSONArray
import org.json.JSONObject
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt

data class ProgramMeta(
    val id: String,
    val title: String,
    val short: String,
    val notePrefix: String,
)

data class ProgramExercise(
    val key: String,
    val name: String,
    val sets: Int,
    val repsMin: Int?,
    val repsMax: Int?,
    val repsExact: Int?,
    val isMax: Boolean,
    val weightKg: Double?,
    val restSec: Int?,
    val notes: String?,
    val isTimeHold: Boolean,
    val holdSec: Int?,
    val isRest: Boolean,
) {
    val label: String get() = name.ifBlank { key }
    val prescription: String
        get() = when {
            isRest -> "отдых"
            isTimeHold -> "${sets}×${holdSec ?: 30} сек"
            isMax -> "${sets}×макс"
            repsExact != null -> "${sets}×$repsExact"
            repsMin != null && repsMax != null -> "${sets}×$repsMin–$repsMax"
            repsMin != null -> "${sets}×$repsMin"
            else -> "${sets}×?"
        }
}

data class WorkoutSession(
    val on: String,
    val programId: String,
    val phase: Int,
    val dayId: String,
    val label: String,
    val title: String,
    val exercises: List<ProgramExercise>,
)

data class LoadedProgram(
    val meta: ProgramMeta,
    val weekdays: List<Int>,
    val rollingSessions: Int?,
    val start: LocalDate?,
    val phases: List<Phase>,
    val calendar: List<CalEntry>,
) {
    data class Phase(val id: Int, val title: String, val days: List<Day>)
    data class Day(val id: String, val title: String, val exercises: List<ProgramExercise>)
    data class CalEntry(val on: LocalDate, val phase: Int, val dayId: String)
}

object ProgramParser {
    private val iso = DateTimeFormatter.ISO_LOCAL_DATE

    fun parse(json: String): LoadedProgram {
        val root = JSONObject(json)
        require(root.optString("schema") == "empire-workout-program/v1") { "bad_schema" }
        val id = root.getString("id")
        val meta = ProgramMeta(
            id = id,
            title = root.optString("title", id),
            short = root.optString("short", root.optString("title", id)),
            notePrefix = root.optString("note_prefix", "подход"),
        )
        val weekdays = parseWeekdays(root.opt("weekdays"))
        val rolling = root.optInt("rolling_sessions", 0).takeIf { it > 0 }
        val start = root.optString("start").takeIf { it.isNotBlank() }?.let { LocalDate.parse(it) }
        val phases = mutableListOf<LoadedProgram.Phase>()
        val phasesArr = root.optJSONArray("phases") ?: JSONArray()
        for (i in 0 until phasesArr.length()) {
            val p = phasesArr.getJSONObject(i)
            val days = mutableListOf<LoadedProgram.Day>()
            val daysArr = p.optJSONArray("days") ?: JSONArray()
            for (j in 0 until daysArr.length()) {
                val d = daysArr.getJSONObject(j)
                days += LoadedProgram.Day(
                    id = d.getString("id"),
                    title = d.optString("title", d.getString("id")),
                    exercises = parseExercises(d.optJSONArray("exercises") ?: JSONArray()),
                )
            }
            phases += LoadedProgram.Phase(
                id = p.optInt("id", i + 1),
                title = p.optString("title", "Фаза ${i + 1}"),
                days = days,
            )
        }
        val calendar = mutableListOf<LoadedProgram.CalEntry>()
        val calArr = root.optJSONArray("calendar") ?: JSONArray()
        for (i in 0 until calArr.length()) {
            val c = calArr.getJSONObject(i)
            calendar += LoadedProgram.CalEntry(
                on = LocalDate.parse(c.getString("on")),
                phase = c.optInt("phase", 1),
                dayId = c.getString("day"),
            )
        }
        return LoadedProgram(meta, weekdays.ifEmpty { listOf(0, 2, 4) }, rolling, start, phases, calendar)
    }

    /**
     * Live schedule like VPS `resolve_schedule`: session specs from the program
     * (calendar order or phase days), placed on Mon/Wed/Fri from [anchor].
     * Embedded JSON calendar dates are templates, not frozen forever.
     */
    fun liveCalendar(
        program: LoadedProgram,
        anchor: LocalDate? = null,
        startDay: String = "A",
    ): List<WorkoutSession> {
        val slots = program.weekdays.ifEmpty { listOf(0, 2, 4) }.sorted()
        val specs = sessionSpecs(program, startDay)
        if (specs.isEmpty() || slots.isEmpty()) return emptyList()
        val start = snapToSlot(anchor ?: defaultAnchor(), slots)
        val dates = generateSlotDates(start, specs.size, slots)
        return dates.zip(specs).map { (on, spec) ->
            val day = findDay(program, spec.phase, spec.dayId)
            WorkoutSession(
                on = on.format(iso),
                programId = program.meta.id,
                phase = spec.phase,
                dayId = spec.dayId,
                label = "Фаза ${spec.phase} / День ${spec.dayId}",
                title = day?.title ?: spec.dayId,
                exercises = day?.exercises.orEmpty(),
            )
        }
    }

    fun sessionForDate(
        program: LoadedProgram,
        on: LocalDate,
        anchor: LocalDate? = null,
        startDay: String = "A",
    ): WorkoutSession? {
        // Prefer exact date from live schedule (same rules as server).
        val live = liveCalendar(program, anchor, startDay)
        live.find { it.on == on.format(iso) }?.let { return it }
        // If embedded calendar still covers this date (historical), use it.
        val cal = program.calendar.find { it.on == on }
        if (cal != null) {
            val day = findDay(program, cal.phase, cal.dayId) ?: return null
            return WorkoutSession(
                on = on.format(iso),
                programId = program.meta.id,
                phase = cal.phase,
                dayId = cal.dayId,
                label = "Фаза ${cal.phase} / День ${cal.dayId}",
                title = day.title,
                exercises = day.exercises,
            )
        }
        return null
    }

    fun nextSession(
        program: LoadedProgram,
        from: LocalDate = LocalDate.now(),
        anchor: LocalDate? = null,
        startDay: String = "A",
    ): WorkoutSession? {
        val fromStr = from.format(iso)
        liveCalendar(program, anchor, startDay).firstOrNull { it.on >= fromStr }?.let { return it }
        for (i in 0..90) {
            sessionForDate(program, from.plusDays(i.toLong()), anchor, startDay)?.let { return it }
        }
        return null
    }

    private data class SessionSpec(val phase: Int, val dayId: String)

    private fun sessionSpecs(program: LoadedProgram, startDay: String): List<SessionSpec> {
        val rolling = program.rollingSessions
        val flatDays = program.phases.flatMap { ph -> ph.days.map { SessionSpec(ph.id, it.id) } }
        val base: List<SessionSpec> = when {
            rolling != null && rolling > 0 && flatDays.isNotEmpty() -> {
                val startIdx = flatDays.indexOfFirst { it.dayId.equals(startDay, true) }.coerceAtLeast(0)
                (0 until rolling).map { i -> flatDays[(startIdx + i) % flatDays.size] }
            }
            program.calendar.isNotEmpty() ->
                program.calendar.map { SessionSpec(it.phase, it.dayId) }
            else -> flatDays
        }
        if (base.isEmpty()) return emptyList()
        val startIdx = base.indexOfFirst { it.dayId.equals(startDay, true) }.coerceAtLeast(0)
        return base.drop(startIdx) + base.take(startIdx)
    }

    private fun findDay(program: LoadedProgram, phase: Int, dayId: String): LoadedProgram.Day? {
        val ph = program.phases.find { it.id == phase } ?: program.phases.firstOrNull()
        return ph?.days?.find { it.id.equals(dayId, ignoreCase = true) }
    }

    /** Next Monday strictly after today (if Monday — next week's Monday). Matches VPS. */
    fun defaultAnchor(today: LocalDate = LocalDate.now()): LocalDate {
        var daysAhead = (DayOfWeek.MONDAY.value - today.dayOfWeek.value + 7) % 7
        if (daysAhead == 0) daysAhead = 7
        return today.plusDays(daysAhead.toLong())
    }

    private fun snapToSlot(d: LocalDate, slots: List<Int>): LocalDate {
        var cur = d
        repeat(8) {
            if (cur.dayOfWeek.toMon0() in slots) return cur
            cur = cur.plusDays(1)
        }
        return d
    }

    private fun generateSlotDates(anchor: LocalDate, count: Int, slots: List<Int>): List<LocalDate> {
        val out = mutableListOf<LocalDate>()
        var d = snapToSlot(anchor, slots)
        while (out.size < count) {
            if (d.dayOfWeek.toMon0() in slots) out += d
            d = d.plusDays(1)
        }
        return out
    }

    private fun DayOfWeek.toMon0(): Int = (value + 5) % 7 // Mon=0 … Sun=6

    private fun parseWeekdays(raw: Any?): List<Int> {
        if (raw == null) return emptyList()
        if (raw is JSONArray) {
            val out = mutableListOf<Int>()
            for (i in 0 until raw.length()) {
                val v = raw.get(i)
                out += when (v) {
                    is Number -> v.toInt()
                    is String -> when (v.lowercase()) {
                        "mon", "пн" -> 0
                        "tue", "вт" -> 1
                        "wed", "ср" -> 2
                        "thu", "чт" -> 3
                        "fri", "пт" -> 4
                        "sat", "сб" -> 5
                        "sun", "вс" -> 6
                        else -> v.toIntOrNull() ?: continue
                    }
                    else -> continue
                }
            }
            return out
        }
        return emptyList()
    }

    private fun parseExercises(arr: JSONArray): List<ProgramExercise> {
        val out = mutableListOf<ProgramExercise>()
        for (i in 0 until arr.length()) {
            val e = arr.getJSONObject(i)
            val key = e.getString("key")
            val isRest = key == "отдых"
            val isHold = e.optBoolean("is_time_hold", false) || e.has("hold_sec")
            val (rMin, rMax, rExact, isMax) = parseReps(e.opt("reps"))
            out += ProgramExercise(
                key = key,
                name = e.optString("name", key),
                sets = e.optInt("sets", if (isHold) 1 else 3),
                repsMin = rMin,
                repsMax = rMax,
                repsExact = rExact,
                isMax = isMax,
                weightKg = parseWeight(e.opt("weight_kg")),
                restSec = e.optInt("rest_sec").takeIf { e.has("rest_sec") },
                notes = e.optString("notes").takeIf { it.isNotBlank() },
                isTimeHold = isHold,
                holdSec = e.optInt("hold_sec").takeIf { e.has("hold_sec") },
                isRest = isRest,
            )
        }
        return out
    }

    private data class Reps(val min: Int?, val max: Int?, val exact: Int?, val isMax: Boolean)

    private fun parseReps(raw: Any?): Reps {
        when (raw) {
            null -> return Reps(null, null, null, false)
            is Number -> return Reps(null, null, raw.toInt(), false)
            is String -> {
                if (raw.equals("max", true) || raw.equals("макс", true)) {
                    return Reps(null, null, null, true)
                }
                raw.toIntOrNull()?.let { return Reps(null, null, it, false) }
            }
            is JSONArray -> {
                if (raw.length() >= 2) {
                    return Reps(raw.getInt(0), raw.getInt(1), null, false)
                }
                if (raw.length() == 1) return Reps(null, null, raw.getInt(0), false)
            }
        }
        return Reps(null, null, null, false)
    }

    private fun parseWeight(raw: Any?): Double? = when (raw) {
        null -> null
        is Number -> raw.toDouble()
        is JSONArray -> {
            if (raw.length() >= 2) (raw.getDouble(0) + raw.getDouble(1)) / 2.0
            else if (raw.length() == 1) raw.getDouble(0)
            else null
        }
        is String -> raw.replace(',', '.').toDoubleOrNull()
        else -> null
    }

    fun defaultReps(ex: ProgramExercise): Int =
        when {
            ex.isTimeHold -> ex.holdSec ?: 30
            ex.repsExact != null -> ex.repsExact
            ex.repsMin != null -> ex.repsMin
            else -> 8
        }
}

fun Double.pretty(): String =
    if (this == this.roundToInt().toDouble()) this.roundToInt().toString() else "%.1f".format(this)

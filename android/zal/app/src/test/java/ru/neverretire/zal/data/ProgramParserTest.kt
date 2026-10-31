package ru.neverretire.zal.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.time.LocalDate

class ProgramParserTest {
    private fun loadAsset(name: String): String {
        val roots = listOf(
            File("src/main/assets/programs/$name"),
            File("app/src/main/assets/programs/$name"),
            File("../app/src/main/assets/programs/$name"),
        )
        val f = roots.firstOrNull { it.isFile }
            ?: error("asset not found: $name in ${File(".").absolutePath}")
        return f.readText()
    }

    @Test
    fun gym2026_hasFullPhase1DayA() {
        val program = ProgramParser.parse(loadAsset("gym_2026.json"))
        assertEquals("gym_2026", program.meta.id)
        assertEquals("Зал", program.meta.short)
        val day = program.phases.first { it.id == 1 }.days.first { it.id == "A" }
        val work = day.exercises.filter { !it.isRest }
        assertEquals(6, work.size)
        assertTrue(work.any { it.key.contains("жим") })
    }

    @Test
    fun outsideHall_hasManyExercises() {
        val program = ProgramParser.parse(loadAsset("outside_hall.json"))
        assertEquals("Вне зала", program.meta.short)
        val day = program.phases.first().days.first { it.id == "A" }
        assertTrue(day.exercises.filter { !it.isRest }.size >= 8)
    }

    @Test
    fun liveCalendar_nextSession_isFullDayNotTaper() {
        val program = ProgramParser.parse(loadAsset("gym_2026.json"))
        val from = LocalDate.of(2026, 9, 11)
        val session = ProgramParser.nextSession(program, from)
        assertNotNull(session)
        val work = session!!.exercises.filter { !it.isRest }
        assertTrue(
            "expected full day (>=5), got ${work.size}: ${work.map { it.key }}",
            work.size >= 5,
        )
        assertEquals(1, session.phase)
        assertEquals("A", session.dayId)
    }

    @Test
    fun noDemoProgramAsset() {
        val dir = listOf(
            File("src/main/assets/programs"),
            File("app/src/main/assets/programs"),
        ).first { it.isDirectory }
        val names = dir.list()?.toList().orEmpty()
        assertTrue(names.none { it.contains("full_body") })
        assertTrue(names.contains("gym_2026.json"))
        assertTrue(names.contains("outside_hall.json"))
    }
}

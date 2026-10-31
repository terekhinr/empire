package ru.neverretire.zal.ui.program

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import ru.neverretire.zal.data.GymRepository
import ru.neverretire.zal.data.ProgramExercise
import ru.neverretire.zal.data.ProgramMeta
import ru.neverretire.zal.data.ProgramParser
import ru.neverretire.zal.data.WorkoutSession
import ru.neverretire.zal.ui.components.ConvexButton
import ru.neverretire.zal.ui.components.ConvexChip
import ru.neverretire.zal.ui.components.ConvexPrimaryButton
import ru.neverretire.zal.ui.components.ConvexStyle
import ru.neverretire.zal.ui.components.HoldTimerBar
import ru.neverretire.zal.ui.components.HoldTimerState
import ru.neverretire.zal.ui.components.RestTimerBar
import ru.neverretire.zal.ui.components.RestTimerState
import ru.neverretire.zal.ui.components.ZalCard
import ru.neverretire.zal.ui.theme.ZalColors
import java.time.LocalDate

@Composable
fun ProgramScreen(
    repo: GymRepository,
    restTimer: RestTimerState,
    holdTimer: HoldTimerState,
    onMessage: (String) -> Unit,
) {
    val scope = rememberCoroutineScope()
    val ctx = LocalContext.current
    var programs by remember { mutableStateOf<List<ProgramMeta>>(emptyList()) }
    var programId by remember { mutableStateOf("gym_2026") }
    var programTitle by remember { mutableStateOf("") }
    var notePrefix by remember { mutableStateOf("подход") }
    var date by remember { mutableStateOf(LocalDate.now()) }
    var session by remember { mutableStateOf<WorkoutSession?>(null) }
    var restAutostart by remember { mutableStateOf(true) }
    var autosaveHint by remember { mutableStateOf("Подходы сохраняются автоматически") }
    var saveJob by remember { mutableStateOf<Job?>(null) }
    val done = remember { mutableStateMapOf<String, Boolean>() }
    val weights = remember { mutableStateMapOf<String, String>() }
    val reps = remember { mutableStateMapOf<String, String>() }

    fun key(exIdx: Int, set: Int) = "$exIdx-$set"

    fun collectEntries(s: WorkoutSession): List<GymRepository.SetEntry> {
        val entries = mutableListOf<GymRepository.SetEntry>()
        s.exercises.forEachIndexed { exIdx, ex ->
            if (ex.isRest) return@forEachIndexed
            val n = ex.sets.coerceAtLeast(1)
            for (setIdx in 1..n) {
                val k = key(exIdx, setIdx)
                if (done[k] != true) continue
                val r = reps[k]?.toIntOrNull() ?: continue
                if (r < 1) continue
                val w = weights[k]?.toDoubleOrNull() ?: 0.0
                entries += GymRepository.SetEntry(
                    exerciseKey = ex.key,
                    exerciseLabel = ex.label,
                    setIndex = setIdx,
                    setTotal = n,
                    weightKg = w,
                    reps = r,
                )
            }
        }
        return entries
    }

    fun scheduleAutosave(s: WorkoutSession) {
        saveJob?.cancel()
        saveJob = scope.launch {
            delay(900)
            val entries = collectEntries(s)
            if (entries.isEmpty()) return@launch
            autosaveHint = "Сохранение…"
            repo.saveProgramSets(s.on, s.programId, notePrefix, entries)
            autosaveHint = "Автосохранено · ${entries.size} подх."
        }
    }

    fun startRestIfNeeded() {
        if (restAutostart) restTimer.start(restTimer.presetSec)
    }

    fun reload() {
        scope.launch {
            runCatching {
                programs = repo.listPrograms()
                programId = repo.getProgramId()
                restAutostart = repo.restAutostart()
                restTimer.presetSec = repo.getRestSec()
                val program = repo.loadProgram(programId)
                notePrefix = program.meta.notePrefix
                programTitle = program.meta.title
                val loaded = ProgramParser.sessionForDate(program, date)
                    ?: ProgramParser.nextSession(program, date)?.also {
                        date = LocalDate.parse(it.on)
                    }
                session = loaded
                val day = (loaded?.on ?: date.toString())
                val dayLogs = repo.logsForDay(day)
                done.clear()
                weights.clear()
                reps.clear()
                loaded?.exercises?.forEachIndexed { exIdx, ex ->
                    if (ex.isRest) return@forEachIndexed
                    val n = ex.sets.coerceAtLeast(1)
                    for (s in 1..n) {
                        val k = key(exIdx, s)
                        val prev = dayLogs.find {
                            it.exerciseKey == ex.key && (it.note ?: "").contains("$s/$n")
                        }
                        if (prev != null) {
                            done[k] = true
                            weights[k] = prev.weightKg.toString()
                            reps[k] = prev.reps.toString()
                        } else {
                            weights[k] = if (s == 1) ex.weightKg?.toString().orEmpty() else ""
                            reps[k] = ProgramParser.defaultReps(ex).toString()
                        }
                    }
                }
            }.onFailure {
                onMessage("Ошибка загрузки: ${it.message ?: it.javaClass.simpleName}")
            }
        }
    }

    LaunchedEffect(Unit) { reload() }

    val pickProgram = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent(),
    ) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            runCatching {
                ctx.contentResolver.openInputStream(uri)?.use { ins ->
                    val text = ins.bufferedReader().use { it.readText() }
                    val meta = repo.importUserProgramJson(text)
                    repo.setProgramId(meta.id)
                    onMessage("Загружено: ${meta.title}")
                    reload()
                }
            }.onFailure { onMessage(it.message ?: "Ошибка файла") }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ZalColors.Bg)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        RestTimerBar(
            state = restTimer,
            autostart = restAutostart,
            onAutostartChange = {
                restAutostart = it
                scope.launch { repo.setRestAutostart(it) }
            },
            onPresetSelected = { scope.launch { repo.setRestSec(it) } },
            onFinished = { onMessage("Отдых окончен — следующий подход") },
        )
        HoldTimerBar(
            state = holdTimer,
            onFinished = {
                onMessage("Удержание готово")
                startRestIfNeeded()
            },
            modifier = Modifier.padding(top = 8.dp),
        )

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.weight(1f).fillMaxWidth().padding(top = 10.dp),
        ) {
            item {
                ZalCard {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        programs.forEach { p ->
                            ConvexChip(
                                text = p.short,
                                selected = p.id == programId,
                                onClick = {
                                    scope.launch {
                                        repo.setProgramId(p.id)
                                        reload()
                                    }
                                },
                            )
                        }
                    }
                    if (programTitle.isNotBlank()) {
                        Text(
                            programTitle,
                            color = ZalColors.Muted,
                            fontSize = 13.sp,
                            modifier = Modifier.padding(top = 6.dp),
                        )
                    }
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.padding(top = 8.dp),
                    ) {
                        ConvexButton("←", { date = date.minusDays(1); reload() }, style = ConvexStyle.Small)
                        Text(date.toString(), color = ZalColors.Text, fontWeight = FontWeight.SemiBold)
                        ConvexButton("→", { date = date.plusDays(1); reload() }, style = ConvexStyle.Small)
                        ConvexButton("Сегодня", {
                            date = LocalDate.now()
                            reload()
                        }, style = ConvexStyle.Small)
                    }
                    Row(modifier = Modifier.padding(top = 8.dp)) {
                        ConvexButton(
                            text = "Загрузить файл",
                            onClick = { pickProgram.launch("*/*") },
                            style = ConvexStyle.Small,
                        )
                    }
                    Text(
                        autosaveHint,
                        color = ZalColors.Muted,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(top = 6.dp),
                    )
                }
            }

            val s = session
            if (s == null) {
                item {
                    Text(
                        "На эту дату нет тренировки по календарю этой программы",
                        color = ZalColors.Muted,
                    )
                }
            } else {
                val work = s.exercises.filter { !it.isRest }
                item {
                    ZalCard {
                        Text(s.label, color = ZalColors.Text, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text(s.title, color = ZalColors.Muted, fontSize = 14.sp)
                        Text(
                            "${work.size} упражнений · все раскрыты",
                            color = ZalColors.Sky,
                            fontSize = 13.sp,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                }
                item {
                    Text("Упражнения", color = ZalColors.Text, fontWeight = FontWeight.SemiBold)
                }
                itemsIndexed(s.exercises) { exIdx, ex ->
                    if (ex.isRest) {
                        Text(
                            "Отдых: ${ex.notes ?: ""}",
                            color = ZalColors.Muted,
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(ZalColors.Surface, RoundedCornerShape(12.dp))
                                .padding(12.dp),
                        )
                    } else {
                        ExerciseCard(
                            ex = ex,
                            exIdx = exIdx,
                            done = done,
                            weights = weights,
                            reps = reps,
                            onToggleSet = { setIdx, checked ->
                                val k = key(exIdx, setIdx)
                                done[k] = checked
                                if (checked) {
                                    if (ex.isTimeHold) {
                                        holdTimer.start(
                                            reps[k]?.toIntOrNull() ?: ProgramParser.defaultReps(ex),
                                            ex.label,
                                        )
                                    } else {
                                        startRestIfNeeded()
                                    }
                                }
                                scheduleAutosave(s)
                            },
                            onFieldChange = { scheduleAutosave(s) },
                            onHoldClick = { setIdx, sec ->
                                holdTimer.start(sec, ex.label)
                                reps[key(exIdx, setIdx)] = sec.toString()
                            },
                            onCopyWeight = {
                                val first = weights[key(exIdx, 1)].orEmpty()
                                val n = ex.sets.coerceAtLeast(1)
                                for (i in 1..n) weights[key(exIdx, i)] = first
                                scheduleAutosave(s)
                            },
                        )
                    }
                }
                item {
                    ConvexPrimaryButton(
                        text = "Сохранить сейчас",
                        onClick = {
                            scope.launch {
                                val entries = collectEntries(s)
                                if (entries.isEmpty()) {
                                    onMessage("Отметьте хотя бы один подход")
                                    return@launch
                                }
                                repo.saveProgramSets(s.on, s.programId, notePrefix, entries)
                                autosaveHint = "Сохранено: ${entries.size}"
                                onMessage("Сохранено: ${entries.size}")
                            }
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun ExerciseCard(
    ex: ProgramExercise,
    exIdx: Int,
    done: MutableMap<String, Boolean>,
    weights: MutableMap<String, String>,
    reps: MutableMap<String, String>,
    onToggleSet: (Int, Boolean) -> Unit,
    onFieldChange: () -> Unit,
    onHoldClick: (Int, Int) -> Unit,
    onCopyWeight: () -> Unit,
) {
    val n = ex.sets.coerceAtLeast(1)
    val doneCount = (1..n).count { done["$exIdx-$it"] == true }
    val dots = "●".repeat(doneCount) + "○".repeat((n - doneCount).coerceAtLeast(0))
    val holdSec = ex.holdSec
    val plan = when {
        ex.isTimeHold -> "${ex.prescription} · ${ProgramParser.defaultReps(ex)} сек"
        holdSec != null -> "${ex.prescription} · ⏱ $holdSec сек"
        else -> ex.prescription
    }
    val fieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = ZalColors.Accent,
        unfocusedBorderColor = ZalColors.Surface2,
        focusedTextColor = ZalColors.Text,
        unfocusedTextColor = ZalColors.Text,
        focusedContainerColor = ZalColors.Bg,
        unfocusedContainerColor = ZalColors.Bg,
        focusedLabelColor = ZalColors.Muted,
        unfocusedLabelColor = ZalColors.Muted,
    )

    ZalCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(ex.label, color = ZalColors.Text, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
                Text(plan, color = ZalColors.Muted, fontSize = 13.sp)
            }
            if (holdSec != null && !ex.isTimeHold) {
                ConvexButton("⏱ $holdSec", { onHoldClick(1, holdSec) }, style = ConvexStyle.Small)
            }
            Text(dots, color = ZalColors.Accent, modifier = Modifier.padding(start = 6.dp))
        }
        if (!ex.notes.isNullOrBlank()) {
            Text(
                listOfNotNull(ex.prescription, ex.notes).joinToString(" · "),
                color = ZalColors.Muted,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 6.dp, bottom = 4.dp),
            )
        }
        for (s in 1..n) {
            val k = "$exIdx-$s"
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
            ) {
                Checkbox(
                    checked = done[k] == true,
                    onCheckedChange = { onToggleSet(s, it) },
                    colors = CheckboxDefaults.colors(
                        checkedColor = ZalColors.Accent,
                        uncheckedColor = ZalColors.Muted,
                    ),
                )
                Text("#$s", color = ZalColors.Muted, fontSize = 13.sp)
                if (ex.isTimeHold) {
                    OutlinedTextField(
                        value = reps[k].orEmpty(),
                        onValueChange = { reps[k] = it; onFieldChange() },
                        label = { Text("сек") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        colors = fieldColors,
                    )
                    ConvexButton(
                        "⏱",
                        {
                            val sec = reps[k]?.toIntOrNull() ?: ProgramParser.defaultReps(ex)
                            onHoldClick(s, sec)
                        },
                        style = ConvexStyle.Small,
                    )
                } else {
                    OutlinedTextField(
                        value = weights[k].orEmpty(),
                        onValueChange = { weights[k] = it; onFieldChange() },
                        label = { Text("кг") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        colors = fieldColors,
                    )
                    OutlinedTextField(
                        value = reps[k].orEmpty(),
                        onValueChange = { reps[k] = it; onFieldChange() },
                        label = { Text("повт") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        colors = fieldColors,
                    )
                    if (holdSec != null) {
                        ConvexButton("⏱", { onHoldClick(s, holdSec) }, style = ConvexStyle.Small)
                    }
                }
            }
        }
        if (!ex.isTimeHold && n > 1) {
            ConvexButton(
                text = "Тот же вес во всех",
                onClick = onCopyWeight,
                style = ConvexStyle.Small,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
    }
}

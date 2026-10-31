package ru.neverretire.zal.ui.components

import android.content.Context
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import ru.neverretire.zal.ui.theme.ZalColors

val REST_PRESETS = listOf(60, 90, 120, 180)

class RestTimerState {
    var endAtMs by mutableStateOf<Long?>(null)
        private set
    var pausedRemainingMs by mutableStateOf<Long?>(null)
        private set
    var presetSec by mutableStateOf(120)
    var tick by mutableLongStateOf(0L)
        private set

    fun remainingMs(): Long {
        val end = endAtMs
        if (end != null) return (end - System.currentTimeMillis()).coerceAtLeast(0)
        return pausedRemainingMs ?: 0L
    }

    fun isActive(): Boolean = endAtMs != null || pausedRemainingMs != null
    fun isPaused(): Boolean = pausedRemainingMs != null

    fun bump() {
        tick = System.currentTimeMillis()
    }

    fun start(sec: Int = presetSec) {
        presetSec = sec
        pausedRemainingMs = null
        endAtMs = System.currentTimeMillis() + sec * 1000L
        bump()
    }

    fun pause() {
        if (endAtMs == null) return
        pausedRemainingMs = remainingMs()
        endAtMs = null
        bump()
    }

    fun resume() {
        val rem = pausedRemainingMs ?: return
        pausedRemainingMs = null
        endAtMs = System.currentTimeMillis() + rem
        bump()
    }

    fun add30() {
        when {
            endAtMs != null -> endAtMs = endAtMs!! + 30_000
            pausedRemainingMs != null -> pausedRemainingMs = pausedRemainingMs!! + 30_000
            else -> start(presetSec)
        }
        bump()
    }

    fun stop() {
        endAtMs = null
        pausedRemainingMs = null
        bump()
    }

    fun complete() {
        stop()
    }
}

class HoldTimerState {
    var endAtMs by mutableStateOf<Long?>(null)
        private set
    var pausedRemainingMs by mutableStateOf<Long?>(null)
        private set
    var label by mutableStateOf("Удержание")
    var tick by mutableLongStateOf(0L)
        private set

    fun remainingMs(): Long {
        val end = endAtMs
        if (end != null) return (end - System.currentTimeMillis()).coerceAtLeast(0)
        return pausedRemainingMs ?: 0L
    }

    fun isActive(): Boolean = endAtMs != null || pausedRemainingMs != null
    fun isPaused(): Boolean = pausedRemainingMs != null

    fun bump() {
        tick = System.currentTimeMillis()
    }

    fun start(seconds: Int, title: String = "Удержание") {
        label = title
        pausedRemainingMs = null
        endAtMs = System.currentTimeMillis() + seconds.coerceAtLeast(1) * 1000L
        bump()
    }

    fun pause() {
        if (endAtMs == null) return
        pausedRemainingMs = remainingMs()
        endAtMs = null
        bump()
    }

    fun resume() {
        val rem = pausedRemainingMs ?: return
        pausedRemainingMs = null
        endAtMs = System.currentTimeMillis() + rem
        bump()
    }

    fun stop() {
        endAtMs = null
        pausedRemainingMs = null
        bump()
    }
}

@Composable
fun rememberRestTimerState(): RestTimerState = remember { RestTimerState() }

@Composable
fun rememberHoldTimerState(): HoldTimerState = remember { HoldTimerState() }

@Composable
fun RestTimerBar(
    state: RestTimerState,
    autostart: Boolean,
    onAutostartChange: (Boolean) -> Unit,
    onPresetSelected: (Int) -> Unit = {},
    onFinished: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val ctx = LocalContext.current
    LaunchedEffect(state.endAtMs) {
        while (state.endAtMs != null) {
            state.bump()
            if (state.remainingMs() <= 0) {
                state.complete()
                notifyDone(ctx)
                onFinished()
                break
            }
            delay(200)
        }
    }
    @Suppress("UNUSED_VARIABLE")
    val _tick = state.tick

    val active = state.isActive()
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(ZalColors.Bg.copy(alpha = 0.96f), RoundedCornerShape(14.dp))
            .border(
                1.dp,
                if (active) ZalColors.Sky.copy(alpha = 0.45f) else ColorWhite10,
                RoundedCornerShape(14.dp),
            )
            .padding(12.dp),
    ) {
        if (!active) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    "Отдых между подходами",
                    color = ZalColors.Text,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = autostart,
                        onCheckedChange = onAutostartChange,
                        colors = CheckboxDefaults.colors(
                            checkedColor = ZalColors.Accent,
                            uncheckedColor = ZalColors.Muted,
                        ),
                    )
                    Text("После подхода", color = ZalColors.Muted, fontSize = 12.sp)
                }
            }
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            ) {
                REST_PRESETS.forEach { sec ->
                    RestPresetButton(
                        text = formatSec(sec),
                        selected = state.presetSec == sec,
                        onClick = {
                            onPresetSelected(sec)
                            state.start(sec)
                        },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        } else {
            Text(
                formatMs(state.remainingMs()),
                fontSize = 42.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFF0F9FF),
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )
            Text(
                if (state.isPaused()) "пауза" else "осталось",
                color = ZalColors.Muted,
                fontSize = 12.sp,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            ) {
                ConvexButton(
                    text = "+30 сек",
                    onClick = { state.add30() },
                    style = ConvexStyle.Small,
                    modifier = Modifier.weight(1f),
                )
                ConvexButton(
                    text = if (state.isPaused()) "Далее" else "Пауза",
                    onClick = { if (state.isPaused()) state.resume() else state.pause() },
                    style = ConvexStyle.Small,
                    modifier = Modifier.weight(1f),
                )
                ConvexButton(
                    text = "Стоп",
                    onClick = { state.stop() },
                    style = ConvexStyle.Small,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

private val ColorWhite10 = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.10f)

@Composable
fun HoldTimerBar(
    state: HoldTimerState,
    onFinished: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    if (!state.isActive()) return
    val ctx = LocalContext.current
    LaunchedEffect(state.endAtMs) {
        while (state.endAtMs != null) {
            state.bump()
            if (state.remainingMs() <= 0) {
                state.stop()
                notifyDone(ctx)
                onFinished()
                break
            }
            delay(100)
        }
    }
    @Suppress("UNUSED_VARIABLE")
    val _tick = state.tick

    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(ZalColors.Sky.copy(alpha = 0.12f), RoundedCornerShape(14.dp))
            .border(1.dp, ZalColors.Sky.copy(alpha = 0.35f), RoundedCornerShape(14.dp))
            .padding(14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(state.label, color = ZalColors.Text, fontWeight = FontWeight.SemiBold)
        Text(
            formatMs(state.remainingMs()),
            fontSize = 42.sp,
            fontWeight = FontWeight.Bold,
            color = ZalColors.Sky,
        )
        Text("секунд", color = ZalColors.Muted, fontSize = 12.sp)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
            ConvexButton(
                text = if (state.isPaused()) "Далее" else "Пауза",
                onClick = { if (state.isPaused()) state.resume() else state.pause() },
                style = ConvexStyle.Small,
            )
            ConvexButton(
                text = "Стоп",
                onClick = { state.stop() },
                style = ConvexStyle.Small,
            )
        }
    }
}

fun formatSec(sec: Int): String {
    val m = sec / 60
    val s = sec % 60
    return "%d:%02d".format(m, s)
}

fun formatMs(ms: Long): String = formatSec(((ms + 999) / 1000).toInt().coerceAtLeast(0))

@Suppress("DEPRECATION")
fun vibrate(context: Context) {
    try {
        if (Build.VERSION.SDK_INT >= 31) {
            val vm = context.getSystemService(VibratorManager::class.java)
            vm?.defaultVibrator?.vibrate(
                VibrationEffect.createWaveform(longArrayOf(0, 180, 80, 180), -1),
            )
        } else {
            val v = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            if (Build.VERSION.SDK_INT >= 26) {
                v.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 180, 80, 180), -1))
            } else {
                v.vibrate(400)
            }
        }
    } catch (_: Exception) {
    }
}

fun beep() {
    // ToneGenerator can crash on some OEMs / missing audio path — never kill the app.
    try {
        val tg = ToneGenerator(AudioManager.STREAM_MUSIC, 70)
        tg.startTone(ToneGenerator.TONE_PROP_BEEP, 200)
        Handler(Looper.getMainLooper()).postDelayed({
            try {
                tg.release()
            } catch (_: Exception) {
            }
        }, 400)
    } catch (_: Exception) {
    }
}

fun notifyDone(context: Context) {
    vibrate(context)
    beep()
}

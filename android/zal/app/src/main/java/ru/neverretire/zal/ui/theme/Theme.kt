package ru.neverretire.zal.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** Tokens from static/planning/styles.css (:root) */
object ZalColors {
    val Bg = Color(0xFF0F172A)
    val Surface = Color(0xFF1E293B)
    val Surface2 = Color(0xFF334155)
    val Text = Color(0xFFF8FAFC)
    val Muted = Color(0xFF94A3B8)
    val Accent = Color(0xFF3B82F6)
    val AccentDark = Color(0xFF2563EB)
    val AccentDeep = Color(0xFF1D4ED8)
    val AccentPlate = Color(0xFF1E3A8A)
    val Sky = Color(0xFF38BDF8)
    val SkySoft = Color(0xFF7DD3FC)
    val Danger = Color(0xFFEF4444)
    val DangerText = Color(0xFFFCA5A5)
    val Success = Color(0xFF22C55E)
    val ChipTop = Color(0xFF3F4F66)
    val ChipBottom = Color(0xFF334155)
    val BtnTop = Color(0xFF3F4F66)
    val BtnBottom = Color(0xFF2D3A4D)
    val Highlight = Color(0x24FFFFFF) // ~14% white
}

private val colors = darkColorScheme(
    primary = ZalColors.Accent,
    onPrimary = Color.White,
    primaryContainer = ZalColors.AccentDark,
    secondary = ZalColors.Sky,
    onSecondary = ZalColors.Bg,
    background = ZalColors.Bg,
    surface = ZalColors.Surface,
    surfaceVariant = ZalColors.Surface2,
    onBackground = ZalColors.Text,
    onSurface = ZalColors.Text,
    onSurfaceVariant = ZalColors.Muted,
    outline = ZalColors.Surface2,
    error = ZalColors.Danger,
    onError = Color.White,
)

@Composable
fun ZalTheme(content: @Composable () -> Unit) {
    @Suppress("UNUSED_VARIABLE")
    val _dark = isSystemInDarkTheme()
    MaterialTheme(colorScheme = colors, content = content)
}

package ru.neverretire.zal.ui.components

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ru.neverretire.zal.ui.theme.ZalColors

enum class ConvexStyle {
    Default,
    Primary,
    Danger,
    Small,
}

/**
 * Web-style convex button. Avoids fillMaxWidth inside Row (that crashes with
 * infinite max-width constraints).
 */
@Composable
fun ConvexButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    style: ConvexStyle = ConvexStyle.Default,
    enabled: Boolean = true,
    fillMaxWidth: Boolean = false,
) {
    val shape = when (style) {
        ConvexStyle.Small -> RoundedCornerShape(12.dp)
        else -> RoundedCornerShape(14.dp)
    }
    val plateH = when (style) {
        ConvexStyle.Primary -> 4.dp
        else -> 2.dp
    }
    val brush = when (style) {
        ConvexStyle.Primary -> Brush.verticalGradient(
            listOf(ZalColors.Accent, ZalColors.AccentDark, ZalColors.AccentDeep),
        )
        ConvexStyle.Danger -> Brush.verticalGradient(
            listOf(Color(0x59EF4444), Color(0x40B91C1C)),
        )
        else -> Brush.verticalGradient(
            listOf(ZalColors.BtnTop, ZalColors.BtnBottom),
        )
    }
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val sink by animateDpAsState(if (pressed) plateH else 0.dp, label = "sink")
    val elevation by animateDpAsState(if (pressed) 1.dp else plateH + 2.dp, label = "elev")
    val pad = when (style) {
        ConvexStyle.Small -> PaddingValues(horizontal = 14.dp, vertical = 8.dp)
        else -> PaddingValues(horizontal = 14.dp, vertical = 14.dp)
    }
    val fontSize = when (style) {
        ConvexStyle.Small -> 14.sp
        else -> 16.sp
    }
    val textColor = when (style) {
        ConvexStyle.Danger -> ZalColors.DangerText
        ConvexStyle.Primary -> Color.White
        else -> ZalColors.Text
    }

    Box(
        modifier = modifier
            .then(if (fillMaxWidth) Modifier.fillMaxWidth() else Modifier.wrapContentWidth())
            .padding(bottom = if (pressed) 0.dp else plateH)
            .offset(y = sink)
            .shadow(
                elevation = elevation,
                shape = shape,
                ambientColor = Color.Black.copy(alpha = 0.35f),
                spotColor = Color.Black.copy(alpha = 0.45f),
            )
            .clip(shape)
            .background(brush)
            .border(1.dp, Color.White.copy(alpha = 0.10f), shape)
            .clickable(
                enabled = enabled,
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            )
            .padding(pad),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = if (enabled) textColor else ZalColors.Muted,
            fontWeight = FontWeight.SemiBold,
            fontSize = fontSize,
            textAlign = TextAlign.Center,
            maxLines = 1,
        )
    }
}

@Composable
fun ConvexChip(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(20.dp)
    val plateH = if (selected) 3.dp else 2.dp
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val sink by animateDpAsState(if (pressed) plateH else 0.dp, label = "chipSink")
    val elevation by animateDpAsState(if (pressed) 1.dp else plateH + 1.dp, label = "chipElev")
    val brush = if (selected) {
        Brush.verticalGradient(listOf(ZalColors.Accent, ZalColors.AccentDark))
    } else {
        Brush.verticalGradient(listOf(ZalColors.ChipTop, ZalColors.ChipBottom))
    }

    Box(
        modifier = modifier
            .wrapContentWidth()
            .padding(bottom = if (pressed) 0.dp else plateH)
            .offset(y = sink)
            .shadow(elevation, shape, ambientColor = Color.Black.copy(0.3f), spotColor = Color.Black.copy(0.4f))
            .clip(shape)
            .background(brush)
            .border(1.dp, Color.White.copy(alpha = 0.08f), shape)
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            )
            .padding(horizontal = 12.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp,
            maxLines = 1,
        )
    }
}

@Composable
fun ConvexPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    ConvexButton(
        text = text,
        onClick = onClick,
        modifier = modifier,
        style = ConvexStyle.Primary,
        enabled = enabled,
        fillMaxWidth = true,
    )
}

@Composable
fun ZalCard(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ZalColors.Surface)
            .padding(12.dp),
    ) {
        content()
    }
}

@Composable
fun RestPresetButton(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(10.dp)
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val sink by animateDpAsState(if (pressed) 2.dp else 0.dp, label = "preset")
    Box(
        modifier = modifier
            .offset(y = sink)
            .clip(shape)
            .background(
                if (selected) Color(0x2438BDF8) else Color.White.copy(alpha = 0.04f),
            )
            .border(
                1.dp,
                if (selected) Color(0x8C38BDF8) else Color.White.copy(alpha = 0.12f),
                shape,
            )
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            )
            .padding(vertical = 10.dp, horizontal = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            color = if (selected) ZalColors.SkySoft else Color(0xFFE2E8F0),
            fontWeight = FontWeight.SemiBold,
            fontSize = 15.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
            maxLines = 1,
        )
    }
}

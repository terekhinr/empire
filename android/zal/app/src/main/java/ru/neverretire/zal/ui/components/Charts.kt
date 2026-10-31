package ru.neverretire.zal.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

@Composable
fun SparklineCard(
    title: String,
    points: List<Pair<String, Double>>,
    unit: String = "",
    emptyHint: String = "нет данных — добавьте хотя бы 2 точки",
) {
    val drawn = remember(points) { downsample(points, 80) }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            val last = points.lastOrNull()?.second
            Text(
                if (last != null) {
                    val first = points.first().second
                    val delta = last - first
                    val sign = when {
                        delta > 0 -> "+"
                        else -> ""
                    }
                    "$title · сейчас ${fmt(last)}$unit · Δ $sign${fmt(delta)}$unit"
                } else {
                    "$title: $emptyHint"
                },
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (drawn.size >= 2) {
                val color = MaterialTheme.colorScheme.secondary
                Canvas(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp)
                        .padding(top = 8.dp),
                ) {
                    val ys = drawn.map { it.second }
                    val min = ys.min()
                    val max = ys.max().let { if (it == min) it + 1 else it }
                    val path = Path()
                    drawn.forEachIndexed { i, p ->
                        val x = i * size.width / (drawn.size - 1).coerceAtLeast(1)
                        val y = size.height - ((p.second - min) / (max - min) * size.height)
                        if (i == 0) path.moveTo(x, y.toFloat()) else path.lineTo(x, y.toFloat())
                    }
                    drawPath(path, color, style = Stroke(width = 4f, cap = StrokeCap.Round))
                    val lastPt = drawn.last()
                    val lx = size.width
                    val ly = size.height - ((lastPt.second - min) / (max - min) * size.height)
                    drawCircle(color, 6f, Offset(lx, ly.toFloat()))
                }
                RowDates(drawn.first().first, drawn.last().first)
            }
        }
    }
}

/** Keep charts light even with hundreds of scale points. */
fun downsample(points: List<Pair<String, Double>>, maxPoints: Int): List<Pair<String, Double>> {
    if (points.size <= maxPoints) return points
    if (maxPoints < 2) return points.takeLast(1)
    val out = ArrayList<Pair<String, Double>>(maxPoints)
    val last = points.size - 1
    for (i in 0 until maxPoints) {
        val idx = (i * last.toDouble() / (maxPoints - 1)).toInt()
        out += points[idx]
    }
    return out
}

@Composable
private fun RowDates(first: String, last: String) {
    androidx.compose.foundation.layout.Row(
        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween,
    ) {
        Text(first.takeLast(5), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(last.takeLast(5), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private fun fmt(v: Double): String =
    if (v == v.toLong().toDouble()) v.toLong().toString() else "%.1f".format(v)

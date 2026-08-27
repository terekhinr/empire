package ru.neverretire.zadachnik.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.widget.RemoteViews
import ru.neverretire.zadachnik.BuildConfig
import ru.neverretire.zadachnik.MainActivity
import ru.neverretire.zadachnik.R

enum class WidgetFilter(val key: String, val title: String) {
    WEEK("week", "Следующие 7 дней"),
    TODAY("today", "Сегодня"),
    OVERDUE("overdue", "Просрочено"),
    INBOX("inbox", "Входящие"),
    SOMEDAY("someday", "Когда-нибудь");

    companion object {
        fun fromKey(key: String?): WidgetFilter =
            entries.firstOrNull { it.key == key } ?: WEEK

        fun cycle(current: WidgetFilter): WidgetFilter {
            val all = entries
            return all[(all.indexOf(current) + 1) % all.size]
        }
    }
}

object WidgetPrefs {
    private const val PREFS = "zadachnik_widget_prefs"

    private fun prefs(ctx: Context): SharedPreferences =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun getFilter(ctx: Context, appWidgetId: Int): WidgetFilter =
        WidgetFilter.fromKey(prefs(ctx).getString("filter_$appWidgetId", WidgetFilter.WEEK.key))

    fun setFilter(ctx: Context, appWidgetId: Int, filter: WidgetFilter) {
        prefs(ctx).edit().putString("filter_$appWidgetId", filter.key).apply()
    }
}

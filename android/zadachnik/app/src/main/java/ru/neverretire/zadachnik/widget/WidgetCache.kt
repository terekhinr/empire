package ru.neverretire.zadachnik.widget

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import ru.neverretire.zadachnik.data.WidgetTask

object WidgetCache {
    private const val PREFS = "zadachnik_widget"
    private const val KEY = "tasks_json"
    private const val KEY_FILTER = "filter_key"

    fun save(context: Context, tasks: List<WidgetTask>, filter: WidgetFilter) {
        val arr = JSONArray()
        tasks.forEach { t ->
            arr.put(
                JSONObject()
                    .put("id", t.id)
                    .put("title", t.title)
                    .put("dueDate", t.dueDate)
                    .put("overdue", t.overdue),
            )
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY, arr.toString())
            .putString(KEY_FILTER, filter.key)
            .apply()
    }

    fun load(context: Context): List<WidgetTask> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY, null) ?: return emptyList()
        val filter = WidgetFilter.fromKey(prefs.getString(KEY_FILTER, WidgetFilter.WEEK.key))
        return try {
            val arr = JSONArray(raw)
            val items = (0 until arr.length()).map { i ->
                val o = arr.getJSONObject(i)
                WidgetTask(
                    id = o.getLong("id"),
                    title = o.getString("title"),
                    dueDate = o.optString("dueDate", "").takeIf { it.isNotBlank() && it != "null" },
                    overdue = o.optBoolean("overdue"),
                )
            }
            if (filter == WidgetFilter.SOMEDAY || filter == WidgetFilter.OVERDUE || filter == WidgetFilter.INBOX) {
                return items
            }
            buildList {
                val overdue = items.filter { it.overdue }
                val upcoming = items.filter { !it.overdue }
                if (overdue.isNotEmpty()) {
                    add(WidgetTask(id = -1L, title = "Просрочено", dueDate = null, overdue = true))
                    addAll(overdue)
                }
                if (upcoming.isNotEmpty()) {
                    if (overdue.isNotEmpty()) {
                        add(WidgetTask(id = -2L, title = "Ближайшие", dueDate = null, overdue = false))
                    }
                    addAll(upcoming)
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }
}

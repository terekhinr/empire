package ru.neverretire.zadachnik.data

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import ru.neverretire.zadachnik.BuildConfig
import ru.neverretire.zadachnik.widget.WidgetFilter
import java.time.LocalDate
import java.util.concurrent.TimeUnit

data class WidgetTask(
    val id: Long,
    val title: String,
    val dueDate: String?,
    val overdue: Boolean,
)

class PlanningApi(private val token: String) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    private val base = BuildConfig.BASE_URL.trimEnd('/') + BuildConfig.API_PATH

    fun fetchTasks(filter: WidgetFilter): List<WidgetTask> {
        if (filter == WidgetFilter.SOMEDAY) {
            return fetchSomeday()
        }
        val req = Request.Builder()
            .url("$base/tasks")
            .header("X-Planning-Token", token)
            .get()
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("tasks_http_${resp.code}")
            val body = resp.body?.string().orEmpty()
            val root = JSONObject(body)
            val arr: JSONArray = when {
                root.has("tasks") -> root.getJSONArray("tasks")
                else -> JSONArray(body)
            }
            val today = LocalDate.now()
            val weekEnd = today.plusDays(7)
            val out = mutableListOf<WidgetTask>()
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val status = o.optString("status")
                if (status == "done" || status == "cancelled" || status == "archived") continue
                val dueRaw = o.optString("due_date", "")
                val due = dueRaw.takeIf { it.isNotBlank() && it != "null" }
                val projectId = if (o.has("project_id") && !o.isNull("project_id")) o.optLong("project_id") else null
                val overdue = due != null && runCatching { LocalDate.parse(due) < today }.getOrDefault(false)
                val inToday = due == today.isoformat()
                val inWeek = due != null && runCatching { !LocalDate.parse(due).isAfter(weekEnd) }.getOrDefault(false)
                val include = when (filter) {
                    WidgetFilter.WEEK -> overdue || inWeek
                    WidgetFilter.TODAY -> overdue || inToday
                    WidgetFilter.OVERDUE -> overdue
                    WidgetFilter.INBOX -> projectId == null && (due == null || inWeek || overdue)
                    WidgetFilter.SOMEDAY -> false
                }
                if (!include) continue
                if (filter != WidgetFilter.INBOX && due == null) continue
                out += WidgetTask(
                    id = o.getLong("id"),
                    title = o.optString("title"),
                    dueDate = due,
                    overdue = overdue,
                )
            }
            return out.sortedWith(
                compareByDescending<WidgetTask> { it.overdue }
                    .thenBy { it.dueDate ?: "9999" }
                    .thenBy { it.title },
            )
        }
    }

    private fun fetchSomeday(): List<WidgetTask> {
        val req = Request.Builder()
            .url("$base/tasks/someday")
            .header("X-Planning-Token", token)
            .get()
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("someday_http_${resp.code}")
            val root = JSONObject(resp.body?.string().orEmpty())
            val arr = root.optJSONArray("tasks") ?: JSONArray()
            return (0 until arr.length()).map { i ->
                val o = arr.getJSONObject(i)
                WidgetTask(
                    id = o.getLong("id"),
                    title = o.optString("title"),
                    dueDate = null,
                    overdue = false,
                )
            }
        }
    }

    fun complete(taskId: Long) {
        val req = Request.Builder()
            .url("$base/tasks/$taskId/complete")
            .header("X-Planning-Token", token)
            .post(ByteArray(0).toRequestBody(null))
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("complete_http_${resp.code}")
        }
    }
}

private fun LocalDate.isoformat(): String = toString()

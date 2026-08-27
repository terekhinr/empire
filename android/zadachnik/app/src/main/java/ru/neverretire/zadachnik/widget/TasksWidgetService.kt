package ru.neverretire.zadachnik.widget

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.view.View
import android.widget.RemoteViews
import android.widget.RemoteViewsService
import ru.neverretire.zadachnik.R
import ru.neverretire.zadachnik.data.WidgetTask
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

class TasksWidgetService : RemoteViewsService() {
    override fun onGetViewFactory(intent: Intent): RemoteViewsFactory =
        Factory(applicationContext)
}

private class Factory(private val context: Context) : RemoteViewsService.RemoteViewsFactory {
    private var items: List<WidgetTask> = emptyList()
    private val dateFmt = DateTimeFormatter.ofPattern("d MMMM", Locale("ru"))

    override fun onCreate() {}

    override fun onDataSetChanged() {
        items = WidgetCache.load(context)
    }

    override fun onDestroy() {
        items = emptyList()
    }

    override fun getCount(): Int = items.size

    override fun getViewAt(position: Int): RemoteViews {
        val item = items.getOrNull(position) ?: return RemoteViews(context.packageName, R.layout.widget_task_row)
        if (item.id < 0) {
            val header = RemoteViews(context.packageName, R.layout.widget_section_header)
            header.setTextViewText(R.id.section_title, item.title)
            return header
        }
        val row = RemoteViews(context.packageName, R.layout.widget_task_row)
        row.setTextViewText(R.id.task_title, item.title)
        val due = item.dueDate?.let {
            try {
                LocalDate.parse(it).format(dateFmt)
            } catch (_: Exception) {
                it
            }
        }.orEmpty()
        row.setTextViewText(R.id.task_due, due)
        row.setTextColor(
            R.id.task_due,
            if (item.overdue) Color.parseColor("#F87171") else Color.parseColor("#94A3B8"),
        )
        row.setViewVisibility(R.id.task_check, View.VISIBLE)

        // ○ → complete; title/due/row → open task (same list template, different extras)
        val complete = Intent()
            .putExtra(TasksWidgetProvider.EXTRA_TASK_ID, item.id)
            .putExtra(TasksWidgetProvider.EXTRA_ITEM_ACTION, TasksWidgetProvider.ITEM_COMPLETE)
        val open = Intent()
            .putExtra(TasksWidgetProvider.EXTRA_TASK_ID, item.id)
            .putExtra(TasksWidgetProvider.EXTRA_ITEM_ACTION, TasksWidgetProvider.ITEM_OPEN)

        row.setOnClickFillInIntent(R.id.task_check, complete)
        row.setOnClickFillInIntent(R.id.task_title, open)
        row.setOnClickFillInIntent(R.id.task_due, open)
        row.setOnClickFillInIntent(R.id.task_row, open)
        return row
    }

    override fun getLoadingView(): RemoteViews? = null
    override fun getViewTypeCount(): Int = 2
    override fun getItemId(position: Int): Long = items.getOrNull(position)?.id ?: position.toLong()
    override fun hasStableIds(): Boolean = true
}

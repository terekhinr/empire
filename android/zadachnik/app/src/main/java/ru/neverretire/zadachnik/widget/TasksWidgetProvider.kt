package ru.neverretire.zadachnik.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.RemoteViews
import ru.neverretire.zadachnik.BuildConfig
import ru.neverretire.zadachnik.MainActivity
import ru.neverretire.zadachnik.R
import ru.neverretire.zadachnik.data.PlanningApi
import ru.neverretire.zadachnik.data.TokenStore
import kotlin.concurrent.thread

class TasksWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        appWidgetIds.forEach { updateAppWidget(context, appWidgetManager, it) }
        refreshCache(context, appWidgetIds)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        val mgr = AppWidgetManager.getInstance(context)
        val ids = mgr.getAppWidgetIds(ComponentName(context, TasksWidgetProvider::class.java))
        when (intent.action) {
            ACTION_REFRESH, AppWidgetManager.ACTION_APPWIDGET_UPDATE -> {
                refreshCache(context, ids)
                ids.forEach { updateAppWidget(context, mgr, it) }
                mgr.notifyAppWidgetViewDataChanged(ids, R.id.widget_list)
            }
            ACTION_CYCLE_FILTER -> {
                val wid = intent.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID)
                if (wid != AppWidgetManager.INVALID_APPWIDGET_ID) {
                    val next = WidgetFilter.cycle(WidgetPrefs.getFilter(context, wid))
                    WidgetPrefs.setFilter(context, wid, next)
                    refreshCache(context, intArrayOf(wid))
                    updateAppWidget(context, mgr, wid)
                    mgr.notifyAppWidgetViewDataChanged(wid, R.id.widget_list)
                }
            }
            ACTION_COMPLETE, ACTION_ITEM -> {
                val id = intent.getLongExtra(EXTRA_TASK_ID, -1L)
                val itemAction = intent.getStringExtra(EXTRA_ITEM_ACTION) ?: ITEM_COMPLETE
                if (id <= 0) return
                if (itemAction == ITEM_OPEN || intent.action == ACTION_OPEN) {
                    val open = Intent(context, MainActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                        putExtra(
                            MainActivity.EXTRA_PATH,
                            BuildConfig.TASKS_PATH + "?task=$id",
                        )
                    }
                    context.startActivity(open)
                    return
                }
                thread {
                    try {
                        val token = TokenStore(context).token ?: return@thread
                        PlanningApi(token).complete(id)
                    } catch (_: Exception) {
                    }
                    requestRefresh(context)
                }
            }
            ACTION_OPEN -> {
                val id = intent.getLongExtra(EXTRA_TASK_ID, -1L)
                if (id <= 0) return
                val open = Intent(context, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    putExtra(MainActivity.EXTRA_PATH, BuildConfig.TASKS_PATH + "?task=$id")
                }
                context.startActivity(open)
            }
        }
    }

    companion object {
        const val ACTION_REFRESH = "ru.neverretire.zadachnik.ACTION_REFRESH"
        const val ACTION_COMPLETE = "ru.neverretire.zadachnik.ACTION_COMPLETE"
        const val ACTION_ITEM = "ru.neverretire.zadachnik.ACTION_ITEM"
        const val ACTION_OPEN = "ru.neverretire.zadachnik.ACTION_OPEN"
        const val ACTION_CYCLE_FILTER = "ru.neverretire.zadachnik.ACTION_CYCLE_FILTER"
        const val EXTRA_TASK_ID = "task_id"
        const val EXTRA_ITEM_ACTION = "item_action"
        const val ITEM_COMPLETE = "complete"
        const val ITEM_OPEN = "open"

        fun requestRefresh(context: Context) {
            context.sendBroadcast(
                Intent(context, TasksWidgetProvider::class.java).setAction(ACTION_REFRESH),
            )
        }

        private fun refreshCache(context: Context, appWidgetIds: IntArray) {
            thread {
                try {
                    val token = TokenStore(context).token ?: return@thread
                    val api = PlanningApi(token)
                    // Use first widget filter or week default for shared cache keyed per filter
                    val filter = if (appWidgetIds.isNotEmpty()) {
                        WidgetPrefs.getFilter(context, appWidgetIds[0])
                    } else {
                        WidgetFilter.WEEK
                    }
                    val tasks = api.fetchTasks(filter)
                    WidgetCache.save(context, tasks, filter)
                    val mgr = AppWidgetManager.getInstance(context)
                    mgr.notifyAppWidgetViewDataChanged(appWidgetIds, R.id.widget_list)
                } catch (_: Exception) {
                }
            }
        }

        private fun updateAppWidget(context: Context, mgr: AppWidgetManager, appWidgetId: Int) {
            val filter = WidgetPrefs.getFilter(context, appWidgetId)
            val views = RemoteViews(context.packageName, R.layout.widget_tasks)
            views.setTextViewText(R.id.widget_title, filter.title + " ▾")

            val openApp = PendingIntent.getActivity(
                context,
                appWidgetId * 10,
                Intent(context, MainActivity::class.java),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

            val cycle = PendingIntent.getBroadcast(
                context,
                appWidgetId * 10 + 1,
                Intent(context, TasksWidgetProvider::class.java)
                    .setAction(ACTION_CYCLE_FILTER)
                    .putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            views.setOnClickPendingIntent(R.id.widget_title, cycle)

            val addIntent = Intent(context, MainActivity::class.java).apply {
                putExtra(MainActivity.EXTRA_PATH, BuildConfig.TASKS_PATH + "?action=new")
            }
            val addPi = PendingIntent.getActivity(
                context,
                appWidgetId * 10 + 2,
                addIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            views.setOnClickPendingIntent(R.id.widget_add, addPi)

            val refresh = PendingIntent.getBroadcast(
                context,
                appWidgetId * 10 + 3,
                Intent(context, TasksWidgetProvider::class.java).setAction(ACTION_REFRESH),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            views.setOnClickPendingIntent(R.id.widget_more, refresh)

            val svc = Intent(context, TasksWidgetService::class.java).apply {
                putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, appWidgetId)
                data = Uri.parse(toUri(Intent.URI_INTENT_SCHEME))
            }
            views.setRemoteAdapter(R.id.widget_list, svc)
            views.setEmptyView(R.id.widget_list, R.id.widget_empty)

            val clickTemplate = Intent(context, TasksWidgetProvider::class.java).setAction(ACTION_ITEM)
            val clickPi = PendingIntent.getBroadcast(
                context,
                appWidgetId * 10 + 4,
                clickTemplate,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
            )
            views.setPendingIntentTemplate(R.id.widget_list, clickPi)

            // Long-press title area also opens app via empty space — keep openApp on empty
            views.setOnClickPendingIntent(R.id.widget_empty, openApp)

            mgr.updateAppWidget(appWidgetId, views)
        }
    }
}

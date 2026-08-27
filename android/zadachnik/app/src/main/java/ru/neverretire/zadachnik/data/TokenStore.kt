package ru.neverretire.zadachnik.data

import android.content.Context

class TokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("zadachnik", Context.MODE_PRIVATE)

    var token: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) {
            prefs.edit().putString(KEY_TOKEN, value).apply()
        }

    companion object {
        private const val KEY_TOKEN = "planning_token"
    }
}

package ru.neverretire.zal

import android.app.Application
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import ru.neverretire.zal.data.SeedData

/**
 * No WorkManager Configuration.Provider — on Xiaomi dual-init of WM is a common crash.
 * Sync is optional and only enqueued when Supabase is configured.
 */
class ZalApp : Application() {
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        // Defer heavy seed off the critical path slightly so first Activity can draw.
        appScope.launch {
            try {
                SeedData.ensureImported(this@ZalApp)
            } catch (t: Throwable) {
                Log.e("ZalApp", "seed failed", t)
            }
        }
    }
}

package ru.neverretire.zal

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.MonitorWeight
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.launch
import ru.neverretire.zal.data.GymRepository
import ru.neverretire.zal.sync.SyncScheduler
import ru.neverretire.zal.ui.cloud.CloudScreen
import ru.neverretire.zal.ui.components.rememberHoldTimerState
import ru.neverretire.zal.ui.components.rememberRestTimerState
import ru.neverretire.zal.ui.diary.DiaryScreen
import ru.neverretire.zal.ui.meas.MeasScreen
import ru.neverretire.zal.ui.program.ProgramScreen
import ru.neverretire.zal.ui.stats.StatsScreen
import ru.neverretire.zal.ui.theme.ZalColors
import ru.neverretire.zal.ui.theme.ZalTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            enableEdgeToEdge()
        } catch (t: Throwable) {
            Log.w("Zal", "enableEdgeToEdge skipped", t)
        }
        val repo = GymRepository(applicationContext)
        try {
            SyncScheduler.enqueue(applicationContext)
        } catch (t: Throwable) {
            Log.w("Zal", "sync enqueue skipped", t)
        }

        setContent {
            ZalTheme {
                val nav = rememberNavController()
                val snack = remember { SnackbarHostState() }
                val scope = rememberCoroutineScope()
                val restTimer = rememberRestTimerState()
                val holdTimer = rememberHoldTimerState()
                val backStack by nav.currentBackStackEntryAsState()
                val route = backStack?.destination?.route ?: "program"

                fun msg(t: String) {
                    scope.launch {
                        runCatching { snack.showSnackbar(t) }
                    }
                }

                fun go(dest: String) {
                    if (route == dest) return
                    nav.navigate(dest) {
                        launchSingleTop = true
                        popUpTo("program") { saveState = true }
                        restoreState = true
                    }
                }

                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    containerColor = ZalColors.Bg,
                    snackbarHost = { SnackbarHost(snack) },
                    bottomBar = {
                        NavigationBar(containerColor = ZalColors.Surface) {
                            NavigationBarItem(
                                selected = route == "program",
                                onClick = { go("program") },
                                icon = { Icon(Icons.Default.FitnessCenter, contentDescription = null) },
                                label = { Text("Программа") },
                            )
                            NavigationBarItem(
                                selected = route == "diary",
                                onClick = { go("diary") },
                                icon = { Icon(Icons.AutoMirrored.Filled.MenuBook, contentDescription = null) },
                                label = { Text("Дневник") },
                            )
                            NavigationBarItem(
                                selected = route == "meas",
                                onClick = { go("meas") },
                                icon = { Icon(Icons.Default.MonitorWeight, contentDescription = null) },
                                label = { Text("Замеры") },
                            )
                            NavigationBarItem(
                                selected = route == "stats",
                                onClick = { go("stats") },
                                icon = { Icon(Icons.Default.BarChart, contentDescription = null) },
                                label = { Text("Статистика") },
                            )
                            NavigationBarItem(
                                selected = route == "cloud",
                                onClick = { go("cloud") },
                                icon = { Icon(Icons.Default.Cloud, contentDescription = null) },
                                label = { Text("Облако") },
                            )
                        }
                    },
                ) { padding ->
                    NavHost(
                        navController = nav,
                        startDestination = "program",
                        modifier = Modifier.padding(padding),
                    ) {
                        composable("program") {
                            ProgramScreen(repo, restTimer, holdTimer, ::msg)
                        }
                        composable("diary") {
                            DiaryScreen(repo, ::msg)
                        }
                        composable("meas") {
                            MeasScreen(repo, ::msg)
                        }
                        composable("stats") {
                            StatsScreen(repo)
                        }
                        composable("cloud") {
                            CloudScreen(repo, ::msg)
                        }
                    }
                }
            }
        }
    }
}

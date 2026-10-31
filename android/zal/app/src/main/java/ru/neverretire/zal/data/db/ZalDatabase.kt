package ru.neverretire.zal.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        StrengthLogEntity::class,
        MeasurementEntity::class,
        CustomExerciseEntity::class,
        SettingEntity::class,
    ],
    version = 1,
    exportSchema = false,
)
abstract class ZalDatabase : RoomDatabase() {
    abstract fun gymDao(): GymDao

    companion object {
        @Volatile private var instance: ZalDatabase? = null

        fun get(context: Context): ZalDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext,
                    ZalDatabase::class.java,
                    "zal.db",
                ).fallbackToDestructiveMigration().build().also { instance = it }
            }
    }
}

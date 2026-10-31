package ru.neverretire.zal.data.db

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "strength_logs",
    indices = [Index("loggedOn"), Index("exerciseKey"), Index("uuid")],
)
data class StrengthLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uuid: String,
    val loggedOn: String,
    val exerciseKey: String,
    val exerciseLabel: String? = null,
    val weightKg: Double = 0.0,
    val reps: Int = 0,
    val sets: Int = 1,
    val note: String? = null,
    val createdAt: String,
    val updatedAt: String,
    val deleted: Boolean = false,
    val dirty: Boolean = true,
)

@Entity(
    tableName = "measurements",
    indices = [Index("measuredOn"), Index("uuid")],
)
data class MeasurementEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uuid: String,
    val measuredOn: String,
    val weightKg: Double? = null,
    val waistCm: Double? = null,
    val bicepsRCm: Double? = null,
    val bicepsLCm: Double? = null,
    val legsCm: Double? = null,
    val note: String? = null,
    val source: String = "android",
    val createdAt: String,
    val updatedAt: String,
    val deleted: Boolean = false,
    val dirty: Boolean = true,
)

@Entity(tableName = "custom_exercises")
data class CustomExerciseEntity(
    @PrimaryKey val exerciseKey: String,
    val label: String,
    val createdAt: String,
)

@Entity(tableName = "settings")
data class SettingEntity(
    @PrimaryKey val key: String,
    val value: String,
)

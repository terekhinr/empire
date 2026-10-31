package ru.neverretire.zal.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface GymDao {
    @Query("SELECT * FROM strength_logs WHERE deleted = 0 ORDER BY loggedOn DESC, id DESC LIMIT :limit")
    fun observeLogs(limit: Int = 100): Flow<List<StrengthLogEntity>>

    @Query("SELECT * FROM strength_logs WHERE loggedOn = :day AND deleted = 0 ORDER BY id")
    suspend fun logsForDay(day: String): List<StrengthLogEntity>

    @Query("SELECT * FROM strength_logs WHERE dirty = 1")
    suspend fun dirtyLogs(): List<StrengthLogEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertLog(row: StrengthLogEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertLogs(rows: List<StrengthLogEntity>)

    @Query("UPDATE strength_logs SET deleted = 1, dirty = 1, updatedAt = :updatedAt WHERE id = :id")
    suspend fun softDeleteLog(id: Long, updatedAt: String)

    @Query("DELETE FROM strength_logs WHERE loggedOn = :day AND deleted = 0 AND note LIKE :pattern")
    suspend fun deleteProgramLogsForDay(day: String, pattern: String)

    @Query("SELECT * FROM measurements WHERE deleted = 0 ORDER BY measuredOn DESC, id DESC LIMIT :limit")
    fun observeMeasurements(limit: Int = 100): Flow<List<MeasurementEntity>>

    @Query("SELECT * FROM measurements WHERE dirty = 1")
    suspend fun dirtyMeasurements(): List<MeasurementEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertMeasurement(row: MeasurementEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertMeasurements(rows: List<MeasurementEntity>)

    @Query("UPDATE measurements SET deleted = 1, dirty = 1, updatedAt = :updatedAt WHERE id = :id")
    suspend fun softDeleteMeasurement(id: Long, updatedAt: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertExercise(row: CustomExerciseEntity)

    @Query("SELECT * FROM custom_exercises")
    suspend fun allExercises(): List<CustomExerciseEntity>

    @Query("SELECT value FROM settings WHERE key = :key LIMIT 1")
    suspend fun getSetting(key: String): String?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun putSetting(row: SettingEntity)

    @Update
    suspend fun updateLog(row: StrengthLogEntity)

    @Update
    suspend fun updateMeasurement(row: MeasurementEntity)

    @Query("SELECT uuid FROM strength_logs")
    suspend fun allLogUuids(): List<String>

    @Query("SELECT uuid FROM measurements")
    suspend fun allMeasurementUuids(): List<String>

    @Query("SELECT * FROM strength_logs WHERE uuid = :uuid LIMIT 1")
    suspend fun logByUuid(uuid: String): StrengthLogEntity?

    @Query("SELECT * FROM measurements WHERE uuid = :uuid LIMIT 1")
    suspend fun measurementByUuid(uuid: String): MeasurementEntity?
}

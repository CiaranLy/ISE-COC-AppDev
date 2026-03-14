package com.pong.mobile.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface MatchResultDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(result: MatchResult): Long

    @Query("SELECT * FROM match_results ORDER BY timestamp DESC")
    fun getAll(): Flow<List<MatchResult>>

    @Query("SELECT MAX(timestamp) FROM match_results")
    suspend fun getLatestTimestamp(): Long?

    @Query("SELECT * FROM match_results WHERE id = :id")
    fun getById(id: Int): Flow<MatchResult?>
}

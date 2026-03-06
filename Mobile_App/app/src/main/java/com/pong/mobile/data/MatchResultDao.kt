package com.pong.mobile.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface MatchResultDao {
    @Insert
    suspend fun insert(result: MatchResult)

    @Query("SELECT * FROM match_results ORDER BY timestamp DESC")
    fun getAll(): Flow<List<MatchResult>>
}

package com.pong.mobile.data

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "match_results",
    indices = [Index(value = ["matchId"], unique = true)]
)
data class MatchResult(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val gameMode: String,
    val playerScore: Int,
    val opponentScore: Int,
    val won: Boolean,
    val timestamp: Long,
    val matchId: String
)

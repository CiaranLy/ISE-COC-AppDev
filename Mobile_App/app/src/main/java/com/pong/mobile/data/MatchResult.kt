package com.pong.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "match_results")
data class MatchResult(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val gameMode: String,
    val playerScore: Int,
    val opponentScore: Int,
    val won: Boolean,
    val timestamp: Long,
    val matchId: String
)

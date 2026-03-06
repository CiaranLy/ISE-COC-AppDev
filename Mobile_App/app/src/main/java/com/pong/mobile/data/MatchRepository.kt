package com.pong.mobile.data

import kotlinx.coroutines.flow.Flow

class MatchRepository(private val dao: MatchResultDao) {
    val allMatches: Flow<List<MatchResult>> = dao.getAll()

    suspend fun insert(result: MatchResult) {
        dao.insert(result)
    }
}

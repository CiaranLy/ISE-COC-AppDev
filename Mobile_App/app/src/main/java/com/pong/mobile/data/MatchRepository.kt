package com.pong.mobile.data

import kotlinx.coroutines.flow.Flow

class MatchRepository(private val dao: MatchResultDao) {
    val allMatches: Flow<List<MatchResult>> = dao.getAll()

    suspend fun insert(result: MatchResult): Long {
        return dao.insert(result)
    }

    suspend fun getLatestTimestamp(): Long? {
        return dao.getLatestTimestamp()
    }

    fun getById(id: Int): Flow<MatchResult?> {
        return dao.getById(id)
    }
}

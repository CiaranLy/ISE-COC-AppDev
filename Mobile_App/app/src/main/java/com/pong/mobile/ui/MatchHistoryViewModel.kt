/*
 * This file was generated with the assistance of an AI coding agent.
 * Prompt: Migrate the MatchSyncService polling out of the ViewModel and into a WorkManager
 * PeriodicWorkRequest.
 */
package com.pong.mobile.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pong.mobile.data.MatchDatabase
import com.pong.mobile.data.MatchRepository
import com.pong.mobile.data.MatchResult
import com.pong.mobile.data.MatchSyncService
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.workDataOf
import java.util.concurrent.TimeUnit

class MatchHistoryViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = MatchRepository(
        MatchDatabase.getDatabase(application.applicationContext).matchResultDao()
    )
    private val syncService = MatchSyncService()
    private val workManager = WorkManager.getInstance(application)

    val isSyncing: StateFlow<Boolean> = workManager.getWorkInfosForUniqueWorkFlow(SYNC_WORK_NAME)
        .map { workInfos ->
            workInfos.any { it.state == WorkInfo.State.RUNNING }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), false)

    val matches: StateFlow<List<MatchResult>> = repository.allMatches.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = emptyList()
    )

    fun saveMatch(result: MatchResult, deviceId: String) {
        viewModelScope.launch {
            repository.insert(result)
            syncService.uploadMatch(deviceId, result)
        }
    }

    fun startSyncingMatches(deviceId: String) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncRequest = PeriodicWorkRequestBuilder<com.pong.mobile.data.MatchSyncWorker>(15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .setInputData(workDataOf(com.pong.mobile.data.MatchSyncWorker.KEY_DEVICE_ID to deviceId))
            .build()

        workManager.enqueueUniquePeriodicWork(
            SYNC_WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            syncRequest
        )
    }

    companion object {
        private const val SYNC_WORK_NAME = "match_sync_work"
    }

    fun getMatchById(id: Int): Flow<MatchResult?> {
        return repository.getById(id)
    }
}

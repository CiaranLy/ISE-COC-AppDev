/*
 * This file was generated with the assistance of an AI coding agent.
 * Prompt: Migrate the MatchSyncService polling out of the ViewModel and into a WorkManager
 * PeriodicWorkRequest.
 */
package com.pong.mobile.data

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import android.util.Log

class MatchSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        Log.i(TAG, "Starting MatchSyncWorker")
        val deviceId = inputData.getString(KEY_DEVICE_ID)

        if (deviceId.isNullOrBlank()) {
            Log.e(TAG, "Device ID is missing, failing worker")
            return Result.failure()
        }

        return try {
            val repository = MatchRepository(MatchDatabase.getDatabase(applicationContext).matchResultDao())
            val syncService = MatchSyncService()
            
            val latestTimestamp = repository.getLatestTimestamp() ?: 0L
            val cloudMatches = syncService.downloadMatches(deviceId, latestTimestamp)
            
            if (cloudMatches.isNotEmpty()) {
                Log.i(TAG, "Downloaded ${cloudMatches.size} matches from cloud")
                cloudMatches.forEach { match ->
                    repository.insert(match)
                }
            } else {
                Log.d(TAG, "No new matches found in the cloud")
            }
            
            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "MatchSyncWorker failed", e)
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "MatchSyncWorker"
        const val KEY_DEVICE_ID = "device_id"
    }
}

/*
 * This file was generated with the assistance of an AI coding agent.
 * Prompt: Migrate the MatchSyncService polling out of the ViewModel and into a WorkManager
 * PeriodicWorkRequest.
 */
package com.pong.mobile.data

import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore
import kotlinx.coroutines.tasks.await

class MatchSyncService {
    private val firestore = FirebaseFirestore.getInstance()

    suspend fun uploadMatch(deviceId: String, match: MatchResult) {
        if (deviceId.isBlank() || deviceId == "unknown") {
            Log.w(TAG, "Cannot upload match: invalid device ID")
            return
        }

        val matchData = hashMapOf(
            "gameMode" to match.gameMode,
            "playerScore" to match.playerScore,
            "opponentScore" to match.opponentScore,
            "won" to match.won,
            "timestamp" to match.timestamp,
            "matchId" to match.matchId
        )

        try {
            firestore.collection(COLLECTION_USER_MATCHES)
                .document(deviceId)
                .collection(SUBCOLLECTION_MATCHES)
                .document(match.matchId)
                .set(matchData)
                .await()
            Log.i(TAG, "Uploaded match ${match.matchId} for device $deviceId")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to upload match ${match.matchId}", e)
        }
    }

    suspend fun downloadMatches(deviceId: String, afterTimestamp: Long = 0L): List<MatchResult> {
        if (deviceId.isBlank() || deviceId == "unknown") {
            Log.w(TAG, "Cannot download matches: invalid device ID")
            return emptyList()
        }

        return try {
            val snapshot = firestore.collection(COLLECTION_USER_MATCHES)
                .document(deviceId)
                .collection(SUBCOLLECTION_MATCHES)
                .whereGreaterThan("timestamp", afterTimestamp)
                .get()
                .await()

            snapshot.documents.mapNotNull { doc ->
                try {
                    MatchResult(
                        gameMode = doc.getString("gameMode") ?: return@mapNotNull null,
                        playerScore = doc.getLong("playerScore")?.toInt() ?: 0,
                        opponentScore = doc.getLong("opponentScore")?.toInt() ?: 0,
                        won = doc.getBoolean("won") ?: false,
                        timestamp = doc.getLong("timestamp") ?: 0L,
                        matchId = doc.getString("matchId") ?: doc.id
                    )
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to parse match document ${doc.id}", e)
                    null
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to download matches", e)
            emptyList()
        }
    }

    companion object {
        private const val TAG = "MatchSyncService"
        const val COLLECTION_USER_MATCHES = "user_matches"
        const val SUBCOLLECTION_MATCHES = "matches"
    }
}

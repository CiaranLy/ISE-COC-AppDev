package com.pong.mobile.telemetry

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore
import com.pong.mobile.game.GameState
import com.pong.mobile.game.PlayerId
import java.io.Closeable
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Writes telemetry to Firebase Firestore.
 * - Session start: creates game_sessions/{sessionId} doc
 * - Snapshots: adds docs to game_sessions/{sessionId}/snapshots/ (latencyMs, paddleY, collisionCount, timestampMs)
 * - Session end: updates session doc with endedAt, durationMs, final scores
 */
class TelemetryService : Closeable {
    private val firestore = FirebaseFirestore.getInstance()
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private var sessionId: String? = null
    private var gameStartTimeMs: Long = 0L

    fun startSession(matchId: String, gameMode: String, playerId: String, deviceId: String) {
        sessionId = matchId
        snapshotCount = 0
        val id = matchId
        gameStartTimeMs = System.currentTimeMillis()

        val sessionData =
                hashMapOf(
                        "sessionId" to id,
                        "gameMode" to gameMode,
                        "playerId" to playerId,
                        "deviceId" to deviceId,
                        "startedAt" to com.google.firebase.Timestamp.now()
                )

        serviceScope.launch {
            try {
                firestore.collection(COLLECTION_GAME_SESSIONS).document(id).set(sessionData)
                Log.i(TAG, "Telemetry session started: $id ($gameMode) for player $playerId on device $deviceId")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to create telemetry session", e)
            }
        }
    }

    private var snapshotCount = 0

    fun recordSnapshot(collisionCount: Int, latencyMs: Long, paddleY: Float) {
        val id = sessionId ?: run {
            Log.w(TAG, "recordSnapshot called but sessionId is null - skipping")
            return
        }

        val timestampMs = System.currentTimeMillis() - gameStartTimeMs
        val snapshotData =
                hashMapOf(
                        "timestampMs" to timestampMs,
                        "collisionCount" to collisionCount,
                        "latencyMs" to latencyMs,
                        "paddleY" to paddleY
                )

        serviceScope.launch {
            try {
                firestore
                        .collection(COLLECTION_GAME_SESSIONS)
                        .document(id)
                        .collection(SUBCOLLECTION_SNAPSHOTS)
                        .add(snapshotData)
                snapshotCount++
                if (snapshotCount <= 3 || snapshotCount % 10 == 0) {
                    Log.i(TAG, "Telemetry snapshot #$snapshotCount written to Firebase for session $id")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to record telemetry snapshot", e)
            }
        }
    }

    fun endSession(finalState: GameState, localPlayerId: PlayerId) {
        val id = sessionId ?: return

        val durationMs = System.currentTimeMillis() - gameStartTimeMs
        val localPlayerPaddleHits =
                when (localPlayerId) {
                    PlayerId.Player1 -> finalState.player1PaddleHits
                    PlayerId.Player2 -> finalState.player2PaddleHits
                }

        val updateData =
                hashMapOf<String, Any>(
                        "endedAt" to com.google.firebase.Timestamp.now(),
                        "finalScorePlayer1" to finalState.player1Score,
                        "finalScorePlayer2" to finalState.player2Score,
                        "durationMs" to durationMs,
                        "totalLocalPaddleHits" to localPlayerPaddleHits
                )

        sessionId = null

        serviceScope.launch {
            try {
                firestore.collection(COLLECTION_GAME_SESSIONS).document(id).update(updateData)
                Log.i(TAG, "Telemetry session ended: $id (${durationMs}ms)")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to end telemetry session", e)
            }
        }
    }

    override fun close() {
        Handler(Looper.getMainLooper()).postDelayed({
            serviceScope.cancel()
            sessionId = null
        }, 2000)
    }

    companion object {
        private const val TAG = "TelemetryService"
        private const val COLLECTION_GAME_SESSIONS = "game_sessions"
        private const val SUBCOLLECTION_SNAPSHOTS = "snapshots"
    }
}

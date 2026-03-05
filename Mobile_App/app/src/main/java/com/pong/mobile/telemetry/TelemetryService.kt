package com.pong.mobile.telemetry

import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore
import com.pong.mobile.game.GameState
import com.pong.mobile.game.PlayerId
import java.io.Closeable
import java.util.UUID
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class TelemetryService : Closeable {
    private val firestore = FirebaseFirestore.getInstance()
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private var sessionId: String? = null
    private var gameStartTimeMs: Long = 0L

    fun startSession(gameMode: String, playerId: String, deviceId: String) {
        val id = UUID.randomUUID().toString()
        sessionId = id
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

    fun recordSnapshot(collisionCount: Int, latencyMs: Long, paddleY: Float) {
        val id = sessionId ?: return

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

        serviceScope.launch {
            try {
                firestore.collection(COLLECTION_GAME_SESSIONS).document(id).update(updateData)
                Log.i(TAG, "Telemetry session ended: $id (${durationMs}ms)")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to end telemetry session", e)
            }
        }

        sessionId = null
    }

    override fun close() {
        serviceScope.cancel()
        sessionId = null
    }

    companion object {
        private const val TAG = "TelemetryService"
        private const val COLLECTION_GAME_SESSIONS = "game_sessions"
        private const val SUBCOLLECTION_SNAPSHOTS = "snapshots"
    }
}

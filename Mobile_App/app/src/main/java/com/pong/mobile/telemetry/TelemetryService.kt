package com.pong.mobile.telemetry

import android.util.Log
import com.google.firebase.firestore.FirebaseFirestore
import com.pong.mobile.config.Config
import com.pong.mobile.game.GameState
import com.pong.mobile.game.PlayerId
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.Closeable
import java.time.Instant
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

private val telemetryJson = Json {
    encodeDefaults = true
}

@Serializable
private data class SnapshotPayload(
    val type: String = "snapshot",
    val timestamp: String,
    val latency_ms: Long,
    val paddle_y: Float,
    val collision_count: Int,
    val session_id: String
)

@Serializable
private data class SessionStartPayload(
    val type: String = "session_start",
    val timestamp: String,
    val session_id: String
)

@Serializable
private data class SessionEndPayload(
    val type: String = "session_end",
    val timestamp: String,
    val session_id: String,
    val duration_ms: Long,
    val final_score_player1: Int,
    val final_score_player2: Int
)

class TelemetryService : Closeable {
    private val firestore = FirebaseFirestore.getInstance()
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private var sessionId: String? = null
    private var gameStartTimeMs: Long = 0L
    private var telemetryServer: TelemetryServer? = null

    fun startSession(matchId: String, gameMode: String, playerId: String, deviceId: String) {
        sessionId = matchId
        val id = matchId
        gameStartTimeMs = System.currentTimeMillis()

        telemetryServer = TelemetryServer(Config.current.telemetryPort).also {
            it.isDaemon = true
            it.start()
        }
        Log.i(TAG, "Telemetry server started on port ${Config.current.telemetryPort}")

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

        val payload = SessionStartPayload(
            timestamp = Instant.now().toString(),
            session_id = id
        )
        telemetryServer?.broadcastTelemetry(telemetryJson.encodeToString(payload))
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

        val payload = SnapshotPayload(
            timestamp = Instant.now().toString(),
            latency_ms = latencyMs,
            paddle_y = paddleY,
            collision_count = collisionCount,
            session_id = id
        )
        telemetryServer?.broadcastTelemetry(telemetryJson.encodeToString(payload))
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

        val payload = SessionEndPayload(
            timestamp = Instant.now().toString(),
            session_id = id,
            duration_ms = durationMs,
            final_score_player1 = finalState.player1Score,
            final_score_player2 = finalState.player2Score
        )
        telemetryServer?.broadcastTelemetry(telemetryJson.encodeToString(payload))

        sessionId = null
    }

    override fun close() {
        telemetryServer?.stopGracefully()
        telemetryServer = null
        serviceScope.cancel()
        sessionId = null
    }

    companion object {
        private const val TAG = "TelemetryService"
        private const val COLLECTION_GAME_SESSIONS = "game_sessions"
        private const val SUBCOLLECTION_SNAPSHOTS = "snapshots"
    }
}

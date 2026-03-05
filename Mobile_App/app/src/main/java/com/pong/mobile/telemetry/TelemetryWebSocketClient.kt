package com.pong.mobile.telemetry

import android.util.Log
import com.pong.mobile.config.Config
import java.io.Closeable
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject

class TelemetryWebSocketClient : Closeable {
    private var webSocket: WebSocket? = null
    private var connected = false

    private val client =
            OkHttpClient.Builder()
                    .connectTimeout(CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                    .readTimeout(READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                    .writeTimeout(WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                    .build()

    fun connect() {
        val config = Config.current
        val url = "ws://${config.telemetryWsHost}:${config.telemetryWsPort}"

        val request = Request.Builder().url(url).build()

        webSocket =
                client.newWebSocket(
                        request,
                        object : WebSocketListener() {
                            override fun onOpen(webSocket: WebSocket, response: Response) {
                                connected = true
                                Log.i(TAG, "Connected to collector at $url")
                            }

                            override fun onFailure(
                                    webSocket: WebSocket,
                                    t: Throwable,
                                    response: Response?
                            ) {
                                connected = false
                                Log.d(
                                        TAG,
                                        "Collector not available at $url (this is OK if collector is not running)"
                                )
                            }

                            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                                connected = false
                                Log.i(TAG, "Disconnected from collector: $reason")
                            }
                        }
                )
    }

    fun sendSessionStart(sessionId: String, gameMode: String) {
        val json =
                JSONObject().apply {
                    put(FIELD_TYPE, MSG_TYPE_SESSION_START)
                    put(FIELD_SESSION_ID, sessionId)
                    put(FIELD_GAME_MODE, gameMode)
                }
        send(json)
    }

    fun sendSnapshot(collisionCount: Int, latencyMs: Long, paddleY: Float) {
        val json =
                JSONObject().apply {
                    put(FIELD_TYPE, MSG_TYPE_SNAPSHOT)
                    put(FIELD_COLLISION_COUNT, collisionCount)
                    put(FIELD_LATENCY_MS, latencyMs)
                    put(FIELD_PADDLE_Y, paddleY.toDouble())
                }
        send(json)
    }

    fun sendSessionEnd(
            sessionId: String,
            durationMs: Long,
            finalScorePlayer1: Int,
            finalScorePlayer2: Int,
            totalLocalPaddleHits: Int
    ) {
        val json =
                JSONObject().apply {
                    put(FIELD_TYPE, MSG_TYPE_SESSION_END)
                    put(FIELD_SESSION_ID, sessionId)
                    put(FIELD_DURATION_MS, durationMs)
                    put(FIELD_FINAL_SCORE_PLAYER1, finalScorePlayer1)
                    put(FIELD_FINAL_SCORE_PLAYER2, finalScorePlayer2)
                    put(FIELD_TOTAL_LOCAL_PADDLE_HITS, totalLocalPaddleHits)
                }
        send(json)
    }

    fun disconnect() {
        webSocket?.close(NORMAL_CLOSURE_CODE, "Session ended")
        connected = false
    }

    override fun close() {
        disconnect()
        client.dispatcher.executorService.shutdown()
    }

    private fun send(json: JSONObject) {
        if (!connected) return
        try {
            webSocket?.send(json.toString())
        } catch (e: Exception) {
            Log.d(TAG, "Failed to send telemetry via WebSocket", e)
        }
    }

    companion object {
        private const val TAG = "TelemetryWS"
        private const val CONNECT_TIMEOUT_SECONDS = 5L
        private const val READ_TIMEOUT_SECONDS = 10L
        private const val WRITE_TIMEOUT_SECONDS = 10L
        private const val NORMAL_CLOSURE_CODE = 1000

        private const val FIELD_TYPE = "type"
        private const val FIELD_SESSION_ID = "session_id"
        private const val FIELD_GAME_MODE = "game_mode"
        private const val FIELD_COLLISION_COUNT = "collision_count"
        private const val FIELD_LATENCY_MS = "latency_ms"
        private const val FIELD_PADDLE_Y = "paddle_y"
        private const val FIELD_DURATION_MS = "duration_ms"
        private const val FIELD_FINAL_SCORE_PLAYER1 = "final_score_player1"
        private const val FIELD_FINAL_SCORE_PLAYER2 = "final_score_player2"
        private const val FIELD_TOTAL_LOCAL_PADDLE_HITS = "total_local_paddle_hits"

        private const val MSG_TYPE_SNAPSHOT = "snapshot"
        private const val MSG_TYPE_SESSION_START = "session_start"
        private const val MSG_TYPE_SESSION_END = "session_end"
    }
}

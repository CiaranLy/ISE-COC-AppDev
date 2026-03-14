package com.pong.mobile.game.server.network

import android.util.Log
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId
import com.pong.mobile.game.server.GameServer
import kotlinx.coroutines.*
import org.java_websocket.client.WebSocketClient
import org.java_websocket.handshake.ServerHandshake
import java.net.URI
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.BlockingQueue
import java.util.concurrent.TimeUnit

class NetworkGameClient(
    private val host: String = Constants.LOCALHOST,
    private val port: Int = Constants.DEFAULT_SERVER_PORT
) : GameServer {
    private var webSocketClient: GameWebSocketClient? = null
    private val messageQueue: BlockingQueue<String> = ArrayBlockingQueue(256)
    private var connected = false
    private var localPlayerId: PlayerId? = null
    private var sessionId: String = ""
    @Volatile
    private var gameState: GameState? = null
    @Volatile
    private var lastLatencyMs: Long = 0L
    @Volatile
    private var pingStartTimeMs: Long = 0L
    private val clientScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private inner class GameWebSocketClient(uri: URI, private val queue: BlockingQueue<String>) :
        WebSocketClient(uri) {
        override fun onMessage(message: String) {
            queue.put(message)
        }
        override fun onClose(code: Int, reason: String, remote: Boolean) {}
        override fun onError(ex: Exception) {
            Log.e(TAG, "WebSocket error", ex)
        }
        override fun onOpen(handshakedata: ServerHandshake) {}
    }

    override fun connect(): Boolean {
        if (connected) {
            Log.w(TAG, "Already connected to server")
            return true
        }

        return try {
            val uri = URI("ws://$host:$port")
            Log.i(TAG, "Connecting via WebSocket to $uri")
            webSocketClient = GameWebSocketClient(uri, messageQueue)
            webSocketClient!!.connectBlocking(10, TimeUnit.SECONDS)
            if (webSocketClient?.isOpen != true) {
                Log.e(TAG, "WebSocket connection failed to open")
                disconnect()
                return false
            }

            val sessionStartRaw = messageQueue.poll(10, TimeUnit.SECONDS)
                ?: run {
                    Log.e(TAG, "Did not receive session_start from server")
                    disconnect()
                    return false
                }
            if (!SessionStartPayload.isSessionStart(sessionStartRaw)) {
                Log.e(TAG, "Expected session_start, got: $sessionStartRaw")
                disconnect()
                return false
            }
            val sessionStart = SessionStartPayload.fromJson(sessionStartRaw)
            sessionId = sessionStart.session_id
            Log.i(TAG, "Session started at ${sessionStart.timestamp}, matchId=$sessionId")

            sendRaw(SessionStartPayload.toJson(SessionStartPayload.create(sessionId = sessionId)))

            Log.i(TAG, "Sending ConnectRequest to server")
            sendMessage(NetworkMessage.ConnectRequest())

            Log.i(TAG, "Waiting for ConnectResponse from server")
            val responseRaw = messageQueue.poll(10, TimeUnit.SECONDS)
                ?: run {
                    Log.e(TAG, "Did not receive ConnectResponse from server")
                    disconnect()
                    return false
                }
            val response = MessageSerializer.deserialize(responseRaw)
            Log.i(TAG, "Received response: ${response.messageType}")

            if (response is NetworkMessage.ConnectResponse) {
                localPlayerId = response.playerId
                gameState = response.gameState
                connected = true
                Log.i(TAG, "Connected to server as ${localPlayerId?.name}")

                clientScope.launch {
                    listenForMessages()
                }

                true
            } else if (response is NetworkMessage.Error) {
                Log.e(TAG, "Server error: ${response.error}")
                disconnect()
                false
            } else {
                Log.e(TAG, "Unexpected response type: ${response.messageType}")
                disconnect()
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to connect to server at $host:$port", e)
            disconnect()
            false
        }
    }

    override fun disconnect() {
        connected = false
        try {
            webSocketClient?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing WebSocket", e)
        }
        webSocketClient = null
        messageQueue.clear()
        clientScope.cancel()
        Log.i(TAG, "Disconnected from server")
    }

    override fun startGame(): GameState {
        if (!connected) {
            throw IllegalStateException("Not connected to server")
        }

        val existingGameState = gameState
        if (existingGameState != null) {
            return existingGameState
        }

        sendMessage(NetworkMessage.StartGameRequest())

        return runBlocking {
            var retries = 0
            val maxRetries = Config.current.gameStartRetries
            while (retries < maxRetries) {
                val currentState = gameState
                if (currentState != null) {
                    return@runBlocking currentState
                }
                delay(Config.current.gameStartRetryDelayMs)
                retries++
            }
            throw IllegalStateException("Game state not available after $maxRetries retries")
        }
    }

    override fun updatePaddle(playerId: PlayerId, paddle: Paddle) {
        if (!connected) {
            return
        }

        if (playerId == localPlayerId) {
            sendMessage(NetworkMessage.PaddleUpdate(playerId = playerId, paddle = paddle))
        }
    }

    override fun getGameState(): GameState {
        return gameState ?: throw IllegalStateException("Game not started")
    }

    override fun isConnected(): Boolean {
        return connected && webSocketClient?.isOpen == true
    }

    override fun getLocalPlayerId(): PlayerId {
        return localPlayerId ?: throw IllegalStateException("Not connected to server")
    }

    fun getSessionId(): String = sessionId

    fun getLatencyMs(): Long = lastLatencyMs

    fun measureLatency() {
        if (!connected) return
        pingStartTimeMs = System.currentTimeMillis()
        sendMessage(NetworkMessage.Ping())
    }

    private fun sendMessage(message: NetworkMessage) {
        if (webSocketClient?.isOpen == true) {
            try {
                val json = MessageSerializer.serialize(message)
                webSocketClient!!.send(json)
            } catch (e: Exception) {
                Log.e(TAG, "Error sending message to server", e)
            }
        } else {
            Log.w(TAG, "Cannot send message: WebSocket is not open")
        }
    }

    private fun sendRaw(json: String) {
        if (webSocketClient?.isOpen == true) {
            try {
                webSocketClient!!.send(json)
            } catch (e: Exception) {
                Log.e(TAG, "Error sending raw message to server", e)
            }
        }
    }

    private suspend fun listenForMessages() {
        while (connected && webSocketClient?.isOpen == true) {
            try {
                val line = withContext(Dispatchers.IO) {
                    messageQueue.take()
                }
                if (SessionStartPayload.isSessionStart(line) || !line.contains("\"${Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE}\"")) {
                    continue
                }
                val message = MessageSerializer.deserialize(line)
                handleMessage(message)
            } catch (e: Exception) {
                if (connected) {
                    Log.e(TAG, "Error receiving message from server", e)
                }
                break
            }
        }
        disconnect()
    }

    private fun handleMessage(message: NetworkMessage) {
        when (message) {
            is NetworkMessage.GameStateUpdate -> {
                gameState = message.gameState
            }
            is NetworkMessage.PaddleUpdate -> {
                gameState = gameState?.let { state ->
                    when (message.playerId) {
                        PlayerId.Player1 -> state.copy(player1Paddle = message.paddle)
                        PlayerId.Player2 -> state.copy(player2Paddle = message.paddle)
                    }
                }
            }
            is NetworkMessage.StartGameResponse -> {
                gameState = message.gameState
            }
            is NetworkMessage.Error -> {
                Log.e(TAG, "Server error: ${message.error}")
            }
            is NetworkMessage.Pong -> {
                if (pingStartTimeMs > 0) {
                    lastLatencyMs = System.currentTimeMillis() - pingStartTimeMs
                    pingStartTimeMs = 0L
                }
            }
            else -> {
                Log.w(TAG, "Unexpected message type: ${message.messageType}")
            }
        }
    }

    companion object {
        private const val TAG = "NetworkGameClient"
    }
}

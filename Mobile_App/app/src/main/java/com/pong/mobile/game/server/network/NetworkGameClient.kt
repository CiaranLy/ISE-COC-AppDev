package com.pong.mobile.game.server.network

import android.util.Log
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId
import com.pong.mobile.game.server.GameServer
import kotlinx.coroutines.*
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.Socket

class NetworkGameClient(
    private val host: String = Constants.LOCALHOST,
    private val port: Int = Constants.DEFAULT_SERVER_PORT
) : GameServer {
    private var socket: Socket? = null
    private var reader: BufferedReader? = null
    private var writer: PrintWriter? = null
    private var connected = false
    private var localPlayerId: PlayerId? = null
    @Volatile
    private var gameState: GameState? = null
    private val clientScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun connect(): Boolean {
        if (connected) {
            Log.w(TAG, "Already connected to server")
            return true
        }

        return try {
            Log.i(TAG, "Creating socket connection to $host:$port")
            socket = Socket(host, port)
            reader = BufferedReader(InputStreamReader(socket!!.getInputStream()))
            writer = PrintWriter(socket!!.getOutputStream(), true)

            Log.i(TAG, "Sending ConnectRequest to server")
            sendMessage(NetworkMessage.ConnectRequest())

            Log.i(TAG, "Waiting for ConnectResponse from server")
            val response = receiveMessage()
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
            socket?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing socket", e)
        }
        reader = null
        writer = null
        socket = null
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
        return connected && socket?.isConnected == true
    }

    override fun getLocalPlayerId(): PlayerId {
        return localPlayerId ?: throw IllegalStateException("Not connected to server")
    }

    private fun sendMessage(message: NetworkMessage) {
        if (writer != null) {
            try {
                val json = MessageSerializer.serialize(message)
                writer!!.println(json)
                writer!!.flush()
            } catch (e: Exception) {
                Log.e(TAG, "Error sending message to server", e)
            }
        } else {
            Log.w(TAG, "Cannot send message: writer is null")
        }
    }

    private fun receiveMessage(): NetworkMessage {
        return runBlocking(Dispatchers.IO) {
            val line = reader?.readLine() ?: throw Exception("Connection closed")
            MessageSerializer.deserialize(line)
        }
    }

    private suspend fun listenForMessages() {
        while (connected && socket?.isConnected == true) {
            try {
                val line = reader?.readLine() ?: break
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
            else -> {
                Log.w(TAG, "Unexpected message type: ${message.messageType}")
            }
        }
    }

    companion object {
        private const val TAG = "NetworkGameClient"
    }
}

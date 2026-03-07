package com.pong.mobile.game.server.network

import android.util.Log
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.game.Ball
import com.pong.mobile.game.GameConstants
import com.pong.mobile.game.GameEngine
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId
import com.pong.mobile.game.server.GameServer
import com.pong.mobile.game.util.PaddleUtils
import com.pong.mobile.util.TimeUtils
import kotlinx.coroutines.*
import org.java_websocket.WebSocket
import org.java_websocket.handshake.ClientHandshake
import org.java_websocket.server.WebSocketServer
import java.net.BindException
import java.net.InetSocketAddress
import java.util.UUID
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.BlockingQueue
import java.util.concurrent.ConcurrentHashMap

private const val SESSION_CLOSED_SENTINEL = "__CLOSED__"

class NetworkGameServer(
    private val port: Int = Config.current.gameServerPort,
    private val gameWidth: Float,
    private val gameHeight: Float
) {
    private val matchId: String = UUID.randomUUID().toString()
    private var webSocketServer: GameWebSocketServer? = null
    private val clients = ConcurrentHashMap<PlayerId, ClientConnection>()
    private val messageQueues = ConcurrentHashMap<WebSocket, BlockingQueue<String>>()
    private var gameEngine: GameEngine? = null
    @Volatile
    private var gameState: GameState? = null
    private var isRunning = false
    private val serverScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val gameStateLock = Any()

    private inner class GameWebSocketServer(addr: InetSocketAddress) : WebSocketServer(addr) {
        override fun onOpen(conn: WebSocket, handshake: ClientHandshake) {
            val queue = ArrayBlockingQueue<String>(256)
            messageQueues[conn] = queue
            val sessionStart = SessionStartPayload.toJson(SessionStartPayload.create(sessionId = matchId))
            conn.send(sessionStart)
            Log.d(TAG, "Sent session_start to ${conn.remoteSocketAddress}")
            serverScope.launch {
                handleClientConnection(conn, queue)
            }
        }

        override fun onMessage(conn: WebSocket, message: String) {
            messageQueues[conn]?.put(message)
        }

        override fun onClose(conn: WebSocket, code: Int, reason: String, remote: Boolean) {
            messageQueues.remove(conn)?.put(SESSION_CLOSED_SENTINEL)
        }

        override fun onError(conn: WebSocket?, ex: Exception) {
            Log.e(TAG, "WebSocket error for ${conn?.remoteSocketAddress}", ex)
        }

        override fun onStart() {}
    }

    fun start() {
        if (isRunning) {
            Log.w(TAG, "Server is already running")
            return
        }

        try {
            webSocketServer = GameWebSocketServer(InetSocketAddress(port))
            webSocketServer?.start()
            isRunning = true
            Log.i(TAG, "Network game server (WebSocket) started on port $port")
        } catch (e: BindException) {
            Log.e(TAG, Constants.ERROR_MESSAGE_PORT_IN_USE.format(port), e)
            isRunning = false
            webSocketServer = null
        } catch (e: Exception) {
            Log.e(TAG, Constants.ERROR_MESSAGE_FAILED_START_SERVER.format(port), e)
            isRunning = false
            webSocketServer = null
        }
    }

    fun isRunning(): Boolean {
        return isRunning
    }

    fun stop() {
        isRunning = false
        try {
            webSocketServer?.stop()
        } catch (e: Exception) {
            Log.d(TAG, "Error stopping WebSocket server", e)
        }
        webSocketServer = null
        messageQueues.clear()
        clients.values.forEach { it.close() }
        clients.clear()
        serverScope.cancel()
        Log.i(TAG, "Network game server stopped")
    }

    private suspend fun handleClientConnection(conn: WebSocket, queue: BlockingQueue<String>) {
        val connection = ClientConnection(conn, queue)

        try {
            var line = connection.receiveRaw() ?: return
            if (SessionStartPayload.isSessionStart(line)) {
                Log.d(TAG, "Received client session_start from ${conn.remoteSocketAddress}")
                line = connection.receiveRaw() ?: return
            }
            val connectRequest = MessageSerializer.deserialize(line)
            if (connectRequest !is NetworkMessage.ConnectRequest) {
                connection.sendMessage(NetworkMessage.Error(error = Constants.ERROR_MESSAGE_EXPECTED_CONNECT))
                connection.close()
                return
            }

            val playerId = assignPlayerId()
            if (playerId == null) {
                connection.sendMessage(NetworkMessage.Error(error = Constants.ERROR_MESSAGE_SERVER_FULL.format(Constants.MAX_PLAYERS)))
                connection.close()
                return
            }

            connection.playerId = playerId
            clients[playerId] = connection

            Log.i(TAG, "Player ${playerId.name} connected from ${conn.remoteSocketAddress}")

            connection.sendMessage(
                NetworkMessage.ConnectResponse(
                    playerId = playerId,
                    gameState = gameState
                )
            )

            if (clients.size == Constants.MAX_PLAYERS) {
                startGame()
            }

            connection.startListening()
        } catch (e: Exception) {
            if (isRunning) {
                Log.e(TAG, "Error handling client connection", e)
            }
            connection.close()
            if (connection.playerId != null) {
                clients.remove(connection.playerId)
            }
            messageQueues.remove(conn)
        }
    }

    private fun assignPlayerId(): PlayerId? {
        if (!clients.containsKey(PlayerId.Player1)) {
            return PlayerId.Player1
        }
        if (!clients.containsKey(PlayerId.Player2)) {
            return PlayerId.Player2
        }
        return null
    }

    private fun startGame() {
        Log.i(TAG, "Starting game with ${Constants.MAX_PLAYERS} players")

        val player1Paddle = Paddle(
            x = GameConstants.PADDLE_MARGIN,
            y = gameHeight / GameConstants.CENTER_DIVISOR - GameConstants.PADDLE_HEIGHT / GameConstants.CENTER_DIVISOR,
            width = GameConstants.PADDLE_WIDTH,
            height = GameConstants.PADDLE_HEIGHT,
            velocityY = PaddleUtils.NO_MOVEMENT_DIRECTION
        )

        val player2Paddle = Paddle(
            x = gameWidth - GameConstants.PADDLE_MARGIN - GameConstants.PADDLE_WIDTH,
            y = gameHeight / GameConstants.CENTER_DIVISOR - GameConstants.PADDLE_HEIGHT / GameConstants.CENTER_DIVISOR,
            width = GameConstants.PADDLE_WIDTH,
            height = GameConstants.PADDLE_HEIGHT,
            velocityY = PaddleUtils.NO_MOVEMENT_DIRECTION
        )

        val ball = Ball(
            x = gameWidth / GameConstants.CENTER_DIVISOR,
            y = gameHeight / GameConstants.CENTER_DIVISOR,
            velocityX = GameConstants.INITIAL_BALL_VELOCITY_X,
            velocityY = GameConstants.INITIAL_BALL_VELOCITY_Y,
            radius = GameConstants.BALL_RADIUS
        )

        val initialFreezeTime = System.currentTimeMillis() + GameConstants.INITIAL_BALL_FREEZE_DURATION_MS
        synchronized(gameStateLock) {
            gameState = GameState(
                ball = ball,
                player1Paddle = player1Paddle,
                player2Paddle = player2Paddle,
                player1Score = Constants.INITIAL_PLAYER_SCORE,
                player2Score = Constants.INITIAL_PLAYER_SCORE,
                isGameOver = false,
                ballFrozenUntil = initialFreezeTime,
                matchId = matchId,
                ballCollisionCount = 0
            )
        }
        Log.i(TAG, "Match started: $matchId")

        val serverGameServer = object : GameServer {
            override fun connect(): Boolean = true
            override fun disconnect() {}
            override fun startGame(): GameState = synchronized(gameStateLock) { gameState!! }
            override fun updatePaddle(playerId: PlayerId, paddle: Paddle) {
                broadcastPaddleUpdate(playerId, paddle)
            }
            override fun getGameState(): GameState = synchronized(gameStateLock) { gameState!! }
            override fun isConnected(): Boolean = true
            override fun getLocalPlayerId(): PlayerId = PlayerId.Player1
        }

        gameEngine = GameEngine(serverGameServer, gameWidth, gameHeight)

        val stateToSend = synchronized(gameStateLock) { gameState!! }
        clients.values.forEach { client ->
            client.sendMessage(
                NetworkMessage.StartGameResponse(gameState = stateToSend)
            )
        }

        broadcastGameState(stateToSend)

        serverScope.launch {
            runGameLoop()
        }
    }

    private suspend fun runGameLoop() {
        var lastTime = 0L
        var lastFrameTime = System.currentTimeMillis()

        while (shouldContinueGameLoop()) {
            val currentTime = System.nanoTime()
            val currentFrameTime = System.currentTimeMillis()

            val timeSinceLastFrame = currentFrameTime - lastFrameTime
            val gameLoopDelayMs = Config.current.gameLoopDelayMs

            if (timeSinceLastFrame >= gameLoopDelayMs) {
                lastFrameTime = currentFrameTime

                val deltaTime = if (lastTime == 0L) {
                    gameLoopDelayMs / 1000f
                } else {
                    TimeUtils.calculateDeltaTime(currentTime, lastTime)
                }
                lastTime = currentTime

                if (TimeUtils.isValidDeltaTime(deltaTime)) {
                    val currentTimeMs = System.currentTimeMillis()
                    val serverGameServer = object : GameServer {
                        override fun connect(): Boolean = true
                        override fun disconnect() {}
                        override fun startGame(): GameState = synchronized(gameStateLock) { gameState!! }
                        override fun updatePaddle(playerId: PlayerId, paddle: Paddle) {
                            updatePaddleState(playerId, paddle)
                        }
                        override fun getGameState(): GameState = synchronized(gameStateLock) { gameState!! }
                        override fun isConnected(): Boolean = true
                        override fun getLocalPlayerId(): PlayerId = PlayerId.Player1
                    }

                    val engine = gameEngine ?: GameEngine(serverGameServer, gameWidth, gameHeight)

                    val currentState = synchronized(gameStateLock) { gameState }

                    if (currentState == null) {
                        delay(gameLoopDelayMs)
                        continue
                    }

                    val updatedPlayer1Paddle = updatePaddlePosition(currentState.player1Paddle, deltaTime, gameHeight)
                    val updatedPlayer2Paddle = updatePaddlePosition(currentState.player2Paddle, deltaTime, gameHeight)

                    val isBallFrozen = currentState.ballFrozenUntil != null && currentTimeMs < currentState.ballFrozenUntil
                    val (updatedBall, wallBounceCount) = if (isBallFrozen) {
                        currentState.ball to 0
                    } else {
                        engine.updateBall(currentState.ball, deltaTime)
                    }

                    val collisionResult = engine.checkCollisions(
                        updatedBall,
                        updatedPlayer1Paddle,
                        updatedPlayer2Paddle,
                        currentState.player1Score,
                        currentState.player2Score,
                        currentState.ballFrozenUntil,
                        currentTimeMs
                    )

                    val isGameOver = collisionResult.player1Score >= GameConstants.WINNING_SCORE ||
                            collisionResult.player2Score >= GameConstants.WINNING_SCORE
                    val ballFrozenUntil = if (isGameOver) null else collisionResult.ballFrozenUntil
                    val newBallCollisionCount = currentState.ballCollisionCount + wallBounceCount + collisionResult.paddleCollisionCount

                    synchronized(gameStateLock) {
                        val prevState = gameState!!
                        gameState = GameState(
                            ball = collisionResult.ball,
                            player1Paddle = updatedPlayer1Paddle,
                            player2Paddle = updatedPlayer2Paddle,
                            player1Score = collisionResult.player1Score,
                            player2Score = collisionResult.player2Score,
                            isGameOver = isGameOver,
                            ballFrozenUntil = ballFrozenUntil,
                            matchId = currentState.matchId,
                            ballCollisionCount = newBallCollisionCount,
                            player1PaddleHits = prevState.player1PaddleHits + if (collisionResult.player1PaddleHit) 1 else 0,
                            player2PaddleHits = prevState.player2PaddleHits + if (collisionResult.player2PaddleHit) 1 else 0
                        )
                    }

                    broadcastGameState(synchronized(gameStateLock) { gameState!! })
                }
            } else {
                val remainingTime = gameLoopDelayMs - timeSinceLastFrame
                if (remainingTime > 0) {
                    delay(remainingTime)
                }
            }
        }
    }

    fun shouldContinueGameLoop(): Boolean {
        return synchronized(gameStateLock) {
            isRunning && clients.size == Constants.MAX_PLAYERS && gameState != null && !gameState!!.isGameOver
        }
    }

    private fun updatePaddleState(playerId: PlayerId, paddle: Paddle) {
        synchronized(gameStateLock) {
            gameState = gameState?.let { state ->
                when (playerId) {
                    PlayerId.Player1 -> state.copy(player1Paddle = state.player1Paddle.copy(velocityY = paddle.velocityY))
                    PlayerId.Player2 -> state.copy(player2Paddle = state.player2Paddle.copy(velocityY = paddle.velocityY))
                }
            }
        }
    }

    private fun updatePaddlePosition(paddle: Paddle, deltaTime: Float, gameHeight: Float): Paddle {
        val movement = paddle.velocityY * deltaTime
        val newY = (paddle.y + movement).coerceIn(0f, gameHeight - paddle.height)
        return paddle.copy(y = newY)
    }

    private fun broadcastPaddleUpdate(playerId: PlayerId, paddle: Paddle) {
        updatePaddleState(playerId, paddle)
        val message = NetworkMessage.PaddleUpdate(playerId = playerId, paddle = paddle)
        clients.values.forEach { client ->
            if (client.playerId != playerId) {
                client.sendMessage(message)
            }
        }
    }

    private fun broadcastGameState(state: GameState) {
        val message = NetworkMessage.GameStateUpdate(gameState = state)
        clients.values.forEach { client ->
            client.sendMessage(message)
        }
    }

    private inner class ClientConnection(
        private val conn: WebSocket,
        private val queue: BlockingQueue<String>
    ) {
        var playerId: PlayerId? = null
        private var isClosed = false

        fun sendMessage(message: NetworkMessage) {
            if (!isClosed && conn.isOpen) {
                try {
                    val json = MessageSerializer.serialize(message)
                    conn.send(json)
                } catch (e: Exception) {
                    Log.e(TAG, "Error sending message to player ${playerId?.name}", e)
                }
            }
        }

        suspend fun receiveRaw(): String? {
            return withContext(Dispatchers.IO) {
                val line = queue.take()
                if (line == SESSION_CLOSED_SENTINEL) null else line
            }
        }

        fun startListening() {
            serverScope.launch {
                try {
                    while (!isClosed && conn.isOpen) {
                        val line = receiveRaw() ?: break
                        if (SessionStartPayload.isSessionStart(line)) {
                            continue
                        }
                        val message = MessageSerializer.deserialize(line)
                        handleMessage(message)
                    }
                } catch (e: Exception) {
                    if (!isClosed && isRunning) {
                        Log.e(TAG, "Error receiving message from player ${playerId?.name}", e)
                    }
                } finally {
                    close()
                }
            }
        }

        private fun handleMessage(message: NetworkMessage) {
            when (message) {
                is NetworkMessage.PaddleUpdate -> {
                    if (message.playerId == playerId) {
                        broadcastPaddleUpdate(message.playerId, message.paddle)
                    }
                }
                is NetworkMessage.StartGameRequest -> {
                    if (clients.size == Constants.MAX_PLAYERS && gameState != null) {
                        sendMessage(NetworkMessage.StartGameResponse(gameState = gameState!!))
                    }
                }
                is NetworkMessage.Ping -> {
                    sendMessage(NetworkMessage.Pong())
                }
                else -> {
                    Log.w(TAG, "Unexpected message type: ${message.messageType}")
                }
            }
        }

        fun close() {
            if (!isClosed) {
                isClosed = true
                try {
                    conn.close()
                } catch (e: Exception) {
                    Log.e(TAG, "Error closing client connection", e)
                }
                if (playerId != null) {
                    clients.remove(playerId)
                    Log.i(TAG, "Player ${playerId?.name} disconnected")
                }
            }
        }
    }

    companion object {
        private const val TAG = "NetworkGameServer"
    }
}

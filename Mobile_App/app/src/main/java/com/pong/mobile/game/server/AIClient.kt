package com.pong.mobile.game.server

import android.util.Log
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.game.GameConstants
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId
import com.pong.mobile.game.server.network.NetworkGameClient
import com.pong.mobile.game.util.PaddleUtils
import com.pong.mobile.util.TimeUtils
import kotlinx.coroutines.*

class AIClient(
    private val host: String = Constants.LOCALHOST,
    private val port: Int = Constants.DEFAULT_SERVER_PORT,
    private val gameHeight: Float
) {
    private var client: NetworkGameClient? = null
    private var isRunning = false
    private val aiScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun start() {
        if (isRunning) {
            Log.w(TAG, "AI client is already running")
            return
        }

        isRunning = true
        aiScope.launch {
            try {
                client = NetworkGameClient(host, port)
                val isConnected = client!!.connect()
                if (isConnected) {
                    Log.i(TAG, "AI client connected to server")

                    var gameStarted = false
                    var retries = 0
                    while (!gameStarted && retries < Config.current.gameStartRetries && isRunning) {
                        try {
                            client!!.startGame()
                            gameStarted = true
                            Log.i(TAG, "AI client game started")
                        } catch (e: Exception) {
                            retries++
                            delay(Config.current.gameStartRetryDelayMs)
                        }
                    }

                    if (gameStarted) {
                        runAILoop()
                    } else {
                        Log.e(TAG, "AI client failed to start game after retries")
                    }
                } else {
                    Log.e(TAG, "AI client failed to connect to server")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error starting AI client", e)
            }
        }
    }

    fun stop() {
        isRunning = false
        client?.disconnect()
        client = null
        aiScope.cancel()
        Log.i(TAG, "AI client stopped")
    }

    private suspend fun runAILoop() {
        var lastTime = System.nanoTime()
        var lastFrameTime = System.currentTimeMillis()

        while (isRunning && client?.isConnected() == true) {
            try {
                val currentTime = System.nanoTime()
                val currentFrameTime = System.currentTimeMillis()
                val deltaTime = TimeUtils.calculateDeltaTime(currentTime, lastTime)
                lastTime = currentTime

                val gameLoopDelayMs = Config.current.gameLoopDelayMs
                val timeSinceLastFrame = currentFrameTime - lastFrameTime

                if (timeSinceLastFrame >= gameLoopDelayMs) {
                    lastFrameTime = currentFrameTime

                    if (TimeUtils.isValidDeltaTime(deltaTime)) {
                        val gameState = client!!.getGameState()
                        val aiPlayerId = client!!.getLocalPlayerId()

                        if (!gameState.isGameOver) {
                            val velocityY = calculateAIPaddleVelocity(gameState, aiPlayerId)
                            val currentPaddle = if (aiPlayerId == PlayerId.Player1) {
                                gameState.player1Paddle
                            } else {
                                gameState.player2Paddle
                            }
                            val updatedPaddle = currentPaddle.copy(velocityY = velocityY)
                            client!!.updatePaddle(aiPlayerId, updatedPaddle)
                        }
                    }
                } else {
                    val remainingTime = gameLoopDelayMs - timeSinceLastFrame
                    if (remainingTime > 0) {
                        delay(remainingTime)
                    }
                }
            } catch (e: Exception) {
                if (isRunning) {
                    Log.e(TAG, "Error in AI loop", e)
                }
                break
            }
        }
        stop()
    }

    private fun calculateAIPaddleVelocity(gameState: GameState, playerId: PlayerId): Float {
        val currentPaddle = if (playerId == PlayerId.Player1) {
            gameState.player1Paddle
        } else {
            gameState.player2Paddle
        }

        val ball = gameState.ball
        val isBallAlignedWithPaddle = ball.y >= currentPaddle.y && ball.y <= currentPaddle.y + currentPaddle.height

        if (isBallAlignedWithPaddle) {
            return PaddleUtils.calculateVelocityY(PaddleUtils.NO_MOVEMENT_DIRECTION, GameConstants.AI_DIFFICULTY)
        }

        val targetY = PaddleUtils.calculateTargetY(ball, currentPaddle)
        val direction = PaddleUtils.calculateDirection(targetY, currentPaddle.y)
        return PaddleUtils.calculateVelocityY(direction, GameConstants.AI_DIFFICULTY)
    }

    companion object {
        private const val TAG = "AIClient"
    }
}

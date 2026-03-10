package com.pong.mobile.ui

import android.provider.Settings
import android.util.Log
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.data.MatchResult
import com.pong.mobile.game.GameConstants
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId
import com.pong.mobile.game.server.network.NetworkGameClient
import com.pong.mobile.game.util.PaddleUtils
import com.pong.mobile.telemetry.TelemetryService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext

private data class ViewportInfo(val scale: Float, val offsetX: Float, val offsetY: Float)

object GameScreen {
    private const val TAG = "GameScreen"
    private const val TELEMETRY_SNAPSHOT_INTERVAL_MS = 500L

    private fun getPaddleForPlayer(playerId: PlayerId, gameState: GameState): Paddle {
        return if (playerId == PlayerId.Player1) gameState.player1Paddle else gameState.player2Paddle
    }

    private fun getScoreForPlayer(playerId: PlayerId, gameState: GameState): Int {
        return if (playerId == PlayerId.Player1) gameState.player1Score else gameState.player2Score
    }

    private fun getOpponentScoreForPlayer(playerId: PlayerId, gameState: GameState): Int {
        return if (playerId == PlayerId.Player1) gameState.player2Score else gameState.player1Score
    }

    private fun getPaddleColor(playerId: PlayerId, localPlayerId: PlayerId): Color {
        return if (playerId == localPlayerId) Color.White else Color.Red
    }

    @Composable
    fun Content(
        host: String,
        port: Int,
        gameMode: String,
        onBackToMenu: () -> Unit
    ) {
        BackHandler { onBackToMenu() }

        val context = LocalContext.current
        val density = LocalDensity.current
        val config = Config.current
        val gameWidthLogical = config.gameWidth
        val gameHeightLogical = config.gameHeight

        val matchHistoryViewModel: MatchHistoryViewModel = viewModel()
        val gameServer = remember(host, port) { NetworkGameClient(host, port) }

        var gameState by remember { mutableStateOf<GameState?>(null) }
        var touchGameY by remember { mutableStateOf<Float?>(null) }
        var viewportInfo by remember { mutableStateOf<ViewportInfo?>(null) }
        var showErrorDialog by remember { mutableStateOf(false) }
        var isGameRunning by remember { mutableStateOf(false) }
        var matchSaved by remember { mutableStateOf(false) }

        val telemetryService = remember { TelemetryService() }

        val localPlayerId = remember {
            try { gameServer.getLocalPlayerId() } catch (e: Exception) { null }
        }

        val deviceId = remember {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
        }

        LaunchedEffect(Unit) {
            Log.i(TAG, "GameScreen LaunchedEffect started")
            try {
                if (!gameServer.isConnected()) {
                    Log.i(TAG, "Connecting to game server")
                    if (!gameServer.connect()) {
                        Log.e(TAG, Constants.ERROR_MESSAGE_CONNECTING_GAME_SERVER)
                        showErrorDialog = true
                        return@LaunchedEffect
                    }
                }

                // Session start: match desktop - send as soon as we have session ID (after connect)
                val sessionId = gameServer.getSessionId()
                val lpId = try { gameServer.getLocalPlayerId() } catch (e: Exception) { null }
                if (sessionId.isNotBlank() && lpId != null) {
                    telemetryService.startSession(
                        matchId = sessionId,
                        gameMode = gameMode,
                        playerId = lpId.name,
                        deviceId = deviceId
                    )
                }

                // Start game with retry logic (moved from Navigation)
                var gameStarted = false
                var retries = 0
                val maxRetries = config.maxPlayerClientStartRetries
                while (!gameStarted && retries < maxRetries) {
                    try {
                        gameServer.startGame()
                        gameStarted = true
                        Log.i(TAG, "Game started successfully")
                    } catch (e: Exception) {
                        retries++
                        delay(config.playerClientStartRetryDelayMs)
                    }
                }

                if (!gameStarted) {
                    Log.e(TAG, "${Constants.ERROR_MESSAGE_STARTING_GAME_RETRIES} $maxRetries retries")
                    showErrorDialog = true
                    return@LaunchedEffect
                }
            } catch (e: Exception) {
                Log.e(TAG, Constants.ERROR_MESSAGE_CONNECTING_GAME_SCREEN, e)
                showErrorDialog = true
                return@LaunchedEffect
            }

            delay(config.gameStateRetryDelayMs)

            var consecutiveErrors = 0
            var lastTelemetrySnapshotMs = 0L

            withContext(Dispatchers.IO) {
                while (currentCoroutineContext().isActive) {
                    val shouldShowError = withContext(Dispatchers.Main) { showErrorDialog }
                    if (shouldShowError) break

                    try {
                        if (gameServer.isConnected()) {
                            try {
                                val currentState = gameServer.getGameState()

                                withContext(Dispatchers.Main) {
                                    gameState = currentState
                                    consecutiveErrors = 0

                                    if (!isGameRunning) {
                                        isGameRunning = true
                                    }

                                    val now = System.currentTimeMillis()
                                    if (now - lastTelemetrySnapshotMs >= TELEMETRY_SNAPSHOT_INTERVAL_MS) {
                                        lastTelemetrySnapshotMs = now
                                        val lpId = localPlayerId ?: PlayerId.Player1
                                        val localPaddle = getPaddleForPlayer(lpId, currentState)
                                        telemetryService.recordSnapshot(
                                                collisionCount = currentState.ballCollisionCount,
                                                latencyMs = 0L,
                                                paddleY = localPaddle.y
                                        )
                                    }

                                    if (currentState.isGameOver) {
                                        isGameRunning = false

                                        val lpId = localPlayerId ?: PlayerId.Player1
                                        telemetryService.endSession(currentState, lpId)

                                        // Save match result to Room (only once)
                                        if (!matchSaved) {
                                            matchSaved = true
                                            val playerScore = getScoreForPlayer(lpId, currentState)
                                            val opponentScore = getOpponentScoreForPlayer(lpId, currentState)
                                            val won = playerScore >= GameConstants.WINNING_SCORE
                                            matchHistoryViewModel.saveMatch(
                                                MatchResult(
                                                    gameMode = gameMode,
                                                    playerScore = playerScore,
                                                    opponentScore = opponentScore,
                                                    won = won,
                                                    timestamp = System.currentTimeMillis(),
                                                    matchId = currentState.matchId
                                                )
                                            )
                                        }
                                    }
                                }

                                if (currentState.isGameOver) break
                            } catch (e: IllegalStateException) {
                                if (e.message?.contains(Constants.ERROR_MESSAGE_GAME_NOT_STARTED) ==
                                                true
                                ) {
                                    consecutiveErrors = 0
                                    delay(config.gameStateRetryDelayMs)
                                    continue
                                } else {
                                    throw e
                                }
                            }
                        } else {
                            delay(config.gameStateRetryDelayMs)
                            continue
                        }
                    } catch (e: Exception) {
                        if (!currentCoroutineContext().isActive) break
                        consecutiveErrors++
                        if (consecutiveErrors >= config.maxConsecutiveErrors) {
                            Log.e(TAG, Constants.ERROR_MESSAGE_GETTING_GAME_STATE, e)
                            withContext(Dispatchers.Main) { showErrorDialog = true }
                            break
                        }
                        delay(config.gameStateRetryDelayMs)
                        continue
                    }
                    delay(config.gameStatePollingDelayMs)
                }
            }
        }

        if (showErrorDialog) {
            AlertDialog(
                onDismissRequest = { showErrorDialog = false; onBackToMenu() },
                title = { Text(Constants.UI_ERROR_DIALOG_TITLE) },
                text = { Text(Constants.UI_ERROR_DIALOG_MESSAGE) },
                confirmButton = {
                    Button(onClick = { showErrorDialog = false; onBackToMenu() }) {
                        Text(Constants.UI_ERROR_DIALOG_BUTTON)
                    }
                }
            )
        }

        LaunchedEffect(isGameRunning) {
            if (isGameRunning && localPlayerId != null) {
                var lastVelocityY: Float? = null
                while (isGameRunning) {
                    try {
                        val currentState = gameState
                        val info = viewportInfo

                        if (touchGameY != null && currentState != null && info != null) {
                            val paddle = getPaddleForPlayer(localPlayerId, currentState)
                            val paddleCenterY = PaddleUtils.calculatePaddleCenterY(paddle)
                            val distanceFromPaddleCenter = touchGameY!! - paddleCenterY
                            val unscaledDirection =
                                    distanceFromPaddleCenter / Constants.TOUCH_TO_DIRECTION_SCALE
                            val direction =
                                    unscaledDirection.coerceIn(
                                            PaddleUtils.MIN_DIRECTION,
                                            PaddleUtils.MAX_DIRECTION
                                    )
                            val velocityY = PaddleUtils.calculateVelocityY(direction)

                            if (lastVelocityY == null || lastVelocityY != velocityY) {
                                val currentPaddle = getPaddleForPlayer(localPlayerId, currentState)
                                val updatedPaddle = currentPaddle.copy(velocityY = velocityY)
                                withContext(Dispatchers.IO) {
                                    gameServer.updatePaddle(localPlayerId, updatedPaddle)
                                }
                                lastVelocityY = velocityY
                            }
                        } else {
                            if (lastVelocityY != null &&
                                            lastVelocityY != PaddleUtils.NO_MOVEMENT_DIRECTION
                            ) {
                                val cs = gameState
                                if (cs != null) {
                                    val currentPaddle = getPaddleForPlayer(localPlayerId, cs)
                                    val updatedPaddle =
                                            currentPaddle.copy(
                                                    velocityY = PaddleUtils.NO_MOVEMENT_DIRECTION
                                            )
                                    withContext(Dispatchers.IO) {
                                        gameServer.updatePaddle(localPlayerId, updatedPaddle)
                                    }
                                    lastVelocityY = PaddleUtils.NO_MOVEMENT_DIRECTION
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, Constants.ERROR_MESSAGE_UPDATING_PADDLE, e)
                    }
                    delay(config.gameLoopDelayMs)
                }
            }
        }

        DisposableEffect(Unit) {
            onDispose {
                gameServer.disconnect()
                val finalState = gameState
                if (finalState != null && localPlayerId != null) {
                    telemetryService.endSession(finalState, localPlayerId)
                }
                telemetryService.close()
            }
        }

        Box(modifier = Modifier.fillMaxSize().background(Color.Black)) {
            if (showErrorDialog) return@Box

            if (gameState == null) {
                Text(
                        text = Constants.UI_LOADING_TEXT,
                        color = Color.White,
                        fontSize = 24.sp,
                        modifier = Modifier.align(Alignment.Center)
                )
            } else {
                Column(
                        modifier = Modifier.fillMaxSize(),
                        horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                                text =
                                        "${Constants.UI_SCORE_PLAYER_1_LABEL}${gameState!!.player1Score}",
                                color = Color.White,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold
                        )
                        Text(
                                text =
                                        "${Constants.UI_SCORE_PLAYER_2_LABEL}${gameState!!.player2Score}",
                                color = Color.White,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold
                        )
                    }
                    val displaySessionId =
                            gameServer.getSessionId().ifBlank { gameState!!.matchId }
                    if (displaySessionId.isNotBlank()) {
                        Text(
                                text = "Session: $displaySessionId",
                                color = Color.Gray,
                                fontSize = 14.sp,
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                        )
                    }

                    BoxWithConstraints(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .pointerInput(Unit) {
                                detectDragGestures(
                                    onDragStart = { offset ->
                                        val info = viewportInfo
                                        if (info != null) {
                                            val gameY = (offset.y - info.offsetY) / info.scale
                                            if (gameY in Constants.GAME_ORIGIN_Y..gameHeightLogical) {
                                                touchGameY = gameY
                                            }
                                        }
                                    },
                                    onDrag = { change, _ ->
                                        change.consume()
                                        val info = viewportInfo
                                        if (info != null) {
                                            val gameY = (change.position.y - info.offsetY) / info.scale
                                            if (gameY in Constants.GAME_ORIGIN_Y..gameHeightLogical) {
                                                touchGameY = gameY
                                            }
                                        }
                                    },
                                    onDragEnd = { touchGameY = null },
                                    onDragCancel = { touchGameY = null }
                                )
                            }
                    ) {
                        val containerWidthPx = with(density) { maxWidth.toPx() }
                        val containerHeightPx = with(density) { maxHeight.toPx() }
                        val scaleToFit =
                                minOf(
                                        containerWidthPx / gameWidthLogical,
                                        containerHeightPx / gameHeightLogical
                                )
                        val scale = scaleToFit * Constants.VIEWPORT_MAX_SCALE_FACTOR
                        val offsetX =
                                (containerWidthPx - gameWidthLogical * scale) /
                                        Constants.VIEWPORT_CENTER_DIVISOR
                        val offsetY =
                                (containerHeightPx - gameHeightLogical * scale) /
                                        Constants.VIEWPORT_CENTER_DIVISOR

                        SideEffect {
                            viewportInfo =
                                    ViewportInfo(
                                            scale = scale,
                                            offsetX = offsetX,
                                            offsetY = offsetY
                                    )
                        }

                        Canvas(modifier = Modifier.fillMaxSize()) {
                            val state = gameState!!
                            drawRect(Color(Constants.VIEWPORT_BORDER_COLOR_ARGB))

                            val lpId = localPlayerId ?: PlayerId.Player1
                            val player1PaddleColor = getPaddleColor(PlayerId.Player1, lpId)
                            val player2PaddleColor = getPaddleColor(PlayerId.Player2, lpId)

                            drawRect(
                                color = player1PaddleColor,
                                topLeft = Offset(state.player1Paddle.x * scale + offsetX, state.player1Paddle.y * scale + offsetY),
                                size = Size(state.player1Paddle.width * scale, state.player1Paddle.height * scale)
                            )
                            drawRect(
                                color = player2PaddleColor,
                                topLeft = Offset(state.player2Paddle.x * scale + offsetX, state.player2Paddle.y * scale + offsetY),
                                size = Size(state.player2Paddle.width * scale, state.player2Paddle.height * scale)
                            )
                            drawCircle(
                                color = Color.White,
                                radius = state.ball.radius * scale,
                                center = Offset(state.ball.x * scale + offsetX, state.ball.y * scale + offsetY)
                            )
                        }
                    }

                    if (gameState!!.isGameOver) {
                        val lpId = localPlayerId ?: PlayerId.Player1
                        val localPlayerScore = getScoreForPlayer(lpId, gameState!!)
                        val playerWon = localPlayerScore >= GameConstants.WINNING_SCORE
                        val gameOverMessage =
                                if (playerWon) Constants.UI_GAME_OVER_WIN
                                else Constants.UI_GAME_OVER_LOSE
                        Text(
                                text = gameOverMessage,
                                color = Color.White,
                                fontSize = 32.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(16.dp)
                        )
                    }

                    Text(
                            text = Constants.UI_INSTRUCTION_TEXT,
                            color = Color.Gray,
                            fontSize = 14.sp,
                            modifier = Modifier.padding(8.dp)
                    )
                }
            }
        }
    }
}

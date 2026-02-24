package com.pong.mobile.ui

import android.util.Log
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.game.server.AIClient
import com.pong.mobile.game.server.GameServer
import com.pong.mobile.game.server.network.NetworkGameClient
import com.pong.mobile.game.server.network.NetworkGameServer
import com.pong.mobile.matchmaking.MatchmakingClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "Navigation"

sealed class Screen {
    object MainMenu : Screen()
    object Settings : Screen()
    object Game : Screen()
}

@Composable
fun Navigation() {
    var currentScreen by remember { mutableStateOf<Screen>(Screen.MainMenu) }
    var gameServer by remember { mutableStateOf<GameServer?>(null) }
    var localNetworkServer by remember { mutableStateOf<NetworkGameServer?>(null) }
    var aiClient by remember { mutableStateOf<AIClient?>(null) }
    var isFindingMatch by remember { mutableStateOf(false) }
    var showMatchmakingError by remember { mutableStateOf(false) }
    var gameMode by remember { mutableStateOf("") }
    val coroutineScope = rememberCoroutineScope()

    when (currentScreen) {
        is Screen.MainMenu -> {
            Box(modifier = Modifier.fillMaxSize()) {
                MainMenu.Content(
                    onSingleplayerClick = singleplayer@{
                        Log.i(TAG, "Singleplayer button clicked")
                        val isLocalServerRunning = localNetworkServer != null && localNetworkServer!!.isRunning()
                        if (isLocalServerRunning) {
                            Log.w(TAG, Constants.ERROR_MESSAGE_SERVER_ALREADY_RUNNING)
                            return@singleplayer
                        }

                        val config = Config.current
                        val gameWidth = config.gameWidth
                        val gameHeight = config.gameHeight

                        coroutineScope.launch(Dispatchers.IO) {
                            localNetworkServer?.stop()
                            aiClient?.stop()

                            withContext(Dispatchers.Main) {
                                localNetworkServer = null
                                aiClient = null
                            }

                            val server = NetworkGameServer(
                                port = config.gameServerPort,
                                gameWidth = gameWidth,
                                gameHeight = gameHeight
                            )
                            server.start()

                            if (!server.isRunning()) {
                                Log.e(TAG, Constants.ERROR_MESSAGE_NETWORK_SERVER_FAILED_TO_START)
                                return@launch
                            }

                            withContext(Dispatchers.Main) {
                                localNetworkServer = server
                            }

                            kotlinx.coroutines.delay(config.serverStartupDelayMs)

                            val aiClientInstance = AIClient(
                                host = Constants.LOCALHOST,
                                port = config.gameServerPort,
                                gameHeight = gameHeight
                            )
                            aiClientInstance.start()

                            withContext(Dispatchers.Main) {
                                aiClient = aiClientInstance
                            }

                            kotlinx.coroutines.delay(config.aiClientStartupDelayMs)

                            val client = NetworkGameClient(Constants.LOCALHOST, config.gameServerPort)
                            Log.i(TAG, "Connecting player client to server")
                            if (client.connect()) {
                                Log.i(TAG, "Player client connected, starting game")
                                try {
                                    var gameStarted = false
                                    var retries = 0
                                    val maxRetries = Config.current.maxPlayerClientStartRetries
                                    while (!gameStarted && retries < maxRetries) {
                                        try {
                                            client.startGame()
                                            gameStarted = true
                                            Log.i(TAG, "Game started successfully")
                                        } catch (e: Exception) {
                                            retries++
                                            kotlinx.coroutines.delay(Config.current.playerClientStartRetryDelayMs)
                                        }
                                    }

                                    if (gameStarted) {
                                        withContext(Dispatchers.Main) {
                                            gameServer = client
                                            gameMode = "singleplayer"
                                            currentScreen = Screen.Game
                                        }
                                    } else {
                                        Log.e(TAG, "${Constants.ERROR_MESSAGE_STARTING_GAME_RETRIES} $maxRetries retries")
                                        client.disconnect()
                                    }
                                } catch (e: Exception) {
                                    Log.e(TAG, Constants.ERROR_MESSAGE_STARTING_GAME, e)
                                    client.disconnect()
                                }
                            } else {
                                Log.e(TAG, Constants.ERROR_MESSAGE_CONNECTING_PLAYER_CLIENT)
                            }
                        }
                    },
                    onFindMatchClick = findMatch@{
                        if (isFindingMatch) return@findMatch
                        isFindingMatch = true
                        coroutineScope.launch(Dispatchers.IO) {
                            val endpoint = MatchmakingClient(Config.current.matchmakingHost, Config.current.matchmakingPort).findMatch()
                            withContext(Dispatchers.Main) { isFindingMatch = false }
                            if (endpoint == null) {
                                withContext(Dispatchers.Main) { showMatchmakingError = true }
                                return@launch
                            }
                            val client = NetworkGameClient(endpoint.host, endpoint.port)
                            Log.i(TAG, "Connecting to game server ${endpoint.host}:${endpoint.port}")
                            if (!client.connect()) {
                                withContext(Dispatchers.Main) { showMatchmakingError = true }
                                return@launch
                            }
                            try {
                                var gameStarted = false
                                var retries = 0
                                val maxRetriesMatch = Config.current.maxPlayerClientStartRetries
                                while (!gameStarted && retries < maxRetriesMatch) {
                                    try {
                                        client.startGame()
                                        gameStarted = true
                                    } catch (e: Exception) {
                                        retries++
                                        kotlinx.coroutines.delay(Config.current.playerClientStartRetryDelayMs)
                                    }
                                }
                                if (gameStarted) {
                                    withContext(Dispatchers.Main) {
                                        gameServer = client
                                        gameMode = "multiplayer"
                                        currentScreen = Screen.Game
                                    }
                                } else {
                                    client.disconnect()
                                    withContext(Dispatchers.Main) { showMatchmakingError = true }
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, Constants.ERROR_MESSAGE_STARTING_GAME, e)
                                client.disconnect()
                                withContext(Dispatchers.Main) { showMatchmakingError = true }
                            }
                        }
                    },
                    onSettingsClick = { currentScreen = Screen.Settings }
                )
                if (isFindingMatch) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(Constants.UI_MATCHMAKING_WAITING)
                    }
                }
            }
            if (showMatchmakingError) {
                AlertDialog(
                    onDismissRequest = { showMatchmakingError = false },
                    title = { Text(Constants.UI_ERROR_DIALOG_TITLE) },
                    text = { Text(Constants.ERROR_MESSAGE_MATCHMAKING_CONNECT) },
                    confirmButton = {
                        Button(onClick = { showMatchmakingError = false }) {
                            Text(Constants.UI_ERROR_DIALOG_BUTTON)
                        }
                    }
                )
            }
        }
        is Screen.Settings -> {
            SettingsScreen.Content(onBack = { currentScreen = Screen.MainMenu })
        }
        is Screen.Game -> {
            gameServer?.let { server ->
                DisposableEffect(Unit) {
                    onDispose {
                        aiClient?.stop()
                        aiClient = null
                        localNetworkServer?.stop()
                        localNetworkServer = null
                    }
                }

                GameScreen.Content(
                    gameServer = server,
                    gameMode = gameMode,
                    onBackToMenu = {
                        Log.i(TAG, "Returning to main menu")
                        aiClient?.stop()
                        aiClient = null
                        localNetworkServer?.stop()
                        localNetworkServer = null
                        currentScreen = Screen.MainMenu
                        gameServer = null
                    }
                )
            } ?: run {
                Log.w(TAG, Constants.ERROR_MESSAGE_GAME_SERVER_NULL)
            }
        }
    }
}

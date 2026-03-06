package com.pong.mobile.ui

import android.util.Log
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.game.server.AIClient
import com.pong.mobile.game.server.network.NetworkGameServer
import com.pong.mobile.matchmaking.MatchmakingClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "Navigation"

object Routes {
    const val MAIN_MENU = "main_menu"
    const val SETTINGS = "settings"
    const val MATCH_HISTORY = "match_history"
    const val GAME = "game/{host}/{port}/{gameMode}"

    fun game(host: String, port: Int, gameMode: String) = "game/$host/$port/$gameMode"
}

@Composable
fun Navigation() {
    val navController = rememberNavController()
    var localNetworkServer by remember { mutableStateOf<NetworkGameServer?>(null) }
    var aiClient by remember { mutableStateOf<AIClient?>(null) }
    var isFindingMatch by remember { mutableStateOf(false) }
    var showMatchmakingError by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

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

    NavHost(navController = navController, startDestination = Routes.MAIN_MENU) {
        composable(Routes.MAIN_MENU) {
            MainMenu.Content(
                onSingleplayerClick = singleplayer@{
                    Log.i(TAG, "Singleplayer button clicked")
                    val isLocalServerRunning = localNetworkServer != null && localNetworkServer!!.isRunning()
                    if (isLocalServerRunning) {
                        Log.w(TAG, Constants.ERROR_MESSAGE_SERVER_ALREADY_RUNNING)
                        return@singleplayer
                    }

                    val config = Config.current
                    coroutineScope.launch(Dispatchers.IO) {
                        localNetworkServer?.stop()
                        aiClient?.stop()
                        withContext(Dispatchers.Main) {
                            localNetworkServer = null
                            aiClient = null
                        }

                        val server = NetworkGameServer(
                            port = config.gameServerPort,
                            gameWidth = config.gameWidth,
                            gameHeight = config.gameHeight
                        )
                        server.start()

                        if (!server.isRunning()) {
                            Log.e(TAG, Constants.ERROR_MESSAGE_NETWORK_SERVER_FAILED_TO_START)
                            return@launch
                        }
                        withContext(Dispatchers.Main) { localNetworkServer = server }

                        kotlinx.coroutines.delay(config.serverStartupDelayMs)

                        val aiClientInstance = AIClient(
                            host = Constants.LOCALHOST,
                            port = config.gameServerPort,
                            gameHeight = config.gameHeight
                        )
                        aiClientInstance.start()
                        withContext(Dispatchers.Main) { aiClient = aiClientInstance }

                        kotlinx.coroutines.delay(config.aiClientStartupDelayMs)

                        withContext(Dispatchers.Main) {
                            navController.navigate(
                                Routes.game(Constants.LOCALHOST, config.gameServerPort, "singleplayer")
                            )
                        }
                    }
                },
                onFindMatchClick = findMatch@{
                    if (isFindingMatch) return@findMatch
                    isFindingMatch = true
                    coroutineScope.launch(Dispatchers.IO) {
                        val endpoint = MatchmakingClient(
                            Config.current.matchmakingHost,
                            Config.current.matchmakingPort
                        ).findMatch()
                        withContext(Dispatchers.Main) { isFindingMatch = false }
                        if (endpoint == null) {
                            withContext(Dispatchers.Main) { showMatchmakingError = true }
                            return@launch
                        }
                        withContext(Dispatchers.Main) {
                            navController.navigate(
                                Routes.game(endpoint.host, endpoint.port, "multiplayer")
                            )
                        }
                    }
                },
                onSettingsClick = { navController.navigate(Routes.SETTINGS) },
                onMatchHistoryClick = { navController.navigate(Routes.MATCH_HISTORY) },
                isFindingMatch = isFindingMatch
            )
        }

        composable(Routes.SETTINGS) {
            SettingsScreen.Content(onBack = { navController.popBackStack() })
        }

        composable(Routes.MATCH_HISTORY) {
            MatchHistoryScreen.Content(onBack = { navController.popBackStack() })
        }

        composable(
            route = Routes.GAME,
            arguments = listOf(
                navArgument("host") { type = NavType.StringType },
                navArgument("port") { type = NavType.IntType },
                navArgument("gameMode") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val host = backStackEntry.arguments?.getString("host") ?: ""
            val port = backStackEntry.arguments?.getInt("port") ?: 0
            val gameMode = backStackEntry.arguments?.getString("gameMode") ?: ""

            GameScreen.Content(
                host = host,
                port = port,
                gameMode = gameMode,
                onBackToMenu = {
                    Log.i(TAG, "Returning to main menu")
                    aiClient?.stop()
                    aiClient = null
                    localNetworkServer?.stop()
                    localNetworkServer = null
                    navController.popBackStack()
                }
            )
        }
    }
}

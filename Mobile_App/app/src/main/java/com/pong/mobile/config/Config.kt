package com.pong.mobile.config

import android.content.Context
import com.pong.mobile.Constants

data class Config(
        val gameWidth: Float = Constants.GAME_WIDTH,
        val gameHeight: Float = Constants.GAME_HEIGHT,
        val gameServerHost: String = "10.0.2.2",
        val gameServerPort: Int = Constants.DEFAULT_SERVER_PORT,
        val matchmakingHost: String = "10.0.2.2",
        val matchmakingPort: Int = Constants.MATCHMAKING_DEFAULT_PORT,
        val serverStartupDelayMs: Long = 1000L,
        val aiClientStartupDelayMs: Long = 500L,
        val gameLoopDelayMs: Long = 33L,
        val gameStatePollingDelayMs: Long = 16L,
        val gameStateRetryDelayMs: Long = 200L,
        val maxConsecutiveErrors: Int = 50,
        val gameStartRetries: Int = 30,
        val gameStartRetryDelayMs: Long = 200L,
        val maxPlayerClientStartRetries: Int = 30,
        val playerClientStartRetryDelayMs: Long = 200L,
        val matchmakingGameServerPortRangeStart: Int =
                Constants.MATCHMAKING_GAME_SERVER_PORT_RANGE_START,
        val telemetryWsHost: String = "10.0.2.2",
        val telemetryWsPort: Int = 6789
) {
    companion object {
        private const val PREFS_NAME = "pong_settings"
        private const val KEY_GAME_SERVER_HOST = "game_server_host"
        private const val KEY_GAME_SERVER_PORT = "game_server_port"
        private const val KEY_MATCHMAKING_HOST = "matchmaking_host"
        private const val KEY_MATCHMAKING_PORT = "matchmaking_port"

        @Volatile
        var current: Config = Config()
            private set

        fun load(context: Context) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            current =
                    Config(
                            gameServerHost =
                                    prefs.getString(KEY_GAME_SERVER_HOST, current.gameServerHost)
                                            ?: current.gameServerHost,
                            gameServerPort =
                                    prefs.getInt(KEY_GAME_SERVER_PORT, current.gameServerPort),
                            matchmakingHost =
                                    prefs.getString(KEY_MATCHMAKING_HOST, current.matchmakingHost)
                                            ?: current.matchmakingHost,
                            matchmakingPort =
                                    prefs.getInt(KEY_MATCHMAKING_PORT, current.matchmakingPort)
                    )
        }

        fun save(context: Context, config: Config) {
            current = config
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit()
                    .putString(KEY_GAME_SERVER_HOST, config.gameServerHost)
                    .putInt(KEY_GAME_SERVER_PORT, config.gameServerPort)
                    .putString(KEY_MATCHMAKING_HOST, config.matchmakingHost)
                    .putInt(KEY_MATCHMAKING_PORT, config.matchmakingPort)
                    .apply()
        }
    }
}

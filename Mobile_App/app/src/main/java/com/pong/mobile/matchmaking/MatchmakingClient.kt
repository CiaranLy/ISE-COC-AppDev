package com.pong.mobile.matchmaking

import android.util.Log
import com.pong.mobile.Constants
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.Socket

data class GameServerEndpoint(val host: String, val port: Int)

class MatchmakingClient(
    private val host: String = Constants.LOCALHOST,
    private val port: Int = Constants.MATCHMAKING_DEFAULT_PORT
) {
    fun findMatch(): GameServerEndpoint? {
        return try {
            Log.i(TAG, "Connecting to matchmaking server at $host:$port")
            Socket(host, port).use { socket ->
                val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
                val writer = PrintWriter(socket.getOutputStream(), true)
                writer.println(MatchmakingSerializer.encode(MatchmakingMessage.QueueJoin()))
                val responseLine = reader.readLine() ?: return null
                val response = MatchmakingSerializer.decode(responseLine)
                when (response) {
                    is MatchmakingMessage.QueueWaiting -> {
                        Log.i(TAG, "Waiting for opponent...")
                        waitForGameReady(reader)
                    }
                    is MatchmakingMessage.GameReady -> GameServerEndpoint(response.host, response.port)
                    is MatchmakingMessage.MatchmakingError -> {
                        Log.e(TAG, "Matchmaking error: ${response.error}")
                        null
                    }
                    else -> null
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to connect to matchmaking server at $host:$port", e)
            null
        }
    }

    private fun waitForGameReady(reader: BufferedReader): GameServerEndpoint? {
        while (true) {
            val line = reader.readLine() ?: return null
            val msg = MatchmakingSerializer.decode(line)
            when (msg) {
                is MatchmakingMessage.GameReady -> {
                    Log.i(TAG, "Match found: ${msg.host}:${msg.port}")
                    return GameServerEndpoint(msg.host, msg.port)
                }
                is MatchmakingMessage.MatchmakingError -> {
                    Log.e(TAG, "Matchmaking error: ${msg.error}")
                    return null
                }
                else -> { }
            }
        }
    }

    companion object {
        private const val TAG = "MatchmakingClient"
    }
}

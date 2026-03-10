package com.pong.mobile.matchmaking

import android.util.Log
import com.pong.mobile.Constants
import com.pong.mobile.game.server.network.NetworkGameServer
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.atomic.AtomicInteger

class MatchmakingServer(
    private val port: Int = Constants.MATCHMAKING_DEFAULT_PORT,
    private val advertisedHost: String = Constants.LOCALHOST,
    private val gameWidth: Float = Constants.GAME_WIDTH,
    private val gameHeight: Float = Constants.GAME_HEIGHT,
    private val gameServerPortRangeStart: Int = Constants.MATCHMAKING_GAME_SERVER_PORT_RANGE_START
) {
    private var serverSocket: ServerSocket? = null
    private val queueMutex = Mutex()
    private val queue = mutableListOf<QueuedPlayer>()
    private val nextPort = AtomicInteger(gameServerPortRangeStart)
    private val activeGameServers = mutableListOf<NetworkGameServer>()
    private var isRunning = false
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun start() {
        if (isRunning) {
            Log.w(TAG, "Matchmaking server is already running")
            return
        }
        try {
            serverSocket = ServerSocket(port)
            isRunning = true
            Log.i(TAG, "Matchmaking server started on port $port, advertised host $advertisedHost")
            scope.launch {
                while (isRunning) {
                    try {
                        val socket = serverSocket?.accept() ?: break
                        scope.launch { handleConnection(socket) }
                    } catch (e: Exception) {
                        if (isRunning) Log.e(TAG, "Error accepting connection", e)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start matchmaking server on port $port", e)
            isRunning = false
        }
    }

    fun stop() {
        isRunning = false
        serverSocket?.close()
        serverSocket = null
        activeGameServers.forEach { it.stop() }
        activeGameServers.clear()
        Log.i(TAG, "Matchmaking server stopped")
    }

    fun isRunning(): Boolean = isRunning

    private suspend fun handleConnection(socket: Socket) {
        val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
        val writer = PrintWriter(socket.getOutputStream(), true)
        try {
            val line = reader.readLine() ?: return
            val msg = MatchmakingSerializer.decode(line)
            if (msg !is MatchmakingMessage.QueueJoin) {
                writer.println(MatchmakingSerializer.encode(
                    MatchmakingMessage.MatchmakingError(error = Constants.ERROR_MESSAGE_EXPECTED_QUEUE_JOIN)
                ))
                return
            }
            writer.println(MatchmakingSerializer.encode(MatchmakingMessage.QueueWaiting()))
            val player = QueuedPlayer(socket, reader, writer)
            queueMutex.withLock {
                queue.add(player)
                if (queue.size >= Constants.MAX_PLAYERS) {
                    val pair = queue.take(Constants.MAX_PLAYERS).also { queue.removeAll(it) }
                    scope.launch { launchGameForPair(pair) }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error handling matchmaking connection", e)
            try {
                writer.println(MatchmakingSerializer.encode(
                    MatchmakingMessage.MatchmakingError(error = e.message ?: Constants.ERROR_MESSAGE_UNKNOWN)
                ))
            } catch (_: Exception) {}
        }
    }

    private fun launchGameForPair(pair: List<QueuedPlayer>) {
        val port = findAvailablePort()
        val gameServer = NetworkGameServer(
            port = port,
            gameWidth = gameWidth,
            gameHeight = gameHeight
        )
        gameServer.start()
        if (!gameServer.isRunning()) {
            Log.e(TAG, Constants.ERROR_MESSAGE_FAILED_START_SERVER.format(port))
            pair.forEach { it.send(MatchmakingMessage.MatchmakingError(error = Constants.ERROR_MESSAGE_COULD_NOT_START_GAME_SERVER)) }
            pair.forEach { it.close() }
            return
        }
        activeGameServers.add(gameServer)
        val sessionId = gameServer.getSessionId()
        val ready = MatchmakingMessage.GameReady(host = advertisedHost, port = port, sessionId = sessionId)
        pair.forEach {
            it.send(ready)
            it.close()
        }
        Log.i(TAG, "Started game server on port $port for ${Constants.MAX_PLAYERS} players")
    }

    private fun findAvailablePort(): Int {
        while (true) {
            val port = nextPort.getAndIncrement()
            try {
                ServerSocket(port).close()
                return port
            } catch (_: Exception) { }
        }
    }

    private data class QueuedPlayer(
        val socket: Socket,
        val reader: BufferedReader,
        val writer: PrintWriter
    ) {
        fun send(message: MatchmakingMessage) {
            writer.println(MatchmakingSerializer.encode(message))
        }
        fun close() {
            try {
                socket.close()
            } catch (_: Exception) {}
        }
    }

    companion object {
        private const val TAG = "MatchmakingServer"
    }
}

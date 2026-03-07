package com.pong.mobile.telemetry

import android.util.Log
import org.java_websocket.WebSocket
import org.java_websocket.handshake.ClientHandshake
import org.java_websocket.server.WebSocketServer
import java.net.InetSocketAddress

class TelemetryServer(port: Int) : WebSocketServer(InetSocketAddress(port)) {

    override fun onOpen(conn: WebSocket, handshake: ClientHandshake) {
        Log.i(TAG, "Telemetry client connected: ${conn.remoteSocketAddress}")
    }

    override fun onClose(conn: WebSocket, code: Int, reason: String, remote: Boolean) {
        Log.i(TAG, "Telemetry client disconnected: ${conn.remoteSocketAddress}")
    }

    override fun onMessage(conn: WebSocket, message: String) {}

    override fun onError(conn: WebSocket?, ex: Exception) {
        Log.e(TAG, "Telemetry server error", ex)
    }

    override fun onStart() {
        Log.i(TAG, "Telemetry server listening on port $port")
    }

    fun broadcastTelemetry(message: String) {
        broadcast(message)
    }

    fun stopGracefully() {
        try {
            stop()
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping telemetry server", e)
        }
    }

    companion object {
        private const val TAG = "TelemetryServer"
    }
}

package com.pong.mobile.game.server.network

import com.pong.mobile.Constants
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId

sealed class NetworkMessage {
    abstract val messageType: String

    data class ConnectRequest(override val messageType: String = Constants.NETWORK_MSG_CONNECT) : NetworkMessage()
    data class ConnectResponse(
        override val messageType: String = Constants.NETWORK_MSG_CONNECT_RESPONSE,
        val playerId: PlayerId,
        val gameState: GameState? = null
    ) : NetworkMessage()

    data class PaddleUpdate(
        override val messageType: String = Constants.NETWORK_MSG_PADDLE_UPDATE,
        val playerId: PlayerId,
        val paddle: Paddle
    ) : NetworkMessage()

    data class GameStateUpdate(
        override val messageType: String = Constants.NETWORK_MSG_GAME_STATE_UPDATE,
        val gameState: GameState
    ) : NetworkMessage()

    data class StartGameRequest(override val messageType: String = Constants.NETWORK_MSG_START_GAME) : NetworkMessage()
    data class StartGameResponse(
        override val messageType: String = Constants.NETWORK_MSG_START_GAME_RESPONSE,
        val gameState: GameState
    ) : NetworkMessage()

    data class Error(
        override val messageType: String = Constants.NETWORK_MSG_ERROR,
        val error: String
    ) : NetworkMessage()

    data class Ping(override val messageType: String = Constants.NETWORK_MSG_PING) : NetworkMessage()
    data class Pong(override val messageType: String = Constants.NETWORK_MSG_PONG) : NetworkMessage()
}

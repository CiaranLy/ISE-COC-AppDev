package com.pong.mobile.game.server.network

import com.pong.mobile.Constants
import com.pong.mobile.game.Ball
import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Serializable
private data class SerializableBall(
    val x: Float,
    val y: Float,
    val velocityX: Float,
    val velocityY: Float,
    val radius: Float
)

@Serializable
private data class SerializablePaddle(
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float,
    val velocityY: Float
)

@Serializable
private data class SerializableGameState(
    val ball: SerializableBall,
    val player1Paddle: SerializablePaddle,
    val player2Paddle: SerializablePaddle,
    val player1Score: Int,
    val player2Score: Int,
    val isGameOver: Boolean,
    val ballFrozenUntil: Long?,
    val matchId: String = "",
    val ballCollisionCount: Int = 0,
    val player1PaddleHits: Int = 0,
    val player2PaddleHits: Int = 0
)

@Serializable
private data class SerializableConnectResponse(
    val messageType: String,
    val playerId: String,
    val gameState: SerializableGameState?
)

@Serializable
private data class SerializablePaddleUpdate(
    val messageType: String,
    val playerId: String,
    val paddle: SerializablePaddle
)

@Serializable
private data class SerializableGameStateUpdate(
    val messageType: String,
    val gameState: SerializableGameState
)

@Serializable
private data class SerializableStartGameResponse(
    val messageType: String,
    val gameState: SerializableGameState
)

@Serializable
private data class SerializableError(
    val messageType: String,
    val error: String
)

object MessageSerializer {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun serialize(message: NetworkMessage): String {
        return when (message) {
            is NetworkMessage.ConnectRequest -> json.encodeToString(mapOf(Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE to message.messageType))
            is NetworkMessage.ConnectResponse -> {
                val serializable = SerializableConnectResponse(
                    messageType = message.messageType,
                    playerId = message.playerId.name,
                    gameState = message.gameState?.let { serializeGameState(it) }
                )
                json.encodeToString(serializable)
            }
            is NetworkMessage.PaddleUpdate -> {
                val serializable = SerializablePaddleUpdate(
                    messageType = message.messageType,
                    playerId = message.playerId.name,
                    paddle = serializePaddle(message.paddle)
                )
                json.encodeToString(serializable)
            }
            is NetworkMessage.GameStateUpdate -> {
                val serializable = SerializableGameStateUpdate(
                    messageType = message.messageType,
                    gameState = serializeGameState(message.gameState)
                )
                json.encodeToString(serializable)
            }
            is NetworkMessage.StartGameRequest -> json.encodeToString(mapOf(Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE to message.messageType))
            is NetworkMessage.StartGameResponse -> {
                val serializable = SerializableStartGameResponse(
                    messageType = message.messageType,
                    gameState = serializeGameState(message.gameState)
                )
                json.encodeToString(serializable)
            }
            is NetworkMessage.Error -> {
                val serializable = SerializableError(
                    messageType = message.messageType,
                    error = message.error
                )
                json.encodeToString(serializable)
            }
            is NetworkMessage.Ping -> json.encodeToString(mapOf(Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE to message.messageType))
            is NetworkMessage.Pong -> json.encodeToString(mapOf(Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE to message.messageType))
        }
    }

    fun deserialize(jsonString: String): NetworkMessage {
        val jsonObj = try {
            json.parseToJsonElement(jsonString).jsonObject
        } catch (e: Exception) {
            throw IllegalArgumentException(Constants.ERROR_MESSAGE_INVALID_JSON.format(jsonString), e)
        }
        val messageType = jsonObj[Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE]?.jsonPrimitive?.content
            ?: throw IllegalArgumentException(Constants.ERROR_MESSAGE_MISSING_MESSAGE_TYPE)

        return when (messageType) {
            Constants.NETWORK_MSG_CONNECT -> NetworkMessage.ConnectRequest()
            Constants.NETWORK_MSG_CONNECT_RESPONSE -> {
                val response = json.decodeFromString<SerializableConnectResponse>(jsonString)
                NetworkMessage.ConnectResponse(
                    playerId = PlayerId.valueOf(response.playerId),
                    gameState = response.gameState?.let { deserializeGameState(it) }
                )
            }
            Constants.NETWORK_MSG_PADDLE_UPDATE -> {
                val update = json.decodeFromString<SerializablePaddleUpdate>(jsonString)
                NetworkMessage.PaddleUpdate(
                    playerId = PlayerId.valueOf(update.playerId),
                    paddle = deserializePaddle(update.paddle)
                )
            }
            Constants.NETWORK_MSG_GAME_STATE_UPDATE -> {
                val update = json.decodeFromString<SerializableGameStateUpdate>(jsonString)
                NetworkMessage.GameStateUpdate(
                    gameState = deserializeGameState(update.gameState)
                )
            }
            Constants.NETWORK_MSG_START_GAME -> NetworkMessage.StartGameRequest()
            Constants.NETWORK_MSG_START_GAME_RESPONSE -> {
                val response = json.decodeFromString<SerializableStartGameResponse>(jsonString)
                NetworkMessage.StartGameResponse(
                    gameState = deserializeGameState(response.gameState)
                )
            }
            Constants.NETWORK_MSG_ERROR -> {
                val error = json.decodeFromString<SerializableError>(jsonString)
                NetworkMessage.Error(error = error.error)
            }
            Constants.NETWORK_MSG_PING -> NetworkMessage.Ping()
            Constants.NETWORK_MSG_PONG -> NetworkMessage.Pong()
            else -> throw IllegalArgumentException(Constants.ERROR_MESSAGE_UNKNOWN_MESSAGE_TYPE.format(messageType))
        }
    }

    private fun serializePaddle(paddle: Paddle): SerializablePaddle {
        return SerializablePaddle(
            x = paddle.x, y = paddle.y,
            width = paddle.width, height = paddle.height,
            velocityY = paddle.velocityY
        )
    }

    private fun deserializePaddle(paddle: SerializablePaddle): Paddle {
        return Paddle(
            x = paddle.x, y = paddle.y,
            width = paddle.width, height = paddle.height,
            velocityY = paddle.velocityY
        )
    }

    private fun serializeBall(ball: Ball): SerializableBall {
        return SerializableBall(
            x = ball.x, y = ball.y,
            velocityX = ball.velocityX, velocityY = ball.velocityY,
            radius = ball.radius
        )
    }

    private fun deserializeBall(ball: SerializableBall): Ball {
        return Ball(
            x = ball.x, y = ball.y,
            velocityX = ball.velocityX, velocityY = ball.velocityY,
            radius = ball.radius
        )
    }

    private fun serializeGameState(state: GameState): SerializableGameState {
        return SerializableGameState(
            ball = serializeBall(state.ball),
            player1Paddle = serializePaddle(state.player1Paddle),
            player2Paddle = serializePaddle(state.player2Paddle),
            player1Score = state.player1Score,
            player2Score = state.player2Score,
            isGameOver = state.isGameOver,
            ballFrozenUntil = state.ballFrozenUntil,
            matchId = state.matchId,
            ballCollisionCount = state.ballCollisionCount,
            player1PaddleHits = state.player1PaddleHits,
            player2PaddleHits = state.player2PaddleHits
        )
    }

    private fun deserializeGameState(state: SerializableGameState): GameState {
        return GameState(
            ball = deserializeBall(state.ball),
            player1Paddle = deserializePaddle(state.player1Paddle),
            player2Paddle = deserializePaddle(state.player2Paddle),
            player1Score = state.player1Score,
            player2Score = state.player2Score,
            isGameOver = state.isGameOver,
            ballFrozenUntil = state.ballFrozenUntil,
            matchId = state.matchId,
            ballCollisionCount = state.ballCollisionCount,
            player1PaddleHits = state.player1PaddleHits,
            player2PaddleHits = state.player2PaddleHits
        )
    }
}

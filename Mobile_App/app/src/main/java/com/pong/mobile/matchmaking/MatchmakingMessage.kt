package com.pong.mobile.matchmaking

import com.pong.mobile.Constants
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Serializable
sealed class MatchmakingMessage {
    @Serializable
    data class QueueJoin(val messageType: String = "QUEUE_JOIN") : MatchmakingMessage()

    @Serializable
    data class QueueWaiting(val messageType: String = "QUEUE_WAITING") : MatchmakingMessage()

    @Serializable
    data class GameReady(
        val messageType: String = "GAME_READY",
        val host: String,
        val port: Int,
        val sessionId: String = ""
    ) : MatchmakingMessage()

    @Serializable
    data class MatchmakingError(
        val messageType: String = "MATCHMAKING_ERROR",
        val error: String
    ) : MatchmakingMessage()
}

object MatchmakingSerializer {
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun encode(message: MatchmakingMessage): String = json.encodeToString(message)

    fun decode(line: String): MatchmakingMessage {
        val obj = json.parseToJsonElement(line).jsonObject
        val messageType = obj[Constants.NETWORK_MSG_FIELD_MESSAGE_TYPE]?.jsonPrimitive?.content
            ?: throw IllegalArgumentException(Constants.ERROR_MESSAGE_MISSING_MESSAGE_TYPE)
        return when (messageType) {
            Constants.MATCHMAKING_MSG_QUEUE_JOIN -> json.decodeFromString<MatchmakingMessage.QueueJoin>(line)
            Constants.MATCHMAKING_MSG_QUEUE_WAITING -> json.decodeFromString<MatchmakingMessage.QueueWaiting>(line)
            Constants.MATCHMAKING_MSG_GAME_READY -> json.decodeFromString<MatchmakingMessage.GameReady>(line)
            Constants.MATCHMAKING_MSG_MATCHMAKING_ERROR -> json.decodeFromString<MatchmakingMessage.MatchmakingError>(line)
            else -> throw IllegalArgumentException(Constants.ERROR_MESSAGE_UNKNOWN_MESSAGE_TYPE.format(messageType))
        }
    }
}

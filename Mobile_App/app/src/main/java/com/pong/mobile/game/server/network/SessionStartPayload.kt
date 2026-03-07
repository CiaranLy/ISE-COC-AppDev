package com.pong.mobile.game.server.network

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import java.time.Instant

private val sessionStartJson = Json {
    ignoreUnknownKeys = true
    encodeDefaults = true
}

@Serializable
data class SessionStartPayload(
    val type: String = "session_start",
    val timestamp: String,
    val session_id: String
) {
    companion object {
        fun create(sessionId: String): SessionStartPayload =
            SessionStartPayload(timestamp = Instant.now().toString(), session_id = sessionId)

        fun toJson(payload: SessionStartPayload): String =
            sessionStartJson.encodeToString(payload)

        fun fromJson(jsonString: String): SessionStartPayload =
            sessionStartJson.decodeFromString(jsonString)

        fun isSessionStart(jsonString: String): Boolean =
            runCatching { fromJson(jsonString).type == "session_start" }.getOrElse { false }
    }
}

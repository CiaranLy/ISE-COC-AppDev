package com.pong.mobile.game.server

import com.pong.mobile.game.GameState
import com.pong.mobile.game.Paddle
import com.pong.mobile.game.PlayerId

interface GameServer {
    fun connect(): Boolean
    fun disconnect()
    fun startGame(): GameState
    fun updatePaddle(playerId: PlayerId, paddle: Paddle)
    fun getGameState(): GameState
    fun isConnected(): Boolean
    fun getLocalPlayerId(): PlayerId
}

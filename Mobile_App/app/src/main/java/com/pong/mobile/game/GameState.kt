package com.pong.mobile.game

data class GameState(
    val ball: Ball,
    val player1Paddle: Paddle,
    val player2Paddle: Paddle,
    val player1Score: Int,
    val player2Score: Int,
    val isGameOver: Boolean,
    val ballFrozenUntil: Long? = null,
    val matchId: String = "",
    val ballCollisionCount: Int = 0,
    val player1PaddleHits: Int = 0,
    val player2PaddleHits: Int = 0
)

data class Ball(
    val x: Float,
    val y: Float,
    val velocityX: Float,
    val velocityY: Float,
    val radius: Float
)

data class Paddle(
    val x: Float,
    val y: Float,
    val width: Float,
    val height: Float,
    val velocityY: Float
)

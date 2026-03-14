package com.pong.mobile.game

import com.pong.mobile.game.server.GameServer
import com.pong.mobile.game.util.PaddleUtils
import kotlin.math.absoluteValue

class GameEngine(
    private val gameServer: GameServer,
    private val gameWidth: Float,
    private val gameHeight: Float
) {
    internal data class CollisionResult(
        val ball: Ball,
        val player1Score: Int,
        val player2Score: Int,
        val ballFrozenUntil: Long?,
        val paddleCollisionCount: Int = 0,
        val player1PaddleHit: Boolean = false,
        val player2PaddleHit: Boolean = false
    )

    fun update(deltaTime: Float, localPlayerDirection: Float, currentTimeMs: Long): GameState {
        val currentState = gameServer.getGameState()
        val localPlayerId = gameServer.getLocalPlayerId()

        val updatedPlayer1Paddle = if (localPlayerId == PlayerId.Player1) {
            updateLocalPlayerPaddle(currentState.player1Paddle, localPlayerDirection, deltaTime)
        } else {
            currentState.player1Paddle
        }

        val updatedPlayer2Paddle = if (localPlayerId == PlayerId.Player2) {
            updateLocalPlayerPaddle(currentState.player2Paddle, localPlayerDirection, deltaTime)
        } else {
            currentState.player2Paddle
        }

        val isBallFrozen = isBallFrozen(currentState, currentTimeMs)
        val (updatedBall, wallBounceCount) = if (isBallFrozen) {
            currentState.ball to 0
        } else {
            updateBall(currentState.ball, deltaTime)
        }

        val collisionResult = checkCollisions(
            updatedBall, updatedPlayer1Paddle, updatedPlayer2Paddle,
            currentState.player1Score, currentState.player2Score,
            currentState.ballFrozenUntil, currentTimeMs
        )

        val isGameOver = isGameOver(collisionResult.player1Score, collisionResult.player2Score)
        val ballFrozenUntil = calculateBallFrozenUntil(isGameOver, collisionResult.ballFrozenUntil)
        val newBallCollisionCount = currentState.ballCollisionCount + wallBounceCount + collisionResult.paddleCollisionCount

        val newState = GameState(
            ball = collisionResult.ball,
            player1Paddle = updatedPlayer1Paddle,
            player2Paddle = updatedPlayer2Paddle,
            player1Score = collisionResult.player1Score,
            player2Score = collisionResult.player2Score,
            isGameOver = isGameOver,
            ballFrozenUntil = ballFrozenUntil,
            matchId = currentState.matchId,
            ballCollisionCount = newBallCollisionCount,
            player1PaddleHits = currentState.player1PaddleHits + if (collisionResult.player1PaddleHit) 1 else 0,
            player2PaddleHits = currentState.player2PaddleHits + if (collisionResult.player2PaddleHit) 1 else 0
        )

        gameServer.updatePaddle(localPlayerId, if (localPlayerId == PlayerId.Player1) updatedPlayer1Paddle else updatedPlayer2Paddle)

        return newState
    }

    private fun isBallFrozen(gameState: GameState, currentTimeMs: Long): Boolean {
        return gameState.ballFrozenUntil != null && currentTimeMs < gameState.ballFrozenUntil
    }

    private fun isGameOver(player1Score: Int, player2Score: Int): Boolean {
        return player1Score >= GameConstants.WINNING_SCORE || player2Score >= GameConstants.WINNING_SCORE
    }

    private fun calculateBallFrozenUntil(isGameOver: Boolean, currentBallFrozenUntil: Long?): Long? {
        return if (isGameOver) null else currentBallFrozenUntil
    }

    private fun updateLocalPlayerPaddle(
        paddle: Paddle,
        direction: Float,
        deltaTime: Float
    ): Paddle {
        val newY = PaddleUtils.calculateNewY(paddle.y, direction, deltaTime, gameHeight, paddle.height)
        val velocityY = PaddleUtils.calculateVelocityY(direction)

        return paddle.copy(y = newY, velocityY = velocityY)
    }

    internal fun updateBall(ball: Ball, deltaTime: Float): Pair<Ball, Int> {
        var newX = ball.x + ball.velocityX * deltaTime
        var newY = ball.y + ball.velocityY * deltaTime
        var newVelX = ball.velocityX
        var newVelY = ball.velocityY
        var wallBounceCount = 0

        val isWallCollision = newY <= ball.radius || newY >= gameHeight - ball.radius
        if (isWallCollision) {
            newVelY = -newVelY
            newY = newY.coerceIn(ball.radius, gameHeight - ball.radius)
            wallBounceCount = 1
        }

        return Ball(
            x = newX, y = newY,
            velocityX = newVelX, velocityY = newVelY,
            radius = ball.radius
        ) to wallBounceCount
    }

    internal fun checkCollisions(
        ball: Ball,
        player1Paddle: Paddle,
        player2Paddle: Paddle,
        currentPlayer1Score: Int,
        currentPlayer2Score: Int,
        currentFreezeTime: Long?,
        currentTimeMs: Long
    ): CollisionResult {
        var updatedBall = ball
        var player1Score = currentPlayer1Score
        var player2Score = currentPlayer2Score
        var newFreezeTime = currentFreezeTime
        var paddleCollisionCount = 0
        var player1PaddleHit = false
        var player2PaddleHit = false

        val isCollidingWithPlayer1 = ball.x - ball.radius <= player1Paddle.x + player1Paddle.width &&
            ball.x + ball.radius >= player1Paddle.x &&
            ball.y - ball.radius <= player1Paddle.y + player1Paddle.height &&
            ball.y + ball.radius >= player1Paddle.y

        if (isCollidingWithPlayer1) {
            paddleCollisionCount = 1
            player1PaddleHit = true
            val paddleCenterY = PaddleUtils.calculatePaddleCenterY(player1Paddle)
            val relativeIntersectY = paddleCenterY - ball.y
            val normalizedIntersectY = PaddleUtils.calculateNormalizedIntersectY(relativeIntersectY, player1Paddle)
            val baseSpeed = ball.velocityX.absoluteValue * GameConstants.BALL_ACCELERATION_FACTOR
            val newVelocityY = normalizedIntersectY * baseSpeed * GameConstants.BOUNCE_ANGLE_MULTIPLIER

            updatedBall = ball.copy(
                x = player1Paddle.x + player1Paddle.width + ball.radius,
                velocityX = baseSpeed,
                velocityY = newVelocityY
            )
        }

        val isCollidingWithPlayer2 = ball.x + ball.radius >= player2Paddle.x &&
            ball.x - ball.radius <= player2Paddle.x + player2Paddle.width &&
            ball.y - ball.radius <= player2Paddle.y + player2Paddle.height &&
            ball.y + ball.radius >= player2Paddle.y

        if (isCollidingWithPlayer2) {
            paddleCollisionCount = 1
            player2PaddleHit = true
            val paddleCenterY = PaddleUtils.calculatePaddleCenterY(player2Paddle)
            val relativeIntersectY = paddleCenterY - ball.y
            val normalizedIntersectY = PaddleUtils.calculateNormalizedIntersectY(relativeIntersectY, player2Paddle)
            val baseSpeed = ball.velocityX.absoluteValue * GameConstants.BALL_ACCELERATION_FACTOR
            val newVelocityY = normalizedIntersectY * baseSpeed * GameConstants.BOUNCE_ANGLE_MULTIPLIER

            updatedBall = ball.copy(
                x = player2Paddle.x - ball.radius,
                velocityX = -baseSpeed,
                velocityY = newVelocityY
            )
        }

        val isOutOfBoundsLeft = ball.x < 0
        if (isOutOfBoundsLeft) {
            player2Score++
            updatedBall = ball.copy(
                x = gameWidth / GameConstants.CENTER_DIVISOR,
                y = gameHeight / GameConstants.CENTER_DIVISOR,
                velocityX = GameConstants.INITIAL_BALL_VELOCITY_X,
                velocityY = GameConstants.INITIAL_BALL_VELOCITY_Y
            )
            newFreezeTime = currentTimeMs + GameConstants.POINT_START_BALL_FREEZE_DURATION_MS
        }

        val isOutOfBoundsRight = ball.x > gameWidth
        if (isOutOfBoundsRight) {
            player1Score++
            updatedBall = ball.copy(
                x = gameWidth / GameConstants.CENTER_DIVISOR,
                y = gameHeight / GameConstants.CENTER_DIVISOR,
                velocityX = -GameConstants.INITIAL_BALL_VELOCITY_X,
                velocityY = GameConstants.INITIAL_BALL_VELOCITY_Y
            )
            newFreezeTime = currentTimeMs + GameConstants.POINT_START_BALL_FREEZE_DURATION_MS
        }

        return CollisionResult(updatedBall, player1Score, player2Score, newFreezeTime, paddleCollisionCount, player1PaddleHit, player2PaddleHit)
    }
}

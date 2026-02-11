package com.pong.mobile.game.util

import com.pong.mobile.game.Ball
import com.pong.mobile.game.GameConstants
import com.pong.mobile.game.Paddle

object PaddleUtils {
    const val MIN_DIRECTION = -1f
    const val MAX_DIRECTION = 1f
    const val NO_MOVEMENT_DIRECTION = 0f

    fun calculateNewY(
        currentPaddleY: Float,
        direction: Float,
        deltaTime: Float,
        gameHeight: Float,
        paddleHeight: Float,
        speedMultiplier: Float = 1f
    ): Float {
        val movement = direction * GameConstants.PADDLE_SPEED * speedMultiplier * deltaTime
        return (currentPaddleY + movement).coerceIn(0f, gameHeight - paddleHeight)
    }

    fun calculateVelocityY(direction: Float, speedMultiplier: Float = 1f): Float {
        return direction * GameConstants.PADDLE_SPEED * speedMultiplier
    }

    fun calculateTargetY(ball: Ball, paddle: Paddle): Float {
        return ball.y - paddle.height / GameConstants.CENTER_DIVISOR
    }

    fun calculateDirection(targetY: Float, currentPaddleY: Float): Float {
        return (targetY - currentPaddleY).coerceIn(MIN_DIRECTION, MAX_DIRECTION)
    }

    fun calculatePaddleCenterY(paddle: Paddle): Float {
        return paddle.y + paddle.height / GameConstants.CENTER_DIVISOR
    }

    fun calculatePaddleHalfHeight(paddle: Paddle): Float {
        return paddle.height / GameConstants.CENTER_DIVISOR
    }

    fun calculateNormalizedIntersectY(relativeIntersectY: Float, paddle: Paddle): Float {
        return relativeIntersectY / calculatePaddleHalfHeight(paddle)
    }
}

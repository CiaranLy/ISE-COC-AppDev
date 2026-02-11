package com.pong.mobile.util

import com.pong.mobile.Constants

object TimeUtils {
    fun calculateDeltaTime(currentTimeNanos: Long, lastTimeNanos: Long): Float {
        return (currentTimeNanos - lastTimeNanos) / Constants.NANOSECONDS_PER_SECOND
    }

    fun isValidDeltaTime(deltaTime: Float): Boolean {
        return deltaTime > 0f && deltaTime < 1f
    }
}

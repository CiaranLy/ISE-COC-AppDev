package com.pong.mobile.ui.components

import androidx.compose.ui.Modifier

object ButtonFactory {
    fun createStandardButton(
        text: String,
        onClick: () -> Unit,
        modifier: Modifier = Modifier
    ): BaseButton {
        return BaseButton(
            text = text,
            onClick = onClick,
            modifier = modifier
        )
    }
}

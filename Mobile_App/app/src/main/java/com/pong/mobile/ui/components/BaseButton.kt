package com.pong.mobile.ui.components

import androidx.compose.ui.Modifier

data class BaseButton(
    override val text: String,
    override val onClick: () -> Unit,
    override val modifier: Modifier = Modifier,
    override val width: Int = 300,
    override val height: Int = 60
) : ButtonSpec

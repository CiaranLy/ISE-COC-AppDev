package com.pong.mobile.ui.components

import androidx.compose.ui.Modifier

interface ButtonSpec {
    val text: String
    val onClick: () -> Unit
    val modifier: Modifier
    val width: Int
    val height: Int
}

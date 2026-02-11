package com.pong.mobile.ui.components

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ButtonComposable(
    buttonSpec: ButtonSpec,
    modifier: Modifier = Modifier
) {
    val combinedModifier = buttonSpec.modifier
        .then(modifier)
        .width(buttonSpec.width.dp)
        .height(buttonSpec.height.dp)

    Button(
        onClick = { buttonSpec.onClick() },
        modifier = combinedModifier
    ) {
        Text(
            text = buttonSpec.text,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

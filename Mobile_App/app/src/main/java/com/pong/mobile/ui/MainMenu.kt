package com.pong.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pong.mobile.Constants
import com.pong.mobile.ui.components.ButtonComposable
import com.pong.mobile.ui.components.ButtonFactory

object MainMenu {
    @Composable
    fun Content(
        onSingleplayerClick: () -> Unit,
        onFindMatchClick: () -> Unit,
        onSettingsClick: () -> Unit,
        onMatchHistoryClick: () -> Unit
    ) {
        val singleplayerButton = ButtonFactory.createStandardButton(
            text = Constants.UI_BUTTON_SINGLEPLAYER,
            onClick = onSingleplayerClick
        )

        val findMatchButton = ButtonFactory.createStandardButton(
            text = Constants.UI_BUTTON_FIND_MATCH,
            onClick = onFindMatchClick
        )

        val settingsButton = ButtonFactory.createStandardButton(
            text = Constants.UI_BUTTON_SETTINGS,
            onClick = onSettingsClick
        )

        val matchHistoryButton = ButtonFactory.createStandardButton(
            text = Constants.UI_BUTTON_MATCH_HISTORY,
            onClick = onMatchHistoryClick
        )

        Box(modifier = Modifier.fillMaxSize()) {
            Text(
                text = Constants.APPLICATION_NAME,
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 32.dp)
            )

            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                ButtonComposable(buttonSpec = singleplayerButton)
                ButtonComposable(buttonSpec = findMatchButton)
                ButtonComposable(buttonSpec = settingsButton)
                ButtonComposable(buttonSpec = matchHistoryButton)
            }
        }
    }
}

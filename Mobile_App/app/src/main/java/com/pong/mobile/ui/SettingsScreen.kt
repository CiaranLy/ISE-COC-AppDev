package com.pong.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pong.mobile.Constants
import com.pong.mobile.config.Config

object SettingsScreen {
    @Composable
    fun Content(onBack: () -> Unit) {
        val context = LocalContext.current
        val config = Config.current

        var gameServerHost by remember { mutableStateOf(config.gameServerHost) }
        var gameServerPort by remember { mutableStateOf(config.gameServerPort.toString()) }
        var matchmakingHost by remember { mutableStateOf(config.matchmakingHost) }
        var matchmakingPort by remember { mutableStateOf(config.matchmakingPort.toString()) }
        var statusMessage by remember { mutableStateOf("") }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = Constants.UI_SETTINGS_TITLE,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 24.dp)
            )

            OutlinedTextField(
                value = gameServerHost,
                onValueChange = { gameServerHost = it },
                label = { Text(Constants.UI_SETTINGS_SERVER_ADDRESS) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = gameServerPort,
                onValueChange = { gameServerPort = it },
                label = { Text(Constants.UI_SETTINGS_GAME_SERVER_PORT) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = matchmakingHost,
                onValueChange = { matchmakingHost = it },
                label = { Text(Constants.UI_SETTINGS_MATCHMAKING_HOST) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = matchmakingPort,
                onValueChange = { matchmakingPort = it },
                label = { Text(Constants.UI_SETTINGS_MATCHMAKING_PORT) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(16.dp))

            if (statusMessage.isNotEmpty()) {
                Text(text = statusMessage, modifier = Modifier.padding(bottom = 8.dp))
            }

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = onBack) {
                    Text(Constants.UI_BUTTON_BACK)
                }
                Button(onClick = {
                    val portNum = gameServerPort.toIntOrNull()
                    val mmPortNum = matchmakingPort.toIntOrNull()
                    if (portNum == null || portNum < Constants.PORT_MIN || portNum > Constants.PORT_MAX ||
                        mmPortNum == null || mmPortNum < Constants.PORT_MIN || mmPortNum > Constants.PORT_MAX
                    ) {
                        statusMessage = Constants.UI_SETTINGS_PORT_INVALID
                        return@Button
                    }
                    Config.save(
                        context,
                        Config.current.copy(
                            gameServerHost = gameServerHost,
                            gameServerPort = portNum,
                            matchmakingHost = matchmakingHost,
                            matchmakingPort = mmPortNum
                        )
                    )
                    statusMessage = Constants.UI_SETTINGS_SAVED
                }) {
                    Text(Constants.UI_BUTTON_SAVE)
                }
            }
        }
    }
}

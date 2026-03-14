package com.pong.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.pong.mobile.Constants
import com.pong.mobile.config.Config
import com.pong.mobile.matchmaking.GameServerEndpoint
import com.pong.mobile.matchmaking.MatchmakingClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object QueueingScreen {
    @Composable
    fun Content(onBack: () -> Unit, onMatchFound: (GameServerEndpoint) -> Unit) {
        var hasError by remember { mutableStateOf(false) }

        LaunchedEffect(Unit) {
            val endpoint = withContext(Dispatchers.IO) {
                MatchmakingClient(
                    Config.current.matchmakingHost,
                    Config.current.matchmakingPort
                ).findMatch()
            }
            if (endpoint != null) {
                onMatchFound(endpoint)
            } else {
                hasError = true
            }
        }

        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(24.dp)
            ) {
                Text(
                    text = "Matchmaking",
                    fontSize = 32.sp,
                    fontWeight = FontWeight.Bold
                )

                if (hasError) {
                    Text(
                        text = Constants.ERROR_MESSAGE_MATCHMAKING_CONNECT,
                        color = MaterialTheme.colorScheme.error,
                        fontSize = 18.sp
                    )
                    Button(onClick = onBack) {
                        Text(Constants.UI_BUTTON_BACK)
                    }
                } else {
                    CircularProgressIndicator(modifier = Modifier.size(64.dp))
                    Text(
                        text = Constants.UI_MATCHMAKING_WAITING,
                        fontSize = 20.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Button(onClick = onBack) {
                        Text("Cancel")
                    }
                }
            }
        }
    }
}

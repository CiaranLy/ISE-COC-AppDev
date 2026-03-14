package com.pong.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pong.mobile.Constants
import com.pong.mobile.data.MatchResult
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object MatchDetailScreen {
    @Composable
    fun Content(matchId: Int, onBack: () -> Unit) {
        val viewModel: MatchHistoryViewModel = viewModel()
        val match by viewModel.getMatchById(matchId).collectAsStateWithLifecycle(null)

        Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(onClick = onBack) {
                    Text(Constants.UI_BUTTON_BACK)
                }
                Spacer(modifier = Modifier.width(16.dp))
                Text(
                    text = Constants.UI_MATCH_DETAILS_TITLE,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            if (match == null) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                val m = match!!
                val resultText = if (m.won) Constants.UI_MATCH_RESULT_WIN else Constants.UI_MATCH_RESULT_LOSS
                val resultColor = if (m.won) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error

                Card(modifier = Modifier.fillMaxWidth().padding(8.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = resultText,
                            fontWeight = FontWeight.Bold,
                            fontSize = 32.sp,
                            color = resultColor,
                            modifier = Modifier.align(Alignment.CenterHorizontally)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(text = "Game Mode: ${m.gameMode.replaceFirstChar { it.uppercase() }}", fontSize = 18.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = "Player Score: ${m.playerScore}", fontSize = 18.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = "Opponent Score: ${m.opponentScore}", fontSize = 18.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        val dateFormat = SimpleDateFormat("MMM dd, yyyy HH:mm:ss", Locale.getDefault())
                        Text(text = "Date: ${dateFormat.format(Date(m.timestamp))}", fontSize = 18.sp)
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(text = "Session ID: ${m.matchId}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

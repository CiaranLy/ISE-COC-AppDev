package com.pong.mobile.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.provider.Settings
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.pong.mobile.Constants
import com.pong.mobile.data.MatchResult
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object MatchHistoryScreen {
    @Composable
    fun Content(onBack: () -> Unit, onMatchClick: (Int) -> Unit) {
        val viewModel: MatchHistoryViewModel = viewModel()
        val matches by viewModel.matches.collectAsStateWithLifecycle()
        val isSyncing by viewModel.isSyncing.collectAsStateWithLifecycle()
        
        val context = LocalContext.current
        val deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: Constants.DEVICE_ID_UNKNOWN

        LaunchedEffect(Unit) {
            viewModel.startSyncingMatches(deviceId)
        }

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
                    text = Constants.UI_MATCH_HISTORY_TITLE,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (isSyncing && matches.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator()
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = Constants.UI_MATCH_HISTORY_SYNCING, fontSize = 16.sp)
                    }
                }
            } else if (matches.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(text = Constants.UI_MATCH_HISTORY_EMPTY, fontSize = 16.sp)
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 150.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(matches) { match ->
                        MatchCard(match, onClick = { onMatchClick(match.id) })
                    }
                }
            }
        }
    }

    @Composable
    private fun MatchCard(match: MatchResult, onClick: () -> Unit) {
        val dateFormat = SimpleDateFormat("MMM dd, HH:mm", Locale.getDefault())
        val dateStr = dateFormat.format(Date(match.timestamp))
        val resultText = if (match.won) Constants.UI_MATCH_RESULT_WIN else Constants.UI_MATCH_RESULT_LOSS
        val resultColor = if (match.won) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error

        Card(modifier = Modifier.fillMaxWidth().clickable { onClick() }) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = resultText,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp,
                        color = resultColor
                    )
                    Text(text = match.gameMode.replaceFirstChar { it.uppercase() }, fontSize = 12.sp)
                    Text(text = dateStr, fontSize = 12.sp)
                }
                Text(
                    text = "${match.playerScore} - ${match.opponentScore}",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

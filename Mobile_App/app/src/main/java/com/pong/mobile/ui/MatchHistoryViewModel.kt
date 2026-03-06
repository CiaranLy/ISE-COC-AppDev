package com.pong.mobile.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pong.mobile.data.MatchDatabase
import com.pong.mobile.data.MatchRepository
import com.pong.mobile.data.MatchResult
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MatchHistoryViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = MatchRepository(
        MatchDatabase.getDatabase(application.applicationContext).matchResultDao()
    )

    val matches: StateFlow<List<MatchResult>> = repository.allMatches.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = emptyList()
    )

    fun saveMatch(result: MatchResult) {
        viewModelScope.launch {
            repository.insert(result)
        }
    }
}

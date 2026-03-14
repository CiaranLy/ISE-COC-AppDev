package com.pong.mobile.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.pong.mobile.Constants

@Database(entities = [MatchResult::class], version = 1, exportSchema = false)
abstract class MatchDatabase : RoomDatabase() {
    abstract fun matchResultDao(): MatchResultDao

    companion object {
        @Volatile private var INSTANCE: MatchDatabase? = null

        fun getDatabase(context: Context): MatchDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(
                    context.applicationContext,
                    MatchDatabase::class.java,
                    Constants.DATABASE_NAME
                ).build().also { INSTANCE = it }
            }
        }
    }
}

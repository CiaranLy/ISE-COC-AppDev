package com.pong.mobile

object Constants {
    const val APPLICATION_NAME = "Pong"
    const val GAME_WIDTH = 640f
    const val GAME_HEIGHT = 360f
    const val GAME_ORIGIN_Y = 0f
    const val VIEWPORT_BORDER_COLOR_ARGB = 0xFF1a1a1a
    const val VIEWPORT_CENTER_DIVISOR = 2
    const val VIEWPORT_MAX_SCALE_FACTOR = 1f

    const val NANOSECONDS_PER_SECOND = 1_000_000_000f
    const val TOUCH_TO_DIRECTION_SCALE = 100f

    const val DEFAULT_SERVER_PORT = 8080
    const val MATCHMAKING_DEFAULT_PORT = 9090
    const val MATCHMAKING_GAME_SERVER_PORT_RANGE_START = 8080
    const val MAX_PLAYERS = 2
    const val INITIAL_PLAYER_SCORE = 0

    const val LOCALHOST = "localhost"

    const val UI_LOADING_TEXT = "Loading..."
    const val UI_ERROR_DIALOG_TITLE = "Error"
    const val UI_ERROR_DIALOG_MESSAGE = "Failed to enter game."
    const val UI_ERROR_DIALOG_BUTTON = "OK"
    const val UI_GAME_OVER_WIN = "You Win!"
    const val UI_GAME_OVER_LOSE = "You Lose!"
    const val UI_SCORE_PLAYER_1_LABEL = "Player 1: "
    const val UI_SCORE_PLAYER_2_LABEL = "Player 2: "
    const val UI_INSTRUCTION_TEXT = "Touch and drag to control paddle | Press Back to return to menu"
    const val UI_BUTTON_SINGLEPLAYER = "Singleplayer"
    const val UI_BUTTON_FIND_MATCH = "Find Match"
    const val UI_BUTTON_SETTINGS = "Settings"
    const val UI_BUTTON_BACK = "Back"
    const val UI_BUTTON_SAVE = "Save"
    const val UI_SETTINGS_TITLE = "Settings"
    const val UI_SETTINGS_SERVER_ADDRESS = "Server Address"
    const val UI_SETTINGS_MATCHMAKING_HOST = "Matchmaking server"
    const val UI_SETTINGS_MATCHMAKING_PORT = "Matchmaking port"
    const val UI_SETTINGS_SAVED = "Settings saved."
    const val UI_SETTINGS_PORT_INVALID = "Port must be a number (1\u201365535)."
    const val UI_MATCHMAKING_WAITING = "Finding opponent..."

    const val ERROR_MESSAGE_GAME_NOT_STARTED = "Game not started"
    const val ERROR_MESSAGE_STARTING_GAME = "Error starting game"
    const val ERROR_MESSAGE_CONNECTING_GAME_SERVER = "Failed to connect gameServer in GameScreen"
    const val ERROR_MESSAGE_CONNECTING_GAME_SCREEN = "Failed to connect in GameScreen"
    const val ERROR_MESSAGE_GETTING_GAME_STATE = "Too many consecutive errors getting game state"
    const val ERROR_MESSAGE_UPDATING_PADDLE = "Error updating paddle"
    const val ERROR_MESSAGE_CONNECTING_PLAYER_CLIENT = "Failed to connect player client to server"
    const val ERROR_MESSAGE_STARTING_GAME_RETRIES = "Failed to start game after"
    const val ERROR_MESSAGE_GAME_SERVER_NULL = "Game screen selected but gameServer is null - this should not happen"
    const val ERROR_MESSAGE_SERVER_ALREADY_RUNNING = "Local server already running, returning early"
    const val ERROR_MESSAGE_NETWORK_SERVER_FAILED_TO_START = "Network server failed to start"
    const val ERROR_MESSAGE_MATCHMAKING_CONNECT = "Failed to connect to matchmaking server"
    const val ERROR_MESSAGE_EXPECTED_CONNECT = "Expected CONNECT message"
    const val ERROR_MESSAGE_SERVER_FULL = "Server is full (%d players maximum)"
    const val ERROR_MESSAGE_EXPECTED_QUEUE_JOIN = "Expected QUEUE_JOIN"
    const val ERROR_MESSAGE_UNKNOWN = "Unknown error"
    const val ERROR_MESSAGE_COULD_NOT_START_GAME_SERVER = "Could not start game server"
    const val ERROR_MESSAGE_MISSING_MESSAGE_TYPE = "Missing messageType"
    const val ERROR_MESSAGE_UNKNOWN_MESSAGE_TYPE = "Unknown message type: %s"
    const val ERROR_MESSAGE_INVALID_JSON = "Invalid JSON: %s"
    const val ERROR_MESSAGE_PORT_IN_USE = "Failed to start server on port %d: Port is already in use."
    const val ERROR_MESSAGE_FAILED_START_SERVER = "Failed to start server on port %d"

    const val NETWORK_MSG_CONNECT = "CONNECT"
    const val NETWORK_MSG_CONNECT_RESPONSE = "CONNECT_RESPONSE"
    const val NETWORK_MSG_PADDLE_UPDATE = "PADDLE_UPDATE"
    const val NETWORK_MSG_GAME_STATE_UPDATE = "GAME_STATE_UPDATE"
    const val NETWORK_MSG_START_GAME = "START_GAME"
    const val NETWORK_MSG_START_GAME_RESPONSE = "START_GAME_RESPONSE"
    const val NETWORK_MSG_ERROR = "ERROR"
    const val NETWORK_MSG_FIELD_MESSAGE_TYPE = "messageType"

    const val MATCHMAKING_MSG_QUEUE_JOIN = "QUEUE_JOIN"
    const val MATCHMAKING_MSG_QUEUE_WAITING = "QUEUE_WAITING"
    const val MATCHMAKING_MSG_GAME_READY = "GAME_READY"
    const val MATCHMAKING_MSG_MATCHMAKING_ERROR = "MATCHMAKING_ERROR"

    const val PORT_MIN = 1
    const val PORT_MAX = 65535
    const val SERVER_ADDRESS_PORT_SEPARATOR = ":"
}

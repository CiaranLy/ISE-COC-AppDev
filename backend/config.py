"""Application configuration."""

import os

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./database_ise_coc.db")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# API
API_TITLE = "Data Collector API"
API_VERSION = "1.0.0"

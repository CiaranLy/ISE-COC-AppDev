"""Application configuration backed by Pydantic BaseSettings."""

from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str = Field("sqlite+aiosqlite:///./database_ise_coc.db")
    db_echo: bool = Field(False)

    # API
    api_title: str = Field("Data Collector API")
    api_version: str = Field("1.0.0")

    # CORS
    cors_origins: List[str] = Field(["*"])

    # Uvicorn
    uvicorn_host: str = Field("0.0.0.0")
    uvicorn_port: int = Field(8000)
    uvicorn_workers: int = Field(4)

    # Logging
    log_level: str = Field("INFO")
    log_file: str = Field("backend.log")

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

DATABASE_URL = settings.database_url
DB_ECHO = settings.db_echo
API_TITLE = settings.api_title
API_VERSION = settings.api_version
CORS_ORIGINS = settings.cors_origins
UVICORN_HOST = settings.uvicorn_host
UVICORN_PORT = settings.uvicorn_port
UVICORN_WORKERS = settings.uvicorn_workers

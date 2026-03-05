"""
Logging configuration for the backend API.

Sets up structured logging with dual targets:
- Console: human-readable format
- File: JSON format for machine parsing
"""

import logging
import logging.handlers
import os
from pathlib import Path

_LOG_DIR = Path(__file__).parent / "logs"
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_LOG_FILE = "backend.log"
_MAX_LOG_BYTES = 5_000_000
_BACKUP_COUNT = 3
_CONSOLE_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
_CONSOLE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_FILE_FORMAT = (
    '{"time":"%(asctime)s","name":"%(name)s",'
    '"level":"%(levelname)s","message":"%(message)s"}'
)
_FILE_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", _DEFAULT_LOG_LEVEL)
    log_file = os.getenv("LOG_FILE", _DEFAULT_LOG_FILE)

    _LOG_DIR.mkdir(exist_ok=True)
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT, datefmt=_CONSOLE_DATE_FORMAT))
    root.addHandler(console)

    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_DIR / log_file,
        maxBytes=_MAX_LOG_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_FILE_DATE_FORMAT))
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


setup_logging()

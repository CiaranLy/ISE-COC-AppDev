"""
Config Manager - Thread-safe, hot-reloadable configuration.

Watches config.json for changes and automatically reloads when the file
is modified. All consumers read from the same shared instance.
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from log_config import get_logger

logger = get_logger("ConfigManager")

CONFIG_FILE = Path(__file__).parent / "config.json"
_POLL_INTERVAL_SECONDS = 2.0

DEFAULTS = {
    "api_base_url": "http://localhost:8000/api/v1",
    "collector_name": "default_collector",
    "collection_interval_seconds": 5.0,
    "batch_size": 10,
    "flush_interval_seconds": 5.0,
    "max_retries": 3,
    "retry_delay_seconds": 2.0,
    "queue_host": "localhost",
    "queue_port": 15555,
    "ack_timeout_seconds": 90,
    "dlq_file": "dead_letter_queue.json",
    "num_sender_workers": 4,
    "ws_host": "localhost",
    "desktop_collector_ws_port": 6790,
    "game_server_host": "localhost",
    "game_server_port": 8081,
    "matchmaking_host": "localhost",
    "matchmaking_telemetry_port": 9091,
    "reconnect_delay_seconds": 5.0,
    "queue_send_retries": 3,
    "snapshot_interval_seconds": 1.0,
    "log_level": "INFO",
    "log_file": "collector.log",
}


class ConfigManager:

    def __init__(self, config_path: Path = CONFIG_FILE):
        self._path = config_path
        self._lock = threading.Lock()
        self._data: dict = {}
        self._last_mtime: float = 0.0
        self._watcher_thread: Optional[threading.Thread] = None
        self._running = False
        self._load()

    def _load(self):
        try:
            mtime = os.path.getmtime(self._path)
            with open(self._path, "r") as f:
                new_data = json.load(f)
            with self._lock:
                self._data = new_data
                self._last_mtime = mtime
            logger.info("Loaded config from %s", self._path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Error loading config: %s", e)

    def _poll(self):
        while self._running:
            try:
                mtime = os.path.getmtime(self._path)
                if mtime != self._last_mtime:
                    self._load()
                    logger.info("Config reloaded (file changed)")
            except FileNotFoundError:
                pass
            time.sleep(_POLL_INTERVAL_SECONDS)

    def start_watching(self):
        if self._running:
            return
        self._running = True
        self._watcher_thread = threading.Thread(
            target=self._poll, daemon=True, name="config-watcher"
        )
        self._watcher_thread.start()

    def stop_watching(self):
        self._running = False
        if self._watcher_thread:
            self._watcher_thread.join(timeout=_POLL_INTERVAL_SECONDS + 1)
            self._watcher_thread = None

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            val = self._data.get(key)
        if val is not None:
            return val
        if default is not None:
            return default
        return DEFAULTS.get(key)

    def snapshot(self) -> dict:
        """Return a copy of the full config at this moment."""
        with self._lock:
            merged = {**DEFAULTS, **self._data}
        return merged


config = ConfigManager()
config.start_watching()

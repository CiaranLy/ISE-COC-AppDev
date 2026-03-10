"""
Queue Client - Connects to the Queue Manager to send data.

Supports automatic reconnection with retries when connection is lost.
"""

import json
import socket
import time

from config_manager import config as app_config
from log_config import get_logger

logger = get_logger("QueueClient")

SOCKET_TIMEOUT_SECONDS = 5.0
DEFAULT_SEND_RETRIES = 3
DEFAULT_RECONNECT_DELAY = 2.0


class QueueNotRunningError(Exception):
    """Raised when trying to connect to a queue that isn't running."""
    pass


class QueueClient:
    """Client for sending data to the Queue Manager."""

    def __init__(self, host: str = None, port: int = None):
        if host is None:
            host = app_config.get("queue_host", "localhost")
        if port is None:
            port = app_config.get("queue_port", 15555)

        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

    def connect(self):
        """Connect to the Queue Manager. Raises QueueNotRunningError if not available."""
        if self.connected:
            return

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(SOCKET_TIMEOUT_SECONDS)

        try:
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info("Connected to queue at %s:%d", self.host, self.port)
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            self._force_close_socket()
            raise QueueNotRunningError(
                f"Queue Manager is not running at {self.host}:{self.port}. "
                f"Start it first with: python queue_manager.py"
            ) from e

    def _attempt_reconnect(self) -> bool:
        """Try to reconnect. Returns True if reconnected."""
        self._force_close_socket()
        self.connected = False
        try:
            self.connect()
            return True
        except QueueNotRunningError:
            return False

    def send(self, data: dict, retries: int = None):
        """Send a data point to the queue. Retries with reconnection on connection loss."""
        if retries is None:
            retries = app_config.get("queue_send_retries", DEFAULT_SEND_RETRIES)
        reconnect_delay = app_config.get("retry_delay_seconds", DEFAULT_RECONNECT_DELAY)

        for attempt in range(retries):
            if not self.connected:
                if not self._attempt_reconnect():
                    if attempt < retries - 1:
                        time.sleep(reconnect_delay)
                        continue
                    raise QueueNotRunningError(
                        f"Queue Manager is not running at {self.host}:{self.port}"
                    ) from None

            try:
                message = json.dumps(data) + '\n'
                self.socket.sendall(message.encode('utf-8'))
                return
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                logger.warning("Send failed (attempt %d/%d): %s", attempt + 1, retries, e)
                self.connected = False
                self._force_close_socket()
                if attempt < retries - 1:
                    time.sleep(reconnect_delay)
                else:
                    raise QueueNotRunningError(
                        f"Lost connection to Queue Manager after {retries} retries: {e}"
                    ) from e

    def _force_close_socket(self):
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None

    def close(self):
        """Close the connection."""
        self._force_close_socket()
        self.connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

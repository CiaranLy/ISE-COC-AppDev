"""
Queue Client - Connects to the Queue Manager to send data.

Raises an error if the Queue Manager is not running.
"""

import json
import socket

from config_manager import config as app_config
from log_config import get_logger

logger = get_logger("QueueClient")

SOCKET_TIMEOUT_SECONDS = 5.0


class QueueNotRunningError(Exception):
    """Raised when trying to connect to a queue that isn't running."""
    pass


class QueueClient:
    """Client for sending data to the Queue Manager."""

    def __init__(self, host: str = None, port: int = None):
        if host is None:
            host = app_config.get("queue_host", "localhost")
        if port is None:
            port = app_config.get("queue_port", 5555)

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

    def send(self, data: dict):
        """Send a data point to the queue."""
        if not self.connected:
            raise QueueNotRunningError("Not connected to queue. Call connect() first.")

        try:
            message = json.dumps(data) + '\n'
            self.socket.sendall(message.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            self.connected = False
            self._force_close_socket()
            raise QueueNotRunningError(
                f"Lost connection to Queue Manager: {e}"
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

"""
Queue Client - Connects to the Queue Manager to send data.

Raises an error if the Queue Manager is not running.
"""

import json
import socket
from pathlib import Path


class QueueNotRunningError(Exception):
    """Raised when trying to connect to a queue that isn't running."""
    pass


class QueueClient:
    """Client for sending data to the Queue Manager."""
    
    def __init__(self, host: str = None, port: int = None):
        # Load config if host/port not provided
        if host is None or port is None:
            config_file = Path(__file__).parent / "config.json"
            with open(config_file, "r") as f:
                config = json.load(f)
            host = host or config["queue_host"]
            port = port or config["queue_port"]
        
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """Connect to the Queue Manager. Raises QueueNotRunningError if not available."""
        if self.connected:
            return
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5.0)
        
        try:
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[Collector] Connected to queue at {self.host}:{self.port}")
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            self.socket.close()
            self.socket = None
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
            self.socket.close()
            self.socket = None
            raise QueueNotRunningError(
                f"Lost connection to Queue Manager: {e}"
            ) from e
    
    def close(self):
        """Close the connection."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

"""
Collector - Abstract base class for WebSocket-based telemetry collectors.

Subclasses implement process_message() to convert app-specific JSON into DataPoints.
"""

import abc
import asyncio
import json
import signal
from pathlib import Path
from typing import List, Optional

import websockets

from data_point import DataPoint
from queue_client import QueueClient, QueueNotRunningError

CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r") as f:
    _config = json.load(f)

DEFAULT_WS_HOST = "localhost"
STARTUP_BANNER_WIDTH = 60


class Collector(abc.ABC):

    def __init__(
        self,
        collector_name: str,
        ws_host: str = None,
        ws_port: int = None,
    ):
        self.collector_name = collector_name
        self.ws_host = ws_host or _config.get("ws_host", DEFAULT_WS_HOST)
        self.ws_port = ws_port
        self.queue: Optional[QueueClient] = None
        self.running = False
        self._connected_clients = set()

    def __enter__(self):
        self.queue = QueueClient()
        self.queue.connect()
        self.running = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        if self.queue:
            self.queue.close()
            self.queue = None
        return False

    @abc.abstractmethod
    def process_message(self, data: dict) -> List[DataPoint]:
        ...

    async def _handle_connection(self, websocket):
        remote = websocket.remote_address
        print(f"[{self.collector_name}] App connected from {remote}")
        self._connected_clients.add(websocket)

        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    data_points = self.process_message(data)

                    for dp in data_points:
                        self.queue.send(dp.to_dict())

                    if data_points:
                        print(
                            f"[{self.collector_name}] Sent {len(data_points)} data points"
                        )

                except json.JSONDecodeError as e:
                    print(f"[{self.collector_name}] Invalid JSON: {e}")
                except QueueNotRunningError as e:
                    print(f"[{self.collector_name}] Queue error: {e}")
                    if not self._try_reconnect_queue():
                        print(
                            f"[{self.collector_name}] Could not reconnect to queue. Stopping."
                        )
                        return
                except Exception as e:
                    print(f"[{self.collector_name}] Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._connected_clients.discard(websocket)
            print(f"[{self.collector_name}] App disconnected from {remote}")

    def _try_reconnect_queue(self) -> bool:
        try:
            if self.queue:
                self.queue.close()
            self.queue = QueueClient()
            self.queue.connect()
            print(f"[{self.collector_name}] Reconnected to queue")
            return True
        except QueueNotRunningError:
            return False

    def run(self):
        self._print_startup_banner()

        try:
            with self as collector:
                asyncio.run(collector._serve())
        except QueueNotRunningError as e:
            print(f"\n[ERROR] {e}")
            print("\nPlease start the Queue Manager first:")
            print("    python queue_manager.py")
            return 1
        except KeyboardInterrupt:
            print(f"\n[{self.collector_name}] Interrupted by user")

        print(f"[{self.collector_name}] Collector stopped")
        return 0

    def _print_startup_banner(self):
        print("=" * STARTUP_BANNER_WIDTH)
        print(f"{self.collector_name} Collector Starting")
        print("=" * STARTUP_BANNER_WIDTH)
        print(f"Collector Name: {self.collector_name}")
        print(f"WebSocket:      {self.ws_host}:{self.ws_port}")
        print("=" * STARTUP_BANNER_WIDTH)

    async def _serve(self):
        loop = asyncio.get_event_loop()
        stop = loop.create_future()

        def _signal_handler():
            if not stop.done():
                stop.set_result(None)

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                # Windows does not support add_signal_handler
                pass

        async with websockets.serve(
            self._handle_connection, self.ws_host, self.ws_port
        ):
            print(
                f"[{self.collector_name}] WebSocket server listening on "
                f"ws://{self.ws_host}:{self.ws_port}"
            )
            print(f"[{self.collector_name}] Waiting for app connections...")

            try:
                await stop
            except asyncio.CancelledError:
                pass

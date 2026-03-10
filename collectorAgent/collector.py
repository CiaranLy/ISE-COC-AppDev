"""
Collector - Abstract base class for WebSocket-based telemetry collectors.

Subclasses implement process_message() to convert app-specific JSON into DataPoints.
"""

import abc
import asyncio
import json
import signal
from typing import List, Optional

import aiohttp
import websockets

from config_manager import config as app_config
from data_point import DataPoint
from log_config import get_logger
from queue_client import QueueClient, QueueNotRunningError

STARTUP_BANNER_WIDTH = 60
ALERT_POLL_INTERVAL_SECONDS = 2


class Collector(abc.ABC):

    def __init__(
        self,
        collector_name: str,
        ws_host: str = None,
        ws_port: int = None,
    ):
        self.collector_name = collector_name
        self.logger = get_logger(collector_name)
        self.ws_host = ws_host or app_config.get("ws_host", "localhost")
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
        self.logger.info("App connected from %s", remote)
        self._connected_clients.add(websocket)

        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    data_points = self.process_message(data)

                    for dp in data_points:
                        self.queue.send(dp.to_dict())

                    if data_points:
                        self.logger.debug("Sent %d data points", len(data_points))

                except json.JSONDecodeError as e:
                    self.logger.warning("Invalid JSON: %s", e)
                except QueueNotRunningError as e:
                    self.logger.error("Queue error: %s", e)
                    if not self._try_reconnect_queue():
                        self.logger.error("Could not reconnect to queue. Stopping.")
                        return
                except Exception as e:
                    self.logger.error("Error processing message: %s", e)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._connected_clients.discard(websocket)
            self.logger.info("App disconnected from %s", remote)

    def _try_reconnect_queue(self) -> bool:
        try:
            if self.queue:
                self.queue.close()
            self.queue = QueueClient()
            self.queue.connect()
            self.logger.info("Reconnected to queue")
            return True
        except QueueNotRunningError:
            return False

    def run(self):
        self._print_startup_banner()

        try:
            with self as collector:
                asyncio.run(collector._serve())
        except QueueNotRunningError as e:
            self.logger.error("%s", e)
            self.logger.error("Please start the Queue Manager first: python queue_manager.py")
            return 1
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")

        self.logger.info("Collector stopped")
        return 0

    def _print_startup_banner(self):
        self.logger.info("=" * STARTUP_BANNER_WIDTH)
        self.logger.info("%s Collector Starting", self.collector_name)
        self.logger.info("=" * STARTUP_BANNER_WIDTH)
        self.logger.info("Collector Name: %s", self.collector_name)
        self.logger.info("WebSocket:      %s:%s", self.ws_host, self.ws_port)
        self.logger.info("=" * STARTUP_BANNER_WIDTH)

    async def _alert_poll_loop(self):
        """Poll the backend for pending alerts and forward them to connected clients."""
        api_base_url = app_config.get("api_base_url", "http://localhost:8000/api/v1")
        pending_url = f"{api_base_url}/alerts/pending"
        ack_url_template = f"{api_base_url}/alerts/{{alert_id}}/acknowledge"

        async with aiohttp.ClientSession() as http:
            while self.running:
                await asyncio.sleep(ALERT_POLL_INTERVAL_SECONDS)
                try:
                    async with http.get(pending_url, params={"collector_name": self.collector_name}) as resp:
                        if resp.status != 200:
                            continue
                        alerts = await resp.json()

                    for alert in alerts:
                        alert_id = alert["id"]
                        message = json.dumps({
                            "type": "high_ping_alert",
                            "value": alert["value"],
                            "threshold": alert["threshold"],
                            "unit": alert["unit"],
                        })
                        for ws in list(self._connected_clients):
                            try:
                                await ws.send(message)
                            except Exception:
                                pass
                        if alerts:
                            self.logger.info(
                                "Forwarded high_ping_alert to %d client(s): value=%.1f threshold=%.1f",
                                len(self._connected_clients), alert["value"], alert["threshold"],
                            )
                        async with http.post(ack_url_template.format(alert_id=alert_id)) as _:
                            pass

                except Exception as e:
                    self.logger.debug("Alert poll error: %s", e)

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
                pass

        async with websockets.serve(
            self._handle_connection, self.ws_host, self.ws_port
        ):
            self.logger.info(
                "WebSocket server listening on ws://%s:%s",
                self.ws_host, self.ws_port,
            )
            self.logger.info("Waiting for app connections...")

            asyncio.create_task(self._alert_poll_loop())

            try:
                await stop
            except asyncio.CancelledError:
                pass

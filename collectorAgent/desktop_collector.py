"""
Desktop Collector - Receives game telemetry from the Pong desktop client via WebSocket.

This collector acts as a WebSocket CLIENT that connects to the telemetry server
embedded in the Pong game client, extracts telemetry data, and forwards it to
the local Queue Manager.

Usage:
    python desktop_collector.py
    python desktop_collector.py --port 6790
"""

import argparse
import asyncio
import json
import signal
import sys
import time
from datetime import datetime, timezone

import websockets

from config_manager import config as app_config
from data_point import DataPoint
from log_config import get_logger
from queue_client import QueueClient, QueueNotRunningError

logger = get_logger("desktop_pong")

COLLECTOR_NAME = "desktop_pong"
DEFAULT_WS_PORT = 6790

MSG_TYPE_SNAPSHOT = "snapshot"
MSG_TYPE_SESSION_START = "session_start"
MSG_TYPE_SESSION_END = "session_end"

FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_SESSION_ID = "session_id"
FIELD_LATENCY_MS = "latency_ms"
FIELD_PADDLE_Y = "paddle_y"
FIELD_COLLISION_COUNT = "collision_count"
FIELD_DURATION_MS = "duration_ms"
FIELD_FINAL_SCORE_PLAYER1 = "final_score_player1"
FIELD_FINAL_SCORE_PLAYER2 = "final_score_player2"

UNIT_LATENCY_MS = "latency_ms"
UNIT_PADDLE_Y = "paddle_y"
UNIT_COLLISION_COUNT = "collision_count"
UNIT_SESSION_START = "session_start"
UNIT_SESSION_DURATION_MS = "session_duration_ms"
UNIT_FINAL_SCORE_PLAYER1 = "final_score_player1"
UNIT_FINAL_SCORE_PLAYER2 = "final_score_player2"

SESSION_START_MARKER_VALUE = 1.0
DEFAULT_DURATION_MS = 0

SNAPSHOT_UNITS = {UNIT_LATENCY_MS, UNIT_PADDLE_Y, UNIT_COLLISION_COUNT}


class DesktopCollector:

    def __init__(self, ws_host: str = None, ws_port: int = None):
        self.collector_name = COLLECTOR_NAME
        self.ws_host = ws_host or app_config.get("ws_host", "localhost")
        self.ws_port = ws_port or app_config.get("desktop_collector_ws_port", DEFAULT_WS_PORT)
        queue_port = app_config.get("queue_port", 15555)
        if self.ws_port == queue_port:
            raise ValueError(
                f"Game telemetry port ({self.ws_port}) cannot equal queue port ({queue_port}). "
                f"Use --port to specify the game client port (e.g. 6790)."
            )
        self.queue = QueueClient()
        self.running = True
        self._last_snapshot_time: dict[str, float] = {}
        self._snapshot_interval = app_config.get("snapshot_interval_seconds", 1.0)

    def _should_forward_snapshots(self, data_points: list, session_id: str) -> bool:
        """Return True if snapshot metrics should be forwarded (throttle check)."""
        if not data_points or not all(dp.unit in SNAPSHOT_UNITS for dp in data_points):
            return True
        now = time.monotonic()
        last = self._last_snapshot_time.get(session_id, 0)
        if now - last >= self._snapshot_interval:
            self._last_snapshot_time[session_id] = now
            return True
        return False

    def __enter__(self):
        self.queue.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        self.queue.close()
        return False

    def _get_server_url(self) -> str:
        return f"ws://{self.ws_host}:{self.ws_port}"

    def _parse_timestamp(self, data: dict) -> datetime:
        raw = data.get(FIELD_TIMESTAMP)
        if raw:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                logger.warning("Unparseable timestamp: %s", raw)
        return datetime.now(timezone.utc)

    def process_message(self, raw_message):
        """Process a telemetry message. Accepts str or bytes (decoded as UTF-8)."""
        try:
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode("utf-8")
            data = json.loads(raw_message)
            msg_type = data.get(FIELD_TYPE, MSG_TYPE_SNAPSHOT)
            timestamp = self._parse_timestamp(data)
            session_id = data.get(FIELD_SESSION_ID)

            if not session_id:
                logger.error("Missing session_id in %s message, dropping", msg_type)
                return []

            def create_dp(content: float, unit: str) -> DataPoint:
                return DataPoint(
                    collector_name=self.collector_name,
                    content=content,
                    unit=unit,
                    timestamp=timestamp,
                    session_id=session_id,
                )

            if msg_type == MSG_TYPE_SESSION_START:
                return [create_dp(SESSION_START_MARKER_VALUE, UNIT_SESSION_START)]

            if msg_type == MSG_TYPE_SESSION_END:
                metrics = []
                try:
                    metrics.append(create_dp(
                        float(data.get(FIELD_DURATION_MS, DEFAULT_DURATION_MS)),
                        UNIT_SESSION_DURATION_MS,
                    ))
                except (TypeError, ValueError):
                    logger.warning("Invalid duration_ms: %r", data.get(FIELD_DURATION_MS))
                for field, unit in [
                    (FIELD_FINAL_SCORE_PLAYER1, UNIT_FINAL_SCORE_PLAYER1),
                    (FIELD_FINAL_SCORE_PLAYER2, UNIT_FINAL_SCORE_PLAYER2),
                ]:
                    if field in data:
                        try:
                            metrics.append(create_dp(float(data[field]), unit))
                        except (TypeError, ValueError):
                            logger.warning("Invalid value for %s: %r", field, data[field])
                return metrics

            return self._extract_snapshot_metrics(data, create_dp)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Invalid message (JSON/UTF-8): %s", e)
            return []

    def _extract_snapshot_metrics(self, data: dict, create_dp) -> list:
        metrics = []
        for field, unit in [
            (FIELD_LATENCY_MS, UNIT_LATENCY_MS),
            (FIELD_PADDLE_Y, UNIT_PADDLE_Y),
            (FIELD_COLLISION_COUNT, UNIT_COLLISION_COUNT),
        ]:
            if field in data:
                try:
                    metrics.append(create_dp(float(data[field]), unit))
                except (TypeError, ValueError):
                    logger.warning("Invalid numeric value for %s: %r", field, data[field])
        return metrics

    async def run(self):
        logger.info("Starting %s collector...", self.collector_name)
        recv_timeout = 1.0

        while self.running:
            server_url = self._get_server_url()
            logger.info("Connecting to game client telemetry: %s", server_url)
            try:
                async with websockets.connect(server_url) as websocket:
                    logger.info("Connected to game client")
                    while self.running:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=recv_timeout)
                        except asyncio.TimeoutError:
                            continue
                        data_points = self.process_message(message)
                        if not data_points:
                            continue
                        session_id = data_points[0].session_id
                        if not self._should_forward_snapshots(data_points, session_id):
                            continue
                        for dp in data_points:
                            self.queue.send(dp.to_dict())
                        logger.debug("Forwarded %d points", len(data_points))

            except (websockets.ConnectionClosed, OSError, QueueNotRunningError) as e:
                if not self.running:
                    break
                delay = app_config.get("reconnect_delay_seconds", 5.0)
                logger.warning("Connection error: %s. Retrying in %ss...", e, delay)
                for _ in range(int(delay * 10)):
                    if not self.running:
                        break
                    await asyncio.sleep(0.1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                self.running = False
                break

        logger.info("%s stopped", self.collector_name)


def main():
    parser = argparse.ArgumentParser(description="Desktop Pong telemetry collector")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=app_config.get("desktop_collector_ws_port", DEFAULT_WS_PORT),
        help="Game client telemetry port to connect to",
    )
    parser.add_argument(
        "--host",
        default=app_config.get("ws_host", "localhost"),
        help="Game client telemetry host to connect to",
    )
    args = parser.parse_args()

    collector = DesktopCollector(ws_host=args.host, ws_port=args.port)

    def shutdown_handler(signum=None, frame=None):
        collector.running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        with collector:
            asyncio.run(collector.run())
    except QueueNotRunningError as e:
        logger.error("%s", e)
        logger.error("Please start the Queue Manager first: python queue_manager.py")
        return 1
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        collector.running = False
        collector.queue.close()
        logger.info("Desktop collector exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())

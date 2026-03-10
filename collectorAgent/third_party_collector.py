"""
Third-Party Collector - Pulls telemetry from the Pong matchmaking server via WebSocket.

Connects to the matchmaking server with a session_id. The matchmaking server looks up
the game server running that session and streams telemetry over the WebSocket.
"""

import argparse
import asyncio
import json
import signal
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import websockets

from config_manager import config as app_config
from data_point import DataPoint
from log_config import get_logger
from queue_client import QueueClient, QueueNotRunningError

logger = get_logger("third_party_pong")

COLLECTOR_NAME = "third_party_pong"

MSG_TYPE_SNAPSHOT = "snapshot"
MSG_TYPE_SESSION_START = "session_start"
MSG_TYPE_SESSION_END = "session_end"

FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_SESSION_ID = "session_id"
FIELD_PADDLE_Y_PLAYER1 = "paddle_y_player1"
FIELD_PADDLE_Y_PLAYER2 = "paddle_y_player2"
FIELD_LATENCY_MS_PLAYER1 = "latency_ms_player1"
FIELD_LATENCY_MS_PLAYER2 = "latency_ms_player2"
FIELD_COLLISION_COUNT = "collision_count"
FIELD_SCORE_PLAYER1 = "score_player1"
FIELD_SCORE_PLAYER2 = "score_player2"
FIELD_DURATION_MS = "duration_ms"
FIELD_FINAL_SCORE_PLAYER1 = "final_score_player1"
FIELD_FINAL_SCORE_PLAYER2 = "final_score_player2"

UNIT_PADDLE_Y_PLAYER1 = "paddle_y_player1"
UNIT_PADDLE_Y_PLAYER2 = "paddle_y_player2"
UNIT_LATENCY_MS_PLAYER1 = "latency_ms_player1"
UNIT_LATENCY_MS_PLAYER2 = "latency_ms_player2"
UNIT_COLLISION_COUNT = "collision_count"
UNIT_SCORE_PLAYER1 = "score_player1"
UNIT_SCORE_PLAYER2 = "score_player2"
UNIT_SESSION_START = "session_start"
UNIT_SESSION_DURATION_MS = "session_duration_ms"
UNIT_FINAL_SCORE_PLAYER1 = "final_score_player1"
UNIT_FINAL_SCORE_PLAYER2 = "final_score_player2"

SESSION_START_MARKER_VALUE = 1.0
DEFAULT_DURATION_MS = 0

SNAPSHOT_UNITS = {
    UNIT_PADDLE_Y_PLAYER1, UNIT_PADDLE_Y_PLAYER2,
    UNIT_LATENCY_MS_PLAYER1, UNIT_LATENCY_MS_PLAYER2,
    UNIT_COLLISION_COUNT, UNIT_SCORE_PLAYER1, UNIT_SCORE_PLAYER2,
}


class ThirdPartyCollector:
    def __init__(self, session_id: str = None, matchmaking_host: str = None, matchmaking_telemetry_port: int = None):
        self.collector_name = COLLECTOR_NAME
        self.session_id = session_id or app_config.get("session_id")
        self._matchmaking_host = matchmaking_host or app_config.get("matchmaking_host", "localhost")
        self._matchmaking_telemetry_port = matchmaking_telemetry_port or app_config.get("matchmaking_telemetry_port", 9091)
        self.queue = QueueClient()
        self.running = True
        self._last_snapshot_time: dict[str, float] = {}
        self._snapshot_interval = app_config.get("snapshot_interval_seconds", 1.0)

    def _should_forward_snapshots(self, data_points: list, session_id: str) -> bool:
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

    def _parse_timestamp(self, data: dict) -> datetime:
        raw = data.get(FIELD_TIMESTAMP)
        if raw:
            try:
                return datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                logger.warning("Unparseable timestamp: %s", raw)
        return datetime.now(timezone.utc)

    def process_message(self, raw_message: str):
        try:
            data = json.loads(raw_message)
            timestamp = self._parse_timestamp(data)
            session_id = data.get(FIELD_SESSION_ID)
            msg_type = data.get(FIELD_TYPE, MSG_TYPE_SNAPSHOT)

            if not session_id:
                logger.error("Missing session_id in %s message, dropping", msg_type)
                return []

            if msg_type == MSG_TYPE_SESSION_START:
                return [self._create_dp(SESSION_START_MARKER_VALUE, UNIT_SESSION_START, timestamp, session_id)]
            elif msg_type == MSG_TYPE_SESSION_END:
                return self._extract_session_end_metrics(data, timestamp, session_id)

            return self._extract_snapshot_metrics(data, timestamp, session_id)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("Invalid message: %s", e)
            return []

    def _extract_snapshot_metrics(self, data: dict, timestamp: datetime, session_id: str):
        metrics = []
        snapshot_fields = [
            (FIELD_PADDLE_Y_PLAYER1, UNIT_PADDLE_Y_PLAYER1),
            (FIELD_PADDLE_Y_PLAYER2, UNIT_PADDLE_Y_PLAYER2),
            (FIELD_LATENCY_MS_PLAYER1, UNIT_LATENCY_MS_PLAYER1),
            (FIELD_LATENCY_MS_PLAYER2, UNIT_LATENCY_MS_PLAYER2),
            (FIELD_COLLISION_COUNT, UNIT_COLLISION_COUNT),
            (FIELD_SCORE_PLAYER1, UNIT_SCORE_PLAYER1),
            (FIELD_SCORE_PLAYER2, UNIT_SCORE_PLAYER2),
        ]
        for field, unit in snapshot_fields:
            if field in data:
                try:
                    metrics.append(self._create_dp(float(data[field]), unit, timestamp, session_id))
                except (TypeError, ValueError):
                    logger.warning("Invalid numeric value for %s: %r", field, data[field])
        return metrics

    def _extract_session_end_metrics(self, data: dict, timestamp: datetime, session_id: str):
        metrics = []
        try:
            metrics.append(self._create_dp(
                float(data.get(FIELD_DURATION_MS, DEFAULT_DURATION_MS)),
                UNIT_SESSION_DURATION_MS,
                timestamp,
                session_id,
            ))
        except (TypeError, ValueError):
            logger.warning("Invalid duration_ms: %r", data.get(FIELD_DURATION_MS))
        for field, unit in [
            (FIELD_FINAL_SCORE_PLAYER1, UNIT_FINAL_SCORE_PLAYER1),
            (FIELD_FINAL_SCORE_PLAYER2, UNIT_FINAL_SCORE_PLAYER2),
        ]:
            if field in data:
                try:
                    metrics.append(self._create_dp(float(data[field]), unit, timestamp, session_id))
                except (TypeError, ValueError):
                    logger.warning("Invalid value for %s: %r", field, data[field])
        return metrics

    def _create_dp(self, content: float, unit: str, timestamp: datetime, session_id: str) -> DataPoint:
        return DataPoint(
            collector_name=self.collector_name,
            content=float(content),
            unit=unit,
            timestamp=timestamp,
            session_id=session_id,
        )

    def _get_server_url(self) -> str:
        """Connect to matchmaking telemetry WebSocket with session_id."""
        params = urlencode({"session_id": self.session_id}) if self.session_id else ""
        base = f"ws://{self._matchmaking_host}:{self._matchmaking_telemetry_port}"
        return f"{base}?{params}" if params else base

    async def run(self):
        if not self.session_id:
            logger.error("session_id is required. Provide via --session-id or config.json")
            return

        logger.info("Starting %s collector for session_id=%s...", self.collector_name, self.session_id)
        recv_timeout = 1.0

        while self.running:
            server_url = self._get_server_url()
            logger.info("Connecting to matchmaking telemetry: %s", server_url)
            try:
                async with websockets.connect(server_url) as websocket:
                    logger.info("Connected to matchmaking, streaming telemetry for session %s", self.session_id)
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

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError, QueueNotRunningError) as e:
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
    parser = argparse.ArgumentParser(description="Third-party Pong telemetry collector (via matchmaking)")
    parser.add_argument(
        "--session-id", "-s",
        default=app_config.get("session_id"),
        help="Session ID from matchmaking GameReady. Required.",
    )
    parser.add_argument(
        "--matchmaking-host",
        default=app_config.get("matchmaking_host", "localhost"),
        help="Matchmaking server host",
    )
    parser.add_argument(
        "--matchmaking-telemetry-port",
        type=int,
        default=app_config.get("matchmaking_telemetry_port", 9091),
        help="Matchmaking telemetry WebSocket port",
    )
    args = parser.parse_args()

    if not args.session_id:
        logger.error("session_id is required. Use --session-id or set session_id in config.json")
        logger.error("Get session_id from matchmaking GameReady when a match starts.")
        return 1

    collector = ThirdPartyCollector(
        session_id=args.session_id,
        matchmaking_host=args.matchmaking_host,
        matchmaking_telemetry_port=args.matchmaking_telemetry_port,
    )

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
        logger.info("Third-party collector exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Third-Party Collector - Pulls telemetry from the Pong submodule server via WebSocket.

This collector acts as a WebSocket CLIENT that connects to an external server,
extracts telemetry data, and forwards it to the local Queue Manager.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

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


class ThirdPartyCollector:
    def __init__(self):
        self.collector_name = COLLECTOR_NAME
        self.queue = QueueClient()
        self.running = True

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
            msg_type = data.get(FIELD_TYPE, MSG_TYPE_SNAPSHOT)

            if msg_type == MSG_TYPE_SNAPSHOT:
                return self._extract_snapshot_metrics(data, timestamp)
            elif msg_type == MSG_TYPE_SESSION_START:
                return [self._create_dp(SESSION_START_MARKER_VALUE, UNIT_SESSION_START, timestamp)]
            elif msg_type == MSG_TYPE_SESSION_END:
                return self._extract_session_end_metrics(data, timestamp)

            return self._extract_snapshot_metrics(data, timestamp)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON: %s", e)
            return []

    def _extract_snapshot_metrics(self, data: dict, timestamp: datetime):
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
                metrics.append(self._create_dp(float(data[field]), unit, timestamp))
        return metrics

    def _extract_session_end_metrics(self, data: dict, timestamp: datetime):
        metrics = [
            self._create_dp(
                float(data.get(FIELD_DURATION_MS, DEFAULT_DURATION_MS)),
                UNIT_SESSION_DURATION_MS,
                timestamp,
            )
        ]
        for field, unit in [
            (FIELD_FINAL_SCORE_PLAYER1, UNIT_FINAL_SCORE_PLAYER1),
            (FIELD_FINAL_SCORE_PLAYER2, UNIT_FINAL_SCORE_PLAYER2),
        ]:
            if field in data:
                metrics.append(self._create_dp(float(data[field]), unit, timestamp))
        return metrics

    def _create_dp(self, content: float, unit: str, timestamp: datetime) -> DataPoint:
        return DataPoint(
            collector_name=self.collector_name,
            content=float(content),
            unit=unit,
            timestamp=timestamp,
        )

    def _get_server_url(self) -> str:
        host = app_config.get("game_server_host", "localhost")
        port = app_config.get("game_server_port", 8081)
        return f"ws://{host}:{port}"

    async def run(self):
        logger.info("Starting %s collector...", self.collector_name)

        while self.running:
            server_url = self._get_server_url()
            logger.info("Connecting to server: %s", server_url)
            try:
                async with websockets.connect(server_url) as websocket:
                    logger.info("Connected to server")
                    async for message in websocket:
                        data_points = self.process_message(message)
                        for dp in data_points:
                            self.queue.send(dp.to_dict())

                        if data_points:
                            logger.debug("Forwarded %d points", len(data_points))

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                delay = app_config.get("reconnect_delay_seconds")
                logger.warning("Connection error: %s. Retrying in %ss...", e, delay)
                await asyncio.sleep(delay)
            except KeyboardInterrupt:
                self.running = False
                break

        logger.info("%s stopped", self.collector_name)


def main():
    collector = ThirdPartyCollector()
    try:
        with collector:
            asyncio.run(collector.run())
    except QueueNotRunningError as e:
        logger.error("%s", e)
        logger.error("Please start the Queue Manager first: python queue_manager.py")
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

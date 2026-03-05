"""
Third-Party Collector - Pulls telemetry from the Pong submodule server via WebSocket.

This collector acts as a WebSocket CLIENT that connects to an external server,
extracts telemetry data, and forwards it to the local Queue Manager.
"""

import asyncio
import json
import signal
from datetime import datetime, timezone
from pathlib import Path

import websockets

from data_point import DataPoint
from queue_client import QueueClient, QueueNotRunningError

CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

COLLECTOR_NAME = "third_party_pong"
SERVER_URL = config.get("third_party_server_url", "ws://localhost:8081")

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

    def _parse_timestamp(self, data: dict) -> datetime:
        raw = data.get(FIELD_TIMESTAMP)
        if raw:
            try:
                return datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                pass
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
            print(f"[{self.collector_name}] Invalid JSON: {e}")
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

    async def run(self):
        print(f"[{self.collector_name}] Starting Third-Party Collector...")
        print(f"[{self.collector_name}] Connecting to server: {SERVER_URL}")

        try:
            self.queue.connect()
        except QueueNotRunningError as e:
            print(f"[ERROR] {e}")
            return

        while self.running:
            try:
                async with websockets.connect(SERVER_URL) as websocket:
                    print(f"[{self.collector_name}] Connected to server!")
                    async for message in websocket:
                        data_points = self.process_message(message)
                        for dp in data_points:
                            self.queue.send(dp.to_dict())

                        if data_points:
                            print(f"[{self.collector_name}] Forwarded {len(data_points)} points")

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                print(f"[{self.collector_name}] Connection error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
            except KeyboardInterrupt:
                self.running = False
                break

        self.queue.close()
        print(f"[{self.collector_name}] Stopped.")

if __name__ == "__main__":
    collector = ThirdPartyCollector()
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        pass

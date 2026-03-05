"""
Mobile Collector - Receives game telemetry from the Pong mobile app via WebSocket.

The mobile app connects over loopback (10.0.2.2 from the Android emulator,
or localhost on a real device with adb reverse).

Usage:
    python mobile_collector.py
    python mobile_collector.py --port 6789
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from data_point import DataPoint
from collector import Collector

CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

COLLECTOR_NAME = "mobile_pong"
DEFAULT_WS_PORT = 6789

MSG_TYPE_SNAPSHOT = "snapshot"
MSG_TYPE_SESSION_START = "session_start"
MSG_TYPE_SESSION_END = "session_end"

FIELD_TYPE = "type"
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


class MobileCollector(Collector):

    def __init__(self, ws_host: str = None, ws_port: int = None):
        port = ws_port or config.get("mobile_collector_ws_port", DEFAULT_WS_PORT)
        super().__init__(
            collector_name=COLLECTOR_NAME,
            ws_host=ws_host,
            ws_port=port,
        )

    def process_message(self, data: dict) -> List[DataPoint]:
        msg_type = data.get(FIELD_TYPE, MSG_TYPE_SNAPSHOT)
        now = datetime.now(timezone.utc)
        data_points = []

        if msg_type == MSG_TYPE_SNAPSHOT:
            data_points.extend(self._extract_snapshot_metrics(data, now))
        elif msg_type == MSG_TYPE_SESSION_START:
            data_points.append(self._create_data_point(SESSION_START_MARKER_VALUE, UNIT_SESSION_START, now))
        elif msg_type == MSG_TYPE_SESSION_END:
            data_points.extend(self._extract_session_end_metrics(data, now))

        return data_points

    def _extract_snapshot_metrics(self, data: dict, timestamp: datetime) -> List[DataPoint]:
        metrics = []
        snapshot_fields = [
            (FIELD_LATENCY_MS, UNIT_LATENCY_MS),
            (FIELD_PADDLE_Y, UNIT_PADDLE_Y),
            (FIELD_COLLISION_COUNT, UNIT_COLLISION_COUNT),
        ]
        for field, unit in snapshot_fields:
            if field in data:
                metrics.append(self._create_data_point(float(data[field]), unit, timestamp))
        return metrics

    def _extract_session_end_metrics(self, data: dict, timestamp: datetime) -> List[DataPoint]:
        metrics = [
            self._create_data_point(
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
                metrics.append(self._create_data_point(float(data[field]), unit, timestamp))
        return metrics

    def _create_data_point(self, content: float, unit: str, timestamp: datetime) -> DataPoint:
        return DataPoint(
            collector_name=self.collector_name,
            content=content,
            unit=unit,
            timestamp=timestamp,
        )


def main():
    parser = argparse.ArgumentParser(description="Mobile Pong telemetry collector")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=config.get("mobile_collector_ws_port", DEFAULT_WS_PORT),
        help="WebSocket server port",
    )
    parser.add_argument(
        "--host",
        default=config.get("ws_host", "localhost"),
        help="WebSocket server host",
    )
    args = parser.parse_args()

    collector = MobileCollector(ws_host=args.host, ws_port=args.port)
    return collector.run()


if __name__ == "__main__":
    sys.exit(main())

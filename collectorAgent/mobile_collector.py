"""
Mobile Collector - Receives game telemetry from the Pong mobile client via WebSocket.

This collector acts as a WebSocket CLIENT that connects to the telemetry server
embedded in the mobile Pong app, extracts telemetry data, and forwards it to
the local Queue Manager.

Usage:
    python mobile_collector.py
    python mobile_collector.py --host 192.168.1.50 --port 6790
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

import aiohttp
import websockets

from config_manager import config as app_config
from data_point import DataPoint
from log_config import get_logger
from queue_client import QueueClient, QueueNotRunningError

logger = get_logger("mobile_pong")

COLLECTOR_NAME = "mobile_pong"
DEFAULT_WS_PORT = 6790
ALERT_POLL_INTERVAL_SECONDS = 2

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


class MobileCollector:

    def __init__(self, ws_host: str = None, ws_port: int = None):
        self.collector_name = COLLECTOR_NAME
        self.ws_host = ws_host or app_config.get("mobile_client_host", "localhost")
        self.ws_port = ws_port or app_config.get("mobile_client_port", DEFAULT_WS_PORT)
        self.queue = QueueClient()
        self.running = True

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
                return datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                logger.warning("Unparseable timestamp: %s", raw)
        return datetime.now(timezone.utc)

    def process_message(self, raw_message: str):
        try:
            data = json.loads(raw_message)
            msg_type = data.get(FIELD_TYPE, MSG_TYPE_SNAPSHOT)
            timestamp = self._parse_timestamp(data)
            session_id = data.get(FIELD_SESSION_ID)

            if not session_id:
                logger.error("Missing session_id in %s message, dropping", msg_type)
                return []

            if msg_type == MSG_TYPE_SESSION_START:
                return [self._create_dp(SESSION_START_MARKER_VALUE, UNIT_SESSION_START, timestamp, session_id)]

            if msg_type == MSG_TYPE_SESSION_END:
                return self._extract_session_end_metrics(data, timestamp, session_id)

            return self._extract_snapshot_metrics(data, timestamp, session_id)
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON: %s", e)
            return []

    def _extract_snapshot_metrics(self, data: dict, timestamp: datetime, session_id: str):
        metrics = []
        snapshot_fields = [
            (FIELD_LATENCY_MS, UNIT_LATENCY_MS),
            (FIELD_PADDLE_Y, UNIT_PADDLE_Y),
            (FIELD_COLLISION_COUNT, UNIT_COLLISION_COUNT),
        ]
        for field, unit in snapshot_fields:
            if field in data:
                metrics.append(self._create_dp(float(data[field]), unit, timestamp, session_id))
        return metrics

    def _extract_session_end_metrics(self, data: dict, timestamp: datetime, session_id: str):
        metrics = [
            self._create_dp(
                float(data.get(FIELD_DURATION_MS, DEFAULT_DURATION_MS)),
                UNIT_SESSION_DURATION_MS,
                timestamp,
                session_id,
            )
        ]
        for field, unit in [
            (FIELD_FINAL_SCORE_PLAYER1, UNIT_FINAL_SCORE_PLAYER1),
            (FIELD_FINAL_SCORE_PLAYER2, UNIT_FINAL_SCORE_PLAYER2),
        ]:
            if field in data:
                metrics.append(self._create_dp(float(data[field]), unit, timestamp, session_id))
        return metrics

    def _create_dp(self, content: float, unit: str, timestamp: datetime, session_id: str) -> DataPoint:
        return DataPoint(
            collector_name=self.collector_name,
            content=content,
            unit=unit,
            timestamp=timestamp,
            session_id=session_id,
        )

    async def _alert_poller(self, websocket):
        """Poll the backend for pending alerts and forward them to the mobile client."""
        api_base_url = app_config.get("api_base_url", "http://localhost:8000/api/v1")
        pending_url = f"{api_base_url}/alerts/pending"
        ack_url_template = f"{api_base_url}/alerts/{{alert_id}}/acknowledge"

        async with aiohttp.ClientSession() as http:
            while True:
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
                        await websocket.send(message)
                        logger.info(
                            "Forwarded high_ping_alert to mobile client: value=%.1f threshold=%.1f",
                            alert["value"], alert["threshold"],
                        )
                        async with http.post(ack_url_template.format(alert_id=alert_id)) as _:
                            pass

                except Exception as e:
                    logger.debug("Alert poll error: %s", e)

    async def run(self):
        logger.info("Starting %s collector...", self.collector_name)

        while self.running:
            server_url = self._get_server_url()
            logger.info("Connecting to mobile client telemetry: %s", server_url)
            try:
                async with websockets.connect(server_url) as websocket:
                    logger.info("Connected to mobile client")
                    poller_task = asyncio.create_task(self._alert_poller(websocket))
                    try:
                        async for message in websocket:
                            data_points = self.process_message(message)
                            for dp in data_points:
                                self.queue.send(dp.to_dict())

                            if data_points:
                                logger.debug("Forwarded %d points", len(data_points))
                    finally:
                        poller_task.cancel()

            except (websockets.ConnectionClosed, OSError) as e:
                delay = app_config.get("reconnect_delay_seconds", 5.0)
                logger.warning("Connection error: %s. Retrying in %ss...", e, delay)
                await asyncio.sleep(delay)
            except KeyboardInterrupt:
                self.running = False
                break

        logger.info("%s stopped", self.collector_name)


def main():
    parser = argparse.ArgumentParser(description="Mobile Pong telemetry collector")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=app_config.get("mobile_client_port", DEFAULT_WS_PORT),
        help="Mobile client telemetry port to connect to",
    )
    parser.add_argument(
        "--host",
        default=app_config.get("mobile_client_host", "localhost"),
        help="Mobile client telemetry host to connect to",
    )
    args = parser.parse_args()

    collector = MobileCollector(ws_host=args.host, ws_port=args.port)
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

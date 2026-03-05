"""
Mobile Collector - Pulls game telemetry from Firebase Firestore.

This collector runs on the desktop and listens for updates in the Firebase
collections 'game_sessions' and their 'snapshots' subcollections.

Requirements:
    pip install firebase-admin
    A 'serviceAccountKey.json' file in this directory.
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from data_point import DataPoint
from log_config import get_logger
from queue_client import QueueClient, QueueNotRunningError

logger = get_logger("mobile_pong")

SERVICE_ACCOUNT_FILE = Path(__file__).parent / "serviceAccountKey.json"

COLLECTOR_NAME = "mobile_pong"
UNIT_LATENCY_MS = "latency_ms"
UNIT_PADDLE_Y = "paddle_y"
UNIT_COLLISION_COUNT = "collision_count"
UNIT_SESSION_START = "session_start"
UNIT_SESSION_DURATION_MS = "session_duration_ms"
UNIT_FINAL_SCORE_PLAYER1 = "final_score_player1"
UNIT_FINAL_SCORE_PLAYER2 = "final_score_player2"


class MobileFirebaseCollector:
    def __init__(self):
        self.collector_name = COLLECTOR_NAME
        self.queue = QueueClient()
        self.db = None
        self._session_start_times = {}

    def __enter__(self):
        self.queue.connect()
        if not self._connect_firebase():
            raise RuntimeError("Failed to connect to Firebase")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.queue.close()
        return False

    def _connect_firebase(self) -> bool:
        if not SERVICE_ACCOUNT_FILE.exists():
            logger.error("Firebase service account file missing: %s", SERVICE_ACCOUNT_FILE)
            return False

        cred = credentials.Certificate(str(SERVICE_ACCOUNT_FILE))
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        logger.info("Connected to Firebase")
        return True

    def _send_to_queue(self, content: float, unit: str, timestamp: datetime):
        try:
            dp = DataPoint(
                collector_name=self.collector_name,
                content=float(content),
                unit=unit,
                timestamp=timestamp,
            )
            self.queue.send(dp.to_dict())
        except QueueNotRunningError as e:
            logger.error("Queue error: %s", e)
        except Exception as e:
            logger.error("Error sending data: %s", e)

    def _to_utc_datetime(self, firebase_timestamp) -> datetime:
        if firebase_timestamp.tzinfo is None:
            return firebase_timestamp.replace(tzinfo=timezone.utc)
        return firebase_timestamp

    def _make_snapshot_listener(self, session_id):
        def on_snapshot_received(doc_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    data = change.document.to_dict()
                    start_time = self._session_start_times.get(session_id)
                    if start_time and "timestampMs" in data:
                        timestamp = start_time + timedelta(milliseconds=data["timestampMs"])
                    else:
                        timestamp = datetime.now(timezone.utc)

                    if "latencyMs" in data:
                        self._send_to_queue(data["latencyMs"], UNIT_LATENCY_MS, timestamp)
                    if "paddleY" in data:
                        self._send_to_queue(data["paddleY"], UNIT_PADDLE_Y, timestamp)
                    if "collisionCount" in data:
                        self._send_to_queue(data["collisionCount"], UNIT_COLLISION_COUNT, timestamp)
        return on_snapshot_received

    def on_session_received(self, doc_snapshot, changes, read_time):
        for change in changes:
            data = change.document.to_dict()
            session_id = change.document.id

            if change.type.name == 'ADDED':
                timestamp = (
                    self._to_utc_datetime(data["startedAt"])
                    if "startedAt" in data
                    else datetime.now(timezone.utc)
                )
                self._session_start_times[session_id] = timestamp

                logger.info("New Session: %s", session_id)
                self._send_to_queue(1.0, UNIT_SESSION_START, timestamp)

                self.db.collection("game_sessions").document(session_id)\
                    .collection("snapshots").on_snapshot(self._make_snapshot_listener(session_id))

            elif change.type.name == 'MODIFIED' and "endedAt" in data:
                timestamp = self._to_utc_datetime(data["endedAt"])
                logger.info("Session Ended: %s", session_id)
                if "durationMs" in data:
                    self._send_to_queue(data["durationMs"], UNIT_SESSION_DURATION_MS, timestamp)
                if "finalScorePlayer1" in data:
                    self._send_to_queue(data["finalScorePlayer1"], UNIT_FINAL_SCORE_PLAYER1, timestamp)
                if "finalScorePlayer2" in data:
                    self._send_to_queue(data["finalScorePlayer2"], UNIT_FINAL_SCORE_PLAYER2, timestamp)
                self._session_start_times.pop(session_id, None)

    def run(self):
        logger.info("Starting %s (Firebase Mode)...", self.collector_name)

        self.db.collection("game_sessions").on_snapshot(self.on_session_received)

        logger.info("Listening for Firebase updates. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping...")


def main():
    collector = MobileFirebaseCollector()
    try:
        with collector:
            collector.run()
    except (QueueNotRunningError, RuntimeError) as e:
        logger.error("%s", e)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

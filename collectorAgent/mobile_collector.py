"""
Mobile Collector - Pulls game telemetry from Firebase Firestore.

This collector runs on the desktop and listens for updates in the Firebase
collections 'game_sessions' and their 'snapshots' subcollections.

Requirements:
    pip install firebase-admin
    A 'serviceAccountKey.json' file in this directory.
"""

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from data_point import DataPoint
from queue_client import QueueClient, QueueNotRunningError

CONFIG_FILE = Path(__file__).parent / "config.json"
SERVICE_ACCOUNT_FILE = Path(__file__).parent / "serviceAccountKey.json"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

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
        self._active_sessions = set()
        self._session_start_times = {}

    def connect_firebase(self):
        if not SERVICE_ACCOUNT_FILE.exists():
            print(f"[ERROR] Firebase service account file missing: {SERVICE_ACCOUNT_FILE}")
            return False

        cred = credentials.Certificate(str(SERVICE_ACCOUNT_FILE))
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        print(f"[{self.collector_name}] Connected to Firebase")
        return True

    def _send_to_queue(self, content: float, unit: str, timestamp: datetime):
        try:
            dp = DataPoint(
                collector_name=self.collector_name,
                content=float(content),
                unit=unit,
                timestamp=timestamp
            )
            self.queue.send(dp.to_dict())
        except QueueNotRunningError as e:
            print(f"[{self.collector_name}] Queue Error: {e}")
        except Exception as e:
            print(f"[{self.collector_name}] Error sending data: {e}")

    def _to_utc_datetime(self, firebase_timestamp) -> datetime:
        dt = firebase_timestamp.replace(tzinfo=timezone.utc) if firebase_timestamp.tzinfo is None else firebase_timestamp
        return dt

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
                timestamp = self._to_utc_datetime(data["startedAt"]) if "startedAt" in data else datetime.now(timezone.utc)
                self._session_start_times[session_id] = timestamp

                print(f"[{self.collector_name}] New Session: {session_id}")
                self._send_to_queue(1.0, UNIT_SESSION_START, timestamp)

                self.db.collection("game_sessions").document(session_id)\
                    .collection("snapshots").on_snapshot(self._make_snapshot_listener(session_id))

            elif change.type.name == 'MODIFIED' and "endedAt" in data:
                timestamp = self._to_utc_datetime(data["endedAt"])
                print(f"[{self.collector_name}] Session Ended: {session_id}")
                if "durationMs" in data:
                    self._send_to_queue(data["durationMs"], UNIT_SESSION_DURATION_MS, timestamp)
                if "finalScorePlayer1" in data:
                    self._send_to_queue(data["finalScorePlayer1"], UNIT_FINAL_SCORE_PLAYER1, timestamp)
                if "finalScorePlayer2" in data:
                    self._send_to_queue(data["finalScorePlayer2"], UNIT_FINAL_SCORE_PLAYER2, timestamp)
                self._session_start_times.pop(session_id, None)

    def run(self):
        print(f"Starting {self.collector_name} (Firebase Mode)...")
        try:
            self.queue.connect()
        except QueueNotRunningError as e:
            print(f"[ERROR] {e}")
            return

        if not self.connect_firebase():
            return

        # Listen for new game sessions
        self.db.collection("game_sessions").on_snapshot(self.on_session_received)

        print(f"[{self.collector_name}] Listening for Firebase updates. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"[{self.collector_name}] Stopping...")
        finally:
            self.queue.close()

if __name__ == "__main__":
    collector = MobileFirebaseCollector()
    collector.run()

"""
Mobile Collector - Pulls telemetry from Firebase Firestore and sends each metric to the queue.

This version uses a more robust listener and detailed logging to track data flow.
"""

import argparse
import signal
import sys
import time
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

from config_manager import config as app_config
from data_point import DataPoint
from log_config import get_logger
from queue_client import QueueClient, QueueNotRunningError

logger = get_logger("mobile_pong")

COLLECTOR_NAME = "mobile_pong"

# Units (must match dashboard expectations)
UNIT_SESSION_START = "session_start"
UNIT_LATENCY_MS = "latency_ms"
UNIT_PADDLE_Y = "paddle_y"
UNIT_COLLISION_COUNT = "collision_count"
UNIT_SESSION_DURATION_MS = "session_duration_ms"
UNIT_FINAL_SCORE_PLAYER1 = "final_score_player1"
UNIT_FINAL_SCORE_PLAYER2 = "final_score_player2"

class MobileCollector:
    def __init__(self, key_path: str = "serviceAccountKey.json"):
        self.collector_name = COLLECTOR_NAME
        self.key_path = key_path
        self.queue = QueueClient()
        self._db = None
        self._running = True
        self._snapshot_listeners = {}
        self._processed_docs = set()

    def _send(self, unit: str, content: float, timestamp: datetime, session_id: str):
        dp = DataPoint(
            collector_name=self.collector_name,
            content=content,
            unit=unit,
            timestamp=timestamp,
            session_id=session_id,
        )
        try:
            self.queue.send(dp.to_dict())
            logger.debug("Sent %s for session %s", unit, session_id)
        except Exception as e:
            logger.error("Failed to send %s to queue: %s", unit, e)

    def _on_snapshot_added(self, session_id, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                doc_id = change.document.id
                if doc_id in self._processed_docs:
                    continue

                data = change.document.to_dict()
                dt = datetime.now(timezone.utc)

                # Send all available metrics in the snapshot
                count = 0
                if 'latencyMs' in data:
                    self._send(UNIT_LATENCY_MS, float(data['latencyMs']), dt, session_id)
                    count += 1
                if 'paddleY' in data:
                    self._send(UNIT_PADDLE_Y, float(data['paddleY']), dt, session_id)
                    count += 1
                if 'collisionCount' in data:
                    self._send(UNIT_COLLISION_COUNT, float(data['collisionCount']), dt, session_id)
                    count += 1

                self._processed_docs.add(doc_id)
                if count > 0:
                    logger.info("Live Update: Session %s -> %d metrics forwarded", session_id, count)

    def _on_session_change(self, col_snapshot, changes, read_time):
        for change in changes:
            doc = change.document
            session_id = doc.id
            data = doc.to_dict()

            if change.type.name == 'ADDED':
                logger.info(">>> NEW LIVE SESSION DETECTED: %s", session_id)
                self._send(UNIT_SESSION_START, 1.0, datetime.now(timezone.utc), session_id)

                # Attach listener to the subcollection
                callback = lambda c, ch, rt, sid=session_id: self._on_snapshot_added(sid, ch, rt)
                self._snapshot_listeners[session_id] = doc.reference.collection('snapshots').on_snapshot(callback)

            elif change.type.name == 'MODIFIED' and 'endedAt' in data:
                logger.info("<<< SESSION ENDED: %s", session_id)
                dt = datetime.now(timezone.utc)
                self._send(UNIT_SESSION_DURATION_MS, float(data.get('durationMs', 0)), dt, session_id)

                if session_id in self._snapshot_listeners:
                    self._snapshot_listeners[session_id].unsubscribe()
                    del self._snapshot_listeners[session_id]

    def run(self):
        logger.info("Connecting to Queue Manager...")
        self.queue.connect()

        logger.info("Initializing Firebase with %s...", self.key_path)
        cred = credentials.Certificate(self.key_path)
        firebase_admin.initialize_app(cred)
        self._db = firestore.client()

        logger.info("Listening for game sessions in Firestore...")
        self._db.collection('game_sessions').on_snapshot(self._on_session_change)

        while self._running:
            time.sleep(1)

    def stop(self):
        self._running = False
        logger.info("Stopping collector...")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", default="serviceAccountKey.json")
    args = parser.parse_args()

    collector = MobileCollector(key_path=args.key)

    signal.signal(signal.SIGINT, lambda s, f: collector.stop())

    try:
        collector.run()
    except Exception as e:
        logger.error("Collector Error: %s", e)
    finally:
        collector.stop()

if __name__ == "__main__":
    main()

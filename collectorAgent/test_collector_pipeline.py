"""
Integration test: simulates a mobile app sending telemetry via WebSocket
to the mobile_collector, which forwards it to the queue manager.

Usage: python test_collector_pipeline.py
Requires: queue_manager.py and mobile_collector.py to be running.
"""

import asyncio
import json
import sys

import websockets

COLLECTOR_WS_URL = "ws://localhost:6789"

SNAPSHOT_MESSAGE = {
    "type": "snapshot",
    "latency_ms": 42,
    "paddle_y": 320.5,
    "collision_count": 7,
}

SESSION_START_MESSAGE = {
    "type": "session_start",
    "session_id": "test-session-001",
    "game_mode": "multiplayer",
}

SESSION_END_MESSAGE = {
    "type": "session_end",
    "session_id": "test-session-001",
    "duration_ms": 60000,
    "final_score_player1": 5,
    "final_score_player2": 3,
}

TEST_MESSAGES = [
    ("session_start", SESSION_START_MESSAGE),
    ("snapshot", SNAPSHOT_MESSAGE),
    ("snapshot", SNAPSHOT_MESSAGE),
    ("session_end", SESSION_END_MESSAGE),
]


async def run_test():
    print(f"Connecting to collector at {COLLECTOR_WS_URL}...")
    try:
        async with websockets.connect(COLLECTOR_WS_URL) as ws:
            print("Connected!\n")

            for label, message in TEST_MESSAGES:
                print(f"Sending {label}: {json.dumps(message)}")
                await ws.send(json.dumps(message))
                await asyncio.sleep(0.5)

            print("\nAll test messages sent successfully!")
            print("Check the queue manager and collector logs for output.")

    except ConnectionRefusedError:
        print(f"ERROR: Could not connect to {COLLECTOR_WS_URL}")
        print("Make sure both queue_manager.py and mobile_collector.py are running.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_test()))

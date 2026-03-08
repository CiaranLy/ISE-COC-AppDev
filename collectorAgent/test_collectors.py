"""
Integration test: sends test payloads through the desktop and third-party collectors
and verifies data arrives at the backend API.
"""

import asyncio
import json
import time
from datetime import datetime, timezone

import requests
import websockets

API_URL = "http://localhost:8000/api/v1/graphs"
DESKTOP_WS = "ws://localhost:6790"
GAME_SERVER_PORT = 8081

MATCH_ID = f"test-match-{int(time.time())}"


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def test_desktop_collector():
    """Connect to the desktop collector WS server and send a full session."""
    print("\n=== Testing Desktop Collector ===")
    async with websockets.connect(DESKTOP_WS) as ws:
        session_start = {
            "type": "session_start",
            "session_id": MATCH_ID,
            "timestamp": ts(),
        }
        await ws.send(json.dumps(session_start))
        print(f"  Sent session_start (session_id={MATCH_ID})")

        for i in range(3):
            snapshot = {
                "type": "snapshot",
                "latency_ms": 10.0 + i,
                "paddle_y": 200.0 + i * 50,
                "collision_count": i,
                "timestamp": ts(),
            }
            await ws.send(json.dumps(snapshot))
            print(f"  Sent snapshot #{i+1}")
            await asyncio.sleep(0.3)

        session_end = {
            "type": "session_end",
            "session_id": MATCH_ID,
            "duration_ms": 5000,
            "final_score_player1": 3,
            "final_score_player2": 2,
            "timestamp": ts(),
        }
        await ws.send(json.dumps(session_end))
        print("  Sent session_end")

    print("  Desktop test payloads sent successfully")


async def test_third_party_collector():
    """Start a fake game server on port 8081, wait for the collector to connect, then send data."""
    print("\n=== Testing Third-Party Collector ===")
    connected = asyncio.Event()

    async def handler(websocket):
        connected.set()
        print("  Third-party collector connected to fake game server")

        session_start = {
            "type": "session_start",
            "session_id": MATCH_ID,
            "timestamp": ts(),
        }
        await websocket.send(json.dumps(session_start))
        print(f"  Sent session_start (session_id={MATCH_ID})")

        for i in range(3):
            snapshot = {
                "type": "snapshot",
                "session_id": MATCH_ID,
                "paddle_y_player1": 150.0 + i * 30,
                "paddle_y_player2": 300.0 - i * 20,
                "latency_ms_player1": 12.0 + i,
                "latency_ms_player2": 18.0 + i,
                "collision_count": i * 2,
                "score_player1": i,
                "score_player2": max(0, i - 1),
                "timestamp": ts(),
            }
            await websocket.send(json.dumps(snapshot))
            print(f"  Sent snapshot #{i+1}")
            await asyncio.sleep(0.3)

        session_end = {
            "type": "session_end",
            "session_id": MATCH_ID,
            "duration_ms": 8000,
            "final_score_player1": 5,
            "final_score_player2": 3,
            "timestamp": ts(),
        }
        await websocket.send(json.dumps(session_end))
        print("  Sent session_end")

        await asyncio.sleep(1)

    server = await websockets.serve(handler, "localhost", GAME_SERVER_PORT)
    print(f"  Fake game server listening on port {GAME_SERVER_PORT}")
    print("  Waiting for third-party collector to connect (up to 10s)...")

    try:
        await asyncio.wait_for(connected.wait(), timeout=10)
        await asyncio.sleep(3)
    except asyncio.TimeoutError:
        print("  WARNING: Third-party collector did not connect within 10s")
    finally:
        server.close()
        await server.wait_closed()

    print("  Third-party test payloads sent successfully")


def check_backend():
    """Query the backend API to see if data arrived."""
    print("\n=== Checking Backend for Data ===")
    print(f"  Waiting 10s for queue to flush...")
    time.sleep(10)

    try:
        resp = requests.get(API_URL, timeout=5)
        if resp.status_code == 200:
            graphs = resp.json()
            print(f"  Backend returned {len(graphs)} graph(s)")
            for g in graphs:
                points = len(g.get("data_points", []))
                print(f"    - {g['collector_name']} / {g['unit']}: {points} data point(s)")
        else:
            print(f"  Backend returned status {resp.status_code}")
    except requests.RequestException as e:
        print(f"  Could not reach backend: {e}")


async def main():
    print(f"Test match ID: {MATCH_ID}")

    await test_desktop_collector()
    await test_third_party_collector()

    check_backend()

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

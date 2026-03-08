"""
Test 1: Verify collectors connect to game clients and forward data to the queue.

This test:
1. Starts the real queue manager on port 5555
2. Starts two WebSocket servers simulating:
   - Desktop game client telemetry (port 6790)
   - Game server for third-party collector (port 8081)
3. Starts the desktop and third-party collectors
4. Waits for collectors to connect to both the queue and the fake servers
5. Sends telemetry payloads from the fake servers
6. Verifies the queue manager received data by checking its log output
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import websockets

DESKTOP_TELEMETRY_PORT = 6790
GAME_SERVER_PORT = 8081
SEND_COUNT = 5

VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def start_process(script):
    return subprocess.Popen(
        [VENV_PYTHON, "-u", script],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


async def run_telemetry_server(port, server_name, collector_name, send_fn):
    """Run a WebSocket server, wait for a collector to connect, then send data."""
    connected = asyncio.Event()
    clients = set()

    async def handler(ws):
        clients.add(ws)
        print(f"[{server_name}] Collector connected!")
        connected.set()
        try:
            await ws.wait_closed()
        finally:
            clients.discard(ws)

    async with websockets.serve(handler, "localhost", port):
        print(f"[{server_name}] Listening on port {port}, waiting for collector...")

        try:
            await asyncio.wait_for(connected.wait(), timeout=15)
        except asyncio.TimeoutError:
            print(f"[{server_name}] TIMEOUT: No collector connected after 15s")
            return False

        await asyncio.sleep(0.5)
        await send_fn(clients, server_name)
        await asyncio.sleep(2)

    return True


async def send_desktop_data(clients, name):
    """Send desktop-style telemetry payloads."""
    now = lambda: datetime.now(timezone.utc).isoformat()

    msg = json.dumps({"type": "session_start", "timestamp": now(), "session_id": "test-desktop-001"})
    for ws in list(clients):
        await ws.send(msg)
    print(f"[{name}] Sent session_start")

    for i in range(SEND_COUNT):
        msg = json.dumps({
            "type": "snapshot", "timestamp": now(),
            "latency_ms": 15 + i, "paddle_y": 120.0 + i * 5, "collision_count": i
        })
        for ws in list(clients):
            await ws.send(msg)
        await asyncio.sleep(0.2)
    print(f"[{name}] Sent {SEND_COUNT} snapshots")

    msg = json.dumps({
        "type": "session_end", "timestamp": now(), "session_id": "test-desktop-001",
        "duration_ms": 30000, "final_score_player1": 5, "final_score_player2": 3
    })
    for ws in list(clients):
        await ws.send(msg)
    print(f"[{name}] Sent session_end")


async def send_server_data(clients, name):
    """Send game-server-style telemetry payloads."""
    now = lambda: datetime.now(timezone.utc).isoformat()

    msg = json.dumps({"type": "session_start", "timestamp": now(), "session_id": "test-server-001"})
    for ws in list(clients):
        await ws.send(msg)
    print(f"[{name}] Sent session_start")

    for i in range(SEND_COUNT):
        msg = json.dumps({
            "type": "snapshot", "timestamp": now(),
            "paddle_y_player1": 100.0 + i * 3, "paddle_y_player2": 200.0 - i * 2,
            "latency_ms_player1": 10 + i, "latency_ms_player2": 20 + i,
            "collision_count": i * 2, "score_player1": min(i, 5), "score_player2": min(i // 2, 5)
        })
        for ws in list(clients):
            await ws.send(msg)
        await asyncio.sleep(0.2)
    print(f"[{name}] Sent {SEND_COUNT} snapshots")

    msg = json.dumps({
        "type": "session_end", "timestamp": now(), "session_id": "test-server-001",
        "duration_ms": 45000, "final_score_player1": 5, "final_score_player2": 2
    })
    for ws in list(clients):
        await ws.send(msg)
    print(f"[{name}] Sent session_end")


async def main():
    print("=" * 60)
    print("TEST 1: Collectors -> Queue")
    print("=" * 60)

    # Step 1: Start queue manager
    print("\n[1] Starting queue manager...")
    qm = start_process("queue_manager.py")
    time.sleep(3)
    if qm.poll() is not None:
        print("  FAIL: Queue manager exited early")
        print(qm.stdout.read())
        return 1
    print("  Queue manager running.")

    # Step 2: Start collectors
    print("\n[2] Starting collectors...")
    desktop_proc = start_process("desktop_collector.py")
    thirdparty_proc = start_process("third_party_collector.py")
    time.sleep(2)
    print("  Collectors started.")

    # Step 3: Run telemetry servers and send data
    print("\n[3] Starting telemetry servers and sending data...")
    desktop_ok, server_ok = await asyncio.gather(
        run_telemetry_server(DESKTOP_TELEMETRY_PORT, "DESKTOP-SIM", "desktop_pong", send_desktop_data),
        run_telemetry_server(GAME_SERVER_PORT, "SERVER-SIM", "third_party_pong", send_server_data),
    )

    # Step 4: Wait for queue to flush
    print("\n[4] Waiting for queue manager to process data...")
    time.sleep(8)

    # Collect output
    for proc in [desktop_proc, thirdparty_proc]:
        proc.terminate()

    qm.terminate()
    qm_out = ""
    try:
        qm_out, _ = qm.communicate(timeout=5)
    except Exception:
        qm.kill()

    for proc in [desktop_proc, thirdparty_proc]:
        try:
            proc.communicate(timeout=3)
        except Exception:
            proc.kill()

    # Analyze queue manager output
    collector_connects = qm_out.count("Collector connected")
    batch_lines = [l for l in qm_out.split("\n") if "batch" in l.lower() or "Sent batch" in l]

    print("\n  Queue manager log (key lines):")
    for line in qm_out.strip().split("\n"):
        if any(kw in line.lower() for kw in ["collector connected", "sent batch", "final batch", "failed"]):
            print(f"    {line}")

    # Results
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Desktop telemetry server got collector:    {'YES' if desktop_ok else 'NO'}")
    print(f"Game server sim got collector:             {'YES' if server_ok else 'NO'}")
    print(f"Queue manager saw collector connections:   {collector_connects}")
    print(f"Queue manager sent batches:                {len(batch_lines)}")

    passed = desktop_ok and server_ok and collector_connects >= 2 and len(batch_lines) > 0
    print(f"\nTest 1 overall: {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

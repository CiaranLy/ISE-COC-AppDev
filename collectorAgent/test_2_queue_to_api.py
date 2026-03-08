"""
Test 2: Verify the queue manager sends data to the aggregator API.

This test:
1. Checks the remote backend is reachable
2. Starts the queue manager (which reads api_base_url from config.json)
3. Sends test data directly to the queue manager via TCP
4. Waits for the queue manager to flush the batch
5. Queries the backend API to verify the data was stored
"""

import json
import os
import socket
import subprocess
import sys
import time

import requests

from config_manager import config as app_config

API_BASE = app_config.get("api_base_url")
HEALTH_URL = API_BASE.rsplit("/api/v1", 1)[0] + "/health"
QUEUE_HOST = "localhost"
QUEUE_PORT = app_config.get("queue_port", 5555)
VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
HTTP_TIMEOUT = 60

TEST_SESSION = f"test-remote-{int(time.time())}"
TEST_POINTS = [
    {"collector_name": "test_collector", "content": 42.0, "unit": "test_metric_alpha",
     "timestamp": "2026-03-05T12:00:00+00:00", "session_id": TEST_SESSION},
    {"collector_name": "test_collector", "content": 99.5, "unit": "test_metric_beta",
     "timestamp": "2026-03-05T12:00:01+00:00", "session_id": TEST_SESSION},
    {"collector_name": "test_collector", "content": 7.0, "unit": "test_metric_gamma",
     "timestamp": "2026-03-05T12:00:02+00:00", "session_id": TEST_SESSION},
]


def check_backend():
    try:
        r = requests.get(HEALTH_URL, timeout=HTTP_TIMEOUT)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def send_to_queue(data_points):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((QUEUE_HOST, QUEUE_PORT))
    for dp in data_points:
        line = json.dumps(dp) + "\n"
        sock.sendall(line.encode("utf-8"))
    time.sleep(0.5)
    sock.close()


def query_graphs():
    try:
        r = requests.get(f"{API_BASE}/graphs", timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] API query failed: {e}")
    return []


def main():
    print("=" * 60)
    print("TEST 2: Queue -> Aggregator API (REMOTE)")
    print("=" * 60)
    print(f"API: {API_BASE}")
    print(f"Session ID: {TEST_SESSION}")

    # Step 1: Check backend
    print(f"\n[1] Checking backend at {HEALTH_URL} ...")
    if not check_backend():
        print("  FAIL: Remote backend is not reachable.")
        return 1
    print("  Backend is healthy.")

    # Step 2: Record pre-existing graphs
    print("\n[2] Checking pre-existing graphs...")
    pre_graphs = query_graphs()
    pre_units = {g["unit"] for g in pre_graphs}
    test_units = {dp["unit"] for dp in TEST_POINTS}
    print(f"  {len(pre_graphs)} existing graph(s).")

    # Step 3: Start queue manager
    print("\n[3] Starting queue manager...")
    qm_proc = subprocess.Popen(
        [VENV_PYTHON, "-u", "queue_manager.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(3)
    if qm_proc.poll() is not None:
        print(f"  FAIL: Queue manager exited early:\n{qm_proc.stdout.read()}")
        return 1
    print("  Queue manager started.")

    # Step 4: Send test data
    print(f"\n[4] Sending {len(TEST_POINTS)} test data points to queue...")
    try:
        send_to_queue(TEST_POINTS)
        print("  Data sent to queue.")
    except ConnectionRefusedError:
        print("  FAIL: Could not connect to queue manager")
        qm_proc.terminate()
        return 1

    # Step 5: Wait for flush + remote API round-trip
    flush_wait = 20
    print(f"\n[5] Waiting {flush_wait}s for queue manager to flush to remote API...")
    time.sleep(flush_wait)

    # Step 6: Query API
    print("\n[6] Querying remote API for test data...")
    graphs = query_graphs()

    found_units = {}
    for g in graphs:
        if g["unit"] in test_units:
            points = g.get("data_points", [])
            matching = [dp for dp in points if dp.get("session_id") == TEST_SESSION]
            if matching:
                found_units[g["unit"]] = {
                    "graph_id": g["id"],
                    "collector_name": g["collector_name"],
                    "data_point_count": len(matching),
                    "matched_by": "session_id",
                }
            elif points:
                expected_dp = next(dp for dp in TEST_POINTS if dp["unit"] == g["unit"])
                content_match = [dp for dp in points if abs(dp["content"] - expected_dp["content"]) < 0.01]
                if content_match:
                    found_units[g["unit"]] = {
                        "graph_id": g["id"],
                        "collector_name": g["collector_name"],
                        "data_point_count": len(content_match),
                        "matched_by": "content_value",
                    }

    for dp in TEST_POINTS:
        unit = dp["unit"]
        if unit in found_units:
            info = found_units[unit]
            print(f"  {unit}: FOUND (graph_id={info['graph_id']}, "
                  f"collector={info['collector_name']}, points={info['data_point_count']}, "
                  f"matched_by={info['matched_by']})")
        else:
            print(f"  {unit}: NOT FOUND")

    # Cleanup
    qm_proc.terminate()
    try:
        qm_out, _ = qm_proc.communicate(timeout=5)
        relevant = [l for l in qm_out.strip().split("\n")
                    if any(kw in l.lower() for kw in ["sent batch", "final batch", "failed", "collector connected", "request failed"])]
        if relevant:
            print("\n  Queue manager log (relevant lines):")
            for line in relevant[-10:]:
                print(f"    {line}")
    except Exception:
        qm_proc.kill()

    # Results
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    found = len(found_units)
    total = len(test_units)
    passed = found == total

    print(f"Unique test units sent:    {total}")
    print(f"Units found in API:        {found}")
    for unit in sorted(test_units):
        status = "PASS" if unit in found_units else "FAIL"
        print(f"  {unit}: {status}")
    print(f"\nQueue -> Remote API: {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

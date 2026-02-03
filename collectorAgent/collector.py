"""
Collector - Collects system metrics and sends to the Queue Manager.

The Queue Manager must be running first, otherwise this will error.

Usage:
    python collector.py                          # Uses config.json collector_name
    python collector.py --name my_custom_name    # Override collector name
"""

import argparse
import json
import signal
import sys
import time
from pathlib import Path

import psutil

from collector_lib import collect_all_metrics
from queue_client import QueueClient, QueueNotRunningError

# Load config
CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)


def main():
    parser = argparse.ArgumentParser(description="System metrics collector")
    parser.add_argument(
        "--name", "-n",
        default=config["collector_name"],
        help=f"Collector name (default: {config['collector_name']})"
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=config["collection_interval_seconds"],
        help=f"Collection interval in seconds (default: {config['collection_interval_seconds']})"
    )
    args = parser.parse_args()
    
    collector_name = args.name
    collection_interval = args.interval
    
    print("=" * 50)
    print("Collector Starting")
    print("=" * 50)
    print(f"Collector Name: {collector_name}")
    print(f"Collection Interval: {collection_interval}s")
    print("=" * 50)
    
    # Initialize CPU percent (first call always returns 0)
    psutil.cpu_percent(interval=None)
    
    # Try to connect to queue
    try:
        queue = QueueClient()
        queue.connect()
    except QueueNotRunningError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease start the Queue Manager first:")
        print("    python queue_manager.py")
        return 1
    
    # Handle graceful shutdown
    running = True
    
    def shutdown_handler(signum, frame):
        nonlocal running
        print("\n[Collector] Shutdown signal received...")
        running = False
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Main collection loop
    print("[Collector] Starting collection loop...")
    
    try:
        while running:
            try:
                # Collect all metrics
                data_points = collect_all_metrics(collector_name)
                
                # Send each data point to the queue
                for dp in data_points:
                    queue.send(dp.to_dict())
                
                print(f"[Collector] Sent {len(data_points)} data points")
                
            except QueueNotRunningError as e:
                print(f"[Collector] Lost connection to queue: {e}")
                print("[Collector] Attempting to reconnect...")
                
                # Try to reconnect
                try:
                    queue.close()
                    queue = QueueClient()
                    queue.connect()
                    print("[Collector] Reconnected!")
                except QueueNotRunningError:
                    print("[Collector] Reconnect failed. Queue Manager may have stopped.")
                    running = False
                    break
            
            # Wait for next collection interval
            time.sleep(collection_interval)
            
    except KeyboardInterrupt:
        print("\n[Collector] Interrupted by user")
    finally:
        queue.close()
    
    print("[Collector] Collector stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

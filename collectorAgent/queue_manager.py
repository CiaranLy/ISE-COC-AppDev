"""
Queue Manager - Runs independently and receives data from collectors.

Start this FIRST, then start collectors.

Features:
- Receives data from multiple collectors via TCP
- Batches and sends data to the backend API
- Tracks message acknowledgments
- Moves unacknowledged messages to Dead Letter Queue (DLQ) after 90 seconds

Usage:
    python queue_manager.py
"""

import json
import signal
import socket
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import List

import requests

from data_point import DataPoint
from dlq import DeadLetterQueue, PendingMessageTracker

# Load config
CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

HOST = config["queue_host"]
PORT = config["queue_port"]
API_BASE_URL = config["api_base_url"]
AGGREGATOR_ENDPOINT = f"{API_BASE_URL}/aggregator"
BATCH_SIZE = config["batch_size"]
FLUSH_INTERVAL = config["flush_interval_seconds"]
MAX_RETRIES = config["max_retries"]
RETRY_DELAY = config["retry_delay_seconds"]
ACK_TIMEOUT = config["ack_timeout_seconds"]
DLQ_FILE = config["dlq_file"]


class QueueManager:
    def __init__(self):
        self.queue: List[dict] = []
        self.queue_lock = threading.Lock()
        self.running = False
        self.server_socket = None
        
        # DLQ and acknowledgment tracking
        self.dlq = DeadLetterQueue(DLQ_FILE)
        self.pending_tracker = PendingMessageTracker(timeout_seconds=ACK_TIMEOUT)
        
    def send_data_point(self, data: dict) -> bool:
        """Send a single data point to the backend API with retries."""
        # Generate message ID for tracking
        message_id = str(uuid.uuid4())
        data_with_id = {**data, "message_id": message_id}
        
        # Track as pending
        self.pending_tracker.add(message_id, data)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    AGGREGATOR_ENDPOINT,
                    json=data_with_id,
                    timeout=30
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Check for acknowledgment
                    if response_data.get("acknowledged") and response_data.get("message_id") == message_id:
                        self.pending_tracker.acknowledge(message_id)
                        return True
                    else:
                        print(f"[Queue] Response missing acknowledgment for {message_id}")
                else:
                    print(f"[Queue] API returned {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"[Queue] Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        
        # Failed after all retries - will be caught by timeout checker
        return False

    def send_batch(self, batch: List[dict]) -> tuple:
        """Send a batch of data points. Returns (success_count, failure_count)."""
        success = 0
        failed = 0
        
        for data in batch:
            if self.send_data_point(data):
                success += 1
            else:
                failed += 1
        
        return success, failed

    def timeout_checker_loop(self):
        """Background thread that checks for timed-out messages and moves them to DLQ."""
        print(f"[Queue] Timeout checker started. Timeout: {ACK_TIMEOUT}s")
        
        while self.running:
            time.sleep(5)  # Check every 5 seconds
            
            # Get timed out messages
            timed_out = self.pending_tracker.get_timed_out()
            
            for message in timed_out:
                self.dlq.add(message, f"No acknowledgment received within {ACK_TIMEOUT} seconds")
            
            if timed_out:
                print(f"[Queue] Moved {len(timed_out)} message(s) to DLQ (timeout)")
                print(f"[Queue] DLQ size: {self.dlq.count()}, Pending: {self.pending_tracker.count()}")

    def sender_loop(self):
        """Background thread that sends batched data to the API."""
        print(f"[Queue] Sender started. Endpoint: {AGGREGATOR_ENDPOINT}")
        
        last_flush_time = time.time()
        
        while self.running:
            time.sleep(0.5)
            
            current_time = time.time()
            time_since_flush = current_time - last_flush_time
            
            with self.queue_lock:
                queue_size = len(self.queue)
                should_flush = (
                    queue_size >= BATCH_SIZE or 
                    (queue_size > 0 and time_since_flush >= FLUSH_INTERVAL)
                )
                
                if should_flush:
                    batch = self.queue.copy()
                    self.queue.clear()
                else:
                    batch = []
            
            if batch:
                success, failed = self.send_batch(batch)
                print(f"[Queue] Sent batch: {success} succeeded, {failed} failed")
                last_flush_time = current_time
        
        # Final flush
        with self.queue_lock:
            if self.queue:
                print(f"[Queue] Final flush: {len(self.queue)} items")
                success, failed = self.send_batch(self.queue)
                print(f"[Queue] Final batch: {success} succeeded, {failed} failed")
                self.queue.clear()

    def handle_client(self, client_socket: socket.socket, address):
        """Handle incoming data from a collector."""
        print(f"[Queue] Collector connected from {address}")
        
        buffer = ""
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                
                # Process complete JSON messages (newline-delimited)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data_point = json.loads(line)
                            with self.queue_lock:
                                self.queue.append(data_point)
                        except json.JSONDecodeError as e:
                            print(f"[Queue] Invalid JSON from {address}: {e}")
                            
        except Exception as e:
            print(f"[Queue] Error handling client {address}: {e}")
        finally:
            client_socket.close()
            print(f"[Queue] Collector disconnected from {address}")

    def start(self):
        """Start the queue manager server."""
        self.running = True
        
        # Start sender thread
        sender_thread = threading.Thread(target=self.sender_loop, daemon=True)
        sender_thread.start()
        
        # Start timeout checker thread
        timeout_thread = threading.Thread(target=self.timeout_checker_loop, daemon=True)
        timeout_thread.start()
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            
            print("=" * 60)
            print("Queue Manager Started")
            print("=" * 60)
            print(f"Listening on {HOST}:{PORT}")
            print(f"Backend: {AGGREGATOR_ENDPOINT}")
            print(f"Batch size: {BATCH_SIZE}, Flush interval: {FLUSH_INTERVAL}s")
            print(f"ACK timeout: {ACK_TIMEOUT}s")
            print(f"DLQ file: {DLQ_FILE}")
            if self.dlq.count() > 0:
                print(f"DLQ contains {self.dlq.count()} message(s) from previous session")
            print("=" * 60)
            print("Waiting for collectors...")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
                    
        except OSError as e:
            print(f"[Queue] Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def stop(self):
        """Stop the queue manager."""
        print("\n[Queue] Shutting down...")
        self.running = False
        
        # Move any remaining pending messages to DLQ
        timed_out = self.pending_tracker.get_timed_out()
        for message in timed_out:
            self.dlq.add(message, "Shutdown before acknowledgment received")
        
        print(f"[Queue] Final DLQ size: {self.dlq.count()}")


def main():
    manager = QueueManager()
    
    def shutdown_handler(signum, frame):
        manager.stop()
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    manager.start()
    print("[Queue] Queue Manager stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

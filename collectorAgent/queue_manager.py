"""
Queue Manager - Runs independently and receives data from collectors.

Start this FIRST, then start collectors.

Features:
- Receives data from multiple collectors via TCP
- Batches and sends data to the backend API
- Tracks message acknowledgments
- Moves unacknowledged messages to Dead Letter Queue (DLQ) after timeout

Usage:
    python queue_manager.py
"""

import json
import queue
import signal
import socket
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import requests

from config_manager import config as app_config
from data_point import DataPoint
from dlq import DeadLetterQueue, PendingMessageTracker
from log_config import get_logger

logger = get_logger("QueueManager")

RECV_BUFFER_SIZE = 4096
SENDER_POLL_INTERVAL_SECONDS = 0.5
TIMEOUT_CHECK_INTERVAL_SECONDS = 5
SERVER_LISTEN_BACKLOG = 5
SERVER_ACCEPT_TIMEOUT_SECONDS = 1.0
HTTP_REQUEST_TIMEOUT_SECONDS = 30
STARTUP_BANNER_WIDTH = 60

# Units that trigger an immediate flush of the current queue to the API
FLUSH_TRIGGER_UNITS = frozenset({
    "session_start",
    "session_duration_ms",
    "final_score_player1",
    "final_score_player2",
    "latency_ms",
    "paddle_y",
    "collision_count"
})

# Units that are critical and MUST be saved to DLQ if they fail
CRITICAL_UNITS = frozenset({
    "session_start",
    "session_duration_ms",
    "final_score_player1",
    "final_score_player2"
})


class QueueManager:
    def __init__(self):
        self.queue: List[dict] = []
        self.queue_lock = threading.Lock()
        self.running = False
        self._stop_event = threading.Event()
        self.server_socket = None
        self.executor = ThreadPoolExecutor(
            max_workers=app_config.get("num_sender_workers")
        )

        self.dlq = DeadLetterQueue(app_config.get("dlq_file"))
        self.pending_tracker = PendingMessageTracker(
            timeout_seconds=app_config.get("ack_timeout_seconds")
        )
        self._flush_requested = False
        self._batch_queue: queue.Queue = queue.Queue()
        self._sender_worker_thread = None

    def _aggregator_endpoint(self) -> str:
        return f"{app_config.get('api_base_url')}/aggregator"

    def send_data_point(self, data: dict) -> bool:
        """Send a single data point to the backend API with retries."""
        message_id = str(uuid.uuid4())
        data_with_id = {**data, "message_id": message_id}

        self.pending_tracker.add(message_id, data)
        max_retries = app_config.get("max_retries")
        retry_delay = app_config.get("retry_delay_seconds")

        for attempt in range(max_retries):
            if self._stop_event.is_set() and data.get("unit") not in CRITICAL_UNITS:
                # If we're stopping and this isn't critical, don't bother retrying
                return False

            try:
                response = requests.post(
                    self._aggregator_endpoint(),
                    json=data_with_id,
                    timeout=HTTP_REQUEST_TIMEOUT_SECONDS,
                )

                if response.status_code == 200:
                    try:
                        response_data = response.json()
                    except (ValueError, json.JSONDecodeError) as e:
                        logger.warning("API returned non-JSON for %s: %s", message_id, e)
                        continue
                    if response_data.get("acknowledged") and response_data.get("message_id") == message_id:
                        self.pending_tracker.acknowledge(message_id)
                        return True
                    else:
                        logger.warning("Response missing acknowledgment for %s", message_id)
                else:
                    logger.warning("API returned %d: %s", response.status_code, response.text)

            except requests.exceptions.RequestException as e:
                logger.warning("Request failed (attempt %d/%d): %s", attempt + 1, max_retries, e)

            if attempt < max_retries - 1:
                # Use a shorter sleep that checks for stop event
                for _ in range(int(retry_delay * 10)):
                    if self._stop_event.is_set() and data.get("unit") not in CRITICAL_UNITS:
                        return False
                    time.sleep(0.1)

        return False

    def send_batch(self, batch: List[dict]) -> tuple:
        """Send a batch of data points concurrently. Returns (success_count, failure_count)."""
        success = 0
        failed = 0

        futures = {self.executor.submit(self.send_data_point, data): data for data in batch}
        for future in as_completed(futures):
            try:
                if future.result():
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.error("Sender worker exception for batch item: %s", e, exc_info=True)

        return success, failed

    def timeout_checker_loop(self):
        """Background thread that checks for timed-out messages and moves them to DLQ."""
        ack_timeout = app_config.get("ack_timeout_seconds")
        logger.info("Timeout checker started. Timeout: %ss", ack_timeout)

        while not self._stop_event.is_set():
            time.sleep(TIMEOUT_CHECK_INTERVAL_SECONDS)

            timed_out = self.pending_tracker.get_timed_out()

            for message in timed_out:
                # Only save critical messages to DLQ on timeout
                if message.get("unit") in CRITICAL_UNITS:
                    self.dlq.add(
                        message,
                        f"No acknowledgment received within {ack_timeout} seconds",
                    )
                else:
                    logger.debug("Dropped stale snapshot %s after timeout", message.get("unit"))

            if timed_out:
                logger.warning(
                    "Processed %d timed-out message(s). Pending: %d",
                    len(timed_out), self.pending_tracker.count(),
                )

    def _sender_worker(self):
        """Worker that sends batches to the API. Runs in background so sender_loop never blocks."""
        while not self._stop_event.is_set() or not self._batch_queue.empty():
            try:
                batch = self._batch_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if batch is None:
                break
            success, failed = self.send_batch(batch)
            logger.info("Sent batch: %d succeeded, %d failed", success, failed)
            self._batch_queue.task_done()
        logger.debug("Sender worker thread finished")

    def sender_loop(self):
        """Background thread that batches data and passes to sender worker. Never blocks on HTTP."""
        logger.info("Sender started. Endpoint: %s", self._aggregator_endpoint())

        last_flush_time = time.time()

        while not self._stop_event.is_set():
            time.sleep(SENDER_POLL_INTERVAL_SECONDS)

            current_time = time.time()
            time_since_flush = current_time - last_flush_time
            batch_size = app_config.get("batch_size")
            flush_interval = app_config.get("flush_interval_seconds")

            with self.queue_lock:
                queue_size = len(self.queue)
                should_flush = (
                    self._flush_requested
                    or queue_size >= batch_size
                    or (queue_size > 0 and time_since_flush >= flush_interval)
                )
                if should_flush and queue_size > 0:
                    self._flush_requested = False
                    take_count = min(batch_size, queue_size)
                    batch = self.queue[:take_count]
                    del self.queue[:take_count]
                else:
                    batch = []

            if batch:
                self._batch_queue.put(batch)
                last_flush_time = current_time

        # Final flush of whatever is left in the local queue
        with self.queue_lock:
            if self.queue:
                logger.info("Queuing final batch: %d items", len(self.queue))
                self._batch_queue.put(self.queue.copy())
                self.queue.clear()

        # Signal sender worker to exit
        self._batch_queue.put(None)
        logger.debug("Sender loop finished")

    def handle_client(self, client_socket: socket.socket, address):
        """Handle incoming data from a collector."""
        logger.info("Collector connected from %s", address)
        client_socket.settimeout(1.0)

        MAX_BUFFER_BYTES = 1024 * 1024
        buffer = ""
        try:
            while not self._stop_event.is_set():
                try:
                    raw = client_socket.recv(RECV_BUFFER_SIZE)
                    if not raw:
                        break
                except socket.timeout:
                    continue

                try:
                    data = raw.decode('utf-8')
                except UnicodeDecodeError:
                    logger.error("Invalid UTF-8 from %s", address)
                    break

                buffer += data
                if len(buffer) > MAX_BUFFER_BYTES:
                    logger.error("Buffer exceeded %d bytes from %s", MAX_BUFFER_BYTES, address)
                    break

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data_point = json.loads(line)
                            with self.queue_lock:
                                self.queue.append(data_point)
                                if data_point.get("unit") in FLUSH_TRIGGER_UNITS:
                                    self._flush_requested = True
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON from %s: %s", address, e)

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error("Error handling client %s: %s", address, e)
        finally:
            try:
                client_socket.close()
            except OSError:
                pass
            logger.info("Collector disconnected from %s", address)

    def start(self):
        """Start the queue manager server."""
        self.running = True
        self._stop_event.clear()

        self._sender_worker_thread = threading.Thread(target=self._sender_worker, name="SenderWorker")
        self._sender_worker_thread.start()

        threading.Thread(target=self.sender_loop, name="SenderLoop").start()
        threading.Thread(target=self.timeout_checker_loop, name="TimeoutChecker").start()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            host = app_config.get("queue_host")
            port = app_config.get("queue_port")
            self.server_socket.bind((host, port))
            self.server_socket.listen(SERVER_LISTEN_BACKLOG)
            self.server_socket.settimeout(SERVER_ACCEPT_TIMEOUT_SECONDS)

            logger.info("=" * STARTUP_BANNER_WIDTH)
            logger.info("Queue Manager Started")
            logger.info("=" * STARTUP_BANNER_WIDTH)
            logger.info("Listening on %s:%s", host, port)
            logger.info("=" * STARTUP_BANNER_WIDTH)

            while not self._stop_event.is_set():
                try:
                    client_socket, address = self.server_socket.accept()
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True,
                    ).start()
                except socket.timeout:
                    continue
                except OSError:
                    if not self._stop_event.is_set():
                        raise

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error("Server error: %s", e)
        finally:
            self.stop()

    def stop(self):
        """Stop the queue manager."""
        if self._stop_event.is_set():
            return

        logger.info("Shutting down Queue Manager...")
        self._stop_event.set()
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        if self._sender_worker_thread and self._sender_worker_thread.is_alive():
            logger.info("Waiting for sender worker to finish flushing (max 10s)...")
            # We give them a window to finish legitimate in-flight HTTP requests
            self._sender_worker_thread.join(timeout=10.0)

        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
        except:
            self.executor.shutdown(wait=False)

        # Handle messages that are still pending (in-flight)
        unacked = self.pending_tracker.drain_all()
        critical_count = 0
        dropped_count = 0

        for message in unacked:
            if message.get("unit") in CRITICAL_UNITS:
                self.dlq.add(message, "Shutdown before acknowledgment received")
                critical_count += 1
            else:
                dropped_count += 1

        if critical_count > 0 or dropped_count > 0:
            logger.info("Shutdown cleanup: Saved %d critical messages to DLQ, dropped %d stale snapshots",
                        critical_count, dropped_count)

        logger.info("Final DLQ size: %d", self.dlq.count())
        logger.info("Queue Manager stopped")


def main():
    manager = QueueManager()

    def shutdown_handler(signum, frame):
        logger.debug("Received signal %d", signum)
        manager.stop()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        manager.start()
    except (KeyboardInterrupt, SystemExit):
        manager.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

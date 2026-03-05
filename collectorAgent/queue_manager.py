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


class QueueManager:
    def __init__(self):
        self.queue: List[dict] = []
        self.queue_lock = threading.Lock()
        self.running = False
        self.server_socket = None
        self.executor = ThreadPoolExecutor(
            max_workers=app_config.get("num_sender_workers")
        )

        self.dlq = DeadLetterQueue(app_config.get("dlq_file"))
        self.pending_tracker = PendingMessageTracker(
            timeout_seconds=app_config.get("ack_timeout_seconds")
        )

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
            try:
                response = requests.post(
                    self._aggregator_endpoint(),
                    json=data_with_id,
                    timeout=HTTP_REQUEST_TIMEOUT_SECONDS,
                )

                if response.status_code == 200:
                    response_data = response.json()

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
                time.sleep(retry_delay)

        return False

    def send_batch(self, batch: List[dict]) -> tuple:
        """Send a batch of data points concurrently. Returns (success_count, failure_count)."""
        success = 0
        failed = 0

        futures = {self.executor.submit(self.send_data_point, data): data for data in batch}
        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failed += 1

        return success, failed

    def timeout_checker_loop(self):
        """Background thread that checks for timed-out messages and moves them to DLQ."""
        ack_timeout = app_config.get("ack_timeout_seconds")
        logger.info("Timeout checker started. Timeout: %ss", ack_timeout)

        while self.running:
            time.sleep(TIMEOUT_CHECK_INTERVAL_SECONDS)

            timed_out = self.pending_tracker.get_timed_out()

            for message in timed_out:
                self.dlq.add(
                    message,
                    f"No acknowledgment received within {app_config.get('ack_timeout_seconds')} seconds",
                )

            if timed_out:
                logger.warning(
                    "Moved %d message(s) to DLQ (timeout). DLQ size: %d, Pending: %d",
                    len(timed_out), self.dlq.count(), self.pending_tracker.count(),
                )

    def sender_loop(self):
        """Background thread that sends batched data to the API."""
        logger.info("Sender started. Endpoint: %s", self._aggregator_endpoint())

        last_flush_time = time.time()

        while self.running:
            time.sleep(SENDER_POLL_INTERVAL_SECONDS)

            current_time = time.time()
            time_since_flush = current_time - last_flush_time
            batch_size = app_config.get("batch_size")
            flush_interval = app_config.get("flush_interval_seconds")

            with self.queue_lock:
                queue_size = len(self.queue)
                should_flush = (
                    queue_size >= batch_size
                    or (queue_size > 0 and time_since_flush >= flush_interval)
                )

                if should_flush:
                    batch = self.queue.copy()
                    self.queue.clear()
                else:
                    batch = []

            if batch:
                success, failed = self.send_batch(batch)
                logger.info("Sent batch: %d succeeded, %d failed", success, failed)
                last_flush_time = current_time

        with self.queue_lock:
            if self.queue:
                logger.info("Final flush: %d items", len(self.queue))
                success, failed = self.send_batch(self.queue)
                logger.info("Final batch: %d succeeded, %d failed", success, failed)
                self.queue.clear()

    def handle_client(self, client_socket: socket.socket, address):
        """Handle incoming data from a collector."""
        logger.info("Collector connected from %s", address)

        buffer = ""
        try:
            while self.running:
                data = client_socket.recv(RECV_BUFFER_SIZE).decode('utf-8')
                if not data:
                    break

                buffer += data

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data_point = json.loads(line)
                            with self.queue_lock:
                                self.queue.append(data_point)
                        except json.JSONDecodeError as e:
                            logger.warning("Invalid JSON from %s: %s", address, e)

        except Exception as e:
            logger.error("Error handling client %s: %s", address, e)
        finally:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            client_socket.close()
            logger.info("Collector disconnected from %s", address)

    def start(self):
        """Start the queue manager server."""
        self.running = True

        sender_thread = threading.Thread(target=self.sender_loop, daemon=True)
        sender_thread.start()

        timeout_thread = threading.Thread(target=self.timeout_checker_loop, daemon=True)
        timeout_thread.start()

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
            logger.info("Backend: %s", self._aggregator_endpoint())
            logger.info(
                "Batch size: %s, Flush interval: %ss",
                app_config.get("batch_size"), app_config.get("flush_interval_seconds"),
            )
            logger.info("Sender workers: %s", app_config.get("num_sender_workers"))
            logger.info("ACK timeout: %ss", app_config.get("ack_timeout_seconds"))
            logger.info("DLQ file: %s", app_config.get("dlq_file"))
            if self.dlq.count() > 0:
                logger.warning("DLQ contains %d message(s) from previous session", self.dlq.count())
            logger.info("=" * STARTUP_BANNER_WIDTH)
            logger.info("Waiting for collectors...")

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True,
                    )
                    client_thread.start()
                except socket.timeout:
                    continue

        except OSError as e:
            logger.error("Server error: %s", e)
        finally:
            if self.server_socket:
                self.server_socket.close()

    def stop(self):
        """Stop the queue manager."""
        logger.info("Shutting down...")
        self.running = False

        self.executor.shutdown(wait=True)

        timed_out = self.pending_tracker.get_timed_out()
        for message in timed_out:
            self.dlq.add(message, "Shutdown before acknowledgment received")

        logger.info("Final DLQ size: %d", self.dlq.count())


def main():
    manager = QueueManager()

    def shutdown_handler(signum, frame):
        manager.stop()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    manager.start()
    logger.info("Queue Manager stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

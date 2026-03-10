"""
Dead Letter Queue (DLQ) - Stores messages that failed to be acknowledged.

Messages are moved to the DLQ if:
1. The backend doesn't respond within the timeout period
2. The backend returns an error
3. The connection is lost before acknowledgment
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from log_config import get_logger
    _logger = get_logger("DLQ")
except ImportError:
    _logger = None


class DeadLetterQueue:
    """Manages the Dead Letter Queue for unacknowledged messages."""
    
    def __init__(self, dlq_file: str = "dead_letter_queue.json"):
        self.dlq_file = Path(__file__).parent / dlq_file
        self.lock = threading.Lock()
        self._load()
    
    def _load(self):
        """Load existing DLQ from file."""
        if self.dlq_file.exists():
            try:
                with open(self.dlq_file, "r") as f:
                    self.messages: List[dict] = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.messages = []
        else:
            self.messages = []
    
    def _save(self):
        """Persist DLQ to file. Atomic write to avoid corruption. Fails silently on disk errors."""
        tmp_path = self.dlq_file.with_suffix(".tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(self.messages, f, indent=2, default=str)
            os.replace(tmp_path, self.dlq_file)
        except OSError as e:
            if _logger:
                _logger.error("DLQ save failed (disk full or permission error): %s", e)
            else:
                print(f"[DLQ] Save failed: {e}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
    
    def add(self, message: dict, reason: str):
        """Add a message to the DLQ."""
        with self.lock:
            dlq_entry = {
                "original_message": message,
                "reason": reason,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "retry_count": 0
            }
            self.messages.append(dlq_entry)
            self._save()
            if _logger:
                _logger.info("DLQ message added: %s", reason)
            else:
                print(f"[DLQ] Message added: {reason}")
    
    def get_all(self) -> List[dict]:
        """Get all messages in the DLQ."""
        with self.lock:
            return self.messages.copy()
    
    def count(self) -> int:
        """Get the number of messages in the DLQ."""
        with self.lock:
            return len(self.messages)
    
    def remove(self, index: int) -> Optional[dict]:
        """Remove a message from the DLQ by index."""
        with self.lock:
            if 0 <= index < len(self.messages):
                message = self.messages.pop(index)
                self._save()
                return message
            return None
    
    def clear(self):
        """Clear all messages from the DLQ."""
        with self.lock:
            self.messages = []
            self._save()
            if _logger:
                _logger.info("DLQ cleared")
            else:
                print("[DLQ] Cleared all messages")
    
    def retry_all(self) -> List[dict]:
        """Get all messages for retry and clear the DLQ."""
        with self.lock:
            messages = [m["original_message"] for m in self.messages]
            self.messages = []
            self._save()
            return messages


class PendingMessageTracker:
    """Tracks messages waiting for acknowledgment."""
    
    def __init__(self, timeout_seconds: float = 90.0):
        self.timeout = timeout_seconds
        self.pending: Dict[str, dict] = {}  # message_id -> {message, sent_at}
        self.lock = threading.Lock()
    
    def add(self, message_id: str, message: dict):
        """Add a message to pending tracking."""
        with self.lock:
            self.pending[message_id] = {
                "message": message,
                "sent_at": datetime.now(timezone.utc)
            }
    
    def acknowledge(self, message_id: str) -> bool:
        """Mark a message as acknowledged. Returns True if found."""
        with self.lock:
            if message_id in self.pending:
                del self.pending[message_id]
                return True
            return False
    
    def get_timed_out(self) -> List[dict]:
        """Get and remove all messages that have timed out."""
        timed_out = []
        now = datetime.now(timezone.utc)
        
        with self.lock:
            expired_ids = []
            for msg_id, data in self.pending.items():
                elapsed = (now - data["sent_at"]).total_seconds()
                if elapsed >= self.timeout:
                    expired_ids.append(msg_id)
                    timed_out.append(data["message"])
            
            for msg_id in expired_ids:
                del self.pending[msg_id]
        
        return timed_out
    
    def drain_all(self) -> List[dict]:
        """Get and remove all pending messages (for shutdown)."""
        with self.lock:
            messages = [data["message"] for data in self.pending.values()]
            self.pending.clear()
        return messages
    
    def count(self) -> int:
        """Get the number of pending messages."""
        with self.lock:
            return len(self.pending)

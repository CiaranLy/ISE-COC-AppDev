# Dead Letter Queue (DLQ)

The Dead Letter Queue is a reliability mechanism that captures messages that fail to be processed successfully.

## What is a DLQ?

A Dead Letter Queue stores messages that couldn't be delivered or acknowledged within a specified time. Instead of losing data, failed messages are saved for later inspection, retry, or manual intervention.

## Why Use a DLQ?

| Problem | DLQ Solution |
|---------|--------------|
| Network timeout | Message saved, can retry later |
| Backend down | Messages accumulate in DLQ until backend recovers |
| Data corruption | Failed messages preserved for debugging |
| Lost acknowledgments | Unconfirmed messages captured |

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           QUEUE MANAGER                                     │
│                                                                             │
│   ┌──────────┐     ┌─────────────────┐     ┌──────────────────────────┐    │
│   │  Queue   │────▶│  Send to API    │────▶│  Wait for Acknowledgment │    │
│   └──────────┘     │  (with msg_id)  │     │  (90 second timeout)     │    │
│                    └─────────────────┘     └──────────────────────────┘    │
│                                                       │                     │
│                              ┌────────────────────────┼────────────────┐    │
│                              │                        │                │    │
│                              ▼                        ▼                │    │
│                    ┌──────────────────┐    ┌──────────────────┐        │    │
│                    │   ACK Received   │    │   No ACK (90s)   │        │    │
│                    │   ✓ Success      │    │   ✗ Timeout      │        │    │
│                    └──────────────────┘    └──────────────────┘        │    │
│                                                       │                │    │
│                                                       ▼                │    │
│                                            ┌──────────────────┐        │    │
│                                            │  Dead Letter     │        │    │
│                                            │  Queue (DLQ)     │        │    │
│                                            │                  │        │    │
│                                            │  Persisted to:   │        │    │
│                                            │  dlq.json        │        │    │
│                                            └──────────────────┘        │    │
│                                                                        │    │
└────────────────────────────────────────────────────────────────────────────┘
```

## Message Lifecycle

### 1. Message Sent
```python
# Queue Manager generates unique ID
message_id = uuid.uuid4()
data_with_id = {**data, "message_id": message_id}

# Track as pending
pending_tracker.add(message_id, data)

# Send to backend
requests.post("/aggregator", json=data_with_id)
```

### 2. Backend Acknowledges
```python
# Backend response
{
    "success": true,
    "acknowledged": true,
    "message_id": "abc-123-..."
}
```

### 3. Acknowledgment Received
```python
# Queue Manager marks as complete
pending_tracker.acknowledge(message_id)
# Message removed from pending tracking
```

### 4. Timeout (No Acknowledgment)
```python
# After 90 seconds with no ACK
timed_out = pending_tracker.get_timed_out()

# Move to DLQ
for message in timed_out:
    dlq.add(message, "No acknowledgment received within 90 seconds")
```

## DLQ File Format

Messages are persisted to `dead_letter_queue.json`:

```json
[
  {
    "original_message": {
      "collector_name": "office_pc",
      "content": 45.2,
      "unit": "cpu_percent",
      "timestamp": "2026-02-03T10:30:00+00:00"
    },
    "reason": "No acknowledgment received within 90 seconds",
    "added_at": "2026-02-03T10:31:30+00:00",
    "retry_count": 0
  }
]
```

## Configuration

In `config.json`:

```json
{
    "ack_timeout_seconds": 90,
    "dlq_file": "dead_letter_queue.json"
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `ack_timeout_seconds` | 90 | Seconds to wait for acknowledgment |
| `dlq_file` | `dead_letter_queue.json` | File to persist DLQ messages |

## Managing the DLQ

Use the `dlq_viewer.py` CLI tool:

```bash
# View all messages in DLQ
python dlq_viewer.py

# Show count only
python dlq_viewer.py --count

# Clear all messages (use with caution)
python dlq_viewer.py --clear

# Export messages for retry
python dlq_viewer.py --retry
```

### Example Output

```
Dead Letter Queue (2 messages)
============================================================

[0] Added: 2026-02-03T10:31:30+00:00
    Reason: No acknowledgment received within 90 seconds
    Message: {
        "collector_name": "office_pc",
        "content": 45.2,
        "unit": "cpu_percent",
        "timestamp": "2026-02-03T10:30:00+00:00"
    }

[1] Added: 2026-02-03T10:32:00+00:00
    Reason: Shutdown before acknowledgment received
    Message: {
        "collector_name": "office_pc",
        "content": 67.8,
        "unit": "memory_percent",
        "timestamp": "2026-02-03T10:30:05+00:00"
    }

============================================================
Total: 2 message(s)
```

## Components

### `dlq.py`

Contains two classes:

#### `DeadLetterQueue`
- Persists failed messages to JSON file
- Thread-safe with locking
- Methods: `add()`, `get_all()`, `count()`, `remove()`, `clear()`, `retry_all()`

#### `PendingMessageTracker`
- Tracks messages awaiting acknowledgment
- Checks for timeouts
- Methods: `add()`, `acknowledge()`, `get_timed_out()`, `count()`

### Integration in `queue_manager.py`

```python
class QueueManager:
    def __init__(self):
        # Initialize DLQ and tracker
        self.dlq = DeadLetterQueue(DLQ_FILE)
        self.pending_tracker = PendingMessageTracker(timeout_seconds=ACK_TIMEOUT)
    
    def timeout_checker_loop(self):
        """Background thread checking for timeouts every 5 seconds"""
        while self.running:
            time.sleep(5)
            timed_out = self.pending_tracker.get_timed_out()
            for message in timed_out:
                self.dlq.add(message, f"No acknowledgment within {ACK_TIMEOUT}s")
```

## Failure Scenarios

### Scenario 1: Backend Timeout
```
Collector → Queue Manager → POST /aggregator → [No Response]
                                    ↓
                            (90 seconds pass)
                                    ↓
                            Message → DLQ
```

### Scenario 2: Backend Error
```
Collector → Queue Manager → POST /aggregator → 500 Error
                                    ↓
                            (Retry 3 times)
                                    ↓
                            (Still failing)
                                    ↓
                            (90 seconds pass)
                                    ↓
                            Message → DLQ
```

### Scenario 3: Queue Manager Shutdown
```
Collector → Queue Manager → POST /aggregator → [Shutdown Signal]
                                    ↓
                            (Pending messages)
                                    ↓
                            All pending → DLQ
```

## Best Practices

1. **Monitor DLQ size** - A growing DLQ indicates problems
2. **Investigate reasons** - Check why messages are failing
3. **Retry periodically** - Export and reprocess when backend is healthy
4. **Don't ignore** - DLQ messages represent lost data if not handled
5. **Set appropriate timeout** - 90 seconds balances reliability vs. responsiveness

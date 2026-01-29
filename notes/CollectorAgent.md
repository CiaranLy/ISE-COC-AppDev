# Collector Agent

The Collector Agent is a distributed system for collecting system metrics and sending them to the backend API.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   Terminal 1                Terminal 2                Terminal 3                │
│   ──────────                ──────────                ──────────                │
│                                                                                 │
│   queue_manager.py          collector.py              collector.py              │
│        │                    --name pc1                --name pc2                │
│        │                         │                         │                    │
│        │◀─── TCP Connect ────────┤                         │                    │
│        │◀─── TCP Connect ──────────────────────────────────┤                    │
│        │                         │                         │                    │
│        │◀─── Data Points ────────┤                         │                    │
│        │◀─── Data Points ──────────────────────────────────┤                    │
│        │                                                                        │
│        ├─────── Batch POST ──────────▶ Backend API /aggregator                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Queue Manager (`queue_manager.py`)

The central hub that must be started **first**. It:

- Listens for TCP connections from collectors on `localhost:5555`
- Receives data points from multiple collectors
- Batches data for efficient API calls
- Sends batched data to the backend `/aggregator` endpoint

**Start command:**
```bash
python queue_manager.py
```

### 2. Collector (`collector.py`)

The script that runs on each machine you want to monitor. It:

- Connects to the Queue Manager via TCP
- Collects system metrics at regular intervals
- Sends data points to the queue
- **Errors if Queue Manager is not running**

**Start command:**
```bash
# Default name from config.json
python collector.py

# Custom collector name
python collector.py --name "office_pc"

# Custom name and interval
python collector.py --name "server_01" --interval 10
```

### 3. Queue Client (`queue_client.py`)

A client library that handles:

- TCP connection to the Queue Manager
- Sending JSON-encoded data points
- Raising `QueueNotRunningError` if queue is unavailable
- Automatic reconnection attempts

### 4. Collector Library (`collector_lib.py`)

Contains the metric collection functions using `psutil`:

| Function | Metric | Unit |
|----------|--------|------|
| `collect_cpu_percent()` | CPU usage | `cpu_percent` |
| `collect_memory_percent()` | RAM usage % | `memory_percent` |
| `collect_memory_used_mb()` | RAM used | `memory_mb` |
| `collect_disk_percent()` | Disk usage | `disk_percent` |
| `collect_all_metrics()` | All of the above | - |

### 5. Data Point (`data_point.py`)

A dataclass representing a single metric reading:

```python
@dataclass
class DataPoint:
    collector_name: str   # e.g., "office_pc"
    content: float        # e.g., 45.2
    unit: str             # e.g., "cpu_percent"
    timestamp: datetime   # UTC timestamp
```

## Configuration (`config.json`)

```json
{
    "api_base_url": "http://localhost:8000",
    "collector_name": "default_collector",
    "collection_interval_seconds": 5.0,
    "batch_size": 10,
    "flush_interval_seconds": 5.0,
    "max_retries": 3,
    "retry_delay_seconds": 2.0,
    "queue_host": "localhost",
    "queue_port": 5555
}
```

| Setting | Description |
|---------|-------------|
| `api_base_url` | Backend API URL |
| `collector_name` | Default name for collectors |
| `collection_interval_seconds` | How often to collect metrics |
| `batch_size` | Data points per batch before sending |
| `flush_interval_seconds` | Max time before force-sending partial batch |
| `max_retries` | API retry attempts on failure |
| `retry_delay_seconds` | Wait time between retries |
| `queue_host` | Queue Manager host address |
| `queue_port` | Queue Manager TCP port |

## Data Flow

1. **Collection**: `collector.py` calls `collect_all_metrics()` every N seconds
2. **Queueing**: Each `DataPoint` is serialized to JSON and sent via TCP to the Queue Manager
3. **Batching**: Queue Manager accumulates data points until batch is full or timeout
4. **Sending**: Batch is POSTed to `/aggregator` endpoint
5. **Storage**: Backend creates/finds collector and graph, stores data point

```
psutil.cpu_percent() → DataPoint → JSON → TCP → Queue → Batch → POST /aggregator → Database
```

## Error Handling

### Queue Not Running

If a collector starts without the Queue Manager running:

```
[ERROR] Queue Manager is not running at localhost:5555. Start it first with: python queue_manager.py

Please start the Queue Manager first:
    python queue_manager.py
```

### Lost Connection

If the Queue Manager stops while a collector is running:

1. Collector detects broken connection
2. Attempts to reconnect
3. If reconnect fails, collector stops gracefully

### API Failures

- Queue Manager retries failed API calls (configurable)
- Failed data points are logged but not re-queued

## Usage Example

```bash
# Terminal 1: Start the queue manager
cd collectorAgent
python queue_manager.py

# Terminal 2: Start a collector for this machine
python collector.py --name "dev_laptop"

# Terminal 3: Start another collector (could be on a different machine)
python collector.py --name "production_server" --interval 10
```

## File Structure

```
collectorAgent/
├── queue_manager.py    # Queue server (start first)
├── collector.py        # Metric collector (start after queue)
├── queue_client.py     # TCP client library
├── collector_lib.py    # psutil metric functions
├── data_point.py       # DataPoint dataclass
├── config.json         # Configuration
└── requirements.txt    # Dependencies (psutil, requests)
```

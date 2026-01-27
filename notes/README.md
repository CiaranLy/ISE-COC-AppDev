# ISE-COC System Monitoring Tool

Data collection and monitoring platform for tracking system metrics from various sources.

## How It Works

The system is built around three core concepts that work together:

1.  **Collectors ("The Source")**
    *   These are the devices or systems you are monitoring (e.g., "Office PC", "Warehouse Sensor").
    *   Each collector is unique and acts as a container for all the data it generates.
    *   Collectors are created automatically when data is first submitted.

2.  **Graphs ("The Definition")**
    *   These define *what* kind of data can be collected (e.g., "CPU Usage", "Temperature", "RAM Used").
    *   A single graph (like "CPU Usage") is defined once globally and can be used by *every* collector.
    *   Graphs are created automatically when data is first submitted with a new collector name and unit.
    *   Think of these as the labels on a chart axis.

3.  **Data ("The Readings")**
    *   This is where everything connects. A Data point says: *"Collector X reported a value of Y for Graph Z at Time T."*
    *   For example:
        *   Collector: "Office PC"
        *   Graph: "CPU Usage" (unit: "%")
        *   Data: "45%"
    *   Later, the same collector can report:
        *   Collector: "Office PC"
        *   Graph: "Temperature" (unit: "°C")
        *   Data: "65°C"

**Conceptual View:**
```
Office PC (Collector)
├──> Reports "CPU Usage" (Graph) -----> Value: 45% (Data)
├──> Reports "CPU Usage" (Graph) -----> Value: 50% (Data)
└──> Reports "Temperature" (Graph) ---> Value: 60°C (Data)

Warehouse Sensor (Collector)
└──> Reports "Temperature" (Graph) ---> Value: 22°C (Data)
```

## Quick Start

```bash
# Setup
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python setup_db.py

# Run
uvicorn main:app --reload
```

Visit http://localhost:8000/docs

## API Endpoints

### POST /aggregator
The main data ingestion endpoint. Automatically creates collectors and graphs as needed.

**Request:**
```json
{
  "collector_name": "temp_sensor_01",
  "content": 23.5,
  "unit": "celsius",
  "timestamp": "2026-01-27T14:30:00"  // optional, defaults to now
}
```

**Response:**
```json
{
  "success": true,
  "collector_id": 1,
  "graph_id": 1,
  "data_id": 1,
  "message": "Data ingested successfully"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/aggregator \
  -H "Content-Type: application/json" \
  -d '{
    "collector_name": "temp_sensor_01",
    "content": 23.5,
    "unit": "celsius"
  }'
```

### GET /graphs
Retrieve all available graphs.

**Response:**
```json
[
  {
    "id": 1,
    "name": "temp_sensor_01",
    "unit": "celsius"
  },
  {
    "id": 2,
    "name": "humidity_sensor",
    "unit": "percent"
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/graphs
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## Database Schema

### Collectors Table
Stores data sources 
```sql
CREATE TABLE collectors (
    id INTEGER PRIMARY KEY,
    display_name VARCHAR(255) UNIQUE NOT NULL,
    time_created DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Fields:**
- `id` - Auto-incrementing primary key
- `display_name` - Unique name for the collector (e.g., "Warehouse Sensor A", "Office PC #1")
- `time_created` - When the collector was registered

### Graphs Table
Stores definitions for types of metrics (e.g., CPU, RAM)

```sql
CREATE TABLE graphs (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    unit VARCHAR(50) NOT NULL
);
```

**Fields:**
- `id` - Auto-incrementing primary key
- `name` - Name of the metric (e.g., "CPU Usage", "RAM Usage")
- `unit` - Unit of measurement (e.g., "%", "MB", "°C")

### Data Table
Stores time-series metrics from collectors

```sql
CREATE TABLE data (
    id INTEGER PRIMARY KEY,
    collector_id INTEGER NOT NULL,
    graph_id INTEGER NOT NULL,
    timestamp_utc DATETIME DEFAULT CURRENT_TIMESTAMP,
    content FLOAT NOT NULL,
    FOREIGN KEY (collector_id) REFERENCES collectors(id) ON DELETE CASCADE,
    FOREIGN KEY (graph_id) REFERENCES graphs(id) ON DELETE CASCADE
);
```

**Fields:**
- `id` - Auto-incrementing primary key
- `collector_id` - Foreign key to collectors table
- `graph_id` - Foreign key to graphs table (identifies what the data is)
- `timestamp_utc` - When the metric was collected (auto-generated or provided)
- `content` - The metric value

### Relationships

**One-to-Many:** Collector → Data
- One collector can have many data points
- Deleting a collector deletes all its data (CASCADE)

**One-to-Many:** Graph → Data
- One graph definition is used by many data points across different collectors
- Deleting a graph deletes all associated data (CASCADE)

## Usage Flow

### First Data Submission
```bash
# Submit data from a new collector
curl -X POST http://127.0.0.1:8000/aggregator \
  -H "Content-Type: application/json" \
  -d '{
    "collector_name": "office_temp",
    "content": 21.5,
    "unit": "celsius"
  }'

# System automatically:
# 1. Creates collector "office_temp" (id: 1)
# 2. Creates graph "office_temp" with unit "celsius" (id: 1)
# 3. Creates data entry linking them (id: 1)
```

### Subsequent Data from Same Collector
```bash
# Submit more data from the same collector
curl -X POST http://127.0.0.1:8000/aggregator \
  -H "Content-Type: application/json" \
  -d '{
    "collector_name": "office_temp",
    "content": 22.1,
    "unit": "celsius"
  }'

# System:
# 1. Finds existing collector "office_temp" (id: 1)
# 2. Finds existing graph "office_temp" (id: 1)
# 3. Creates new data entry (id: 2) with new timestamp
```

### Different Collector
```bash
# Submit data from a different collector
curl -X POST http://127.0.0.1:8000/aggregator \
  -H "Content-Type: application/json" \
  -d '{
    "collector_name": "warehouse_humidity",
    "content": 55.0,
    "unit": "percent"
  }'

# System:
# 1. Creates new collector "warehouse_humidity" (id: 2)
# 2. Creates new graph "warehouse_humidity" (id: 2)
# 3. Creates data entry (id: 3)
```

## Repository Pattern

All database operations go through repositories for clean separation:

**Available Repositories:**
- `CollectorRepository` - Manage collectors
- `GraphRepository` - Manage metric definitions
- `DataRepository` - Manage time-series data

**Base Methods (all repos have these):**
- `create(**kwargs)` - Create new record
- `get_by_id(id)` - Get by ID
- `get_all(limit=1000)` - Get all records
- `delete(id)` - Delete by ID

**Collector-specific:**
- `find_by_display_name(name)` - Find collector by name

**Graph-specific:**
- `find_by_name(name)` - Find graph by name

**Data-specific:**
- `find_by_collector_and_graph(collector_id, graph_id, limit)` - Get data for a collector

## Configuration

Edit `backend/config.py`:

```python
DATABASE_URL = "sqlite+aiosqlite:///./database_ise_coc.db"
DB_ECHO = False  # Set True for SQL query logging
API_TITLE = "Data Collector API"
API_VERSION = "1.0.0"
```

## Project Structure

```
backend/
├── config.py                # Configuration
├── main.py                  # FastAPI app with endpoints
├── setup_db.py             # Database initialization
├── requirements.txt        # Python dependencies
├── database_ise_coc.db     # SQLite database (created on setup)
│
├── schemas/                # Pydantic models
│   ├── __init__.py
│   └── schema.py          # API request/response schemas
│
└── DB/                     # Database layer
    ├── __init__.py
    ├── database.py         # Async engine & session management
    │
    ├── models/             # SQLAlchemy ORM models
    │   ├── __init__.py
    │   ├── base.py        # DeclarativeBase
    │   ├── collector.py   # Collector model
    │   ├── data.py        # Data model
    │   └── graph.py       # Graph model
    │
    └── repositories/       # Data access layer
        ├── __init__.py
        ├── base.py        # AsyncRepository (CRUD operations)
        ├── collector_repository.py
        ├── data_repository.py
        └── graph_repository.py
```

## Code Style

All imports use full folder paths for consistency:
```python
# Good
from DB.models.collector import Collector
from DB.repositories.graph_repository import GraphRepository

# Avoid
from .collector import Collector
from ..repositories.graph_repository import GraphRepository
```

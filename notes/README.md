# ISE-COC System Monitoring Tool

Data collection and monitoring platform for tracking system metrics from various sources.

## How It Works

The system is built around three core concepts that work together:

1.  **Collectors ("The Source")**
    *   These are the devices or systems you are monitoring (e.g., "Office PC", "Warehouse Sensor").
    *   Each collector is unique and acts as a container for all the data it generates.

2.  **Graph Types ("The Definition")**
    *   These define *what* kind of data can be collected (e.g., "CPU Usage", "Temperature", "RAM Used").
    *   A single graph type (like "CPU Usage") is defined once globally and can be used by *every* collector.
    *   Think of these as the labels on a chart axis.

3.  **Data ("The Readings")**
    *   This is where everything connects. A Data point says: *"Collector X reported a value of Y for Graph Type Z at Time T."*
    *   For example:
        *   Collector: "Office PC"
        *   Graph Type: "CPU Usage"
        *   Data: "45%"
    *   Later, the same collector can report:
        *   Collector: "Office PC"
        *   Graph Type: "Temperature"
        *   Data: "65°C"

**Conceptual View:**
```
Office PC (Collector)
├──> Reports "CPU Usage" (GraphType) -----> Value: 45% (Data)
├──> Reports "CPU Usage" (GraphType) -----> Value: 50% (Data)
└──> Reports "Temperature" (GraphType) ---> Value: 60°C (Data)

Warehouse Sensor (Collector)
└──> Reports "Temperature" (GraphType) ---> Value: 22°C (Data)
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

### GraphTypes Table
Stores definitions for types of metrics (e.g., CPU, RAM)

```sql
CREATE TABLE graph_types (
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
    graph_type_id INTEGER NOT NULL,
    timestamp_utc DATETIME DEFAULT CURRENT_TIMESTAMP,
    content FLOAT NOT NULL,
    FOREIGN KEY (collector_id) REFERENCES collectors(id) ON DELETE CASCADE,
    FOREIGN KEY (graph_type_id) REFERENCES graph_types(id) ON DELETE CASCADE
);
```

**Fields:**
- `id` - Auto-incrementing primary key
- `collector_id` - Foreign key to collectors table
- `graph_type_id` - Foreign key to graph_types table (identifies what the data is)
- `timestamp_utc` - When the metric was collected
- `content` - The metric value

### Relationships

**One-to-Many:** Collector → Data
- One collector can have many data points
- Deleting a collector deletes all its data (CASCADE)

**One-to-Many:** GraphType → Data
- One graph type definition is used by many data points across different collectors
- Deleting a graph type deletes all associated data (CASCADE)

## API Endpoints

### Quick Test in Browser

**Option 1: Interactive Docs (Best for Testing)**
```
http://localhost:8000/docs
```
Click any endpoint → "Try it out" → Fill values → "Execute"

**Option 2: Browser URLs (GET endpoints only)**
```
http://localhost:8000/collectors
http://localhost:8000/graph_types
http://localhost:8000/collector/1
http://localhost:8000/data?collector_id=1
http://localhost:8000/health
```

**Option 3: Using curl (for POST endpoints)**
```bash
# Create graph types (seeded automatically, but you can add more)
curl -X POST "http://localhost:8000/create_graph_type?name=Disk%20Usage&unit=%25"

# Create collectors
curl -X POST "http://localhost:8000/create_collector?display_name=Warehouse_Sensor_A"

# Add data (referencing seeded graph types: 1=CPU, 2=RAM)
curl -X POST "http://localhost:8000/create_data?collector_id=1&graph_type_id=1&content=75.5"
curl -X POST "http://localhost:8000/create_data?collector_id=1&graph_type_id=2&content=8192"

# View data
curl "http://localhost:8000/data?collector_id=1"
```

### Endpoint Reference

**Graph Types:**
- `POST /create_graph_type?name=Name&unit=Unit` - Create/Get metric definition
- `GET /graph_types` - List all available metric types

**Collectors:**
- `POST /create_collector?display_name=Name` - Create collector
- `GET /collectors` - List all collectors  
- `GET /collector/{id}` - Get specific collector

**Data:**
- `POST /create_data?collector_id=1&graph_type_id=1&content=75.5` - Add data point
- `GET /data?collector_id=1&graph_type_id=1&limit=100` - Get data

## Usage Examples

### Python Code

```python
from DB.database import AsyncSessionLocal
from DB.repositories import CollectorRepository, DataRepository, GraphTypeRepository

async def example():
    async with AsyncSessionLocal() as session:
        collector_repo = CollectorRepository(session)
        data_repo = DataRepository(session)
        graph_type_repo = GraphTypeRepository(session)
        
        # 1. Get or create Graph Types
        cpu = await graph_type_repo.get_or_create(name="CPU Usage", unit="%")
        ram = await graph_type_repo.get_or_create(name="RAM Usage", unit="MB")
        
        # 2. Create collector
        sensor = await collector_repo.create(display_name="Warehouse Sensor A")
        
        # 3. Add CPU data
        await data_repo.create(
            collector_id=sensor.id,
            graph_type_id=cpu.id,
            content=75.5
        )
        
        # 4. Add RAM data
        await data_repo.create(
            collector_id=sensor.id,
            graph_type_id=ram.id,
            content=8192.0
        )
        
        # 5. Query recent CPU data
        cpu_data = await data_repo.find_by_collector(
            collector_id=sensor.id,
            graph_type_id=cpu.id,
            limit=100
        )
        
        await session.commit()
```

## Repository Pattern

All database operations go through repositories for clean separation:

**Available Repositories:**
- `CollectorRepository` - Manage collectors
- `GraphTypeRepository` - Manage metric definitions
- `DataRepository` - Manage time-series data

**Base Methods (all repos have these):**
- `create(**kwargs)` - Create new record
- `get_by_id(id)` - Get by ID
- `get_all(limit=1000)` - Get all records
- `delete(id)` - Delete by ID

**Data-specific:**
- `find_by_collector(collector_id, graph_type_id, limit)` - Get data for a collector

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
├── database_ise_coc.db     # SQLite database
│
└── DB/                      # Database layer
    ├── __init__.py
    ├── database.py         # Async engine & session management
    │
    ├── models/             # SQLAlchemy ORM models
    │   ├── __init__.py
    │   ├── base.py        # DeclarativeBase
    │   ├── collector.py   # Collector model
    │   ├── data.py        # Data model
    │   └── graph_type.py  # GraphType model
    │
    └── repositories/       # Data access layer
        ├── __init__.py
        ├── base.py        # AsyncRepository (CRUD operations)
        ├── collector_repository.py
        ├── data_repository.py
        └── graph_type_repository.py
```
